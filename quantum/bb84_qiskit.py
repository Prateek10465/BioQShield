"""BB84 transmission on real Qiskit circuits (Aer), producing the same `Transmission`
object as the numpy simulator, so sifting, QBER and key-length code are shared.

One 1-qubit circuit per photon (bit and basis are different for every qubit, so there
is nothing to share between circuits):

    Alice : X if bit=1, then H if basis=X                       prepare |0>,|1>,|+>,|->
    Eve   : (only on intercepted photons)
            H if her basis=X, measure -> clbit 0, then H again   intercept-resend
    Bob   : H if basis=X, measure -> clbit 1

Channel / detector noise is an Aer readout error: each measurement result flips with
probability `noise`, matching the numpy model's "Bob's outcome flips" assumption.

The numpy simulator in `bb84.py` remains the engine for big sweeps. Use this one for
a few thousand qubits and for showing the circuits. Both give the same statistics.
"""
from __future__ import annotations

import numpy as np

from .bb84 import Transmission


def qiskit_available() -> bool:
    try:
        import qiskit  # noqa: F401
        import qiskit_aer  # noqa: F401
    except Exception:
        return False
    return True


def build_circuit(bit: int, alice_basis: int, bob_basis: int, eve_basis: int | None, name: str = "q"):
    """The circuit for one photon. `eve_basis=None` means Eve does not touch this one."""
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(1, 2, name=name)  # clbit 0 = Eve's result, clbit 1 = Bob's result
    if bit:
        qc.x(0)
    if alice_basis:
        qc.h(0)
    qc.barrier()
    if eve_basis is not None:
        if eve_basis:
            qc.h(0)
        qc.measure(0, 0)  # her measurement collapses the photon
        qc.barrier()
        if eve_basis:
            qc.h(0)  # she resends what she saw, encoded in her own basis
        qc.barrier()
    if bob_basis:
        qc.h(0)
    qc.measure(0, 1)
    return qc


def transmit_qiskit(
    n: int,
    noise: float = 0.02,
    eve_rate: float = 0.0,
    eve_start: float = 0.0,
    rng: np.random.Generator | None = None,
    chunk: int = 512,
) -> Transmission:
    """Send `n` photons through Qiskit circuits. Same arguments as `bb84.transmit`."""
    if not qiskit_available():
        raise RuntimeError("Qiskit is not installed: pip install qiskit qiskit-aer")
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, ReadoutError

    rng = rng or np.random.default_rng()
    a_bits = rng.integers(0, 2, n, dtype=np.uint8)
    a_bases = rng.integers(0, 2, n, dtype=np.uint8)
    e_bases = rng.integers(0, 2, n, dtype=np.uint8)
    b_bases = rng.integers(0, 2, n, dtype=np.uint8)
    intercepted = (rng.random(n) < eve_rate) & (np.arange(n) >= int(eve_start * n))

    kwargs = {}
    if noise > 0:
        nm = NoiseModel()
        nm.add_all_qubit_readout_error(ReadoutError([[1 - noise, noise], [noise, 1 - noise]]))
        kwargs["noise_model"] = nm
    sim = AerSimulator(**kwargs)

    b_bits = np.empty(n, dtype=np.uint8)
    for start in range(0, n, chunk):
        stop = min(n, start + chunk)
        circuits = [
            build_circuit(
                int(a_bits[i]), int(a_bases[i]), int(b_bases[i]),
                int(e_bases[i]) if intercepted[i] else None, name=f"q{i}",
            )
            for i in range(start, stop)
        ]
        seed = int(rng.integers(0, 2**31 - 1))
        result = sim.run(circuits, shots=1, seed_simulator=seed).result()
        for k in range(stop - start):
            key = next(iter(result.get_counts(k)))  # bitstring "<bob><eve>", clbit 1 on the left
            b_bits[start + k] = int(key[0])

    return Transmission(
        n=n,
        alice_bits=a_bits,
        alice_bases=a_bases,
        bob_bases=b_bases,
        bob_bits=b_bits,
        intercepted=intercepted,
        eve_knows=intercepted & (e_bases == a_bases),  # same basis: she read the bit exactly
        intensities=None,
        photon_numbers=None,
    )
