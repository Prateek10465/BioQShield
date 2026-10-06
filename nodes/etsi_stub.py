"""A stand-in key-management entity (KME) speaking ETSI GS QKD 014.

For testing the hospital app's ETSI path without vendor hardware. Its keys come from the
operating system's random number generator, NOT from any quantum process, so it provides
no QKD security at all. It exists to prove that the app talks to a standard key-delivery
interface and not to our simulator.

    STUB_SAE_KEYS="hospital-a:key-a,hospital-b:key-b"   which API key is which application
    STUB_ALLOW_CONTROL=1                               enables POST /stub/outage for tests

Run:  uvicorn nodes.etsi_stub:app --port 8004
"""
from __future__ import annotations

import base64
import os
import threading
import uuid

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

KEY_SIZE = 256
MAX_PER_REQUEST = 32


def _sites() -> dict[str, str]:
    raw = os.environ.get("STUB_SAE_KEYS", "hospital-a:dev-key-a,hospital-b:dev-key-b")
    return {key: sae for sae, key in (pair.split(":", 1) for pair in raw.split(",") if ":" in pair)}


app = FastAPI(title="ETSI GS QKD 014 stub KME (NOT QUANTUM)", version="1.0.0")
SITES = _sites()
lock = threading.Lock()
pending: dict[tuple[str, str], dict[str, bytes]] = {}  # (master, slave) -> {key_ID: key}
state = {"down": False}


def caller(api_key: str | None) -> str:
    sae = SITES.get(api_key or "")
    if sae is None:
        raise HTTPException(401, {"message": "unknown or missing API key"})
    return sae


@app.exception_handler(HTTPException)
async def _err(_, exc: HTTPException):
    body = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


def other(sae: str) -> list[str]:
    return [s for s in SITES.values() if s != sae]


class EncRequest(BaseModel):
    number: int = Field(1, ge=1, le=MAX_PER_REQUEST)
    size: int = Field(KEY_SIZE, ge=64, le=1024)


class DecRequest(BaseModel):
    key_IDs: list[dict]


def _enc(master: str, slave: str, number: int, size: int):
    if slave not in other(master):
        raise HTTPException(400, {"message": f"{slave!r} is not a peer SAE of {master!r}"})
    if size % 8:
        raise HTTPException(400, {"message": "size must be a multiple of 8"})
    if state["down"]:
        raise HTTPException(503, {"message": "QKD link down: no key available"})
    keys = []
    with lock:
        bucket = pending.setdefault((master, slave), {})
        for _ in range(number):
            kid, key = str(uuid.uuid4()), os.urandom(size // 8)
            bucket[kid] = key
            keys.append({"key_ID": kid, "key": base64.b64encode(key).decode()})
    return {"keys": keys}


@app.get("/api/v1/keys/{slave}/status")
def status(slave: str, x_api_key: str | None = Header(None)):
    master = caller(x_api_key)
    if slave not in other(master):
        raise HTTPException(400, {"message": f"{slave!r} is not a peer SAE of {master!r}"})
    if state["down"]:
        raise HTTPException(503, {"message": "QKD link down"})
    with lock:
        stored = len(pending.get((master, slave), {}))
    return {"source_KME_ID": f"kme-{master}", "target_KME_ID": f"kme-{slave}", "master_SAE_ID": master,
            "slave_SAE_ID": slave, "key_size": KEY_SIZE, "stored_key_count": stored,
            "max_key_count": 100000, "max_key_per_request": MAX_PER_REQUEST, "max_key_size": 1024,
            "min_key_size": 64, "max_SAE_ID_count": 0}


@app.get("/api/v1/keys/{slave}/enc_keys")
def enc_get(slave: str, number: int = Query(1, ge=1, le=MAX_PER_REQUEST), size: int = Query(KEY_SIZE),
            x_api_key: str | None = Header(None)):
    return _enc(caller(x_api_key), slave, number, size)


@app.post("/api/v1/keys/{slave}/enc_keys")
def enc_post(slave: str, req: EncRequest | None = None, x_api_key: str | None = Header(None)):
    req = req or EncRequest()
    return _enc(caller(x_api_key), slave, req.number, req.size)


def _dec(slave: str, master: str, ids: list[str]):
    if master not in other(slave):
        raise HTTPException(400, {"message": f"{master!r} is not a peer SAE of {slave!r}"})
    out = []
    with lock:
        bucket = pending.get((master, slave), {})
        if any(i not in bucket for i in ids):
            raise HTTPException(400, {"message": "unknown key_ID (never issued, or already delivered)"})
        for i in ids:
            out.append({"key_ID": i, "key": base64.b64encode(bucket.pop(i)).decode()})  # delivered once
    return {"keys": out}


@app.get("/api/v1/keys/{master}/dec_keys")
def dec_get(master: str, key_ID: str = Query(...), x_api_key: str | None = Header(None)):
    return _dec(caller(x_api_key), master, [key_ID])


@app.post("/api/v1/keys/{master}/dec_keys")
def dec_post(master: str, req: DecRequest, x_api_key: str | None = Header(None)):
    ids = [str(k.get("key_ID", "")) for k in req.key_IDs]
    if not ids:
        raise HTTPException(400, {"message": "no key_ID given"})
    return _dec(caller(x_api_key), master, ids)


class Outage(BaseModel):
    down: bool


@app.post("/stub/outage")
def outage(req: Outage):
    if os.environ.get("STUB_ALLOW_CONTROL") != "1":
        raise HTTPException(404, {"message": "not found"})
    state["down"] = req.down
    return state


@app.get("/api/health")
def health():
    return {"ok": True, "role": "etsi-stub", "quantum": False}
