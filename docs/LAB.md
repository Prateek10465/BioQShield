# MediQKD: quantum-secured patient record transfer

Hackathon prototype for Track 2 (Quantum Cryptography and Communication).

Alice (Hospital A) sends a patient record to Bob (Hospital B). The AES-256 key comes from a simulated BB84 quantum key exchange. If an eavesdropper (Eve) touches the qubits, the error rate jumps, the session aborts, and the record is never sent.

Everything is a software simulation. The record is synthetic. No real patient data, ever.

## Run it (2 minutes)

```bash
pip install -r requirements.txt
uvicorn backend.main:app --port 8000
# open http://localhost:8000
```

No Node, no build step, no CDN. The dashboard is plain HTML/JS/CSS served by the backend, so it works offline on conference wifi.

Terminal backup if the browser misbehaves on stage:

```bash
python cli.py                  # clean link
python cli.py --noise 5        # noisy link, still secure
python cli.py --eve            # Eve listening: detected, record blocked
python cli.py --eve --seed 3   # identical every time (rehearsal)
python -m pytest -q            # 29 tests
```

## The 2-minute demo

Use the three preset buttons. All three set 8,192 qubits and are reliable (100 of 100 seeds behaved as below).

| Preset | What you say | What appears |
|---|---|---|
| **Clean link** | "Normal transfer. Key made from qubits, record encrypted and decrypted." | Green. QBER about 2%, about 1,700 secret bits, Alice and Bob key fingerprints match, record decrypted. |
| **Eve listening** | "Now Eve taps the line. She must measure each qubit, and measuring disturbs it." | Red. QBER about 27%, steps 4 to 6 show "Not reached", record blocked. |
| **Noisy link** | "Noise alone doesn't trigger a false alarm." | Green. QBER about 5%, about 700 secret bits. |

Extras to show if time allows:
- Tick **She joins halfway through**. The chart shows clean bars, then red bars from the midpoint.
- Lower **Share she intercepts** to 10 to 20%. A partial attack is harder to see, and the key length shrinks accordingly.
- Open **Run it on real quantum circuits (Qiskit)** to show actual X/H/measure circuits on Aer.

## How the pipeline works

| Step | Code | What it does |
|---|---|---|
| 1. Transmit | `quantum/bb84.py` `transmit` | Alice sends random bits in random bases; optional intercept-resend Eve; channel bit-flip noise; Bob measures in random bases |
| 2. Sift | `bb84.sift` | Keep positions where bases matched (about 50%) |
| 3. Estimate QBER | `bb84.estimate_qber` | Reveal 25% of the sifted key, count errors. Above 11% means abort |
| 4. Error correction | `quantum/postprocess.py` `cascade`, `reconcile` | Cascade with block parities and binary search. Every revealed parity is counted as leaked. Retries with a reshuffle if verification fails |
| 5. Privacy amplification | `postprocess.privacy_amplify` | Toeplitz universal hash. Output length = n(1 - h2(q_upper)) - leaked - 60 |
| 6. Encrypt | `backend/crypto.py` | SHA-256 to a 32-byte key, AES-256-GCM, Bob decrypts. Fingerprints shown, never the key |

`backend/pipeline.py` strings these together and handles aborts.

## API contract

`POST /api/run`

```json
{ "n_qubits": 8192, "noise": 0.02, "eve": false, "eve_rate": 1.0, "eve_start": 0.0, "seed": null }
```

`noise` and `eve_rate` are fractions (0.02 = 2%). `eve_start` is where in the stream Eve joins (0 to 0.95). `seed` makes a run reproducible.

Response (abridged):

```json
{
  "status": "secure | aborted",
  "reason": null,
  "stats": { "qber_est": 0.024, "qber_upper": 0.04, "threshold": 0.11, "final_key_bits": 1708,
             "ec_rounds": 1, "sim_eve_known_fraction": 0.0 },
  "qber_trace": [ { "bin": 0, "start": 0, "end": 512, "n": 64, "qber": 0.02 } ],
  "stages": [ { "id": "qber", "title": "...", "status": "ok | abort | skipped",
                "metrics": [["Measured QBER", "2.4%"]], "note": "..." } ],
  "record": { "status": "delivered | blocked | failed", "plaintext": "...",
              "ciphertext_hex": "...", "decrypted": "..." }
}
```

`POST /api/qiskit-demo` takes `{ "n": 12, "eve": false, "noise": 0.0, "seed": null }` and returns per-qubit rows plus an ASCII circuit. `GET /api/health` returns `{"ok": true}`. Interactive docs are at `/docs`.

## Who owns what (team of four)

| Person | Files |
|---|---|
| Lead: quantum core and integration | `quantum/bb84.py`, `quantum/qiskit_demo.py`, `backend/pipeline.py` |
| Post-processing | `quantum/postprocess.py`, `tests/test_postprocess.py` |
| Backend and crypto | `backend/main.py`, `backend/crypto.py`, `tests/test_api.py` |
| Frontend, slides, demo script | `frontend/*` |

## Be upfront about these (judges will ask)

- **It is a simulation.** BB84 is simulated from exact measurement statistics. Qiskit runs the same protocol as circuits for a handful of qubits, and we cross-checked both: with Eve, QBER is about 25 to 28% in each.
- **Security bounds are simplified.** The key-length formula uses a 4-sigma margin on the sampled QBER, not a rigorous finite-key proof. Say "teaching model", not "certified".
- **Only intercept-resend attacks are modelled.** Real systems also defend against photon-number-splitting, detector blinding and others.
- **QKD secures the key exchange, not the endpoints.** A compromised hospital server is still compromised. Position QKD as a hybrid with post-quantum cryptography for the most sensitive, longest-lived links.
- **Real QKD needs hardware and dedicated fibre,** with range limited to a few hundred km without trusted nodes.
- **2,048 qubits is often too few** to leave 256 secret bits. The UI shows an amber "not enough secure key" state, and 8,192 is the reliable size.

## Troubleshooting

- *"Cannot reach the backend"* in the UI: the server isn't running, or you opened `index.html` from disk. Open `http://localhost:8000` instead, or add `?api=http://host:8000`.
- *Qiskit button fails:* `pip install qiskit qiskit-aer`. The rest of the demo works without them. Qiskit runs in a child process on purpose, because Qiskit 2.x can crash when called from several server threads.
- *Slow first Qiskit click:* about a second of process start-up. Click it once before presenting.
