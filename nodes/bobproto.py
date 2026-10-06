"""Bob's side of the dialogue: one handler per message kind.

Bob keeps a small in-memory state per session id (his detector results, his sifted key, the
running Cascade generator, the keys he has derived but not yet committed). The state lives
only for the length of a session. Keys reach the pool only on `commit`, after Alice has
proved she derived the same ones.

Bob never trusts Alice's numbers where he can check them himself: he recomputes the error
rate from the revealed sample, and he refuses a key length above what that error rate and
his own count of revealed bits allow.
"""
from __future__ import annotations

import json
import threading
import time
import uuid

import numpy as np
from cryptography.exceptions import InvalidTag

from quantum import bb84, postprocess as pp
from quantum.channel_sim import pack_bits, unpack_bits

from .audit import AuditLog
from .common import Config, ProtocolError
from .keymaterial import split_final_key
from .keysource import KeyUnavailable, ReceiverKeySource
from .qlink import BobLink
from .secure_message import open_message
from .store import Store
from .wire import key_confirmation, request_to_wire, unpack_ints

STATE_TTL = 180  # seconds a half-finished session may linger


class _State:
    def __init__(self, sid: str):
        self.sid = sid
        self.created = time.time()
        self.bases: np.ndarray | None = None
        self.bits: np.ndarray | None = None
        self.key: np.ndarray | None = None
        self.qber = self.q_upper = 0.0
        self.m = 0
        self.gen = None
        self.leaked = 0
        self.verified = False
        self.staged: dict | None = None


class BobProtocol:
    def __init__(self, store: Store, cfg: Config, audit: AuditLog, receiver: ReceiverKeySource, link: BobLink | None = None):
        self.store, self.cfg, self.audit, self.receiver = store, cfg, audit, receiver
        self.link = link or BobLink(cfg.channel_url)
        self.sessions: dict[str, _State] = {}
        self.lock = threading.Lock()
        self.rng = np.random.default_rng()

    # ---- dispatch ------------------------------------------------------------
    def handle(self, kind: str, sid: str, payload: dict) -> dict:
        handler = getattr(self, f"on_{kind}", None)
        if handler is None:
            raise ProtocolError(f"unknown message kind {kind!r}")
        try:
            return handler(sid, payload)
        except (KeyError, TypeError, ValueError) as e:  # ProtocolError is not one of these and passes through
            raise ProtocolError(f"malformed {kind} message: {e}") from e

    def _state(self, sid: str) -> _State:
        with self.lock:
            st = self.sessions.get(sid)
        if st is None:
            raise ProtocolError("no such session (expired or never started)")
        return st

    def _drop(self, sid: str) -> None:
        with self.lock:
            self.sessions.pop(sid, None)

    # ---- QKD dialogue ----------------------------------------------------------
    def on_begin(self, sid: str, p: dict) -> dict:
        n = int(p["n"])
        if not 64 <= n <= 65536:
            raise ProtocolError("qubit count out of range")
        now = time.time()
        with self.lock:
            for old in [s for s, st in self.sessions.items() if now - st.created > STATE_TTL]:
                self.sessions.pop(old, None)
            st = self.sessions[sid] = _State(sid)
        st.bases = self.rng.integers(0, 2, n, dtype=np.uint8)
        st.bits = self.link.measure(sid, st.bases)
        return {"bases": pack_bits(st.bases)}

    def on_sift(self, sid: str, p: dict) -> dict:
        st = self._state(sid)
        match = unpack_bits(p["match"], len(st.bits)).astype(bool)
        st.key = st.bits[match].copy()
        return {"kept": int(match.sum())}

    def on_sample(self, sid: str, p: dict) -> dict:
        st = self._state(sid)
        pos = unpack_ints(p["positions"])
        m = int(p["m"])
        if len(pos) != m or m < 1 or pos.min() < 0 or pos.max() >= len(st.key) or len(set(pos.tolist())) != m:
            raise ProtocolError("invalid sample positions")
        alice_sample = unpack_bits(p["bits"], m)
        mine = st.key[pos]
        errors = int((alice_sample != mine).sum())
        st.m, st.qber = m, errors / m
        st.q_upper = bb84.qber_upper_bound(st.qber, m)
        drop = np.ones(len(st.key), dtype=bool)
        drop[pos] = False
        st.key = st.key[drop].copy()
        abort = st.qber > pp.QBER_ABORT_THRESHOLD
        if abort:
            self.audit.record("peer", "eavesdropper_suspected", sid=sid, qber=round(st.qber, 4))
            self._drop(sid)
        return {"bob_bits": pack_bits(mine), "errors": errors, "qber": st.qber, "qber_upper": st.q_upper,
                "abort": abort}

    def on_ec_start(self, sid: str, p: dict) -> dict:
        st = self._state(sid)
        st.gen = pp.reconcile_corrector(st.key, max(st.qber, 0.005), rng=self.rng)
        return self._advance(st, None)

    def on_ec_answer(self, sid: str, p: dict) -> dict:
        st = self._state(sid)
        if st.gen is None:
            raise ProtocolError("error correction was not started")
        answers = [int(a) for a in p["answers"]]
        return self._advance(st, answers)

    def _advance(self, st: _State, answers: list[int] | None) -> dict:
        try:
            request = next(st.gen) if answers is None else st.gen.send(answers)
        except StopIteration as stop:
            leaked, fixed, rounds, verified = stop.value
            st.leaked, st.verified, st.gen = leaked, verified, None
            return {"done": {"leaked": leaked, "fixed": fixed, "rounds": rounds, "verified": verified}}
        except ValueError as e:
            raise ProtocolError(str(e)) from e
        return {"request": request_to_wire(request)}

    def on_amplify(self, sid: str, p: dict) -> dict:
        st = self._state(sid)
        if not st.verified:
            raise ProtocolError("refusing to amplify a key that was not verified")
        out_bits, n_key = int(p["out_bits"]), int(p["n_key"])
        if n_key != len(st.key):
            raise ProtocolError("key length mismatch")
        allowed = pp.secret_key_length(len(st.key), st.q_upper, st.leaked)
        if not 0 < out_bits <= allowed:
            raise ProtocolError(f"key length {out_bits} exceeds what the measured error rate allows ({allowed})")
        seed = unpack_bits(p["seed"], len(st.key) + out_bits - 1)
        final = pp.privacy_amplify(st.key, out_bits, seed)
        auth_key, data_keys = split_final_key(final)
        st.staged = {"auth": auth_key, "data": data_keys, "confirm": key_confirmation(auth_key, data_keys)}
        return {"confirm": st.staged["confirm"]}

    def on_commit(self, sid: str, p: dict) -> dict:
        st = self._state(sid)
        if st.staged is None or p.get("confirm") != st.staged["confirm"]:
            self._drop(sid)
            raise ProtocolError("key confirmation does not match")
        key_ids = [f"{sid}-{i}" for i in range(len(st.staged["data"]))]
        self.store.add_auth_key(sid, st.staged["auth"])
        self.store.add_keys([(kid, sid, i, k) for i, (kid, k) in enumerate(zip(key_ids, st.staged["data"]))],
                            self.cfg.key_ttl)
        self.store.save_session(sid, started=st.created, status="ok", qber=st.qber, n_qubits=len(st.bits),
                                key_bits=len(st.staged["data"]) * 256, keys_added=len(key_ids))
        self.audit.record("peer", "keys_received", sid=sid, keys=len(key_ids), qber=round(st.qber, 4))
        self._drop(sid)
        return {"ok": True, "key_ids": key_ids}

    def on_abort(self, sid: str, p: dict) -> dict:
        self._drop(sid)
        return {"ok": True}

    # ---- records and key rotation ---------------------------------------------
    def on_message(self, sid: str, p: dict) -> dict:
        key_id = str(p["key_id"])
        try:
            key = self.receiver.obtain(key_id)
        except KeyUnavailable as e:
            self.audit.record("peer", "message_rejected", key_id=key_id, reason=e.reason[:120])
            raise ProtocolError(f"cannot fetch the key: {e.reason}") from e
        if key is None:
            self.audit.record("peer", "message_rejected", key_id=key_id, reason="unknown, used or expired key")
            raise ProtocolError("unknown, already used or expired key")
        try:
            _, data = open_message(key, key_id, p["nonce"], p["ciphertext"])
            record = json.loads(data)
            rid = str(record.get("record_id") or uuid.uuid4())[:64]
            payload = {"patient_ref": str(record["patient_ref"]), "title": str(record["title"]),
                       "body": str(record["body"]), "sent_by": str(record.get("sent_by", "")),
                       "sender": self.cfg.peer_name}
        except (InvalidTag, ValueError, KeyError, TypeError) as e:
            self.audit.record("peer", "decrypt_failed", key_id=key_id)
            raise ProtocolError("decryption failed: the data was altered or the key is wrong") from e
        if self.store.record_exists(rid, "inbox"):
            raise ProtocolError("record already received")
        self.store.add_record(rid, "inbox", "received", f"peer:{self.cfg.peer_name}", payload, key_id=key_id)
        self.audit.record("peer", "record_received", record=rid, key_id=key_id)
        return {"ok": True, "record_id": rid}

    def on_rotate(self, sid: str, p: dict) -> dict:
        ids = [str(i) for i in p.get("key_ids", [])][:1000]
        expired = self.store.expire_keys(ids)
        self.audit.record("peer", "keys_rotated", expired=len(expired), requested=len(ids))
        return {"expired": len(expired)}
