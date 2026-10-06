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

    cmd = ["pnpm", "run", "build"]
    # Check if pnpm is installed or fallback to npx/npm
    try:
        res = subprocess.run(cmd, cwd=FRONTEND_V2, env=env, check=True)
    except FileNotFoundError:
        cmd = ["npx", "next", "build"]
        res = subprocess.run(cmd, cwd=FRONTEND_V2, env=env, check=True)

    if not OUT.exists():
        print(f"Error: {OUT} was not generated.")
        sys.exit(1)

    print(f"Syncing static build from {OUT} to {FRONTEND}...")
    # Preserve key files if they exist
    preserved = ["portal", "index_classic.html", "app.js", "style.css"]

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
