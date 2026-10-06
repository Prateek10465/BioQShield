"""BB84 on real Qiskit circuits (Aer simulator) for a small number of qubits.

The numpy simulator in bb84.py is what scales; this module shows the same protocol
as actual quantum circuits, one circuit per qubit:

    Alice:  X if bit=1, then H if basis=X        (state preparation)
    Eve:    H if her basis=X, measure, (resend by re-preparing the measured bit)
    Bob:    H if basis=X, measure
"""
from __future__ import annotations

import numpy as np


def run_qiskit_bb84(
    n: int = 12, eve: bool = False, noise: float = 0.0, seed: int | None = None
) -> dict:
    # Imported lazily: qiskit takes a second or two to import.
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, ReadoutError

    rng = np.random.default_rng(seed)
    a_bits = rng.integers(0, 2, n)
    a_bases = rng.integers(0, 2, n)
    e_bases = rng.integers(0, 2, n)
    b_bases = rng.integers(0, 2, n)

    sim_kwargs = {}
    if noise > 0:
        nm = NoiseModel()
        nm.add_all_qubit_readout_error(ReadoutError([[1 - noise, noise], [noise, 1 - noise]]))
        sim_kwargs["noise_model"] = nm
    sim = AerSimulator(**sim_kwargs)
    sim_seed = int(rng.integers(0, 2**31 - 1))

    circuits = []
    for i in range(n):
        # qubit 0: Alice's qubit, classical bit 0: Eve's result, classical bit 1: Bob's result
        qc = QuantumCircuit(1, 2, name=f"q{i}")
        if a_bits[i]:
            qc.x(0)
        if a_bases[i]:
            qc.h(0)
        qc.barrier()
        if eve:
            if e_bases[i]:
                qc.h(0)
            qc.measure(0, 0)  # Eve's measurement collapses the qubit to |result>
            qc.barrier()
            # Eve resends what she saw, encoded in her own basis. The collapsed qubit
            # already holds her result in the Z basis, so re-encoding is just an H.
            if e_bases[i]:
                qc.h(0)
            qc.barrier()
        if b_bases[i]:
            qc.h(0)
        qc.measure(0, 1)
        circuits.append(qc)

    result = sim.run(circuits, shots=1, seed_simulator=sim_seed).result()
    rows = []
    for i in range(n):
        # counts key is a bitstring "<bob><eve>" (clbit 1 on the left)
        key = next(iter(result.get_counts(i)))
        b_bit = int(key[0])
        kept = bool(a_bases[i] == b_bases[i])
        rows.append(
            {
                "i": i,
                "alice_bit": int(a_bits[i]),
                "alice_basis": "X" if a_bases[i] else "Z",
                "eve_basis": ("X" if e_bases[i] else "Z") if eve else None,
                "bob_basis": "X" if b_bases[i] else "Z",
                "bob_bit": b_bit,
                "kept": kept,
                "error": bool(kept and b_bit != a_bits[i]),
            }
        )

    kept_rows = [r for r in rows if r["kept"]]
    qber = (sum(r["error"] for r in kept_rows) / len(kept_rows)) if kept_rows else None
    return {
        "n": n,
        "eve": eve,
        "noise": noise,
        "circuit_ascii": str(circuits[0].draw(output="text", fold=120)),
        "rows": rows,
        "kept": len(kept_rows),
        "qber": qber,
    }


if __name__ == "__main__":
    # CLI used by the API: python -m quantum.qiskit_demo '{"n": 12, "eve": false}'
    # Runs in its own process because Qiskit 2.x can segfault when circuits are built
    # from several different worker threads in turn (it dies, the web server must not).
    import json
    import sys

    print(json.dumps(run_qiskit_bb84(**json.loads(sys.argv[1]))))
