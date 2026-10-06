#!/usr/bin/env python
"""Build FrontendV2 and sync static assets into frontend/ for FastAPI delivery.

Usage:
    python scripts/build_frontend.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_V2 = ROOT / "FrontendV2"
FRONTEND = ROOT / "frontend"
OUT = FRONTEND_V2 / "out"


def main():
    print(f"Building FrontendV2 at {FRONTEND_V2}...")
    env = os.environ.copy()
    env["NEXT_EXPORT"] = "true"

    pnpm = shutil.which("pnpm")
    npx = shutil.which("npx")
    if pnpm:
        cmd = [pnpm, "run", "build"]
    elif npx:
        cmd = [npx, "next", "build"]
    elif (FRONTEND / "index.html").exists():
        print("Node tooling not found; using the committed static FrontendV2 build.")
        return
    else:
        raise RuntimeError(
            "Node tooling not found and no committed static frontend is available. "
            "Install Node.js and pnpm, then run this command again."
        )

    subprocess.run(cmd, cwd=FRONTEND_V2, env=env, check=True)

    if not OUT.exists():
        print(f"Error: {OUT} was not generated.")
        sys.exit(1)

    print(f"Syncing static build from {OUT} to {FRONTEND}...")
    for item in OUT.iterdir():
        dest = FRONTEND / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    print("Frontend build and integration complete!")


if __name__ == "__main__":
    main()
