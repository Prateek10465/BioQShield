"""The quantum link, behind a two-method interface per side.

Alice prepares and sends qubits; Bob chooses detector bases and reads outcomes. Nothing
else in the project knows how that happens. Here the "fibre" is the link service, which
simulates Eve, noise and Bob's detectors over HTTP.

To use real photonic hardware, replace these two classes with ones that drive your
transmitter and detector, and keep the method signatures. The rest of the protocol
(sifting, error correction, privacy amplification, key pool) runs unchanged.
"""
from __future__ import annotations

import httpx
import numpy as np

from quantum.channel_sim import pack_bits, unpack_bits

from .common import ProtocolError


class AliceLink:
    """Alice's transmitter."""

    def __init__(self, channel_url: str):
        self.url = channel_url

    def send(self, sid: str, bits: np.ndarray, bases: np.ndarray) -> None:
        """Encode bits[i] in bases[i] (0 = Z, 1 = X) and send all qubits."""
        body = {"n": int(len(bits)), "bits": pack_bits(bits), "bases": pack_bits(bases)}
        try:
            r = httpx.post(f"{self.url}/quantum/{sid}/send", json=body, timeout=60)
        except httpx.HTTPError as e:
            raise ProtocolError(f"quantum link unreachable: {e}") from e
        if r.status_code != 200:
            raise ProtocolError(f"quantum link refused the transmission: {r.text[:120]}")


class BobLink:
    """Bob's detector."""

    def __init__(self, channel_url: str):
        self.url = channel_url

    def measure(self, sid: str, bases: np.ndarray) -> np.ndarray:
        """Measure each received qubit i in bases[i] and return the outcomes."""
        try:
            r = httpx.post(
                f"{self.url}/quantum/{sid}/measure",
                json={"n": int(len(bases)), "bases": pack_bits(bases)},
                timeout=60,
            )
        except httpx.HTTPError as e:
            raise ProtocolError(f"quantum link unreachable: {e}") from e
        if r.status_code != 200:
            raise ProtocolError(f"no qubits to measure for session {sid}")
        return unpack_bits(r.json()["bits"], len(bases))
