"""Where a hospital's encryption keys come from: the one place hardware plugs in.

The hospital application never touches qubits. It asks a *key source* for 256-bit keys:

    sender   (Alice)  refill(want)    put fresh keys into the local pool, or raise KeyUnavailable
    receiver (Bob)    obtain(key_id)  return the key with that id, once, or None

Two implementations ship:

    bb84     our own simulated BB84 link (nodes/session.py runs the protocol, nodes/channel.py
             is the simulated fibre). Keys arrive in the local pool through the protocol.
    etsi014  a real or stub key-management entity (KME) over the ETSI GS QKD 014 REST API,
             which is how commercial QKD systems hand keys to applications.

Set QKD_KEY_SOURCE=etsi014 plus QKD_KME_URL / QKD_KME_API_KEY / QKD_SELF_SAE / QKD_PEER_SAE
and the same hospital app runs on top of a vendor device instead of the simulator.

The ETSI client follows the published endpoint and message shapes (status, enc_keys,
dec_keys; key_ID + base64 key). It has only been run against the stub KME in this repo,
not against vendor hardware, and a production link must use mutual TLS
(QKD_KME_CERT / QKD_KME_KEY / QKD_KME_CA).
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Callable, Protocol

import httpx

from .store import Store

KEY_BYTES = 32  # AES-256


class KeyUnavailable(Exception):
    """No secure key can be obtained right now (eavesdropper suspected, link down, KME empty...)."""

    def __init__(self, reason: str, detail: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


class KeySourceError(Exception):
    """The key source answered, but with an error that retrying will not fix (bad request, bad credentials)."""


@dataclass
class Refill:
    added: int
    detail: dict = field(default_factory=dict)


class SenderKeySource(Protocol):
    name: str

    def refill(self, want: int, actor: str = "system") -> Refill: ...


class ReceiverKeySource(Protocol):
    name: str

    def obtain(self, key_id: str) -> bytes | None: ...


# --------------------------------------------------------------------------- #
# ETSI GS QKD 014 client
# --------------------------------------------------------------------------- #
class Etsi014Client:
    """Minimal client for the key-delivery REST API of a KME."""

    def __init__(self, http):
        # `http` is anything with .get/.post returning httpx-style responses: an httpx.Client
        # pointed at the KME, or a Starlette TestClient in tests.
        self.http = http

    def _call(self, method: str, path: str, **kw):
        try:
            r = getattr(self.http, method)(path, **kw)
        except httpx.HTTPError as e:
            raise KeyUnavailable(f"key management entity unreachable ({type(e).__name__})") from e
        if r.status_code == 503:
            raise KeyUnavailable(_message(r) or "key management entity has no key available")
        if r.status_code in (401, 403):
            raise KeySourceError("key management entity rejected our credentials")
        if r.status_code >= 400:
            raise KeySourceError(f"key management entity refused the request: {_message(r) or r.status_code}")
        return r.json()

    def status(self, slave_sae: str) -> dict:
        return self._call("get", f"/api/v1/keys/{slave_sae}/status")

    def enc_keys(self, slave_sae: str, number: int, size: int = KEY_BYTES * 8) -> list[tuple[str, bytes]]:
        """Master SAE: ask for `number` fresh keys shared with `slave_sae`."""
        body = self._call("post", f"/api/v1/keys/{slave_sae}/enc_keys", json={"number": number, "size": size})
        return [_parse_key(k) for k in body.get("keys", [])]

    def dec_keys(self, master_sae: str, key_id: str) -> bytes | None:
        """Slave SAE: fetch the key the master was given under `key_id`. The KME hands it out once."""
        try:
            r = self.http.post(f"/api/v1/keys/{master_sae}/dec_keys", json={"key_IDs": [{"key_ID": key_id}]})
        except httpx.HTTPError as e:
            raise KeyUnavailable(f"key management entity unreachable ({type(e).__name__})") from e
        if r.status_code == 400:
            return None  # unknown or already delivered
        if r.status_code == 503:
            raise KeyUnavailable(_message(r) or "key management entity unavailable")
        if r.status_code >= 400:
            raise KeySourceError(f"key management entity refused the request: {_message(r) or r.status_code}")
        keys = r.json().get("keys", [])
        return _parse_key(keys[0])[1] if keys else None


def _message(r) -> str:
    try:
        return str(r.json().get("message", ""))[:200]
    except ValueError:
        return ""


def _parse_key(entry: dict) -> tuple[str, bytes]:
    key = base64.b64decode(entry["key"])
    if len(key) != KEY_BYTES:
        raise KeySourceError(f"expected a {KEY_BYTES * 8}-bit key, got {len(key) * 8} bits")
    return str(entry["key_ID"]), key


def build_kme_http(url: str, api_key: str, timeout: float = 10.0) -> httpx.Client:
    """httpx client for a KME. Mutual TLS if QKD_KME_CERT / QKD_KME_KEY (and QKD_KME_CA) are set."""
    env = os.environ.get
    cert = (env("QKD_KME_CERT"), env("QKD_KME_KEY")) if env("QKD_KME_CERT") and env("QKD_KME_KEY") else None
    verify = env("QKD_KME_CA") or True
    headers = {"X-API-Key": api_key} if api_key else {}
    return httpx.Client(base_url=url, headers=headers, timeout=timeout, cert=cert, verify=verify)


class Etsi014Sender:
    name = "etsi014"

    def __init__(self, client: Etsi014Client, store: Store, peer_sae: str, ttl: int):
        self.client, self.store, self.peer_sae, self.ttl = client, store, peer_sae, ttl

    def refill(self, want: int, actor: str = "system") -> Refill:
        keys = self.client.enc_keys(self.peer_sae, want)
        if not keys:
            raise KeyUnavailable("key management entity returned no keys")
        self.store.add_keys([(kid, "etsi014", i, key) for i, (kid, key) in enumerate(keys)], self.ttl)
        return Refill(len(keys), {"source": "etsi014", "peer": self.peer_sae})


class Etsi014Receiver:
    name = "etsi014"

    def __init__(self, client: Etsi014Client, master_sae: str):
        self.client, self.master_sae = client, master_sae

    def obtain(self, key_id: str) -> bytes | None:
        return self.client.dec_keys(self.master_sae, key_id)


# --------------------------------------------------------------------------- #
# Simulated BB84 link
# --------------------------------------------------------------------------- #
class Bb84Sender:
    """Alice: run a BB84 session; the protocol itself stores the new keys in her pool."""

    name = "bb84"

    def __init__(self, run_session: Callable[[str], dict]):
        self._run = run_session

    def refill(self, want: int, actor: str = "system") -> Refill:
        result = self._run(actor)
        if result["status"] != "ok":
            raise KeyUnavailable(result["reason"], result)
        return Refill(result["keys_added"], result)


class Bb84Receiver:
    """Bob: the protocol already put the keys in his pool; consume one by id."""

    name = "bb84"

    def __init__(self, store: Store):
        self.store = store

    def obtain(self, key_id: str) -> bytes | None:
        return self.store.consume_key(key_id)
