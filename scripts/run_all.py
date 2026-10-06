#!/usr/bin/env python
"""Run the whole system locally: link service, Hospital B, Hospital A (and optionally a stub KME).

    python scripts/run_all.py            simulated BB84 link (default)
    python scripts/run_all.py --etsi     hospitals get keys from a stub ETSI GS QKD 014 KME instead
    python scripts/run_all.py --fresh    wipe ./data first

Open http://localhost:8001 (Hospital A) and http://localhost:8002 (Hospital B); the link
console, where you switch Eve on and off, is at http://localhost:8003.
Ctrl-C stops everything.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.stack import DEMO, ROOT, Stack  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--etsi", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--data", default=str(ROOT / "data"))
    a = ap.parse_args()
    ports = {"alice": 8001, "bob": 8002, "link": 8003, "kme": 8004}
    stack = Stack(Path(a.data), etsi=a.etsi, ports=ports, fresh=a.fresh)
    try:
        stack.start()
    except Exception as e:
        stack.stop()
        sys.exit(f"could not start: {e}")
    print(f"""
MediQKD is running ({'ETSI 014 stub KME' if a.etsi else 'simulated BB84 link'})

  Hospital A (sends)   {stack.alice}
  Hospital B (receives) {stack.bob}
  Link console (Eve)   {stack.link}
{'  Stub KME             ' + stack.kme if a.etsi else ''}
Demo logins (local use only):
  {'  '.join(f'{u} / {p}' for u, p in DEMO.items())}

Ctrl-C to stop. Logs: {stack.data_dir / 'logs'}
""")
    try:
        while all(p.poll() is None for p in stack.procs.values()):
            time.sleep(1)
        dead = [n for n, p in stack.procs.items() if p.poll() is not None]
        print(f"service exited: {dead}\n" + "\n".join(stack.log_tail(n) for n in dead))
    except KeyboardInterrupt:
        pass
    finally:
        stack.stop()


if __name__ == "__main__":
    main()
