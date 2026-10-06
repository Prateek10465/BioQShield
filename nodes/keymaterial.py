"""Turn a session's privacy-amplified secret into usable keys. Alice and Bob run the same code.

The first 256 bits become the next *authentication* key (this is how QKD replenishes the
secret that authenticates the public channel). Every further full 256-bit chunk becomes
one AES-256 key for the pool. Labels keep the two uses cryptographically separate.
"""
from __future__ import annotations

import hashlib

import numpy as np

from quantum.postprocess import bits_to_bytes

CHUNK = 256
MIN_NET_KEY_BITS = 2 * CHUNK  # one authentication key plus at least one data key


def _derive(label: bytes, chunk: np.ndarray) -> bytes:
    return hashlib.sha256(b"mediqkd/v1/" + label + b"/" + bits_to_bytes(chunk)).digest()


def split_final_key(bits: np.ndarray) -> tuple[bytes, list[bytes]]:
    """Returns (next_auth_key, [aes_key, ...])."""
    auth = _derive(b"auth", bits[:CHUNK])
    n_data = (len(bits) - CHUNK) // CHUNK
    data = [_derive(b"data", bits[CHUNK + i * CHUNK : CHUNK + (i + 1) * CHUNK]) for i in range(n_data)]
    return auth, data
