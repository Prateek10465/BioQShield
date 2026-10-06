"""Encrypt a file or text record with one key from the QKD key pool (AES-256-GCM).

Each key is used exactly once. The key id travels in the clear (it is just a label);
the file name, type, note and a SHA-256 of the content travel *inside* the ciphertext,
so someone watching the wire learns only the approximate size.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .common import b64d, b64e

MAX_BYTES = 5 * 1024 * 1024


def _pack(meta: dict, data: bytes) -> bytes:
    head = json.dumps(meta).encode()
    return len(head).to_bytes(4, "big") + head + data


def _unpack(blob: bytes) -> tuple[dict, bytes]:
    n = int.from_bytes(blob[:4], "big")
    return json.loads(blob[4 : 4 + n]), blob[4 + n :]


def seal_message(key: bytes, key_id: str, data: bytes, filename: str, mime: str, note: str) -> dict:
    meta = {
        "filename": filename,
        "mime": mime,
        "note": note,
        "sha256": hashlib.sha256(data).hexdigest(),
        "sent_at": time.time(),
    }
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, _pack(meta, data), key_id.encode())
    return {"key_id": key_id, "nonce": b64e(nonce), "ciphertext": b64e(ct)}


def open_message(key: bytes, key_id: str, nonce_b64: str, ct_b64: str) -> tuple[dict, bytes]:
    """Raises cryptography.exceptions.InvalidTag if the key is wrong or the data was altered."""
    blob = AESGCM(key).decrypt(b64d(nonce_b64), b64d(ct_b64), key_id.encode())
    meta, data = _unpack(blob)
    if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
        raise ValueError("content hash mismatch")
    return meta, data
