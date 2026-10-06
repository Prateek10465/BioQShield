"""Alice's key pool policy: one-time keys, expiry, rotation, refill on demand.

    acquire   take a fresh key for one record; refill from the key source if the pool is empty
    finish    a key that has been used (or failed in use) is zeroised and never offered again
    rotate    expire every unused key now, on both sides, so keys made before an incident
              (a suspected eavesdropper, a staff change) can no longer be used
    maintain  zeroise keys whose time-to-live ran out, and log it

Keys closer than MIN_TTL seconds to expiry are not handed out: Bob's clock may already
consider them expired, and a key that Bob refuses is a wasted key.
"""
from __future__ import annotations

import threading
import time
import uuid

from .audit import AuditLog
from .client import BobClient
from .common import Config
from .keysource import KeyUnavailable, SenderKeySource
from .store import Store

MIN_TTL = 60
REFILL_WANT = 8  # keys requested from a KME per refill (a BB84 session decides its own yield)


class KeyManager:
    def __init__(self, store: Store, source: SenderKeySource, audit: AuditLog, cfg: Config, now=time.time):
        self.store, self.source, self.audit, self.cfg, self._now = store, source, audit, cfg, now
        self._refill_lock = threading.Lock()

    def maintain(self) -> list[str]:
        expired = self.store.expire_due(self._now())
        if expired:
            self.audit.record("system", "keys_expired", count=len(expired), key_ids=expired[:20])
        return expired

    def acquire(self, actor: str) -> tuple[str, bytes]:
        """Returns (key_id, key). Raises KeyUnavailable if no secure key can be had right now."""
        self.maintain()
        got = self.store.reserve_key(self._now(), MIN_TTL)
        if got:
            return got
        self.refill(actor)
        got = self.store.reserve_key(self._now(), MIN_TTL)
        if got:
            return got
        raise KeyUnavailable("no usable key after refilling")

    def refill(self, actor: str, force: bool = False):
        """Top the pool up. Concurrent callers share one refill: the second finds keys already there.

        `force` makes new keys even if the pool is not empty (the operator's "make keys now").
        """
        with self._refill_lock:
            if not force and self.store.available_count(self._now(), MIN_TTL) > 0:
                return None
            return self.source.refill(REFILL_WANT, actor)

    def finish(self, key_id: str, revoke_at_peer: bool = False) -> None:
        """Destroy our copy. If the key may have been exposed without Bob using it (the message
        was blocked or altered), also tell Bob to destroy his, so a message an attacker held
        back cannot be delivered later under a key Alice has already given up on."""
        self.store.finish_key(key_id, self._now())
        if revoke_at_peer and self.source.name == "bb84":
            client = BobClient(self.store, self.cfg, "rev-" + uuid.uuid4().hex[:10])
            try:
                client.call("rotate", {"key_ids": [key_id]})
            except Exception:
                pass  # Bob unreachable: his copy still expires on its own
            finally:
                client.close()

    def rotate(self, actor: str) -> dict:
        ids = self.store.expire_keys()
        notified = None
        if self.source.name == "bb84" and ids:
            notified = False
            client = BobClient(self.store, self.cfg, "rot-" + uuid.uuid4().hex[:10])
            try:
                client.call("rotate", {"key_ids": ids})
                notified = True
            except Exception:
                pass  # Bob keeps his copies until they time out; Alice can no longer use hers
            finally:
                client.close()
        self.audit.record(actor, "keys_rotated", expired=len(ids), peer_notified=notified, key_ids=ids[:20])
        return {"expired": len(ids), "peer_notified": notified}
