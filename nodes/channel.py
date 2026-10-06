"""Link service: the fibre and the public channel, in one place.

Quantum side
    Alice's qubits go in (POST /quantum/{sid}/send). An optional eavesdropper intercepts
    them and noise is applied. Bob's detector reads them out (POST /quantum/{sid}/measure).
    Each qubit set can be measured once, which is the no-cloning rule in miniature.

Public side
    Every classical message between Alice and Bob is relayed through /public/bob/... .
    That is exactly what makes it public: this service logs all of it (Eve can read every
    byte) and, when "tamper" is on, alters messages in flight. Because the messages are
    HMAC-authenticated, the alteration is detected and rejected.

The operator controls (noise, Eve, tamper) exist only because this is a simulation.
On real fibre nobody can switch an attacker on or off.

Run:  uvicorn nodes.channel:app --port 8003
"""
from __future__ import annotations

import copy
import itertools
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path

import httpx
import numpy as np
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from quantum import channel_sim as cs

from .common import load_config

cfg = load_config("channel")
app = FastAPI(title="MediQKD link service", version="1.0.0")
PORTAL = Path(__file__).resolve().parent.parent / "frontend" / "portal"

lock = threading.Lock()
config = {"noise": 0.02, "eve": False, "eve_rate": 1.0, "eve_start": 0.0, "tamper": False}
stats = {"qubits_sent": 0, "qubits_intercepted": 0, "eve_exact_bits": 0, "public_messages": 0, "tampered_messages": 0}
wire: deque = deque(maxlen=500)
demo_transfers: deque = deque(maxlen=100)
_ids = itertools.count(1)
in_flight: OrderedDict = OrderedDict()  # sid -> qubit states waiting for Bob's detector

# Request kinds an active attacker rewrites when "tamper" is on. The qubit handshake and
# basis announcements are left alone so the attack lands mid-protocol.
TAMPER_KINDS = {"sample", "ec_answer", "amplify", "commit", "message"}
NODES = {"bob": cfg.bob_url}


def log(entry: dict) -> None:
    with lock:
        entry["id"] = next(_ids)
        entry["t"] = time.time()
        wire.append(entry)


def short(obj):
    """Shrink a payload for display: long strings and lists are abbreviated."""
    if isinstance(obj, str):
        return obj if len(obj) <= 60 else f"{obj[:40]}...({len(obj)} chars)"
    if isinstance(obj, list):
        head = [short(x) for x in obj[:6]]
        return head + ([f"...+{len(obj) - 6} more"] if len(obj) > 6 else [])
    if isinstance(obj, dict):
        return {k: short(v) for k, v in obj.items()}
    return obj


def tamper_envelope(envelope: dict) -> dict:
    """Alter one value inside the payload, the way an active attacker would."""
    evil = copy.deepcopy(envelope)

    def walk(node) -> bool:
        items = node.items() if isinstance(node, dict) else enumerate(node)
        for k, v in list(items):
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                node[k] = v ^ 1
                return True
            if isinstance(v, str) and v:
                node[k] = v[:-1] + ("A" if v[-1] != "A" else "B")
                return True
            if isinstance(v, (dict, list)) and walk(v):
                return True
        return False

    walk(evil.get("payload", {}))
    return evil


# --------------------------------------------------------------------------- #
# Operator controls and the attacker's view
# --------------------------------------------------------------------------- #
class LinkConfig(BaseModel):
    noise: float | None = Field(None, ge=0.0, le=0.2)
    eve: bool | None = None
    eve_rate: float | None = Field(None, ge=0.0, le=1.0)
    eve_start: float | None = Field(None, ge=0.0, le=0.95)
    tamper: bool | None = None


@app.get("/api/health")
def health() -> dict:
    with lock:
        active = {key: config[key] for key in ("eve", "eve_rate", "eve_start", "noise", "tamper")}
    return {"ok": True, "role": "link", **active}


@app.get("/api/config")
def get_config() -> dict:
    with lock:
        return {"config": dict(config), "stats": dict(stats)}


@app.post("/api/config")
def set_config(req: LinkConfig) -> dict:
    changes = req.model_dump(exclude_none=True)
    with lock:
        changed = {k: v for k, v in changes.items() if config.get(k) != v}
        config.update(changes)
    if changed:
        log({"type": "config", "text": "Link conditions changed: " + ", ".join(f"{k}={v}" for k, v in changed.items())})
    return get_config()


@app.get("/api/wire")
def get_wire(after: int = 0) -> dict:
    with lock:
        entries = [e for e in wire if e["id"] > after][-200:]
        last = wire[-1]["id"] if wire else 0
    return {"entries": entries, "last": last, **get_config()}


@app.post("/api/wire/clear")
def clear_wire() -> dict:
    with lock:
        wire.clear()
    return {"ok": True}


@app.post("/api/demo-transfers")
def add_demo_transfer(body: dict = Body(...)) -> dict:
    allowed = ("transferId", "patient", "patientId", "department", "data", "destination", "verdict", "status", "threatScore", "qber")
    entry = {key: body.get(key) for key in allowed}
    entry["t"] = time.time()
    with lock:
        demo_transfers.appendleft(entry)
    return {"ok": True}


@app.get("/api/demo-transfers")
def list_demo_transfers() -> dict:
    with lock:
        return {"transfers": list(demo_transfers)}


# --------------------------------------------------------------------------- #
# Quantum side
# --------------------------------------------------------------------------- #
@app.post("/quantum/{sid}/send")
def quantum_send(sid: str, body: dict = Body(...)) -> dict:
    try:
        n = int(body["n"])
        if not 0 < n <= 65536:
            raise ValueError("n out of range")
        bits = cs.unpack_bits(body["bits"], n)
        bases = cs.unpack_bits(body["bases"], n)
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, f"bad transmission: {e}")
    with lock:
        now = dict(config)
    rng = np.random.default_rng()
    rate = now["eve_rate"] if now["eve"] else 0.0
    state_bits, state_bases, intercepted, eve_knows = cs.eve_intercept(bits, bases, rate, now["eve_start"], rng)
    state_bits = cs.apply_noise(state_bits, now["noise"], rng)
    with lock:
        in_flight[sid] = {"bits": state_bits, "bases": state_bases}
        while len(in_flight) > 16:
            in_flight.popitem(last=False)
        stats["qubits_sent"] += n
        stats["qubits_intercepted"] += int(intercepted.sum())
        stats["eve_exact_bits"] += int(eve_knows.sum())
    log(
        {
            "type": "quantum",
            "sid": sid,
            "n": n,
            "eve": bool(now["eve"]),
            "intercepted": int(intercepted.sum()),
            "eve_exact": int(eve_knows.sum()),
            "noise": now["noise"],
        }
    )
    return {"ok": True, "n": n}


@app.post("/quantum/{sid}/measure")
def quantum_measure(sid: str, body: dict = Body(...)) -> dict:
    with lock:
        states = in_flight.pop(sid, None)  # a qubit can only be measured once
    if states is None:
        raise HTTPException(404, "no qubits in flight for this session")
    try:
        n = int(body["n"])
        bases = cs.unpack_bits(body["bases"], n)
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, f"bad measurement request: {e}")
    if n != len(states["bits"]):
        raise HTTPException(400, "basis count does not match the number of qubits")
    out = cs.measure(states["bits"], states["bases"], bases, np.random.default_rng())
    return {"bits": cs.pack_bits(out)}


# --------------------------------------------------------------------------- #
# Public channel relay
# --------------------------------------------------------------------------- #
@app.post("/public/{node}/{path:path}")
def relay(node: str, path: str, body: dict = Body(...)):
    base = NODES.get(node)
    if base is None:
        raise HTTPException(404, f"unknown node {node!r}")
    kind = body.get("kind")
    with lock:
        do_tamper = config["tamper"] and kind in TAMPER_KINDS
        stats["public_messages"] += 1
        if do_tamper:
            stats["tampered_messages"] += 1
    sent = tamper_envelope(body) if do_tamper else body
    log(
        {
            "type": "public",
            "dir": "Alice → Bob",
            "kind": kind,
            "sid": body.get("sid"),
            "seq": body.get("seq"),
            "bytes": len(str(body)),
            "tampered": do_tamper,
            "preview": short(body.get("payload")),
        }
    )
    try:
        r = httpx.post(f"{base}/{path}", json=sent, timeout=120)
    except httpx.HTTPError as e:
        return JSONResponse(status_code=502, content={"error": f"{node} unreachable: {e}"})
    try:
        reply = r.json()
    except ValueError:
        reply = {"error": r.text[:200]}
    payload = reply.get("payload") if isinstance(reply, dict) else None
    log(
        {
            "type": "public",
            "dir": "Bob → Alice",
            "kind": reply.get("kind") if isinstance(reply, dict) else None,
            "sid": reply.get("sid") if isinstance(reply, dict) else None,
            "seq": reply.get("seq") if isinstance(reply, dict) else None,
            "bytes": len(r.content),
            "status": r.status_code,
            "tampered": False,
            "preview": short(payload) if payload is not None else short(reply),
        }
    )
    return JSONResponse(status_code=r.status_code, content=reply)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(PORTAL / "eve.html")


if PORTAL.exists():
    app.mount("/portal", StaticFiles(directory=PORTAL), name="portal")
