# Threat classification + QKD security decision

Workflow: **network data → threat classification → BB84 simulation → noise / eavesdropper → QBER → Accept / Monitor / Reject**

```bash
pip install -r requirements.txt
# put KDDTrain+.txt and KDDTest+.txt (Kaggle: "NSL-KDD") in data/nsl-kdd/
python scripts/threat_qkd_demo.py                      # real NSL-KDD, Qiskit engine if installed
python scripts/threat_qkd_demo.py --synthetic --quick  # no download: synthetic stand-in
python -m pytest -q tests/test_threat.py tests/test_policy.py tests/test_link_fusion.py tests/test_bb84_qiskit.py
```

Options: `--engine auto|qiskit|numpy`, `--qubits 4096`, `--model rf|logreg`, `--out DIR`.
Outputs: tables (`*.csv`), `results.json` and figures. A run on the synthetic stand-in is saved in `docs/threat_qkd_example/`.

## What is where

| Task | Code |
|---|---|
| 1. Preprocess NSL-KDD | `threat/nslkdd.py`: tolerant loader (header or not, 41-43 columns, `normal`/`anomaly` labels), one-hot for `protocol_type`/`service`/`flag`, log+scale for byte counts, scaling, drops constant `num_outbound_cmds`, unseen categories ignored |
| 2. Classifier | `threat/classifier.py`: preprocessing + random forest (or logistic regression) in one scikit-learn pipeline; accuracy, precision, recall, F1, ROC-AUC, confusion matrix, recall per attack family |
| 3. BB84 in Qiskit | `quantum/bb84_qiskit.py`: one circuit per photon (X/H prepare, optional Eve measure-and-resend, H/measure); returns the same `Transmission` as the numpy engine |
| 4. Noise and Eve | readout-error noise in Aer; intercept-resend Eve with adjustable share and start time (`eve_rate`, `eve_start`) |
| 5. QBER | `quantum/bb84.py` `estimate_qber` (25% of the sifted key revealed, plus a 4-sigma upper bound) |
| 6. Channel conditions vs key security | `fusion/experiments.py` `sweep`; figures `fig_qber_vs_conditions.png`, `fig_decision_map.png` |
| 7. Accept / Monitor / Reject | `fusion/policy.py` |
| 8. Threat + QKD together | `scripts/threat_qkd_demo.py`, `fig_integrated.png`, `fig_timeline.png` |
| Optional adaptive policy | `fusion/policy.py` `LinkController(mode="adaptive")` |

## How the two layers meet

The classifier scores a window of connections from features only (labels are never read); the window's **threat score** is the mean attack probability, 0 to 1. The QKD session gives QBER, its upper bound and the secret key length.

**QBER is physics and the threat score is context.** The threat score can make the decision stricter and never looser. The 11% limit and the 256-bit key requirement apply however benign the traffic looks (there is a test for this: `test_threat_can_only_tighten`).

| Action | Meaning | When |
|---|---|---|
| ACCEPT | use the key | QBER within the accept limit, enough key, and not significantly above this link's baseline |
| MONITOR | withhold the key, run a confirmation session; 3 Monitors in a row become Reject | ambiguous: QBER above the accept limit but below 11% (noise or a partial Eve), no usable key, upper bound crosses 11%, QBER 4+ sigma above baseline, or clean QBER while network threat is high |
| REJECT | discard the key, send nothing, rotate keys if one was in use | QBER above 11%; QBER above the accept limit while threat is high (≥ 0.8); QBER 8+ sigma above baseline; escalated Monitor |

**Static policy:** accept ≤ 5%, reject > 11%.
**Adaptive policy:** (1) the link's own noise baseline is learned from accepted, low-threat sessions (exponentially forgotten counts); a link that is steadily noisy gets a higher accept limit (baseline + 3 points, capped at 8%), and a reading that is statistically far above baseline is flagged even when it is below 5%. (2) The threat score shrinks the headroom above the baseline (never below it).

## Results (synthetic stand-in data; the QKD parts do not depend on the dataset)

Mean secret key bits per 8192-qubit session (`sweep_noise_eve.csv`): 2,986 bits on a perfect link, 1,790 at 2% noise, 847 at 5%, 193 at 7% (already below the floor), none from 10%. With Eve on half the photons no key survives at any noise level. The key length drops below the 256-bit AES-256 floor at about 7% noise, before the 11% theoretical limit, because of finite-size margins and error-correction leakage.

Static vs adaptive, share of sessions flagged (300 trials each, link commissioned at 2% noise, 8192 qubits):

| Scenario | Static | Adaptive |
|---|---|---|
| normal, 2% noise | 0.0% | 0.0% |
| benign drift to 3% | 0.0% | 5.0% |
| benign drift to 4% | 5.7% | 49.0% |
| Eve on 5% of photons | 0.0% | 7.7% |
| Eve on 10% | 17.0% | 74.0% |
| Eve on 20% / 50% / 100% | 99.7% / 100% / 100% | 100% |

**This is a trade-off, not a free win.** A weak eavesdropper (Eve on 10% adds about 2.5 points of QBER) is caught four times as often, and benign noise drift is flagged far more often. BB84 cannot tell the two apart from one QBER number; the adaptive policy buys sensitivity with false alarms. Eve on 5% of photons is practically undetectable either way. Monitor's confirmation session and escalation are how the cost is contained.

## Limits: read before trusting any number

- **No NSL-KDD result is reported here.** The dataset is not in this repository and was not available when this was built. The saved example uses `threat/synthetic.py`, a generator with NSL-KDD's schema and invented distributions. Its classifier metrics (accuracy ≈ 0.98) say nothing about NSL-KDD. Run the demo on the real files before quoting any classifier figure. Expect lower numbers on the real KDDTest+, which is known to be much harder than its training file.
- **Qiskit was not run when this was written.** The Qiskit module's logic was checked against a throwaway single-qubit emulator, which proves the circuit construction, bit ordering and the way results are read back. It does not prove the real Qiskit/Aer calls run; the code reuses the API calls of the existing `quantum/qiskit_demo.py`. `tests/test_bb84_qiskit.py` is the real check (statistical agreement with the numpy engine, independence of random outcomes across circuits in a batch). Run it once with Qiskit installed. If the independence test fails, switch `transmit_qiskit` to one run per circuit.
- **The link between traffic and the quantum channel is an assumption.** NSL-KDD describes classical connections; it says nothing about what is happening to photons. In the demo the experimenter chooses the physical scenario and which traffic window accompanies it. The design claim is only: attack traffic on the classical side of the link (key-management and authentication channels) is a reason to be stricter about keys, and never a reason to be looser.
- **Leakage is estimated in sweeps** (1.16 × n × h2(q) + 40 bits) rather than running Cascade each time; it was slightly more pessimistic than the repo's Cascade in testing (`test_fast_leak_estimate_is_not_optimistic_vs_real_cascade`). End-to-end demo sessions use the same estimate; pass `full_cascade=True` to `run_link_session` for the real one.
- Key length uses the repo's simplified finite-key margin, not a composable proof. Only intercept-resend attacks are modelled.
- A patient attacker could raise Eve's activity slowly to drag the learned baseline up. The baseline learns only from accepted sessions, and the accept limit is capped at 8%, which bounds the drift but does not remove it.
- The matrix in `fig_integrated.png` is one seeded session per cell. The rates in the table above are the evidence; the matrix illustrates them.
