"""Terminal version of the demo. Use it as a backup if the browser or projector misbehaves.

    python cli.py                 clean link
    python cli.py --noise 5       noisy link, still secure
    python cli.py --eve           Eve intercepts everything -> detected, record blocked
    python cli.py --eve --seed 3  same run every time (rehearsal)
"""
import argparse

from backend.pipeline import run_session

ICON = {"ok": "[ ok ]", "abort": "[STOP]", "skipped": "[ -- ]"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--qubits", type=int, default=8192)
    ap.add_argument("--noise", type=float, default=2.0, help="channel noise in percent")
    ap.add_argument("--eve", action="store_true", help="enable intercept-resend eavesdropper")
    ap.add_argument("--eve-rate", type=float, default=100.0, help="percent of qubits Eve intercepts")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()

    d = run_session(
        n_qubits=a.qubits, noise=a.noise / 100, eve=a.eve, eve_rate=a.eve_rate / 100, seed=a.seed
    )
    for s in d["stages"]:
        print(f"{ICON[s['status']]} {s['title']}")
        for k, v in s["metrics"]:
            print(f"         {k:<24}{v}")
    print()
    if d["status"] == "secure":
        print("SECURE LINK. Bob decrypted the record:")
        print(d["record"]["decrypted"])
    else:
        print(f"ABORTED: {d['reason']}")
        print(d["record"]["note"] if d["record"] else "")


if __name__ == "__main__":
    main()
