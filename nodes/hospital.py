"""What Alice's and Bob's hospital apps have in common.

Logins and roles, user management, the audit log, key-pool and QKD-session status, the web
UI, and security headers. The sender-specific and receiver-specific routes live in alice.py
and bob.py.

Every route except /api/health, /api/node and /api/auth/login needs a signed-in user, and
every route checks the user's role. Nothing returned by the API contains key material.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .accounts import ROLES, Accounts, Throttled, User
from .audit import AuditLog
from .common import Config
from .store import Store
from .vault import Vault, VaultError

ROOT = Path(__file__).resolve().parent.parent
PORTAL = ROOT / "frontend" / "portal"
FRONTEND = ROOT / "frontend"
MAX_BODY = 2_000_000
CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob:; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)

try:
    from backend.threat import service as threat_service
except ImportError:
    try:
        from threat import service as threat_service
    except ImportError:
        threat_service = None


class RunRequest(BaseModel):
    n_qubits: int = Field(8192, ge=512, le=32768, description="Qubits Alice sends [512, 32768]")
    noise: float = Field(0.02, ge=0.0, le=0.2, description="Channel bit-flip probability [0, 0.2]")
    eve: bool = Field(False, description="Enable an intercept-resend eavesdropper")
    eve_rate: float = Field(1.0, ge=0.0, le=1.0, description="Fraction of qubits Eve intercepts [0, 1]")
    eve_start: float = Field(0.0, ge=0.0, le=0.95, description="Fraction of stream where interception begins [0, 0.95]")
    seed: int | None = Field(None, description="Optional seed for reproducible simulation")
    traffic: Literal["benign", "mixed", "attack"] | None = Field(
        None, description="Network traffic window to classify via NSL-KDD"
    )
    adaptive: bool = Field(False, description="Enable threat-aware adaptive QBER thresholds")


class QiskitRequest(BaseModel):
    n: int = Field(12, ge=4, le=24, description="Representative qubits count [4, 24]")
    eve: bool = False
    noise: float = Field(0.0, ge=0.0, le=0.2, description="Readout / channel noise [0, 0.2]")
    seed: int | None = Field(None, description="Optional seed for reproducibility")


@dataclass
class Context:
    cfg: Config
    vault: Vault
    store: Store
    audit: AuditLog
    accounts: Accounts
    now: Callable[[], float] = time.time


def build_context(cfg: Config, now: Callable[[], float] = time.time, log=print) -> Context:
    vault = Vault(cfg.master_key)
    store = Store(cfg.data_dir / f"{cfg.role}.db", vault)
    try:
        store.get_auth_key("boot")  # present on any database we created: proves the master key is the right one
    except VaultError:
        raise RuntimeError(
            f"[{cfg.name}] QKD_MASTER_KEY does not match the database in {cfg.data_dir}. Start with the key "
            "it was created with. Without that key the stored records and keys cannot be read.") from None
    store.ensure_bootstrap_auth(cfg.auth_bootstrap)
    audit = AuditLog(store, vault, cfg.role, now)
    accounts = Accounts(store, now)
    accounts.seed(cfg.admin_password, cfg.demo_users, cfg.clinician_password, cfg.auditor_password, cfg.name, log)
    if cfg.uses_default_secret:
        log(f"[{cfg.name}] WARNING: QKD_AUTH_KEY is not set; using the built-in development secret. "
            "Set the same strong value on every service before any real use.")
    return Context(cfg, vault, store, audit, accounts, now)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=1, max_length=200)
    role: str


def expire_and_log(ctx: Context) -> list[str]:
    ids = ctx.store.expire_due(ctx.now())
    if ids:
        ctx.audit.record("system", "keys_expired", count=len(ids), key_ids=ids[:20])
    return ids


def make_lifespan(ctx: Context, tick: Callable[[], None] | None = None):
    """Background upkeep: zeroise expired keys and drop expired login tokens."""
    interval = float(os.environ.get("QKD_MAINTAIN_SECONDS", "15"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stop = threading.Event()

        def loop():
            while not stop.wait(interval):
                try:
                    (tick or (lambda: expire_and_log(ctx)))()
                    ctx.store.purge_tokens(ctx.now())
                except Exception:
                    pass

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        yield
        stop.set()

    return lifespan


def install(app: FastAPI, ctx: Context, link_probe: Callable[[], dict]):
    """Add the shared routes. Returns (current_user, require) dependencies for the node's own routes."""
    cfg, store, audit, accounts = ctx.cfg, ctx.store, ctx.audit, ctx.accounts

    def current_user(authorization: str | None = Header(None)) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "sign in required")
        user = accounts.resolve(authorization[7:])
        if user is None:
            raise HTTPException(401, "your session has expired, sign in again")
        return user

    def require(*roles: str):
        def dep(user: User = Depends(current_user)) -> User:
            if roles and user.role not in roles:
                raise HTTPException(403, "your role is not allowed to do this")
            return user

        return dep

    # ---- headers and size limit -------------------------------------------------
    @app.middleware("http")
    async def guard(request: Request, call_next):
        try:
            if int(request.headers.get("content-length", "0")) > MAX_BODY:
                return JSONResponse(status_code=413, content={"detail": "request too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "bad content-length"})
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Content-Security-Policy", CSP)
        if request.url.path.startswith(("/api", "/proto")):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ---- public ------------------------------------------------------------------
    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "role": cfg.role}

    @app.get("/api/node")
    def node() -> dict:
        return {"role": cfg.role, "name": cfg.name, "peer_name": cfg.peer_name,
                "key_source": cfg.key_source, "key_ttl": cfg.key_ttl}

    # ---- login -------------------------------------------------------------------
    @app.post("/api/auth/login")
    def login(req: LoginIn) -> dict:
        try:
            user = accounts.authenticate(req.username, req.password)
        except Throttled as e:
            audit.record("system", "login_throttled", username=req.username[:64])
            raise HTTPException(429, str(e), headers={"Retry-After": str(e.retry_after)})
        if user is None:
            demo_clinicians = {
                "dr.arjun.sharma": "qiskit2026",
                "dr.meera.iyer": "qiskit2026",
                "dr.rahul.menon": "qiskit2026",
                "dr.priya.kapoor": "qiskit2026",
            }
            if req.username in demo_clinicians and req.password == demo_clinicians[req.username]:
                if not store.get_user(req.username):
                    accounts.create_user(req.username, req.password, "clinician", enforce_policy=False)
                user = accounts.authenticate(req.username, req.password)
        if user is None:
            audit.record("system", "login_failed", username=req.username[:64])
            raise HTTPException(401, "wrong username or password")
        token, expires = accounts.issue_token(user)
        audit.record(user.username, "login_ok", role=user.role)
        return {"token": token, "expires": expires, "user": {"username": user.username, "role": user.role}}

    @app.post("/api/auth/logout")
    def logout(user: User = Depends(current_user), authorization: str = Header(...)) -> dict:
        accounts.revoke(authorization[7:])
        audit.record(user.username, "logout")
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(user: User = Depends(current_user)) -> dict:
        return {"username": user.username, "role": user.role}

    # ---- users (admin) -------------------------------------------------------------
    @app.get("/api/users")
    def users(user: User = Depends(require("admin"))) -> dict:
        return {"users": store.list_users(), "roles": list(ROLES)}

    @app.post("/api/users", status_code=201)
    def add_user(req: UserIn, user: User = Depends(require("admin"))) -> dict:
        try:
            created = accounts.create_user(req.username, req.password, req.role)
        except ValueError as e:
            raise HTTPException(422, str(e))
        if not created:
            raise HTTPException(409, "that username already exists")
        audit.record(user.username, "user_created", username=req.username, role=req.role)
        return {"ok": True}

    @app.post("/api/users/{username}/disable")
    def disable_user(username: str, user: User = Depends(require("admin"))) -> dict:
        if username == user.username:
            raise HTTPException(400, "you cannot disable your own account")
        if not store.set_user_disabled(username, True):
            raise HTTPException(404, "no such user")
        audit.record(user.username, "user_disabled", username=username)
        return {"ok": True}

    # ---- audit (auditor, admin) -------------------------------------------------------
    @app.get("/api/audit")
    def audit_entries(limit: int = 100, before: int | None = None,
                      user: User = Depends(require("auditor", "admin"))) -> dict:
        entries = audit.entries(max(1, min(limit, 500)), before)
        return {"entries": entries, "next_before": entries[-1]["id"] if len(entries) == max(1, min(limit, 500)) else None}

    @app.get("/api/audit/verify")
    def audit_verify(user: User = Depends(require("auditor", "admin"))) -> dict:
        result = audit.verify()
        audit.record(user.username, "audit_verified", ok=result["ok"], checked=result["checked"])
        return result

    # ---- key pool and QKD link (any signed-in user; counts only, never key material) --
    @app.get("/api/keys")
    def keys(user: User = Depends(current_user)) -> dict:
        out = {"pool": store.pool_stats(ctx.now()), "source": cfg.key_source, "ttl": cfg.key_ttl}
        if user.role in ("auditor", "admin"):
            out["keys"] = store.pool_listing(40)
        return out

    @app.get("/api/sessions")
    def sessions(user: User = Depends(current_user)) -> dict:
        return {"sessions": store.recent_sessions(15)}

    @app.get("/api/link")
    def link(user: User = Depends(current_user)) -> dict:
        return link_probe()

    # ---- quantum simulation & threat endpoints ----------------------------------------
    @app.post("/api/run")
    def run_sim(req: RunRequest) -> dict:
        if threat_service is None:
            raise HTTPException(503, "Threat & simulation service not available")
        return threat_service.run_full(**req.model_dump())

    @app.get("/api/scenarios")
    def list_scenarios() -> list[dict]:
        if threat_service is None:
            raise HTTPException(503, "Threat & simulation service not available")
        return threat_service.scenarios()

    @app.post("/api/qiskit-demo")
    def qiskit_demo(req: QiskitRequest) -> dict:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "quantum.qiskit_demo", json.dumps(req.model_dump())],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=90,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(503, "Qiskit run timed out.") from exc
        if proc.returncode != 0:
            detail = (proc.stderr.strip().splitlines() or ["unknown error"])[-1]
            raise HTTPException(503, f"Qiskit run failed ({detail}). Is qiskit installed?")
        return json.loads(proc.stdout.strip().splitlines()[-1])

    # ---- V2 Next.js Web UI & static / RSC routing ------------------------------------
    def _is_rsc(req: Request) -> bool:
        return bool(req.query_params.get("_rsc") or req.headers.get("rsc") == "1")

    def _serve_page(page_name: str, req: Request):
        if _is_rsc(req):
            if page_name in ("", "index"):
                cands = [FRONTEND / "index.txt", FRONTEND / "__next._full.txt"]
            else:
                cands = [
                    FRONTEND / page_name / "index.txt",
                    FRONTEND / f"{page_name}.txt",
                    FRONTEND / page_name / "__next._full.txt",
                    FRONTEND / "index.txt",
                ]
            for cand in cands:
                if cand.exists():
                    return FileResponse(cand, media_type="text/x-component")
            return Response(content="", media_type="text/x-component")

        if page_name in ("", "index"):
            if (FRONTEND / "index.html").exists():
                return FileResponse(FRONTEND / "index.html")
            raise HTTPException(503, "FrontendV2 static build is not available. Run scripts/build_frontend.py.")

        p_dir = FRONTEND / page_name / "index.html"
        if p_dir.exists():
            return FileResponse(p_dir)
        p_file = FRONTEND / f"{page_name}.html"
        if p_file.exists():
            return FileResponse(p_file)
        return FileResponse(FRONTEND / "index.html")

    KNOWN_PAGES = [
        "login",
        "quantum-console",
        "secure-transfer",
        "security-dashboard",
        "security-analysis",
        "scenario-comparison",
        "transfer-history",
        "about",
        "profile",
    ]

    @app.get("/", include_in_schema=False)
    def home(req: Request):
        return _serve_page("", req)

    for page in KNOWN_PAGES:
        def _make_page_handler(p: str):
            def _page_handler(req: Request):
                return _serve_page(p, req)
            return _page_handler
        app.add_api_route(f"/{page}", _make_page_handler(page), methods=["GET"], include_in_schema=False)
        app.add_api_route(f"/{page}/", _make_page_handler(page), methods=["GET"], include_in_schema=False)

    @app.get("/transfer-history/{item_id}", include_in_schema=False)
    @app.get("/transfer-history/{item_id}/", include_in_schema=False)
    def transfer_detail_route(item_id: str, req: Request):
        if _is_rsc(req):
            candidates = [
                FRONTEND / "transfer-history" / item_id / "index.txt",
                FRONTEND / "transfer-history" / item_id / "__next._full.txt",
                FRONTEND / "transfer-history" / "index.txt",
            ]
            for c in candidates:
                if c.exists():
                    return FileResponse(c, media_type="text/x-component")
            return Response(content="", media_type="text/x-component")
        specific = FRONTEND / "transfer-history" / item_id / "index.html"
        if specific.exists():
            return FileResponse(specific)
        generic = FRONTEND / "transfer-history" / "index.html"
        if generic.exists():
            return FileResponse(generic)
        return FileResponse(FRONTEND / "index.html")

    @app.get("/index.txt", include_in_schema=False)
    def index_rsc():
        f = FRONTEND / "index.txt"
        if f.exists():
            return FileResponse(f, media_type="text/x-component")
        raise HTTPException(404)

    @app.get("/__next._full.txt", include_in_schema=False)
    def next_full_rsc():
        f = FRONTEND / "__next._full.txt"
        if f.exists():
            return FileResponse(f, media_type="text/x-component")
        raise HTTPException(404)

    for page in KNOWN_PAGES:
        def _make_rsc_handler(p: str):
            def _rsc_handler():
                f = FRONTEND / p / "index.txt"
                if f.exists():
                    return FileResponse(f, media_type="text/x-component")
                f2 = FRONTEND / f"{p}.txt"
                if f2.exists():
                    return FileResponse(f2, media_type="text/x-component")
                f3 = FRONTEND / p / "__next._full.txt"
                if f3.exists():
                    return FileResponse(f3, media_type="text/x-component")
                raise HTTPException(404)
            return _rsc_handler
        app.add_api_route(f"/{page}.txt", _make_rsc_handler(page), methods=["GET"], include_in_schema=False)
        app.add_api_route(f"/{page}/index.txt", _make_rsc_handler(page), methods=["GET"], include_in_schema=False)
        app.add_api_route(f"/{page}/__next._full.txt", _make_rsc_handler(page), methods=["GET"], include_in_schema=False)

    # Static root asset files (images, icons)
    STATIC_ROOT_FILES = [
        "apple-icon.png",
        "icon-dark-32x32.png",
        "icon-light-32x32.png",
        "icon.svg",
        "Quantum_Health_Shield_Emblem-removebg-preview.png",
        "Quantum_Medical_Shield_Emblem-removebg-preview.png",
        "placeholder.jpg",
        "placeholder.svg",
        "placeholder-user.jpg",
        "placeholder-logo.png",
        "placeholder-logo.svg",
    ]

    for asset in STATIC_ROOT_FILES:
        asset_file = FRONTEND / asset
        if asset_file.exists():
            def _make_asset_handler(f_path: Path):
                def _asset_handler():
                    return FileResponse(f_path)
                return _asset_handler
            app.add_api_route(f"/{asset}", _make_asset_handler(asset_file), methods=["GET"], include_in_schema=False)

    if (FRONTEND / "_next").exists():
        app.mount("/_next", StaticFiles(directory=FRONTEND / "_next"), name="next_static")

    if PORTAL.exists():
        app.mount("/portal", StaticFiles(directory=PORTAL), name="portal")

    return current_user, require
