"""Hospital B: the receiving hospital.

Answers Alice's side of the QKD dialogue at /proto/{kind} (every message must carry a valid
HMAC), decrypts incoming records with the matching one-time key, and lets staff read them.

Run:  uvicorn nodes.bob:create_app --factory --port 8002
"""
from __future__ import annotations

import time

import httpx
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .accounts import User
from .bobproto import BobProtocol
from .common import AuthError, Config, ProtocolError, load_config, open_envelope, seal
from .hospital import Context, build_context, install, make_lifespan, expire_and_log
from .keysource import (Bb84Receiver, Etsi014Client, Etsi014Receiver, KeySourceError, KeyUnavailable,
                        build_kme_http)


def view(rec: dict, with_body: bool = False) -> dict:
    p = rec["payload"]
    out = {"id": rec["id"], "status": rec["status"], "received": rec["created"], "key_id": rec["key_id"],
           "from": p.get("sender", ""), "sent_by": p.get("sent_by", ""), "patient_ref": p["patient_ref"],
           "title": p["title"]}
    if with_body:
        out["body"] = p["body"]
    return out


def create_app(cfg: Config | None = None, *, kme_http=None, link=None, now=time.time) -> FastAPI:
    cfg = cfg or load_config("bob")
    ctx: Context = build_context(cfg, now)
    store, audit = ctx.store, ctx.audit

    if cfg.key_source == "etsi014":
        kme = Etsi014Client(kme_http or build_kme_http(cfg.kme_url, cfg.kme_api_key))
        receiver = Etsi014Receiver(kme, cfg.peer_sae)

        def probe() -> dict:
            try:
                s = kme.status(cfg.peer_sae)
                return {"reachable": True, "source": "etsi014", "kme_stored_keys": s.get("stored_key_count")}
            except (KeyUnavailable, KeySourceError) as e:
                return {"reachable": False, "source": "etsi014", "reason": str(e)}
    else:
        receiver = Bb84Receiver(store)

        def probe() -> dict:
            try:
                ok = httpx.get(f"{cfg.channel_url}/api/health", timeout=2).status_code == 200
            except httpx.HTTPError:
                ok = False
            return {"reachable": ok, "source": "bb84"}

    protocol = BobProtocol(store, cfg, audit, receiver, link)
    seen: dict = {}  # replay protection: highest sequence number accepted per session id
    app = FastAPI(title=f"{cfg.name} (receiver)", version="1.0.0",
                  lifespan=make_lifespan(ctx, lambda: expire_and_log(ctx)))
    _, require = install(app, ctx, probe)
    clinician = require("clinician")

    # ---- the QKD dialogue (called by Alice, relayed through the link) -----------------------
    @app.post("/proto/{kind}")
    def proto(kind: str, envelope: dict = Body(...)):
        try:
            opened = open_envelope(envelope, store.get_auth_key, seen)
            if opened.kind != kind:
                raise AuthError("message kind does not match the request")
        except AuthError as e:
            audit.record("peer", "auth_failure", kind=kind[:32], reason=str(e)[:120])
            return JSONResponse(status_code=401, content={"error": str(e)})
        try:
            out = protocol.handle(kind, opened.sid, opened.payload)
        except ProtocolError as e:
            return JSONResponse(status_code=400, content={"error": str(e)})
        # Reply with the key the request used, which Alice is guaranteed to know.
        return seal(opened.kid, store.get_auth_key(opened.kid), opened.sid, opened.seq, kind + "_reply", out)

    # ---- inbox -------------------------------------------------------------------------------
    @app.get("/api/inbox")
    def inbox(user: User = Depends(clinician)) -> dict:
        recs = store.list_records("inbox")
        audit.record(user.username, "inbox_listed", count=len(recs))
        return {"records": [view(r) for r in recs]}

    @app.get("/api/inbox/{rec_id}")
    def inbox_record(rec_id: str, user: User = Depends(clinician)) -> dict:
        rec = store.get_record(rec_id, "inbox")
        if rec is None:
            raise HTTPException(404, "no such record")
        audit.record(user.username, "record_viewed", record=rec_id)
        return view(rec, with_body=True)

    return app
