"""Encoding of the QKD dialogue for the public channel, shared by Alice and Bob."""
from __future__ import annotations

import base64
import hashlib

import numpy as np

from .common import ProtocolError


def pack_ints(values) -> str:
    return base64.b64encode(np.asarray(values, dtype="<i4").tobytes()).decode()


def unpack_ints(text: str) -> np.ndarray:
    try:
        return np.frombuffer(base64.b64decode(text.encode()), dtype="<i4").astype(np.int64)
    except (ValueError, TypeError) as e:
        raise ProtocolError("malformed index list") from e


def request_to_wire(request: tuple) -> dict:
    """Bob's Cascade/verification request -> JSON-safe dict."""
    if request[0] == "parities":
        return {"op": "parities", "sets": [pack_ints(s) for s in request[1]]}
    if request[0] == "verify":
        return {"op": "verify", "seed": int(request[1]), "bits": int(request[2])}
    raise ProtocolError(f"unknown request {request[0]!r}")


def request_from_wire(wire: dict) -> tuple:
    try:
        if wire["op"] == "parities":
            return ("parities", [unpack_ints(s) for s in wire["sets"]])
        if wire["op"] == "verify":
            return ("verify", int(wire["seed"]), int(wire["bits"]))
    except (KeyError, TypeError, ValueError) as e:
        raise ProtocolError("malformed error-correction request") from e
    raise ProtocolError("unknown error-correction request")


def request_cost(request: tuple) -> int:
    """Bits of the secret key a request reveals: one per parity, one per verification tag bit."""
    return len(request[1]) if request[0] == "parities" else int(request[2])


def key_confirmation(auth_key: bytes, data_keys: list[bytes]) -> str:
    """A hash both sides compute over everything they derived. It reveals nothing useful about
    the keys, but differs if even one bit of any key differs."""
    h = hashlib.sha256(b"mediqkd/v1/confirm")
    h.update(hashlib.sha256(auth_key).digest())
    for k in data_keys:
        h.update(hashlib.sha256(k).digest())
    return h.hexdigest()
