"""Staff accounts for a hospital node: passwords, login tokens, roles, brute-force throttle.

Roles
    clinician  creates and sends records (Alice) or reads the inbox (Bob)
    auditor    reads the audit log, key-pool counts and QKD session history; never record contents
    admin      manages users and rotates keys; never reads record contents

Passwords are hashed with scrypt and a per-user salt. Login tokens are random, shown to the
client once, and stored only as a SHA-256 hash, so a leaked database cannot be replayed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from .store import Store

ROLES = ("clinician", "auditor", "admin", "doctor", "worker")
TOKEN_TTL = 8 * 3600
MIN_PASSWORD = 10
THROTTLE_FAILS = 5
THROTTLE_WINDOW = 300

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32, "maxmem": 64 * 1024 * 1024}


class Throttled(Exception):
    def __init__(self, retry_after: int):
        super().__init__(f"too many failed logins, try again in {retry_after}s")
        self.retry_after = retry_after


@dataclass(frozen=True)
class User:
    username: str
    role: str


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def check_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), **_SCRYPT)
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except (ValueError, TypeError):
        return False


_DUMMY = hash_password("dummy-password-for-timing")


class Accounts:
    def __init__(self, store: Store, now=time.time):
        self.store, self._now = store, now
        self._fails: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    # ---- users ---------------------------------------------------------------
    def create_user(self, username: str, password: str, role: str, enforce_policy: bool = True) -> bool:
        role = (role or "").strip().lower()
        if role not in ROLES:
            raise ValueError(f"role must be one of {', '.join(ROLES)}")
        if enforce_policy and len(password) < MIN_PASSWORD:
            raise ValueError(f"password must be at least {MIN_PASSWORD} characters")
        return self.store.create_user(username, hash_password(password), role)

    # ---- login ---------------------------------------------------------------
    def _check_throttle(self, username: str) -> None:
        now = self._now()
        with self._lock:
            q = self._fails[username]
            while q and q[0] <= now - THROTTLE_WINDOW:
                q.popleft()
            if len(q) >= THROTTLE_FAILS:
                raise Throttled(int(q[0] + THROTTLE_WINDOW - now) + 1)

    def authenticate(self, username: str, password: str) -> User | None:
        """Returns the user, or None for a wrong name/password. Raises Throttled after repeated failures."""
        self._check_throttle(username)
        row = self.store.get_user(username)
        ok = check_password(password, row["pw_hash"] if row else _DUMMY)  # same work either way
        if row and ok and not row["disabled"]:
            with self._lock:
                self._fails.pop(username, None)
            return User(row["username"], row["role"])
        with self._lock:
            self._fails[username].append(self._now())
        return None

    def issue_token(self, user: User) -> tuple[str, float]:
        token = secrets.token_urlsafe(32)
        expires = self._now() + TOKEN_TTL
        self.store.save_token(hashlib.sha256(token.encode()).hexdigest(), user.username, expires)
        return token, expires

    def resolve(self, token: str) -> User | None:
        row = self.store.get_token(hashlib.sha256(token.encode()).hexdigest())
        if row is None or row["expires"] <= self._now():
            return None
        user = self.store.get_user(row["username"])
        if user is None or user["disabled"]:
            return None
        return User(user["username"], user["role"])

    def revoke(self, token: str) -> None:
        self.store.delete_token(hashlib.sha256(token.encode()).hexdigest())

    # ---- first start ---------------------------------------------------------
    def seed(self, admin_password: str, demo: bool, clinician_password: str, auditor_password: str,
             node_name: str, log=print) -> None:
        """Create the first accounts. Passwords come from the environment, never from source code.

        With no admin password configured and no users yet, a random one is generated and
        printed once, so a fresh install is never left with a guessable login.
        """
        if self.store.count_users() == 0 and not admin_password:
            admin_password = secrets.token_urlsafe(12)
            log(f"[{node_name}] no QKD_ADMIN_PASSWORD set. Generated admin password (shown once): {admin_password}")
        if admin_password:
            self.create_user("admin", admin_password, "admin", enforce_policy=False)
        if demo:
            if clinician_password:
                self.create_user("dr.rao", clinician_password, "clinician", enforce_policy=False)
            if auditor_password:
                self.create_user("auditor", auditor_password, "auditor", enforce_policy=False)
