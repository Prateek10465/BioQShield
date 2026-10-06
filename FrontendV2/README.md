# BioQShield — Quantum-Secure Communication for Biomedical Networks

> **Qiskit Fall Fest 2026 — Track 2.2**  
> Clinical-grade quantum-secure communication architecture fusing **classical threat intelligence (NSL-KDD)** with **Qiskit Aer BB84 Quantum Key Distribution** to safeguard sensitive biomedical transfers across hospital networks.

---

## 1. Executive Summary

Healthcare networks represent high-value targets handling sensitive Protected Health Information (PHI) and critical medical records. **BioQShield** provides an end-to-end quantum-resistant communication pipeline designed specifically for clinical environments.

Before any biomedical transfer is permitted:
1. **Network Threat Analysis**: An NSL-KDD trained random-forest classifier evaluates inbound and ambient network telemetry to generate an objective threat score.
2. **BB84 QKD Simulation**: A simulated quantum channel executed on **Qiskit Aer** (`AerSimulator`) generates raw quantum keys across randomized rectilinear ($Z$) and diagonal ($X$) bases, modeling physical optical noise and potential eavesdroppers ($Eve$).
3. **QBER & Post-Processing**: The Quantum Bit Error Rate (QBER) is evaluated alongside multi-round Cascade error correction and Toeplitz privacy amplification.
4. **Adaptive Security Policy**: An adaptive policy tightens QBER thresholds according to the network threat level ($QBER_{accept} = 0.06 - 0.03 \cdot Threat$).
5. **Authenticated Biomedical Cryptography**: When security requirements are satisfied, a 256-bit AES key is derived to encrypt synthetic medical records using **AES-256-GCM** with a random 96-bit nonce. If conditions fail, **no cryptographic material or patient data is released**, enforcing strict blocked isolation.

---

## 2. System Architecture

```
                       [ BioQShield Workflow ]
                                  │
    ┌─────────────────────────────┴─────────────────────────────┐
    ▼                                                           ▼
[ Classical Network Telemetry ]               [ Quantum Optical Channel ]
    │                                                           │
    ▼                                                           ▼
NSL-KDD Threat Classifier                     BB84 QKD Simulation (Qiskit Aer)
    │                                                           │
    ├─ Random Forest Model                                      ├─ State Preparation (|0>,|1>,|+>,|->)
    ├─ Traffic Presets (Benign / Mixed / Attack)                ├─ Channel Optical Noise
    └─ Threat Score [0.00 – 1.00]                               ├─ Optional Eve Intercept-Resend
                                                                ├─ Sifting (Basis Match)
                                                                ├─ QBER Estimation & Validation
                                                                ├─ Cascade Error Correction
                                                                └─ Toeplitz Privacy Amplification
                                  │
                                  ▼
                    [ Dual Security Policy Layer ]
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
           Static Policy                    Adaptive Policy
         (Threshold: 11%)          (Threshold: 11% - 4% · Threat)
                 │                                 │
                 └────────────────┬────────────────┘
                                  ▼
                   Security Verdict Decision
                 (ACCEPT / MONITOR / REJECT)
                                  │
          ┌───────────────────────┴───────────────────────┐
          │                                               │
     [ ACCEPT ]                                   [ MONITOR / REJECT ]
          │                                               │
          ▼                                               ▼
Key Release Authorized                          Key Release BLOCKED
Derive 256-bit AES Key                          Zero Cryptographic Exposure
AES-256-GCM Record Encryption                   Ciphertext / Nonce Suppressed
Delivered to Hospital Network                   Audit Incident Logged
```

---

## 3. Core Capabilities & Components

### A. NSL-KDD Classical Threat Engine
- **Model**: Scikit-Learn `RandomForestClassifier` trained on NSL-KDD benchmark flows (`n_estimators=100`, reproducibility seed fixed).
- **Features**: Flow duration, protocol type, service, byte counts, error rates, host connection density.
- **Output**: Calibrated Threat Score $[0.00, 1.00]$, classification (`normal` vs. `attack`), and attack family metadata (`dos`, `probe`, `r2l`, `u2r`).
- **Performance**: High accuracy and F1 score with reproducible weights stored in `backend/threat/model/`.

### B. BB84 Quantum Key Distribution via Qiskit Aer
- **Quantum Simulation**: Native integration with Qiskit 2.x and Qiskit Aer 0.17.x (`AerSimulator`).
- **Basis Pairs**: Rectilinear basis $Z = \{|0\rangle, |1\rangle\}$ and Diagonal basis $X = \{|+\rangle, |-\rangle\}$.
- **Eavesdropping Modeling**: Parameterized intercept-resend attack with configurable interception rate and onset threshold.
- **Statistical Scaling**: Dual-mode engine utilizing real Qiskit quantum circuits for detailed inspection (up to 32 representative qubits with ASCII diagrams) and vectorized simulation for full cryptographic key blocks (up to 32,768 qubits).

### C. Error Correction & Privacy Amplification
- **Cascade Error Correction**: Multi-round parity checking across randomized block permutations to locate and correct bit errors without full disclosure.
- **Toeplitz Privacy Amplification**: Hash reduction shrinking the reconciled key according to mutual information leaked to Eve ($2 \cdot QBER$), producing a secure secret key.

### D. Adaptive vs. Static Security Policy
- **Static Policy**: Rejects when $QBER > 11\%$, monitors when $6\% < QBER \le 11\%$, accepts when $QBER \le 6\%$.
- **Adaptive Policy**: Dynamically adjusts acceptance and rejection bounds based on the NSL-KDD threat score $T$:
  $$QBER_{\text{accept}} = 0.06 - 0.03 \cdot T$$
  $$QBER_{\text{reject}} = 0.11 - 0.04 \cdot T$$
  If $T \ge 0.80$ and status is `MONITOR`, policy escalates automatically to `REJECT`.
- **Predefined Scenarios**: 7 standardized test scenarios demonstrating divergence between static and adaptive evaluations (e.g. *Hostile Network with Low Noise* where static accepts but adaptive strictly rejects).

### E. Clinical Biomedical Cryptography
- **Cipher Suite**: AES-256-GCM (Galois/Counter Mode) authenticated encryption with unique 96-bit random nonce.
- **Payload**: Synthetic electronic health records, diagnostic observations, prescriptions, and clinical summaries.
- **Fail-Safe Invariant**: Under `MONITOR` or `REJECT`, the quantum key is destroyed, `record.status = "blocked"`, and ciphertext is set to `null` to prevent transmission leaks.

---

## 4. Getting Started

### Prerequisites
- **Python**: 3.10+ (tested and verified on Python 3.14.6)
- **Node.js**: 18+ (tested on Node.js 20+)
- **Package Managers**: `pnpm` (or `npm`) and `pip`

### 1. Backend Setup & Startup
Navigate to the root directory and start the FastAPI service:

```bash
# Install Python dependencies
pip install fastapi uvicorn qiskit qiskit-aer numpy scikit-learn pandas cryptography pytest httpx

# Start FastAPI server on port 8000
python -m uvicorn backend.main:app --port 8000
```

Verify backend health:
```bash
curl http://127.0.0.1:8000/api/health
# Response: {"ok": true}
```

### 2. Frontend Setup & Startup
In a separate terminal, launch the Next.js frontend:

```bash
# Install Node dependencies
pnpm install

# Start Next.js development server on port 3000
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your web browser. Next.js automatically rewrites requests from `/api/*` to `http://127.0.0.1:8000/api/*`.

---

## 5. Verification & Testing

### Running Backend Tests
Execute the complete test suite covering BB84 math, Qiskit circuits, Cascade error correction, Toeplitz hashing, AES-256-GCM encryption, adaptive policy invariants, and scenario endpoints:

```bash
python -m pytest backend/tests -v
```
*Result: 52 of 52 tests pass.*

### Running Frontend Production Build
Validate TypeScript types and Next.js static and server routes:

```bash
# Type check
npx tsc --noEmit

# Production build
pnpm build
```
*Result: 11 of 11 routes compile cleanly with zero errors.*

---

## 6. Predefined Scenarios Matrix

| Scenario Name | Traffic Condition | Quantum Channel Noise | Eve Present | Static Verdict | Adaptive Verdict | Rationale |
|:---|:---|:---|:---|:---|:---|:---|
| **Clean Baseline** | Benign | 2.0% | No | ACCEPT | ACCEPT | Both threat and QBER are well below clinical thresholds. |
| **High Channel Noise** | Benign | 12.0% | No | REJECT | REJECT | Channel noise exceeds the 11% theoretical QKD threshold. |
| **Active Intercept Attack** | Benign | 2.0% | Yes (100%) | REJECT | REJECT | Eavesdropper induces ~25% QBER; rejected by both policies. |
| **Moderate Noise Channel** | Benign | 7.0% | No | MONITOR | MONITOR | Intermediate QBER triggers heightened telemetry monitoring. |
| **Hostile Network (Low Noise)** | Attack | 5.0% | No | **ACCEPT** | **REJECT** | **Crucial divergence**: Static policy accepts ($5\% \le 6\%$), but adaptive policy detects classical attack and tightens threshold, blocking the transfer. |
| **Mixed Traffic (Elevated Noise)** | Mixed | 6.5% | No | MONITOR | REJECT | Adaptive policy tightens threshold due to anomalous network traffic. |
| **Low-Rate Eavesdropper** | Benign | 3.0% | Yes (25%) | ACCEPT | MONITOR | Low-rate interception elevates QBER above adaptive acceptance limits. |

---

## 7. API Reference

### `GET /api/health`
Health check endpoint.
```json
{
  "ok": true
}
```

### `POST /api/run`
Execute an end-to-end simulation.
**Payload:**
```json
{
  "n_qubits": 4096,
  "noise": 0.02,
  "eve": false,
  "eve_rate": 1.0,
  "eve_start": 0.0,
  "seed": 42,
  "traffic": "benign",
  "adaptive": true
}
```

### `GET /api/scenarios`
Execute and return all 7 predefined benchmark scenarios.

### `POST /api/qiskit-demo`
Generates real Qiskit Aer BB84 circuits and per-qubit measurement inspection tables.

---

## 8. Official Branding Assets

BioQShield utilizes official hospital-grade identity assets located in `/public`:
- **Light Theme Emblem**: `/Quantum_Medical_Shield_Emblem-removebg-preview.png`
- **Dark Theme Emblem**: `/Quantum_Health_Shield_Emblem-removebg-preview.png`

---

## 9. License & Attribution

Developed for **Qiskit Fall Fest 2026 — Track 2.2: Quantum-Secure Communication for Biomedical Networks**.  
Built using IBM Qiskit, Qiskit Aer, FastAPI, Scikit-Learn, Next.js, and Tailwind CSS.
