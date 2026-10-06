"""Start the whole system as separate processes: link, Hospital B (Bob), Hospital A (Alice),
and optionally a stub ETSI key-management entity.

Used by `python scripts/run_all.py` for local use and by the end-to-end tests, so what the
tests exercise is exactly what you run. Every service is its own OS process and they talk
over real HTTP.
"""
from __future__ import annotations

import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent

# Demo logins for local runs only. The services themselves have no built-in passwords.
DEMO = {"admin": "admin-demo-pass", "dr.rao": "clinician-demo-pass", "auditor": "auditor-demo-pass"}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def free_stale_port(port: int) -> None:
    """If an orphaned local process is holding this port, terminate it."""
    try:
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))
            return
    except OSError:
        pass
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"],
                text=True, timeout=5
            )
            for line in out.strip().splitlines():
                pid = line.strip()
                if pid and pid.isdigit() and int(pid) != os.getpid():
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
        except Exception:
            pass


class Stack:
    def __init__(self, data_dir: Path, *, etsi: bool = False, ports: dict | None = None, env: dict | None = None,
                 fresh: bool = False):
        self.data_dir = Path(data_dir)
        self.etsi = etsi
        p = ports or {}
        self.ports = {k: p.get(k) or free_port() for k in ("alice", "bob", "link", "kme")}
        if ports:
            for port in self.ports.values():
                free_stale_port(port)
        self.extra_env = env or {}
        self.procs: dict[str, subprocess.Popen] = {}
        if fresh and self.data_dir.exists():
            def _on_rm_error(func, path, exc_info):
                import stat
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass
            try:
                shutil.rmtree(self.data_dir, onexc=_on_rm_error)
            except Exception:
                shutil.rmtree(self.data_dir, ignore_errors=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ---- addresses --------------------------------------------------------
    def url(self, name: str) -> str:
        return f"http://127.0.0.1:{self.ports[name]}"

    alice = property(lambda self: self.url("alice"))
    bob = property(lambda self: self.url("bob"))
    link = property(lambda self: self.url("link"))
    kme = property(lambda self: self.url("kme"))

    # ---- lifecycle --------------------------------------------------------
    def _auth_key(self) -> str:
        f = self.data_dir / ".auth_key"
        if not f.exists():
            f.write_text(secrets.token_hex(32))
        return f.read_text().strip()

    def _env(self) -> dict:
        env = dict(os.environ)
        env.update({
            "PYTHONPATH": str(ROOT),
            "QKD_DATA_DIR": str(self.data_dir),
            "QKD_AUTH_KEY": self._auth_key(),
            "QKD_CHANNEL_URL": self.link,
            "QKD_BOB_URL": self.bob,
            "QKD_ALICE_PUBLIC_URL": self.alice,
            "QKD_BOB_PUBLIC_URL": self.bob,
            "QKD_CHANNEL_PUBLIC_URL": self.link,
            "QKD_ADMIN_PASSWORD": DEMO["admin"],
            "QKD_DEMO_USERS": "1",
            "QKD_CLINICIAN_PASSWORD": DEMO["dr.rao"],
            "QKD_AUDITOR_PASSWORD": DEMO["auditor"],
            "STUB_ALLOW_CONTROL": "1",
            "STUB_SAE_KEYS": "hospital-a:stub-key-a,hospital-b:stub-key-b",
        })
        if self.etsi:
            env.update({"QKD_KEY_SOURCE": "etsi014", "QKD_KME_URL": self.kme})
        env.update(self.extra_env)
        return env

    def _spawn(self, name: str, app: str, port: int, env: dict, factory: bool) -> None:
        logs = self.data_dir / "logs"
        logs.mkdir(exist_ok=True)
        cmd = [sys.executable, "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port),
               "--log-level", "warning"]
        if factory:
            cmd.insert(4, "--factory")
        log = open(logs / f"{name}.log", "ab")
        self.procs[name] = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=log)

    def start(self, timeout: float = 45) -> "Stack":
        env = self._env()
        self._spawn("link", "nodes.channel:app", self.ports["link"], env, False)
        if self.etsi:
            self._spawn("kme", "nodes.etsi_stub:app", self.ports["kme"], env, False)
        # Each hospital gets its own KME credentials when running against the ETSI stub.
        for name, mod, key in (("bob", "nodes.bob:create_app", "stub-key-b"), ("alice", "nodes.alice:create_app", "stub-key-a")):
            e = dict(env, QKD_KME_API_KEY=key)
            self._spawn(name, mod, self.ports[name], e, True)
        self._wait(timeout)
        return self

    def _wait(self, timeout: float) -> None:
        deadline = time.time() + timeout
        pending = {n: self.url(n) for n in self.procs}
        while pending and time.time() < deadline:
            for n, u in list(pending.items()):
                if self.procs[n].poll() is not None:
                    raise RuntimeError(f"{n} exited early:\n{self.log_tail(n)}")
                try:
                    if httpx.get(u + "/api/health", timeout=1).status_code == 200:
                        pending.pop(n)
                except httpx.HTTPError:
                    pass
            time.sleep(0.2)
        if pending:
            raise RuntimeError(f"services did not start: {list(pending)}\n" + "\n".join(self.log_tail(n) for n in pending))

    def log_tail(self, name: str, lines: int = 25) -> str:
        f = self.data_dir / "logs" / f"{name}.log"
        return "\n".join(f.read_text(errors="replace").splitlines()[-lines:]) if f.exists() else ""

    def stop(self) -> None:
        for p in self.procs.values():
            if p.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.terminate()
        for p in self.procs.values():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        self.procs.clear()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
