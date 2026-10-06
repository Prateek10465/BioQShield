"""AES-256-GCM encryption of a (synthetic) patient record with the QKD-derived key."""
from __future__ import annotations

import hashlib
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Synthetic demo data only -- clearly marked as required
DEMO_RECORD = {
    "patient_id": "PT-2048",
    "patient_name": "Synthetic Patient",
    "department": "Cardiology",
    "record_type": "Clinical Summary",
    "diagnosis": "Synthetic demo diagnosis: Hypertension with sinus rhythm",
    "prescription": "Synthetic demo prescription: Metformin 500 mg, Amlodipine 5 mg",
    "hospital": "Apollo Hospital · Chennai Main Branch",
    "network_node": "AQ-CHN-01",
    "disclaimer": "SYNTHETIC DEMONSTRATION DATA",
}


def derive_aes_key(secret_key_bytes: bytes) -> bytes:
    """Compress the privacy-amplified secret to exactly 32 bytes."""
    return hashlib.sha256(b"qkd-health-link/v1" + secret_key_bytes).digest()


def key_fingerprint(aes_key: bytes) -> str:
    """Short public label so Alice and Bob can show their keys match without revealing them."""
    return hashlib.sha256(b"fingerprint" + aes_key).hexdigest()[:12]


def encrypt_record(aes_key: bytes, record: dict | None = None) -> dict:
    record = record or DEMO_RECORD
    plaintext = json.dumps(record, indent=2).encode()
    nonce = os.urandom(12)
    ct = AESGCM(aes_key).encrypt(nonce, plaintext, b"qkd-health-link")
    return {"plaintext": plaintext.decode(), "nonce": nonce, "ciphertext": ct}


def decrypt_record(aes_key: bytes, nonce: bytes, ciphertext: bytes) -> str | None:
    try:
        return AESGCM(aes_key).decrypt(nonce, ciphertext, b"qkd-health-link").decode()
    except InvalidTag:
        return None
