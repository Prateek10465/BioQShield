"""FastAPI application for BioQShield: Quantum-Secure Biomedical Communication.
Provides endpoints:
- GET  /api/health
- POST /api/run
- GET  /api/scenarios
- POST /api/qiskit-demo
- Static frontend mounting with Next.js V2 visual interface & legacy backward compatibility
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from backend.threat import service
except ImportError:
    from threat import service

app = FastAPI(
    title="BioQShield API",
    version="1.0.0",
    description="Quantum-Secure Communication for Biomedical Networks",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    return service.run_full(**req.model_dump())


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    """Execute the predefined traffic/channel scenarios."""
    return service.scenarios()


@app.post("/api/qiskit-demo")
def qiskit_demo(req: QiskitRequest) -> dict:
    """Run real Qiskit circuits on Qiskit Aer in an isolated subprocess."""
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
        raise HTTPException(503, f"Qiskit run failed ({detail}). Is qiskit and qiskit-aer installed?")
    return json.loads(proc.stdout.strip().splitlines()[-1])


FRONTEND = ROOT / "frontend"


@app.get("/app.js")
def app_js() -> PlainTextResponse:
    return PlainTextResponse("// Legacy hospital UI removed; use the FrontendV2 build.\n")


@app.get("/style.css")
def style_css() -> PlainTextResponse:
    return PlainTextResponse("/* Legacy hospital UI removed; use the FrontendV2 build. */\n")

# Helper route for clean subpath URLs without trailing slashes
KNOWN_PAGES = [
    "dashboard",
    "quantum-console",
    "secure-transfer",
    "security-analysis",
    "security-dashboard",
    "scenario-comparison",
    "transfer-history",
    "about",
    "login",
    "profile",
    "admin",
]

for page in KNOWN_PAGES:
    def _make_handler(p: str):
        def _handler():
            p_dir = FRONTEND / p / "index.html"
            if p_dir.exists():
                return FileResponse(p_dir)
            p_file = FRONTEND / f"{p}.html"
            if p_file.exists():
                return FileResponse(p_file)
            return FileResponse(FRONTEND / "index.html")
        return _handler
    app.add_api_route(f"/{page}", _make_handler(page), methods=["GET"], include_in_schema=False)
    app.add_api_route(f"/{page}/", _make_handler(page), methods=["GET"], include_in_schema=False)

for page in KNOWN_PAGES:
    def _make_rsc_handler(p: str):
        def _rsc_handler():
            f = FRONTEND / p / "index.txt"
            if f.exists():
                return FileResponse(f, media_type="text/plain")
            f2 = FRONTEND / f"{p}.txt"
            if f2.exists():
                return FileResponse(f2, media_type="text/plain")
            raise HTTPException(404)
        return _rsc_handler
    app.add_api_route(f"/{page}.txt", _make_rsc_handler(page), methods=["GET"], include_in_schema=False)
    app.add_api_route(f"/{page}/index.txt", _make_rsc_handler(page), methods=["GET"], include_in_schema=False)


if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")


# Train classifier lazily in background
threading.Thread(target=service.get_state, daemon=True).start()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
