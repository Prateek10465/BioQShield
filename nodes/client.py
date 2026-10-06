"""Alice's authenticated client for the public channel to Bob.

Every call is signed; every reply must be signed too and bound to the request it answers.
Calls go through the link service, which is where an eavesdropper would sit.
"""
from __future__ import annotations

import httpx

from .common import AuthError, Config, ProtocolError, mac_ok, seal
from .store import Store


class BobClient:
    def __init__(self, store: Store, cfg: Config, sid: str):
        self.store, self.cfg, self.sid = store, cfg, sid
        self.seq = 0
        self.http = httpx.Client(timeout=120)

    def close(self) -> None:
        self.http.close()

    def call(self, kind: str, payload: dict) -> dict:
        self.seq += 1
        kid, key = self.store.latest_auth_key()
        envelope = seal(kid, key, self.sid, self.seq, kind, payload)
        try:
            r = self.http.post(f"{self.cfg.channel_url}/public/bob/proto/{kind}", json=envelope)
        except httpx.HTTPError as e:
            raise ProtocolError(f"cannot reach Bob through the link: {e}") from e
        try:
            body = r.json()
        except ValueError as e:
            raise ProtocolError(f"unreadable reply from Bob (HTTP {r.status_code})") from e
        if r.status_code == 401:
            raise AuthError(f"Bob rejected our '{kind}' message: {body.get('error', 'authentication failed')}")
        if r.status_code >= 400:
            raise ProtocolError(f"Bob refused '{kind}': {body.get('error', body)}")
        reply_key = self.store.get_auth_key(body.get("kid"))
        if reply_key is None or not mac_ok(body, reply_key):
            raise AuthError(f"Bob's reply to '{kind}' failed authentication: it was altered on the wire")
        if body["sid"] != self.sid or body["seq"] != self.seq or body["kind"] != kind + "_reply":
            raise AuthError(f"Bob's reply to '{kind}' does not match the request")
        return body["payload"]
