#!/usr/bin/env python
"""Start a reliable Cloudflare Tunnel for BioQShield Hospital Command Centre."""
import os
import re
import shutil
import subprocess
import sys
import time

PORT = int(os.environ.get("BIOQSHIELD_PORT", 8001))
TARGET_URL = f"http://127.0.0.1:{PORT}"

def find_cloudflared() -> str:
    which = shutil.which("cloudflared")
    if which:
        return which
    candidates = [
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\cloudflared\cloudflared.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "cloudflared"

def main():
    exe = find_cloudflared()
    print("=" * 64)
    print("  BioQShield — Starting Cloudflare Public Tunnel")
    print(f"  Target: {TARGET_URL}")
    print("=" * 64)
    print("Connecting to Cloudflare edge nodes (HTTP/2 fallback enabled)...")

    cmd = [
        exe,
        "tunnel",
        "--url", TARGET_URL,
        "--protocol", "http2",
        "--no-autoupdate",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print(f"\n[ERROR] cloudflared executable not found at '{exe}'.")
        print("Install it via: winget install --id Cloudflare.cloudflared")
        sys.exit(1)

    tunnel_url = None
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match and not tunnel_url:
                tunnel_url = match.group(0)
                print("\n" + "#" * 68)
                print("#" + " " * 66 + "#")
                print(f"#   PUBLIC TUNNEL LIVE:  {tunnel_url:<41} #")
                print("#" + " " * 66 + "#")
                print("#   DEMO CREDENTIALS:                                              #")
                print("#     Doctor:       dr.rao / clinician-demo-pass                    #")
                print("#     Admin:        admin  / admin-demo-pass                        #")
                print("#     Auditor:      auditor / auditor-demo-pass                     #")
                print("#" + " " * 66 + "#")
                print("#" * 68 + "\n")
                print("Press Ctrl+C to stop the tunnel.\n")
            elif "ERR" in line or "error" in line.lower():
                print(line.strip())
    except KeyboardInterrupt:
        print("\nStopping tunnel...")
    finally:
        proc.terminate()

if __name__ == "__main__":
    main()
