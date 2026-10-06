"""SQLite storage for one hospital node.

What lives here: authentication keys, the QKD key pool, QKD session history, user
accounts, patient records and the audit log.

Key material and record contents are sealed with the node's Vault (AES-256-GCM, bound
to the row id), so a copy of the database file reveals no keys and no patient data.
A key that has been used or has expired is zeroised: its sealed value is deleted and only
the id, status and a short fingerprint remain.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from backend.crypto import key_fingerprint

from .vault import Vault

SCHEMA = """
CREATE TABLE IF NOT EXISTS auth_keys (
    kid TEXT PRIMARY KEY, key_enc TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS keys (
    key_id TEXT PRIMARY KEY, session TEXT NOT NULL, idx INTEGER NOT NULL,
    key_enc TEXT, fp TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL,
    expires_at REAL NOT NULL, used_at REAL);
CREATE TABLE IF NOT EXISTS sessions (
    sid TEXT PRIMARY KEY, started REAL, status TEXT, reason TEXT, qber REAL,
    n_qubits INTEGER, key_bits INTEGER, keys_added INTEGER, elapsed_ms INTEGER);
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY, pw_hash TEXT NOT NULL, role TEXT NOT NULL,
    created REAL NOT NULL, disabled INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY, direction TEXT NOT NULL, status TEXT NOT NULL,
    created_by TEXT NOT NULL, created REAL NOT NULL, sent_at REAL, key_id TEXT,
    payload_enc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, actor TEXT NOT NULL,
    event TEXT NOT NULL, detail TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


class Store:
    def __init__(self, path: Path, vault: Vault):
        self.path = str(path)
        self.vault = vault
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._c() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)

    @contextmanager
    def _c(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- authentication keys (authenticate the public channel) ---------------
    def ensure_bootstrap_auth(self, key: bytes) -> None:
        with self._c() as c:
            c.execute(
                "INSERT OR IGNORE INTO auth_keys (kid, key_enc, created) VALUES ('boot', ?, ?)",
                (self.vault.seal(key, "auth:boot"), time.time()),
            )

    def latest_auth_key(self) -> tuple[str, bytes]:
        with self._c() as c:
            row = c.execute("SELECT kid, key_enc FROM auth_keys ORDER BY rowid DESC LIMIT 1").fetchone()
        return row["kid"], self.vault.open(row["key_enc"], f"auth:{row['kid']}")

    def get_auth_key(self, kid) -> bytes | None:
        with self._c() as c:
            row = c.execute("SELECT key_enc FROM auth_keys WHERE kid=?", (str(kid),)).fetchone()
        return self.vault.open(row["key_enc"], f"auth:{kid}") if row else None

    def add_auth_key(self, kid: str, key: bytes) -> None:
        with self._c() as c:
            c.execute(
                "INSERT OR IGNORE INTO auth_keys (kid, key_enc, created) VALUES (?, ?, ?)",
                (kid, self.vault.seal(key, f"auth:{kid}"), time.time()),
            )

    def auth_version(self) -> int:
        with self._c() as c:
            return c.execute("SELECT COUNT(*) FROM auth_keys").fetchone()[0]

    # ---- key pool ------------------------------------------------------------
    def add_keys(self, key_ids_and_keys: list[tuple[str, str, int, bytes]], ttl: int, now: float | None = None) -> list[str]:
        """Add (key_id, session, idx, key) tuples as 'available' keys expiring in `ttl` seconds."""
        now = time.time() if now is None else now
        ids = []
        with self._c() as c:
            for key_id, session, idx, key in key_ids_and_keys:
                c.execute(
                    "INSERT OR IGNORE INTO keys (key_id, session, idx, key_enc, fp, status, created, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, 'available', ?, ?)",
                    (key_id, session, idx, self.vault.seal(key, f"key:{key_id}"), key_fingerprint(key), now, now + ttl),
                )
                ids.append(key_id)
        return ids

    def reserve_key(self, now: float | None = None, min_ttl: int = 0) -> tuple[str, bytes] | None:
        """Alice: take the oldest usable key. The conditional UPDATE makes it atomic.

        Keys closer than `min_ttl` seconds to expiry are skipped: the peer's clock may
        already consider them expired.
        """
        now = time.time() if now is None else now
        for _ in range(5):
            with self._c() as c:
                row = c.execute(
                    "SELECT key_id, key_enc FROM keys WHERE status='available' AND expires_at > ? "
                    "ORDER BY created, idx LIMIT 1",
                    (now + min_ttl,),
                ).fetchone()
                if row is None:
                    return None
                cur = c.execute(
                    "UPDATE keys SET status='reserved' WHERE key_id=? AND status='available'", (row["key_id"],)
                )
                if cur.rowcount == 1:
                    return row["key_id"], self.vault.open(row["key_enc"], f"key:{row['key_id']}")
        return None

    def finish_key(self, key_id: str, now: float | None = None) -> None:
        """Mark a key used and zeroise it. Keys are never reused, even after a failed send."""
        with self._c() as c:
            c.execute(
                "UPDATE keys SET status='used', used_at=?, key_enc=NULL WHERE key_id=?",
                (time.time() if now is None else now, key_id),
            )

    def consume_key(self, key_id: str, now: float | None = None) -> bytes | None:
        """Bob: use one specific key, once. Returns None if unknown, used, expired or reserved."""
        now = time.time() if now is None else now
        with self._c() as c:
            row = c.execute(
                "SELECT key_enc FROM keys WHERE key_id=? AND status='available' AND expires_at > ?",
                (key_id, now),
            ).fetchone()
            if row is None:
                return None
            key = self.vault.open(row["key_enc"], f"key:{key_id}")
            cur = c.execute(
                "UPDATE keys SET status='used', used_at=?, key_enc=NULL WHERE key_id=? AND status='available'",
                (now, key_id),
            )
            return key if cur.rowcount == 1 else None

    def expire_due(self, now: float | None = None) -> list[str]:
        """Zeroise every available key whose time is up. Returns the ids."""
        now = time.time() if now is None else now
        with self._c() as c:
            ids = [r["key_id"] for r in c.execute(
                "SELECT key_id FROM keys WHERE status IN ('available','reserved') AND expires_at <= ?", (now,))]
            if ids:
                c.executemany("UPDATE keys SET status='expired', key_enc=NULL WHERE key_id=?", [(i,) for i in ids])
        return ids

    def expire_keys(self, key_ids: list[str] | None = None) -> list[str]:
        """Zeroise the given keys (or every available key). Used by rotation."""
        with self._c() as c:
            if key_ids is None:
                ids = [r["key_id"] for r in c.execute("SELECT key_id FROM keys WHERE status='available'")]
            else:
                marks = ",".join("?" * len(key_ids)) or "NULL"
                ids = [r["key_id"] for r in c.execute(
                    f"SELECT key_id FROM keys WHERE status='available' AND key_id IN ({marks})", key_ids)]
            if ids:
                c.executemany("UPDATE keys SET status='expired', key_enc=NULL WHERE key_id=?", [(i,) for i in ids])
        return ids

    def available_ids(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now
        with self._c() as c:
            return [r["key_id"] for r in c.execute(
                "SELECT key_id FROM keys WHERE status='available' AND expires_at > ? ORDER BY created, idx", (now,))]

    def available_count(self, now: float | None = None, min_ttl: int = 0) -> int:
        now = time.time() if now is None else now
        with self._c() as c:
            return c.execute(
                "SELECT COUNT(*) FROM keys WHERE status='available' AND expires_at > ?", (now + min_ttl,)
            ).fetchone()[0]

    def pool_stats(self, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        with self._c() as c:
            rows = c.execute("SELECT status, COUNT(*) n FROM keys GROUP BY status").fetchall()
            nxt = c.execute(
                "SELECT MIN(expires_at) FROM keys WHERE status='available' AND expires_at > ?", (now,)
            ).fetchone()[0]
        counts = {r["status"]: r["n"] for r in rows}
        avail = self.available_count(now)
        return {
            "available": avail,
            "reserved": counts.get("reserved", 0),
            "used": counts.get("used", 0),
            "expired": counts.get("expired", 0),
            "key_bits": 256,
            "available_bits": avail * 256,
            "next_expiry": nxt,
            "auth_key_version": self.auth_version(),
        }

    def pool_listing(self, limit: int = 40) -> list[dict]:
        """Key ids, status and a short fingerprint. Never the key itself."""
        with self._c() as c:
            rows = c.execute(
                "SELECT key_id, fp, status, created, expires_at, used_at FROM keys "
                "ORDER BY created DESC, idx LIMIT ?", (limit,)).fetchall()
        return [
            {"key_id": r["key_id"], "status": r["status"], "fingerprint": r["fp"], "created": r["created"],
             "expires_at": r["expires_at"], "used_at": r["used_at"]}
            for r in rows
        ]

    # ---- QKD sessions --------------------------------------------------------
    def save_session(self, sid: str, **f) -> None:
        cols = ("started", "status", "reason", "qber", "n_qubits", "key_bits", "keys_added", "elapsed_ms")
        vals = [f.get(k) for k in cols]
        with self._c() as c:
            c.execute(
                "INSERT INTO sessions (sid, started, status, reason, qber, n_qubits, key_bits, keys_added, elapsed_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(sid) DO UPDATE SET "
                + ", ".join(f"{k}=COALESCE(excluded.{k}, {k})" for k in cols),
                (sid, *vals),
            )

    def recent_sessions(self, limit: int = 10) -> list[dict]:
        with self._c() as c:
            rows = c.execute("SELECT * FROM sessions ORDER BY started DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ---- users and login tokens ----------------------------------------------
    def create_user(self, username: str, pw_hash: str, role: str) -> bool:
        with self._c() as c:
            cur = c.execute(
                "INSERT OR IGNORE INTO users (username, pw_hash, role, created) VALUES (?,?,?,?)",
                (username, pw_hash, role, time.time()),
            )
            return cur.rowcount == 1

    def get_user(self, username: str) -> dict | None:
        with self._c() as c:
            row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self._c() as c:
            rows = c.execute("SELECT username, role, created, disabled FROM users ORDER BY username").fetchall()
        return [dict(r) for r in rows]

    def count_users(self) -> int:
        with self._c() as c:
            return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def set_user_disabled(self, username: str, disabled: bool) -> bool:
        with self._c() as c:
            cur = c.execute("UPDATE users SET disabled=? WHERE username=?", (int(disabled), username))
            if disabled:
                c.execute("DELETE FROM tokens WHERE username=?", (username,))
            return cur.rowcount == 1

    def save_token(self, token_hash: str, username: str, expires: float) -> None:
        with self._c() as c:
            c.execute("INSERT INTO tokens (token_hash, username, expires) VALUES (?,?,?)",
                      (token_hash, username, expires))

    def get_token(self, token_hash: str) -> dict | None:
        with self._c() as c:
            row = c.execute("SELECT username, expires FROM tokens WHERE token_hash=?", (token_hash,)).fetchone()
        return dict(row) if row else None

    def delete_token(self, token_hash: str) -> None:
        with self._c() as c:
            c.execute("DELETE FROM tokens WHERE token_hash=?", (token_hash,))

    def purge_tokens(self, now: float | None = None) -> None:
        with self._c() as c:
            c.execute("DELETE FROM tokens WHERE expires <= ?", (time.time() if now is None else now,))

    # ---- records (sealed at rest) --------------------------------------------
    def add_record(self, rec_id: str, direction: str, status: str, created_by: str, payload: dict,
                   key_id: str | None = None, now: float | None = None) -> None:
        with self._c() as c:
            c.execute(
                "INSERT INTO records (id, direction, status, created_by, created, key_id, payload_enc) "
                "VALUES (?,?,?,?,?,?,?)",
                (rec_id, direction, status, created_by, time.time() if now is None else now, key_id,
                 self.vault.seal(json.dumps(payload).encode(), f"record:{rec_id}")),
            )

    def _record(self, row) -> dict:
        d = dict(row)
        d["payload"] = json.loads(self.vault.open(d.pop("payload_enc"), f"record:{d['id']}"))
        return d

    def get_record(self, rec_id: str, direction: str) -> dict | None:
        with self._c() as c:
            row = c.execute("SELECT * FROM records WHERE id=? AND direction=?", (rec_id, direction)).fetchone()
        return self._record(row) if row else None

    def list_records(self, direction: str, limit: int = 100) -> list[dict]:
        with self._c() as c:
            rows = c.execute(
                "SELECT * FROM records WHERE direction=? ORDER BY created DESC LIMIT ?", (direction, limit)).fetchall()
        return [self._record(r) for r in rows]

    def update_record(self, rec_id: str, **fields) -> None:
        allowed = {"status", "sent_at", "key_id"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return
        with self._c() as c:
            c.execute(f"UPDATE records SET {', '.join(f'{k}=?' for k in sets)} WHERE id=?", (*sets.values(), rec_id))

    def record_exists(self, rec_id: str, direction: str) -> bool:
        with self._c() as c:
            return c.execute("SELECT 1 FROM records WHERE id=? AND direction=?", (rec_id, direction)).fetchone() is not None

    # ---- audit log -----------------------------------------------------------
    def audit_append(self, make_hash: Callable[[str, float, str, str, str], str],
                     make_head: Callable[[int, str], str], genesis: str,
                     ts: float, actor: str, event: str, detail: dict) -> int:
        """Append one chained entry and refresh the signed head, all in one transaction.

        The head (id and hash of the newest entry, signed with the audit key) is what lets
        verification notice that entries were cut off the end of the log.
        """
        detail_json = json.dumps(detail, sort_keys=True, separators=(",", ":"))
        with self._c() as c:
            c.execute("BEGIN IMMEDIATE")
            last = c.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
            prev = last["hash"] if last else genesis
            h = make_hash(prev, ts, actor, event, detail_json)
            cur = c.execute(
                "INSERT INTO audit (ts, actor, event, detail, prev_hash, hash) VALUES (?,?,?,?,?,?)",
                (ts, actor, event, detail_json, prev, h),
            )
            c.execute(
                "INSERT INTO meta (k, v) VALUES ('audit_head', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (make_head(cur.lastrowid, h),),
            )
            return cur.lastrowid

    def audit_rows(self, limit: int = 100, before_id: int | None = None) -> list[dict]:
        with self._c() as c:
            if before_id is None:
                rows = c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM audit WHERE id < ? ORDER BY id DESC LIMIT ?",
                                 (before_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def audit_iter(self, chunk: int = 500):
        last = 0
        while True:
            with self._c() as c:
                rows = c.execute("SELECT * FROM audit WHERE id > ? ORDER BY id LIMIT ?", (last, chunk)).fetchall()
            if not rows:
                return
            for r in rows:
                yield dict(r)
            last = rows[-1]["id"]

    def meta_get(self, k: str) -> str | None:
        with self._c() as c:
            row = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return row["v"] if row else None

    def meta_set(self, k: str, v: str) -> None:
        with self._c() as c:
            c.execute("INSERT INTO meta (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
