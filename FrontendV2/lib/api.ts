/**
 * BioQShield Frontend API Client & State Management
 * Quantum-Secure Communication for Biomedical Networks
 */

// ── Hospital Definitions ────────────────────────────────────────────────
export interface HospitalDef {
  id: string
  name: string
  branch: string
  nodeId: string
  accent: string
  users: { name: string; username: string; password: string; role: string; department: string; initials: string }[]
}

export const HOSPITALS: HospitalDef[] = [
  {
    id: 'hospital-1',
    name: 'Apollo Hospital',
    branch: 'Chennai Main Branch',
    nodeId: 'AQ-CHN-01',
    accent: '#2563EB',
    users: [
      { name: 'Dr. Arjun Sharma', username: 'dr.arjun.sharma', password: 'qiskit2026', role: 'Senior Cardiologist', department: 'Cardiology', initials: 'AS' },
      { name: 'Dr. Meera Iyer', username: 'dr.meera.iyer', password: 'qiskit2026', role: 'Lead Neurologist', department: 'Neurology', initials: 'MI' },
      { name: 'Dr. Rao (Chief Clinician)', username: 'dr.rao', password: 'clinician-demo-pass', role: 'Chief Clinician', department: 'Critical Care', initials: 'DR' },
      { name: 'System Administrator', username: 'admin', password: 'admin-demo-pass', role: 'Security Administrator', department: 'Quantum IT', initials: 'AD' },
    ],
  },
  {
    id: 'hospital-2',
    name: 'Fortis Hospital',
    branch: 'Chennai Main Branch',
    nodeId: 'FT-CHN-02',
    accent: '#14B8A6',
    users: [
      { name: 'Dr. Rahul Menon', username: 'dr.rahul.menon', password: 'qiskit2026', role: 'Chief Medical Officer', department: 'Internal Medicine', initials: 'RM' },
      { name: 'Dr. Priya Kapoor', username: 'dr.priya.kapoor', password: 'qiskit2026', role: 'Head Radiologist', department: 'Radiology', initials: 'PK' },
      { name: 'Dr. Rao (Chief Clinician)', username: 'dr.rao', password: 'clinician-demo-pass', role: 'Chief Clinician', department: 'Critical Care', initials: 'DR' },
      { name: 'System Administrator', username: 'admin', password: 'admin-demo-pass', role: 'Security Administrator', department: 'Quantum IT', initials: 'AD' },
    ],
  },
]

export interface RunParams {
  n_qubits: number
  noise: number
  eve: boolean
  eve_rate: number
  eve_start: number
  seed?: number | null
  traffic?: 'benign' | 'mixed' | 'attack' | null
  adaptive: boolean
}

export interface QBERTraceBin {
  bin: number
  start: number
  end: number
  n: number
  qber: number | null
}

export interface PipelineStage {
  id: 'transmit' | 'sift' | 'qber' | 'ec' | 'pa' | 'aes'
  title: string
  status: 'ok' | 'abort' | 'skipped'
  metrics: [string, string][]
  note: string
}

export interface RecordResult {
  status: 'delivered' | 'blocked' | 'failed'
  plaintext: string
  nonce_hex?: string | null
  ciphertext_hex?: string | null
  ciphertext_bytes?: number | null
  decrypted?: string | null
  note?: string
}

export interface ThreatResult {
  score: number
  classification: 'normal' | 'attack'
  attack_family?: string | null
  mean_prob?: number
  n_flows?: number
  classifier: {
    source: string
    accuracy: number
    f1: number
    n_train: number
  }
}

export interface DecisionResult {
  verdict: 'ACCEPT' | 'MONITOR' | 'REJECT'
  reason: string
  accept_below: number
  reject_at: number
  description: string
}

export interface RunResponse {
  params: {
    n_qubits: number
    noise: number
    eve: boolean
    eve_rate: number
    eve_start: number
  }
  status: 'secure' | 'aborted'
  status_description?: string
  reason: string | null
  stats: {
    n_sent: number
    n_sifted: number
    sample_size: number
    qber_est: number
    qber_upper: number
    threshold: number
    sim_true_qber: number
    sim_eve_known_fraction: number
    ec_errors_fixed: number
    ec_leaked_bits: number
    ec_verified: boolean
    ec_rounds: number
    pa_input_bits: number
    final_key_bits: number
    display_rules: {
      fraction_metrics: string[]
      ui_unit: string
      multiply_by: number
      decimals: number
    }
    key_available: boolean
  }
  qber_trace: QBERTraceBin[]
  stages: PipelineStage[]
  record: RecordResult
  threat: ThreatResult | null
  decision_static: DecisionResult
  decision: DecisionResult
  adaptive: boolean
  elapsed_ms: number
}

export interface ScenarioItem {
  scenario: string
  threat: number
  qber: number
  key_bits: number
  static: 'ACCEPT' | 'MONITOR' | 'REJECT'
  adaptive: 'ACCEPT' | 'MONITOR' | 'REJECT'
  reason: string
}

export interface QiskitDemoRow {
  qubit: number
  alice: { bit: number; basis: string }
  eve: { basis: string } | null
  bob: { basis: string; bit: number }
  outcome: string
  alice_bit?: number
  alice_basis?: string
  eve_basis?: string | null
  bob_basis?: string
  bob_bit?: number
  kept?: boolean
  error?: boolean
}

export interface QiskitDemoResponse {
  protocol: string
  engine: string
  summary: {
    n_qubits: number
    eve: boolean
    noise: number
    kept_qubits: number
    errors: number
    qber: number | null
    sift_rate: number
  }
  rows: QiskitDemoRow[]
  circuit: string
  circuit_ascii?: string
  n?: number
  kept?: number
  qber?: number | null
}

export interface TransferHistoryItem {
  id: string
  timestamp: string
  patient: string
  patientId: string
  department: string
  data: string
  destination: string
  scope: string
  branch?: string
  verdict: 'ACCEPT' | 'MONITOR' | 'REJECT'
  status: 'Delivered' | 'Blocked'
  threatScore: number
  qber: number
  keyBits: number
  runResponse?: RunResponse
}

// Fallback base URL for direct client-side fetch if proxy rewrite is bypassed
const API_BASE = ''

export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: 'no-store' })
    if (!res.ok) return false
    const data = await res.json()
    return Boolean(data.ok)
  } catch {
    return false
  }
}

export async function runSimulation(params: RunParams): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/api/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`Simulation failed (${res.status}): ${errorText}`)
  }
  return res.json()
}

export async function fetchScenarios(): Promise<ScenarioItem[]> {
  const res = await fetch(`${API_BASE}/api/scenarios`, { cache: 'no-store' })
  if (!res.ok) {
    throw new Error(`Failed to load scenarios (${res.status})`)
  }
  return res.json()
}

export async function fetchQiskitDemo(params: {
  n: number
  eve: boolean
  noise: number
  seed?: number | null
}): Promise<QiskitDemoResponse> {
  const res = await fetch(`${API_BASE}/api/qiskit-demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Qiskit Aer simulation failed (${res.status}): ${err}`)
  }
  return res.json()
}

// Initial seed history for demo
const INITIAL_HISTORY: TransferHistoryItem[] = [
  {
    id: 'BQS-2026-004821',
    timestamp: 'Today · 10:42 AM',
    patient: 'John Doe',
    patientId: 'PT-20491',
    department: 'Cardiology',
    data: 'Medical Record + Prescription',
    destination: 'Fortis Hospital Network',
    scope: 'Hospital Network',
    verdict: 'ACCEPT',
    status: 'Delivered',
    threatScore: 0.18,
    qber: 2.4,
    keyBits: 1024,
  },
  {
    id: 'BQS-2026-004820',
    timestamp: 'Today · 09:18 AM',
    patient: 'Sarah Wilson',
    patientId: 'PT-18372',
    department: 'Neurology',
    data: 'Diagnostic Report',
    destination: 'Apollo Hospital Network',
    scope: 'Specific Branch',
    branch: 'Adyar Branch',
    verdict: 'MONITOR',
    status: 'Blocked',
    threatScore: 0.65,
    qber: 7.2,
    keyBits: 0,
  },
  {
    id: 'BQS-2026-004819',
    timestamp: 'Yesterday · 04:30 PM',
    patient: 'Michael Carter',
    patientId: 'PT-17283',
    department: 'Oncology',
    data: 'Medical Record',
    destination: 'Fortis Hospital Network',
    scope: 'Hospital Network',
    verdict: 'REJECT',
    status: 'Blocked',
    threatScore: 0.92,
    qber: 13.8,
    keyBits: 0,
  },
]

export function getTransferHistory(): TransferHistoryItem[] {
  if (typeof window === 'undefined') return INITIAL_HISTORY
  try {
    const stored = localStorage.getItem('bioqshield_transfer_history')
    if (!stored) {
      localStorage.setItem('bioqshield_transfer_history', JSON.stringify(INITIAL_HISTORY))
      return INITIAL_HISTORY
    }
    return JSON.parse(stored)
  } catch {
    return INITIAL_HISTORY
  }
}

export function saveTransferToHistory(item: TransferHistoryItem): void {
  if (typeof window === 'undefined') return
  try {
    const existing = getTransferHistory()
    const updated = [item, ...existing.filter((x) => x.id !== item.id)]
    localStorage.setItem('bioqshield_transfer_history', JSON.stringify(updated))
    localStorage.setItem('bioqshield_latest_run', JSON.stringify(item))
  } catch (err) {
    console.error('Failed to save transfer to history', err)
  }
}

export function getLatestTransfer(): TransferHistoryItem | null {
  if (typeof window === 'undefined') return INITIAL_HISTORY[0]
  try {
    const stored = localStorage.getItem('bioqshield_latest_run')
    if (stored) return JSON.parse(stored)
    const history = getTransferHistory()
    return history[0] || null
  } catch {
    return null
  }
}

export function getTransferById(id: string): TransferHistoryItem | null {
  const history = getTransferHistory()
  return history.find((x) => x.id === id) || null
}

export interface AuthUser {
  name: string
  username: string
  role: string
  department: string
  hospital: string
  hospitalId: string
  branch: string
  nodeId: string
  initials: string
  isLoggedIn: boolean
}

const DEFAULT_USER: AuthUser = {
  name: 'Dr. Arjun Sharma',
  username: 'dr.arjun.sharma',
  role: 'Senior Cardiologist',
  department: 'Cardiology',
  hospital: 'Apollo Hospital',
  hospitalId: 'hospital-1',
  branch: 'Chennai Main Branch',
  nodeId: 'AQ-CHN-01',
  initials: 'AS',
  isLoggedIn: false,
}

export function getAuthUser(): AuthUser {
  if (typeof window === 'undefined') return { ...DEFAULT_USER, isLoggedIn: true }
  try {
    const stored = localStorage.getItem('bioqshield_user')
    if (stored) return JSON.parse(stored)
  } catch {}
  return DEFAULT_USER
}

export function setAuthUser(user: Partial<AuthUser> & { name: string }) {
  if (typeof window === 'undefined') return
  const full: AuthUser = { ...DEFAULT_USER, ...user, isLoggedIn: true }
  localStorage.setItem('bioqshield_user', JSON.stringify(full))
}

export function logoutUser() {
  if (typeof window === 'undefined') return
  localStorage.removeItem('bioqshield_user')
}

export function getHospitalById(id: string): HospitalDef | undefined {
  return HOSPITALS.find((h) => h.id === id)
}
