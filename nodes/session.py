"""Alice's side of one BB84 session, run over the real network.

    1  transmit   Alice sends qubits through the link (the fibre), Bob measures them
    2  sift       Bob announces his bases, Alice says which positions matched
    3  qber       a random quarter of the matching bits is revealed and compared
    4  ec         Cascade error correction, Bob asking and Alice answering parities
    5  pa         privacy amplification shrinks the key to what Eve cannot know
    6  commit     both sides confirm they derived the same keys, then store them

Everything after step 1 travels in HMAC-signed envelopes (nodes/common.py), so someone on
the public channel can read it but cannot alter or forge it undetected. Each successful
session also replenishes the authentication key itself from fresh QKD bits.

The function returns a result dict whose `stages` list the UI renders. `status` is
    ok        keys were added to both pools
    aborted   the protocol worked and refused to make a key (eavesdropper, too noisy)
    failed    something broke (authentication failure, link unreachable, protocol error)
"""
from __future__ import annotations

import threading
import time
import uuid

import numpy as np

from quantum import bb84, postprocess as pp
from quantum.channel_sim import pack_bits, unpack_bits

from .audit import AuditLog
from .client import BobClient
from .common import AuthError, Config, ProtocolError
from .keymaterial import MIN_NET_KEY_BITS, split_final_key
from .qlink import AliceLink
from .store import Store
from .wire import key_confirmation, pack_ints, request_cost, request_from_wire

SAMPLE_FRACTION = 0.25


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


class _Stages:
    ORDER = [
        ("transmit", "Quantum transmission"),
        ("sift", "Basis sifting"),
        ("qber", "QBER estimation"),
        ("ec", "Error correction (Cascade)"),
        ("pa", "Privacy amplification"),
        ("commit", "Key confirmation"),
    ]

    def __init__(self):
        self.items: list[dict] = []

    def add(self, sid: str, status: str, metrics: list[list[str]], note: str = "") -> None:
        title = dict(self.ORDER)[sid]
        self.items.append({"id": sid, "title": title, "status": status, "metrics": metrics, "note": note})

    def finish(self) -> list[dict]:
        done = {s["id"] for s in self.items}
        for sid, title in self.ORDER:
            if sid not in done:
                self.items.append({"id": sid, "title": title, "status": "skipped", "metrics": [],
                                   "note": "Not reached: session stopped earlier."})
        return self.items


class _Stop(Exception):
    def __init__(self, status: str, kind: str, reason: str):
        super().__init__(reason)
        self.status, self.kind, self.reason = status, kind, reason


class SessionRunner:
    """Runs BB84 sessions against Bob. One at a time: the pool and the link are shared."""

    def __init__(self, store: Store, cfg: Config, audit: AuditLog):
        self.store, self.cfg, self.audit = store, cfg, audit
        self.lock = threading.Lock()
        self.link = AliceLink(cfg.channel_url)
        self.last: dict | None = None  # the most recent result, stages included, for the UI

    def run(self, actor: str = "system") -> dict:
        with self.lock:
            self.last = self._run(actor)
            return self.last

    # ------------------------------------------------------------------ #
    def _run(self, actor: str) -> dict:
        t0 = time.perf_counter()
        sid = uuid.uuid4().hex[:12]
        n = self.cfg.qubits
        rng = np.random.default_rng()
        stages = _Stages()
        stats: dict = {"n_sent": n, "threshold": pp.QBER_ABORT_THRESHOLD}
        client = BobClient(self.store, self.cfg, sid)
        self.store.save_session(sid, started=time.time(), status="running", n_qubits=n)
        self.audit.record(actor, "qkd_session_started", sid=sid, qubits=n)
        keys_added = 0
        try:
            # 1. transmit ------------------------------------------------------
            bits = rng.integers(0, 2, n, dtype=np.uint8)
            bases = rng.integers(0, 2, n, dtype=np.uint8)
            self.link.send(sid, bits, bases)
            reply = client.call("begin", {"n": n})
            bob_bases = unpack_bits(reply["bases"], n)
            stages.add("transmit", "ok", [["Qubits sent", f"{n:,}"]],
                       "Alice encodes random bits in random bases; Bob measures in random bases.")

            # 2. sift ----------------------------------------------------------
            match = (bases == bob_bases).astype(np.uint8)
            client.call("sift", {"match": pack_bits(match)})
            key = bits[match == 1]
            stats["n_sifted"] = int(len(key))
            stages.add("sift", "ok", [["Bases matched", f"{len(key):,}"], ["Sift rate", _pct(len(key) / n)]],
                       "Bob announced his bases; Alice said which positions matched. Bits stay private.")

            # 3. QBER ----------------------------------------------------------
            m = max(1, int(len(key) * SAMPLE_FRACTION))
            pick = np.sort(rng.choice(len(key), size=m, replace=False))
            alice_sample = key[pick]
            reply = client.call("sample", {"positions": pack_ints(pick), "bits": pack_bits(alice_sample), "m": m})
            bob_sample = unpack_bits(reply["bob_bits"], m)
            errors = int((alice_sample != bob_sample).sum())  # Alice checks for herself
            qber = errors / m
            q_upper = bb84.qber_upper_bound(qber, m)
            drop = np.ones(len(key), dtype=bool)
            drop[pick] = False
            key = key[drop]
            stats.update({"sample_size": m, "qber": qber, "qber_upper": q_upper})
            high = qber > pp.QBER_ABORT_THRESHOLD
            stages.add("qber", "abort" if high else "ok",
                       [["Bits revealed", f"{m:,}"], ["Measured QBER", _pct(qber)],
                        ["Abort threshold", _pct(pp.QBER_ABORT_THRESHOLD)]],
                       "Error rate too high to be channel noise: eavesdropper suspected." if high
                       else "Error rate is consistent with channel noise. Continuing.")
            if high:
                raise _Stop("aborted", "eavesdropper",
                            f"Eavesdropper suspected: QBER {_pct(qber)} is above the {_pct(pp.QBER_ABORT_THRESHOLD)} limit.")

            # 4. error correction ----------------------------------------------
            reply = client.call("ec_start", {})
            leaked = 0
            rounds = 0
            while "request" in reply:
                request = request_from_wire(reply["request"])
                leaked += request_cost(request)
                rounds += 1
                if rounds > 5000:
                    raise ProtocolError("error correction did not finish")
                reply = client.call("ec_answer", {"answers": pp.answer_request(key, request)})
            done = reply["done"]
            stats.update({"leaked_bits": leaked, "ec_errors_fixed": int(done["fixed"]),
                          "ec_rounds": int(done["rounds"]), "ec_exchanges": rounds})
            verified = bool(done["verified"])
            stages.add("ec", "ok" if verified else "abort",
                       [["Errors fixed", f"{int(done['fixed']):,}"], ["Parity bits leaked", f"{leaked:,}"],
                        ["Key verified", "yes" if verified else "NO"]],
                       "Bob locates his wrong bits with block parities from Alice. "
                       "Every revealed parity is subtracted from the final key.")
            if not verified:
                raise _Stop("aborted", "verification", "Key verification failed after error correction.")

            # 5. privacy amplification -----------------------------------------
            out_bits = pp.secret_key_length(len(key), q_upper, leaked)
            stats["final_bits"] = out_bits
            enough = out_bits >= MIN_NET_KEY_BITS
            stages.add("pa", "ok" if enough else "abort",
                       [["Key before", f"{len(key):,} bits"], ["Secret key after", f"{out_bits:,} bits"],
                        ["Needed", f"{MIN_NET_KEY_BITS} bits"]],
                       "A universal (Toeplitz) hash squeezes out anything Eve might know." if enough
                       else "Too little secret key left after removing noise, leakage and a safety margin.")
            if not enough:
                raise _Stop("aborted", "low_key", "Secure key rate too low: not enough secret bits after noise and leakage.")
            seed = rng.integers(0, 2, len(key) + out_bits - 1, dtype=np.uint8)
            reply = client.call("amplify", {"out_bits": out_bits, "n_key": int(len(key)), "seed": pack_bits(seed)})
            final = pp.privacy_amplify(key, out_bits, seed)
            auth_key, data_keys = split_final_key(final)
            confirm = key_confirmation(auth_key, data_keys)

            # 6. confirm and commit --------------------------------------------
            if reply.get("confirm") != confirm:
                stages.add("commit", "abort", [["Keys agree", "NO"]], "Alice and Bob derived different keys.")
                raise _Stop("failed", "keys_differ", "Alice and Bob derived different keys; nothing was stored.")
            reply = client.call("commit", {"confirm": confirm})
            key_ids = [f"{sid}-{i}" for i in range(len(data_keys))]
            self.store.add_auth_key(sid, auth_key)
            self.store.add_keys([(kid, sid, i, k) for i, (kid, k) in enumerate(zip(key_ids, data_keys))],
                                self.cfg.key_ttl)
            keys_added = len(data_keys)
            stats["keys_added"] = keys_added
            stages.add("commit", "ok", [["Keys agree", "yes"], ["New AES-256 keys", str(keys_added)],
                                         ["Auth key renewed", "yes"]],
                       "Both sides confirmed the same keys, then stored them. Part of the secret renews the "
                       "key that authenticates this channel.")
            result = self._result(sid, "ok", None, None, stats, stages, t0, keys_added)
            self.audit.record(actor, "qkd_session_ok", sid=sid, qber=round(qber, 4), keys_added=keys_added,
                              leaked_bits=leaked)
        except _Stop as stop:
            result = self._stop(sid, actor, stop, stats, stages, t0, client)
        except AuthError as e:
            result = self._stop(sid, actor, _Stop("failed", "auth", f"Authentication failure: {e}"), stats, stages, t0,
                                client, auth=True)
        except (ProtocolError, KeyError, ValueError, TypeError) as e:
            result = self._stop(sid, actor, _Stop("failed", "protocol", f"Session failed: {e}"), stats, stages, t0,
                                client)
        finally:
            client.close()
        self.store.save_session(sid, status=result["status"], reason=result["reason"], qber=stats.get("qber"),
                                key_bits=stats.get("final_bits"), keys_added=keys_added,
                                elapsed_ms=result["elapsed_ms"])
        return result

    # ------------------------------------------------------------------ #
    def _stop(self, sid, actor, stop: _Stop, stats, stages, t0, client, auth: bool = False) -> dict:
        if stop.kind != "auth":
            try:
                client.call("abort", {"reason": stop.kind})  # let Bob drop his state early
            except Exception:
                pass
        if auth:
            self.audit.record(actor, "auth_failure", sid=sid, detail=stop.reason[:160])
        elif stop.kind == "eavesdropper":
            self.audit.record(actor, "eavesdropper_suspected", sid=sid, qber=round(stats.get("qber", 0), 4))
        self.audit.record(actor, "qkd_session_aborted" if stop.status == "aborted" else "qkd_session_failed",
                          sid=sid, kind=stop.kind, reason=stop.reason[:160])
        return self._result(sid, stop.status, stop.kind, stop.reason, stats, stages, t0, 0)

    @staticmethod
    def _result(sid, status, kind, reason, stats, stages, t0, keys_added) -> dict:
        return {"sid": sid, "status": status, "kind": kind, "reason": reason, "stats": stats,
                "stages": stages.finish(), "keys_added": keys_added,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000)}
