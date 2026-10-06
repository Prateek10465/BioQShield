"""What Alice's and Bob's hospital apps have in common.

Logins and roles, user management, the audit log, key-pool and QKD-session status, the web
UI, and security headers. The sender-specific and receiver-specific routes live in alice.py
and bob.py.

Every route except /api/health, /api/node and /api/auth/login needs a signed-in user, and
every route checks the user's role. Nothing returned by the API contains key material.
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .accounts import ROLES, Accounts, Throttled, User
from .audit import AuditLog
from .common import Config
from .store import Store
from .vault import Vault, VaultError

PORTAL = Path(__file__).resolve().parent.parent / "frontend" / "portal"
MAX_BODY = 2_000_000
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


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

    # ---- web UI ------------------------------------------------------------------------
    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(PORTAL / "hospital.html")

    if PORTAL.exists():
        app.mount("/portal", StaticFiles(directory=PORTAL), name="portal")

    return current_user, require
