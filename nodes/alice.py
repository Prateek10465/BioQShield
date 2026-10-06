"""Hospital A: the sending hospital.

Staff create patient records, then send them to Hospital B. Each record is encrypted with
one key from the QKD key pool and the key is destroyed after use. If no secure key can be
made (an eavesdropper is suspected, the link is down) the record is NOT sent.

Run:  uvicorn nodes.alice:create_app --factory --port 8001
"""
from __future__ import annotations

import json
import time
import uuid

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.crypto import key_fingerprint

from .accounts import User
from .client import BobClient
from .common import AuthError, Config, ProtocolError, load_config
from .hospital import Context, build_context, install, make_lifespan
from .keymanager import KeyManager
from .keysource import (Bb84Sender, Etsi014Client, Etsi014Sender, KeySourceError, KeyUnavailable, build_kme_http)
from .secure_message import seal_message
from .session import SessionRunner


class RecordIn(BaseModel):
    patient_ref: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)


def view(rec: dict, with_body: bool = False) -> dict:
    p = rec["payload"]
    out = {"id": rec["id"], "status": rec["status"], "created": rec["created"], "created_by": rec["created_by"],
           "sent_at": rec["sent_at"], "key_id": rec["key_id"], "patient_ref": p["patient_ref"], "title": p["title"]}
    if with_body:
        out["body"] = p["body"]
    return out


def create_app(cfg: Config | None = None, *, kme_http=None, now=time.time) -> FastAPI:
    cfg = cfg or load_config("alice")
    ctx: Context = build_context(cfg, now)
    store, audit = ctx.store, ctx.audit
    runner = SessionRunner(store, cfg, audit)

    if cfg.key_source == "etsi014":
        kme = Etsi014Client(kme_http or build_kme_http(cfg.kme_url, cfg.kme_api_key))
        source = Etsi014Sender(kme, store, cfg.peer_sae, cfg.key_ttl)

        def probe() -> dict:
            try:
                s = kme.status(cfg.peer_sae)
                return {"reachable": True, "source": "etsi014", "kme_stored_keys": s.get("stored_key_count")}
            except (KeyUnavailable, KeySourceError) as e:
                return {"reachable": False, "source": "etsi014", "reason": str(e)}
    else:
        source = Bb84Sender(runner.run)

        def probe() -> dict:
            try:
                response = httpx.get(f"{cfg.channel_url}/api/health", timeout=2)
                ok = response.status_code == 200
                state = response.json() if ok else {}
            except httpx.HTTPError:
                ok = False
                state = {}
            return {"reachable": ok, "source": "bb84", **{key: state[key] for key in ("eve", "eve_rate", "eve_start", "noise", "tamper") if key in state}, "last_session": runner.last and {
                k: runner.last[k] for k in ("sid", "status", "kind", "reason", "elapsed_ms")}}

    km = KeyManager(store, source, audit, cfg, now)
    app = FastAPI(title=f"{cfg.name} (sender)", version="1.0.0", lifespan=make_lifespan(ctx, km.maintain))
    _, require = install(app, ctx, probe)
    clinician = require("clinician")

    # ---- records -----------------------------------------------------------------------
    @app.post("/api/records", status_code=201)
    def create_record(req: RecordIn, user: User = Depends(clinician)) -> dict:
        rec_id = uuid.uuid4().hex[:16]
        store.add_record(rec_id, "outbox", "draft", user.username, req.model_dump(), now=now())
        audit.record(user.username, "record_created", record=rec_id)
        return view(store.get_record(rec_id, "outbox"))

    @app.get("/api/records")
    def list_records(user: User = Depends(clinician)) -> dict:
        recs = store.list_records("outbox")
        audit.record(user.username, "records_listed", count=len(recs))
        return {"records": [view(r) for r in recs]}

    @app.get("/api/records/{rec_id}")
    def get_record(rec_id: str, user: User = Depends(clinician)) -> dict:
        rec = store.get_record(rec_id, "outbox")
        if rec is None:
            raise HTTPException(404, "no such record")
        audit.record(user.username, "record_viewed", record=rec_id)
        return view(rec, with_body=True)

    @app.post("/api/records/{rec_id}/send")
    def send_record(rec_id: str, user: User = Depends(clinician)) -> dict:
        rec = store.get_record(rec_id, "outbox")
        if rec is None:
            raise HTTPException(404, "no such record")
        if rec["status"] == "sent":
            raise HTTPException(409, "this record was already sent")
        link = probe()
        has_existing_keys = store.available_count(now(), 60) > 0
        if link.get("eve") and has_existing_keys:
            reason = "Eavesdropper is active on the link; secure transfer blocked until the link is clean."
            audit.record(user.username, "transfer_blocked", record=rec_id, reason=reason)
            raise HTTPException(503, {"code": "no_secure_key", "message": reason, "session": None})
        try:
            key_id, key = km.acquire(user.username)
        except KeyUnavailable as e:
            audit.record(user.username, "transfer_blocked", record=rec_id, reason=e.reason[:160])
            raise HTTPException(503, {"code": "no_secure_key", "message": e.reason, "session": e.detail or None})
        except KeySourceError as e:
            audit.record(user.username, "transfer_blocked", record=rec_id, reason=str(e)[:160])
            raise HTTPException(502, {"code": "key_source_error", "message": str(e)})

        data = json.dumps({"record_id": rec_id, "sent_by": user.username, **rec["payload"]}).encode()
        sealed = seal_message(key, key_id, data, f"record-{rec_id}.json", "application/json", "")
        client = BobClient(store, cfg, "msg-" + uuid.uuid4().hex[:12])
        try:
            client.call("message", sealed)
        except (AuthError, ProtocolError) as e:
            km.finish(key_id, revoke_at_peer=True)  # never use it again, and Bob must not accept it either
            audit.record(user.username, "transfer_failed", record=rec_id, key_id=key_id, reason=str(e)[:160])
            raise HTTPException(502, {"code": "peer_error", "message": str(e)})
        finally:
            client.close()
        km.finish(key_id)
        store.update_record(rec_id, status="sent", sent_at=now(), key_id=key_id)
        audit.record(user.username, "record_sent", record=rec_id, key_id=key_id, key_fp=key_fingerprint(key))
        return {"ok": True, "record": view(store.get_record(rec_id, "outbox")), "key_id": key_id,
                "key_fingerprint": key_fingerprint(key)}

    # ---- keys ----------------------------------------------------------------------------
    @app.post("/api/keys/refill")
    def refill(user: User = Depends(require("clinician", "admin"))) -> dict:
        """Make new keys now. Always answers 200 with the session result so the UI can show why it failed."""
        try:
            got = km.refill(user.username, force=True)
        except KeyUnavailable as e:
            return e.detail or {"status": "aborted", "reason": e.reason, "stages": [], "keys_added": 0}
        except KeySourceError as e:
            return {"status": "failed", "reason": str(e), "stages": [], "keys_added": 0}
        return (got.detail if got and got.detail.get("stages") else
                {"status": "ok", "reason": None, "stages": [], "keys_added": got.added if got else 0})

    @app.post("/api/keys/rotate")
    def rotate(user: User = Depends(require("admin"))) -> dict:
        return km.rotate(user.username)

    @app.get("/api/sessions/last")
    def last_session(user: User = Depends(require("clinician", "auditor", "admin"))) -> dict:
        return runner.last or {"status": "none", "stages": []}

    return app
