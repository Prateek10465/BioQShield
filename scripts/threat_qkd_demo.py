"""End to end: network data -> threat classification -> QKD simulation -> noise / Eve
-> QBER -> Accept / Monitor / Reject.

    python scripts/threat_qkd_demo.py --data-dir data/nsl-kdd          # real NSL-KDD
    python scripts/threat_qkd_demo.py --synthetic                      # stand-in, no download

Put KDDTrain+.txt and KDDTest+.txt (Kaggle: "NSL-KDD") in --data-dir. Outputs (tables,
figures, results.json) go to --out (default results/).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from fusion import experiments as ex, plots  # noqa: E402
from threat import nslkdd, synthetic  # noqa: E402
from threat.classifier import ThreatClassifier, threat_score  # noqa: E402


def hr(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * (66 - len(title))}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "nsl-kdd"))
    ap.add_argument("--synthetic", action="store_true", help="use the synthetic stand-in (NOT NSL-KDD)")
    ap.add_argument("--model", choices=["rf", "logreg"], default="rf")
    ap.add_argument("--engine", choices=["auto", "qiskit", "numpy"], default="auto", help="BB84 engine for the end-to-end sessions")
    ap.add_argument("--qubits", type=int, default=4096, help="qubits per end-to-end session")
    ap.add_argument("--window", type=int, default=60, help="connections per network window")
    ap.add_argument("--quick", action="store_true", help="fewer repeats in the sweeps")
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    # ---- 1. data -----------------------------------------------------------------------
    hr("1. NSL-KDD preprocessing")
    train_f, test_f = (None, None) if a.synthetic else nslkdd.find_files(a.data_dir)
    if train_f is None:
        if not a.synthetic:
            print(f"No NSL-KDD files found under {a.data_dir}.\n"
                  "Download from Kaggle (NSL-KDD) and put KDDTrain+.txt and KDDTest+.txt there,\n"
                  "or rerun with --synthetic to try the pipeline on a stand-in.")
            return 2
        train, test = synthetic.generate(8000, seed=a.seed + 1), synthetic.generate(4000, seed=a.seed + 2, shifted=True)
        source = "SYNTHETIC STAND-IN (not NSL-KDD)"
        print("!! Using SYNTHETIC data with NSL-KDD's schema. Metrics below say nothing about NSL-KDD.")
    else:
        train = nslkdd.load_nslkdd(train_f)
        source = f"NSL-KDD ({train_f.name}"
        if test_f is not None:
            test = nslkdd.load_nslkdd(test_f)
            source += f", {test_f.name})"
        else:
            source += ")"
            test = None
        if test is None or (test["y"] < 0).any():
            print("No labelled test file: holding out 25% of the training file for evaluation.")
            idx = rng.permutation(len(train))
            cut = int(0.75 * len(train))
            train, test = train.iloc[idx[:cut]].reset_index(drop=True), train.iloc[idx[cut:]].reset_index(drop=True)
    print(f"source: {source}")
    for name, df in (("train", train), ("test", test)):
        d = nslkdd.describe(df)
        print(f"  {name}: {d['rows']:,} connections, {d['normal']:,} normal / {d['attack']:,} attack, categories {d['categories']}")
    print("  features: 41 raw -> 3 one-hot categoricals, 3 log+scaled byte counts, scaled numerics; num_outbound_cmds dropped (constant)")

    # ---- 2. classifier -------------------------------------------------------------------
    hr("2. Normal-vs-attack classifier")
    t0 = time.time()
    clf = ThreatClassifier(a.model, seed=a.seed).fit(train)
    m = clf.evaluate(test)
    print(f"  model: {a.model}   trained in {time.time() - t0:.1f}s   evaluated on {m['n']:,} test connections")
    print(f"  accuracy {m['accuracy']:.3f}  precision {m['precision']:.3f}  recall {m['recall']:.3f}  F1 {m['f1']:.3f}  ROC-AUC {m['roc_auc']:.3f}")
    print(f"  confusion {m['confusion']}")
    print(f"  recall by attack family: { {k: round(v, 3) for k, v in m.get('recall_by_category', {}).items()} }")
    plots.plot_classifier(m, clf.top_features(10), str(out / "fig_classifier.png"), source)

    # ---- 3. network windows -> threat score ----------------------------------------------
    hr("3. Threat score per network window (features only; labels never used)")
    normal, attack = test[test["y"] == 0], test[test["y"] == 1]
    k_att = max(1, a.window // 5)
    windows = {
        "normal traffic": normal.sample(a.window, random_state=a.seed),
        "mixed (20% attack)": __import__("pandas").concat([normal.sample(a.window - k_att, random_state=a.seed), attack.sample(k_att, random_state=a.seed)]),
        "attack traffic": attack.sample(a.window, random_state=a.seed),
    }
    threat = {}
    for name, w in windows.items():
        p = clf.attack_probability(w.reset_index(drop=True))
        threat[name] = threat_score(p)
        print(f"  {name:<20} threat score {threat[name]:.2f}   ({int((p >= 0.5).sum())}/{len(p)} connections flagged)")

    # ---- 4-8. QKD + decision ------------------------------------------------------------
    hr("4-7. BB84 sessions, noise / eavesdropper, QBER, decision")
    from quantum.bb84_qiskit import qiskit_available

    engine = a.engine
    if engine == "auto":
        engine = "qiskit" if qiskit_available() else "numpy"
        if engine == "numpy":
            print("  Qiskit is not installed: using the numpy BB84 engine (pip install qiskit qiskit-aer for circuits)")
    elif engine == "qiskit" and not qiskit_available():
        print("  --engine qiskit requested but Qiskit is not installed")
        return 2
    t0 = time.time()
    mat = ex.threat_matrix(threat, n_qubits=a.qubits, engine=engine, seed=a.seed + 11)
    print(f"  engine: {mat['engine'].iloc[0]}   {a.qubits:,} qubits per session   ({time.time() - t0:.1f}s)")
    hr("8. Threat information and QKD layer together")
    for q, g in mat.groupby("quantum", sort=False):
        print(f"\n  quantum channel: {q}   QBER {g['qber'].iloc[0]:.1%}   secret key {g['key_bits'].iloc[0]} bits")
        for _, r in g.iterrows():
            print(f"    {r['traffic']:<20} threat {r['threat']:.2f} -> {r['action']:<7} {r['why']}")
    plots.plot_integrated(mat, str(out / "fig_integrated.png"), note=f"data: {source}; BB84 engine: {mat['engine'].iloc[0]}")
    mat.to_csv(out / "integrated_decisions.csv", index=False)

    hr("Link over time (adaptive policy, Monitor escalation)")
    quiet, hot = threat["normal traffic"], threat["attack traffic"]
    tl = ex.timeline(
        [("commissioned link", 8, 0.02, 0.0, quiet), ("Eve joins (15%)\ntraffic quiet", 4, 0.02, 0.15, quiet),
         ("Eve + attack\ntraffic", 4, 0.02, 0.15, hot), ("Eve gone", 5, 0.02, 0.0, quiet)],
        n_qubits=a.qubits, seed=a.seed + 21,
    )
    tl.to_csv(out / "timeline.csv", index=False)
    plots.plot_timeline(tl, str(out / "fig_timeline.png"))
    for _, r in tl.iterrows():
        print(f"  #{r['session']:<3} {r['phase'].replace(chr(10), ' '):<28} QBER {r['qber']:>5.1%}  threat {r['threat']:.2f}  {r['action']:<7} {'; '.join(r['why'].split('; ')[::-1][:1] if 'escalated' in r['why'] else r['why'].split('; ')[:1])}")

    # ---- 6. how channel conditions affect key security -----------------------------------
    hr("6. Channel conditions vs key security (numpy engine, 8192 qubits)")
    reps = 12 if a.quick else 30
    sw = ex.sweep(repeats=reps, seed=a.seed)
    sw.to_csv(out / "sweep_noise_eve.csv", index=False)
    plots.plot_sweep(sw, str(out / "fig_qber_vs_conditions.png"))
    plots.plot_decision_map(sw, str(out / "fig_decision_map.png"))
    pivot = sw.pivot(index="noise", columns="eve_rate", values="key_bits").round(0).astype(int)
    pivot.index = [f"{n:.0%}" for n in pivot.index]
    pivot.columns = ["no Eve" if c == 0 else f"Eve {c:.0%}" for c in pivot.columns]
    print("  mean secret key bits per session (rows: channel noise)")
    print("  " + pivot.to_string().replace("\n", "\n  "))

    hr("Optional: static vs adaptive policy")
    trials = 80 if a.quick else 300
    pc = ex.policy_comparison(trials=trials, seed=a.seed + 7)
    pc.to_csv(out / "policy_comparison.csv", index=False)
    plots.plot_policy_comparison(pc, str(out / "fig_policy_comparison.png"))
    print(f"  share of sessions flagged (Monitor or Reject), {trials} trials per scenario, link baseline 2%")
    print(f"  {'scenario':<24}{'static':>9}{'adaptive':>10}")
    for _, r in pc.iterrows():
        print(f"  {r['scenario']:<24}{r['static_flagged']:>9.1%}{r['adaptive_flagged']:>10.1%}")

    (out / "results.json").write_text(json.dumps(
        {"data_source": source, "classifier": {"model": a.model, **{k: v for k, v in m.items() if k != "recall_by_category"}, "recall_by_category": m.get("recall_by_category")},
         "threat_scores": threat, "engine": mat["engine"].iloc[0], "qubits": a.qubits}, indent=2, default=float))
    print(f"\nWrote tables, figures and results.json to {out}/")
    if "SYNTHETIC" in source:
        print("Reminder: the classifier numbers came from synthetic data, not NSL-KDD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
