"""Tamper-evident audit log.

Every entry carries the HMAC of the previous entry's hash plus its own content, keyed with
the node's audit key. Edit a row, delete one from the middle, or reorder them and the chain
breaks at that row. A signed head (newest id and hash) also exposes entries cut off the end.

Limits, stated plainly: someone who holds the master key can forge a whole new chain, and
someone who can only write to the database can roll the log back to an older, validly signed
state. For real use, also ship entries to storage the node cannot rewrite.

Never put key material or patient contents in `detail`: ids, fingerprints and counts only.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

from .store import Store
from .vault import Vault


class AuditLog:
    def __init__(self, store: Store, vault: Vault, node: str, now=time.time):
        self.store, self.node, self._now = store, node, now
        self._key = vault.audit_key
        self.genesis = hashlib.sha256(b"mediqkd/audit/genesis/" + node.encode()).hexdigest()

    def _hash(self, prev: str, ts: float, actor: str, event: str, detail_json: str) -> str:
        msg = "\x1f".join((prev, repr(float(ts)), actor, event, detail_json)).encode()
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()

    def _head(self, entry_id: int, entry_hash: str) -> str:
        return hmac.new(self._key, f"head\x1f{entry_id}\x1f{entry_hash}".encode(), hashlib.sha256).hexdigest()

    def record(self, actor: str, event: str, **detail) -> int:
        return self.store.audit_append(self._hash, self._head, self.genesis, self._now(), actor, event, detail)

    def entries(self, limit: int = 100, before_id: int | None = None) -> list[dict]:
        out = []
        for r in self.store.audit_rows(limit, before_id):
            out.append({"id": r["id"], "ts": r["ts"], "actor": r["actor"], "event": r["event"],
                        "detail": json.loads(r["detail"]), "hash": r["hash"][:16]})
        return out

    def verify(self) -> dict:
        """Walk the whole chain. Returns {ok, checked, problem, bad_id}."""
        prev, checked, last_id, last_hash = self.genesis, 0, 0, None
        for r in self.store.audit_iter():
            if r["id"] != last_id + 1:
                return {"ok": False, "checked": checked, "bad_id": last_id + 1,
                        "problem": f"entry {last_id + 1} is missing"}
            if r["prev_hash"] != prev:
                return {"ok": False, "checked": checked, "bad_id": r["id"],
                        "problem": f"entry {r['id']} does not follow the previous entry"}
            if not hmac.compare_digest(r["hash"], self._hash(prev, r["ts"], r["actor"], r["event"], r["detail"])):
                return {"ok": False, "checked": checked, "bad_id": r["id"],
                        "problem": f"entry {r['id']} was modified"}
            prev, last_id, last_hash, checked = r["hash"], r["id"], r["hash"], checked + 1
        head = self.store.meta_get("audit_head")
        if last_hash is None:
            if head is not None:
                return {"ok": False, "checked": 0, "bad_id": 1, "problem": "the log was emptied"}
        elif head is None or not hmac.compare_digest(head, self._head(last_id, last_hash)):
            return {"ok": False, "checked": checked, "bad_id": last_id,
                    "problem": "entries were removed from the end of the log"}
        return {"ok": True, "checked": checked, "bad_id": None, "problem": None}
