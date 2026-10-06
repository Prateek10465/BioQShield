"""Shared plumbing for the three services: config, signed envelopes, error types.

Every message on the *public* channel (everything except the qubits) travels in a signed
envelope. The MAC covers the key id, session id, sequence number, message kind, a
timestamp and the whole payload, so a message that is altered, forged or replayed is
rejected. This is how real QKD systems work: the classical channel must be authenticated
with a pre-shared secret, and each session's fresh QKD key replenishes that secret.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class AuthError(Exception):
    """A public-channel message failed authentication (altered, forged, replayed or stale)."""


class ProtocolError(Exception):
    """The other side refused or failed a protocol step."""


# --------------------------------------------------------------------------- #
# Configuration (environment variables, so Docker and run_all.py share one path)
# --------------------------------------------------------------------------- #
DEFAULT_SECRET = "mediqkd-dev-preshared-secret-CHANGE-ME"


def bootstrap_key(secret: str) -> bytes:
    """Turn the pre-shared secret (64 hex chars, or any passphrase) into a 32-byte key."""
    if len(secret) == 64:
        try:
            return bytes.fromhex(secret)
        except ValueError:
            pass
    return hashlib.sha256(b"mediqkd-auth-bootstrap/v1" + secret.encode()).digest()


@dataclass(frozen=True)
class Config:
    role: str
    data_dir: Path
    channel_url: str  # how Alice and Bob reach the link service
    bob_url: str  # how the link service reaches Bob
    bob_public_url: str  # what a browser should open
    channel_public_url: str
    alice_public_url: str
    auth_bootstrap: bytes
    uses_default_secret: bool
    # --- hospital nodes (Alice / Bob) ---
    name: str = ""  # display name of this hospital
    peer_name: str = ""
    master_key: bytes = b""  # encrypts keys and records at rest, keys the audit chain
    key_source: str = "bb84"  # "bb84" (simulated link) or "etsi014" (a vendor KME)
    kme_url: str = ""  # ETSI GS QKD 014 endpoint of this site's KME
    kme_api_key: str = ""
    self_sae: str = ""  # this application's SAE id at the KME
    peer_sae: str = ""
    key_ttl: int = 3600  # seconds an unused key stays valid
    qubits: int = 16384  # qubits per BB84 session
    admin_password: str = ""
    demo_users: bool = False
    clinician_password: str = ""
    auditor_password: str = ""


def load_master_key(data_dir: Path) -> bytes:
    """QKD_MASTER_KEY (64 hex chars) if set, else a key generated once into data_dir/master.key.

    The file fallback keeps `python scripts/run_all.py` working with zero setup. In a real
    deployment, inject the key from a secret manager or an HSM instead.
    """
    raw = os.environ.get("QKD_MASTER_KEY", "").strip()
    if raw:
        try:
            key = bytes.fromhex(raw)
        except ValueError:
            key = b""
        if len(key) != 32:
            raise ValueError("QKD_MASTER_KEY must be 64 hex characters (32 bytes)")
        return key
    path = data_dir / "master.key"
    if path.exists():
        return bytes.fromhex(path.read_text().strip())
    data_dir.mkdir(parents=True, exist_ok=True)
    key = os.urandom(32)
    path.write_text(key.hex())
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def load_config(role: str) -> Config:
    env = os.environ.get
    secret = env("QKD_AUTH_KEY", DEFAULT_SECRET)
    data_dir = Path(env("QKD_DATA_DIR", "data")) / role
    hospital = role in ("alice", "bob")
    default_name = {"alice": "Hospital A", "bob": "Hospital B"}.get(role, "")
    default_peer = {"alice": "Hospital B", "bob": "Hospital A"}.get(role, "")
    return Config(
        role=role,
        data_dir=data_dir,
        channel_url=env("QKD_CHANNEL_URL", "http://127.0.0.1:8003").rstrip("/"),
        bob_url=env("QKD_BOB_URL", "http://127.0.0.1:8002").rstrip("/"),
        bob_public_url=env("QKD_BOB_PUBLIC_URL", "http://localhost:8002").rstrip("/"),
        channel_public_url=env("QKD_CHANNEL_PUBLIC_URL", "http://localhost:8003").rstrip("/"),
        alice_public_url=env("QKD_ALICE_PUBLIC_URL", "http://localhost:8001").rstrip("/"),
        auth_bootstrap=bootstrap_key(secret),
        uses_default_secret=secret == DEFAULT_SECRET,
        name=env("QKD_HOSPITAL_NAME", default_name),
        peer_name=env("QKD_PEER_NAME", default_peer),
        master_key=load_master_key(data_dir) if hospital else b"",
        key_source=env("QKD_KEY_SOURCE", "bb84").lower(),
        kme_url=env("QKD_KME_URL", "").rstrip("/"),
        kme_api_key=env("QKD_KME_API_KEY", ""),
        self_sae=env("QKD_SELF_SAE", {"alice": "hospital-a", "bob": "hospital-b"}.get(role, "")),
        peer_sae=env("QKD_PEER_SAE", {"alice": "hospital-b", "bob": "hospital-a"}.get(role, "")),
        key_ttl=int(env("QKD_KEY_TTL", "3600")),
        qubits=int(env("QKD_QUBITS", "16384")),
        admin_password=env("QKD_ADMIN_PASSWORD", ""),
        demo_users=env("QKD_DEMO_USERS", "") in ("1", "true", "yes"),
        clinician_password=env("QKD_CLINICIAN_PASSWORD", ""),
        auditor_password=env("QKD_AUDITOR_PASSWORD", ""),
    )


# --------------------------------------------------------------------------- #
# Encoding helpers
# --------------------------------------------------------------------------- #
def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode()


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode())


# --------------------------------------------------------------------------- #
# Signed envelopes
# --------------------------------------------------------------------------- #
FIELDS = ("kid", "sid", "seq", "kind", "ts", "payload")


def canonical(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def seal(kid: str, key: bytes, sid: str, seq: int, kind: str, payload: dict) -> dict:
    body = {"kid": kid, "sid": sid, "seq": seq, "kind": kind, "ts": int(time.time()), "payload": payload}
    return {**body, "mac": hmac.new(key, canonical(body), hashlib.sha256).hexdigest()}


def mac_ok(envelope: dict, key: bytes) -> bool:
    try:
        body = {f: envelope[f] for f in FIELDS}
        expected = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
        return hmac.compare_digest(str(envelope["mac"]), expected)
    except (KeyError, TypeError):
        return False


@dataclass
class Opened:
    kid: str
    sid: str
    seq: int
    kind: str
    payload: dict


def open_envelope(
    envelope,
    lookup: Callable[[str], bytes | None],
    seen: dict | None = None,
    max_skew: int = 300,
) -> Opened:
    """Check an incoming envelope. Raises AuthError if it is not authentic and fresh.

    `lookup(kid)` returns the auth key for that key id (or None). `seen` maps a session
    id to the highest sequence number accepted so far, which blocks replays.
    """
    if not isinstance(envelope, dict) or any(f not in envelope for f in (*FIELDS, "mac")):
        raise AuthError("malformed envelope")
    key = lookup(str(envelope["kid"]))
    if key is None:
        raise AuthError("unknown key id")
    if not mac_ok(envelope, key):
        raise AuthError("bad MAC: the message was altered or forged")
    sid, seq, ts = envelope["sid"], envelope["seq"], envelope["ts"]
    if not isinstance(sid, str) or not isinstance(seq, int) or not isinstance(ts, (int, float)):
        raise AuthError("malformed envelope")
    if abs(time.time() - ts) > max_skew:
        raise AuthError("stale timestamp")
    if seen is not None:
        if seq <= seen.get(sid, 0):
            raise AuthError("replayed or out-of-order message")
        seen[sid] = seq
        if len(seen) > 2000:  # keep memory bounded: forget the oldest sessions
            for old in list(seen)[:500]:
                seen.pop(old, None)
    return Opened(envelope["kid"], sid, seq, envelope["kind"], envelope["payload"])
