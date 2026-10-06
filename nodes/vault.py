"""Encryption at rest for a hospital node: key material, patient records, audit chain.

One 32-byte master key per node (never stored in the database) derives two sub-keys:
a data key (AES-256-GCM, used to seal key material and records) and an audit key
(HMAC-SHA256, used to chain the audit log). Every sealed value is bound to the row it
belongs to through the AES-GCM associated data, so a blob copied into another row
fails to open.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultError(Exception):
    """A sealed value could not be opened: wrong master key, wrong row, or tampered data."""


def _subkey(master: bytes, label: bytes) -> bytes:
    return hmac.new(master, b"mediqkd/vault/v1/" + label, hashlib.sha256).digest()


class Vault:
    def __init__(self, master_key: bytes):
        if len(master_key) != 32:
            raise ValueError("master key must be 32 bytes")
        self._aes = AESGCM(_subkey(master_key, b"data"))
        self.audit_key = _subkey(master_key, b"audit")

    def seal(self, plaintext: bytes, aad: str) -> str:
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, plaintext, aad.encode())
        return base64.b64encode(nonce + ct).decode()

    def open(self, blob: str, aad: str) -> bytes:
        try:
            raw = base64.b64decode(blob.encode())
            return self._aes.decrypt(raw[:12], raw[12:], aad.encode())
        except (InvalidTag, ValueError) as e:
            raise VaultError("cannot open sealed value (wrong key, wrong row, or altered data)") from e
