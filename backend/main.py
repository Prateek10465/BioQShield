"""FastAPI app: JSON API under /api, dashboard served from /frontend.

Run from the project root:
    uvicorn backend.main:app --reload
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .pipeline import run_session

app = FastAPI(title="QKD Health Link", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class RunRequest(BaseModel):
    n_qubits: int = Field(8192, ge=512, le=32768, description="Qubits Alice sends")
    noise: float = Field(0.02, ge=0.0, le=0.2, description="Channel bit-flip probability")
    eve: bool = Field(False, description="Enable an intercept-resend eavesdropper")
    eve_rate: float = Field(1.0, ge=0.0, le=1.0, description="Fraction of qubits Eve intercepts")
    eve_start: float = Field(0.0, ge=0.0, le=0.95, description="Eve joins at this fraction of the stream")
    seed: int | None = Field(None, description="Set for a reproducible run")


class QiskitRequest(BaseModel):
    n: int = Field(12, ge=4, le=24)
    eve: bool = False
    noise: float = Field(0.0, ge=0.0, le=0.2)
    seed: int | None = None


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    return run_session(**req.model_dump())


ROOT = Path(__file__).resolve().parent.parent


@app.post("/api/qiskit-demo")
def qiskit_demo(req: QiskitRequest) -> dict:
    """Run real Qiskit circuits in a child process.

    Qiskit 2.x segfaults if circuits are built from several different worker threads
    in turn, and a web server's thread pool does exactly that. A subprocess costs about
    a second of start-up but cannot take the server down.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "quantum.qiskit_demo", json.dumps(req.model_dump())],
            cwd=ROOT, capture_output=True, text=True, timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(503, "Qiskit run timed out.") from exc
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or ["unknown error"])[-1]
        raise HTTPException(503, f"Qiskit run failed ({detail}). Is qiskit and qiskit-aer installed?")
    return json.loads(proc.stdout.strip().splitlines()[-1])


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
