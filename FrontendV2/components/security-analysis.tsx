'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Database,
  FileCheck2,
  FileText,
  KeyRound,
  LockKeyhole,
  Network,
  Radio,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Timer,
  X,
  XCircle,
  Zap,
} from 'lucide-react'
import {
  RunParams,
  RunResponse,
  runSimulation,
  fetchLinkState,
  formatTransferTimestamp,
  publishDemoTransfer,
  saveTransferToHistory,
  TransferHistoryItem,
} from '@/lib/api'

type Verdict = 'ACCEPT' | 'MONITOR' | 'REJECT'

function tone(verdict: Verdict) {
  return verdict === 'ACCEPT'
    ? {
      bg: 'bg-[#E8F7EF] dark:bg-[#22C55E]/15',
      border: 'border-[#B9E5D0] dark:border-[#22C55E]/30',
      text: 'text-[#198657] dark:text-[#7BE3A0]',
      strong: '#22A06B',
    }
    : verdict === 'MONITOR'
      ? {
        bg: 'bg-[#FFF5E7] dark:bg-[#F59E0B]/15',
        border: 'border-[#F2D29F] dark:border-[#F59E0B]/30',
        text: 'text-[#B76405] dark:text-[#FFD083]',
        strong: '#D97706',
      }
      : {
        bg: 'bg-[#FDEBEC] dark:bg-[#EF4444]/15',
        border: 'border-[#F2BFC2] dark:border-[#EF4444]/30',
        text: 'text-[#C33E42] dark:text-[#FF9292]',
        strong: '#DC4446',
      }
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] shadow-[0_3px_12px_rgba(18,52,91,0.035)] ${className}`}
    >
      {children}
    </section>
  )
}

function CardHeading({ eyebrow, title, icon: Icon }: { eyebrow?: string; title: string; icon: typeof ShieldCheck }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        {eyebrow && (
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.13em] text-[#14A493]">{eyebrow}</div>
        )}
        <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">{title}</h2>
      </div>
      <div className="flex size-9 items-center justify-center rounded-xl bg-[#EAF2FF] dark:bg-[#2563EB]/20 text-[#2563EB] dark:text-[#67E8F9]">
        <Icon className="size-[18px]" />
      </div>
    </div>
  )
}

export function SecurityPipeline({ stages, verdict }: { stages: RunResponse['stages']; verdict: Verdict }) {
  return (
    <Card className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.13em] text-[#14A493]">Security pipeline</div>
          <h2 className="mt-1 text-[16px] font-bold text-[#172033] dark:text-white">
            From patient record to protected destination database
          </h2>
        </div>
        <span
          className={`rounded-full px-3 py-1.5 text-[10px] font-semibold ${verdict === 'ACCEPT'
            ? 'bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
            : 'bg-[#FDEBEC] dark:bg-[#DC4446]/15 text-[#C33E42] dark:text-[#FF9292]'
            }`}
        >
          {verdict === 'ACCEPT' ? 'Delivery Approved' : 'Transfer Held'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {stages.map((st, index) => {
          const isOk = st.status === 'ok'
          const isAbort = st.status === 'abort'
          const isSkipped = st.status === 'skipped'
          return (
            <div key={st.id} className="relative">
              <div
                className={`flex min-h-[116px] flex-col items-center rounded-xl border p-3 text-center transition ${isAbort
                  ? 'border-[#F2D9DA] dark:border-[#DC4446]/30 bg-[#FFF9F9] dark:bg-[#DC4446]/10'
                  : isOk
                    ? 'border-[#B9E5D0] dark:border-[#22C55E]/30 bg-[#F6FCF8] dark:bg-[#22C55E]/10'
                    : 'border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.02]'
                  }`}
              >
                <div
                  className={`flex size-8 items-center justify-center rounded-full ${isAbort
                    ? 'bg-[#FDEBEC] text-[#DC4446]'
                    : isOk
                      ? 'bg-[#E8F7EF] text-[#22A06B]'
                      : 'bg-[#EEF3F8] dark:bg-white/10 text-[#8A9AAD]'
                    }`}
                >
                  {isAbort ? (
                    <X className="size-4" />
                  ) : isOk ? (
                    <Check className="size-4" strokeWidth={2.5} />
                  ) : (
                    <LockKeyhole className="size-3.5" />
                  )}
                </div>
                <div className="mt-2 text-[10px] font-bold text-[#172033] dark:text-white">{st.title}</div>
                <div className="mt-1 text-[9px] leading-4 text-[#8A9AAD]">
                  {isOk ? 'Verified' : isAbort ? 'Aborted' : 'Blocked'}
                </div>
              </div>
              {index < stages.length - 1 && (
                <ArrowRight className="absolute -right-2 top-14 z-[1] hidden size-3.5 bg-white dark:bg-[#0B1726] text-[#B8C7D5] lg:block" />
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export function ThreatScoreCard({ threat }: { threat: RunResponse['threat'] }) {
  if (!threat) {
    return (
      <Card className="p-6">
        <CardHeading eyebrow="Network conditions" title="Network Threat Analysis" icon={ShieldAlert} />
        <p className="mt-6 text-[12px] text-[#64748B] dark:text-[#9AAABD]">
          No classical traffic window provided. Default baseline assumed safe.
        </p>
      </Card>
    )
  }

  const isAttack = threat.classification === 'attack' || threat.score >= 0.5
  return (
    <Card className="p-6">
      <CardHeading eyebrow="Classical network layer" title="Network Threat Score" icon={ShieldAlert} />
      <div className="mt-6 flex items-end justify-between">
        <div>
          <div className="text-[34px] font-bold tracking-tight text-[#172033] dark:text-white">
            {threat.score.toFixed(2)}
          </div>
          <div className="mt-1 text-[10px] uppercase tracking-[0.1em] text-[#8A9AAD]">Threat score / 1.00</div>
        </div>
        <div className="text-right">
          <div
            className={`text-[12px] font-bold ${isAttack ? 'text-[#DC4446] dark:text-[#FF9292]' : 'text-[#198657] dark:text-[#7BE3A0]'
              }`}
          >
            {threat.classification.toUpperCase()}
          </div>
          <div className="mt-0.5 text-[10px] text-[#64748B] dark:text-[#9AAABD]">
            {threat.attack_family ? threat.attack_family : 'Benign telemetry'}
          </div>
        </div>
      </div>
      <div className="mt-5">
        <div className="h-2 overflow-hidden rounded-full bg-[#E8EEF3] dark:bg-white/10">
          <div
            className={`h-full rounded-full transition-all duration-500 ${threat.score >= 0.8
              ? 'bg-[#DC4446]'
              : threat.score >= 0.5
                ? 'bg-[#D97706]'
                : 'bg-[#22A06B]'
              }`}
            style={{ width: `${Math.min(threat.score * 100, 100)}%` }}
          />
        </div>
        <div className="mt-2 flex justify-between text-[9px] text-[#8A9AAD]">
          <span>NORMAL (&lt; 0.5)</span>
          <span>ATTACK (&ge; 0.5)</span>
        </div>
      </div>
      <div className="mt-5 border-t border-[#EEF2F6] dark:border-white/10 pt-3 text-[10px] text-[#64748B] dark:text-[#9AAABD] flex justify-between">
        <span>Model: {threat.classifier.source}</span>
        <span>Accuracy: {(threat.classifier.accuracy * 100).toFixed(1)}%</span>
        <span>F1: {(threat.classifier.f1 * 100).toFixed(1)}%</span>
      </div>
    </Card>
  )
}

export function QuantumChannelCard({ response }: { response: RunResponse }) {
  const eveActive = response.params.eve
  const noisePct = (response.params.noise * 100).toFixed(1)
  const eveKnownPct = (response.stats.sim_eve_known_fraction * 100).toFixed(1)

  return (
    <Card className="p-6">
      <CardHeading eyebrow="Quantum communication" title="BB84 Quantum Channel" icon={Radio} />
      <div className="mt-6 flex items-center justify-between gap-2">
        <div className="flex flex-col items-center gap-1.5">
          <div className="flex size-11 items-center justify-center rounded-xl bg-[#EAF8F5] dark:bg-[#14B8A6]/20 text-[#128F7C]">
            <Network className="size-5" />
          </div>
          <span className="text-[10px] font-bold text-[#172033] dark:text-white">Alice</span>
          <span className="text-[9px] text-[#8A9AAD]">Source Hospital</span>
        </div>

        <div className="relative flex flex-1 items-center justify-center">
          <div
            className={`h-px w-full border-t border-dashed ${eveActive ? 'border-[#DC4446]' : 'border-[#06B6D4]'
              }`}
          />
          {eveActive ? (
            <div className="absolute flex flex-col items-center">
              <div className="rounded-full bg-[#FDEBEC] dark:bg-[#DC4446]/20 p-1 text-[#DC4446]">
                <Zap className="size-4" />
              </div>
              <span className="mt-1 text-[8px] font-bold text-[#DC4446]">Eve Intercepting</span>
            </div>
          ) : (
            <Zap className="absolute size-5 bg-white dark:bg-[#0B1726] px-1 text-[#06B6D4]" />
          )}
        </div>

        <div className="flex flex-col items-center gap-1.5">
          <div className="flex size-11 items-center justify-center rounded-xl bg-[#EAF2FF] dark:bg-[#2563EB]/20 text-[#2563EB]">
            <Database className="size-5" />
          </div>
          <span className="text-[10px] font-bold text-[#172033] dark:text-white">Bob</span>
          <span className="text-[9px] text-[#8A9AAD]">Authorized Node</span>
        </div>
      </div>

      <div
        className={`mt-5 flex items-center gap-2 rounded-lg px-3 py-2.5 text-[10px] font-semibold ${eveActive
          ? 'bg-[#FDEBEC] dark:bg-[#DC4446]/15 text-[#C33E42] dark:text-[#FF9292]'
          : 'bg-[#EAF8F5] dark:bg-[#14B8A6]/15 text-[#128F7C] dark:text-[#67E8D9]'
          }`}
      >
        {eveActive ? (
          <>
            <AlertTriangle className="size-3.5" />
            Eve intercept-resend active ({eveKnownPct}% bits probed)
          </>
        ) : (
          <>
            <CheckCircle2 className="size-3.5" />
            QKD channel active (Noise: {noisePct}%)
          </>
        )}
        <span className="ml-auto text-[9px] font-medium opacity-75">
          {response.params.n_qubits} qubits
        </span>
      </div>
    </Card>
  )
}

export function QBERCard({ response }: { response: RunResponse }) {
  const qberEstPct = (response.stats.qber_est * 100).toFixed(1)
  const qberUpperPct = (response.stats.qber_upper * 100).toFixed(1)
  const isHigh = response.stats.qber_est >= 0.11

  return (
    <Card className="p-6">
      <CardHeading eyebrow="Channel validation" title="Quantum Bit Error Rate (QBER)" icon={Activity} />
      <div className="mt-5 flex items-baseline gap-2">
        <span className="text-[32px] font-bold text-[#172033] dark:text-white">{qberEstPct}%</span>
        <span className="text-[10px] text-[#64748B] dark:text-[#9AAABD]">measured on revealed sample</span>
      </div>
      <div className="mt-5">
        <div className="relative h-3 overflow-hidden rounded-full bg-[#E8EEF3] dark:bg-white/10">
          <div
            className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${isHigh ? 'bg-[#DC4446]' : response.stats.qber_est >= 0.06 ? 'bg-[#D97706]' : 'bg-[#22A06B]'
              }`}
            style={{ width: `${Math.min((response.stats.qber_est / 0.11) * 60, 100)}%` }}
          />
          <div className="absolute inset-y-[-4px] left-[60%] w-0.5 bg-[#C33E42]" title="11% abort threshold" />
        </div>
        <div className="mt-2 flex justify-between text-[9px] text-[#8A9AAD]">
          <span>0%</span>
          <span className="font-semibold text-[#C33E42]">11.0% Abort threshold</span>
          <span>&gt;15%</span>
        </div>
      </div>
      <div className="mt-4 flex justify-between text-[10px] text-[#64748B] dark:text-[#9AAABD]">
        <span>Upper bound (4&sigma;): {qberUpperPct}%</span>
        <span>Sample bits: {response.stats.sample_size}</span>
      </div>
    </Card>
  )
}

export function PolicyComparisonCard({ response }: { response: RunResponse }) {
  const stat = response.decision_static
  const adap = response.decision
  const threatScore = response.threat ? response.threat.score : 0
  const isEscalated = response.threat && response.threat.score >= 0.8 && stat.verdict === 'MONITOR'

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
            Decision intelligence
          </div>
          <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">Static vs. Adaptive Policy</h2>
        </div>
        <span className="rounded bg-[#EAF2FF] dark:bg-[#2563EB]/20 px-2.5 py-1 text-[10px] font-bold text-[#2563EB] dark:text-[#67E8F9]">
          {response.adaptive ? 'Adaptive Active' : 'Static Active'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Static Policy */}
        <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.02] p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#64748B] dark:text-[#9AAABD]">Static Policy</span>
            <span
              className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${stat.verdict === 'ACCEPT'
                ? 'bg-[#E8F7EF] text-[#198657]'
                : stat.verdict === 'MONITOR'
                  ? 'bg-[#FFF5E7] text-[#B76405]'
                  : 'bg-[#FDEBEC] text-[#C33E42]'
                }`}
            >
              {stat.verdict}
            </span>
          </div>
          <div className="mt-3 text-[10px] text-[#4D6075] dark:text-[#A8BACB] space-y-1">
            <div>Accept: &lt; {(stat.accept_below * 100).toFixed(1)}% QBER</div>
            <div>Reject: &ge; {(stat.reject_at * 100).toFixed(1)}% QBER</div>
            <div className="text-[9px] text-[#8A9AAD] mt-2">Fixed thresholds only; ignores classical threats.</div>
          </div>
        </div>

        {/* Adaptive Policy */}
        <div className="rounded-xl border border-[#2563EB]/30 dark:border-[#2563EB]/40 bg-[#F5FAFF] dark:bg-[#2563EB]/10 p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#2563EB] dark:text-[#67E8F9]">Adaptive Policy</span>
            <span
              className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${adap.verdict === 'ACCEPT'
                ? 'bg-[#E8F7EF] text-[#198657]'
                : adap.verdict === 'MONITOR'
                  ? 'bg-[#FFF5E7] text-[#B76405]'
                  : 'bg-[#FDEBEC] text-[#C33E42]'
                }`}
            >
              {adap.verdict}
            </span>
          </div>
          <div className="mt-3 text-[10px] text-[#4D6075] dark:text-[#A8BACB] space-y-1">
            <div>Accept: &lt; {(adap.accept_below * 100).toFixed(1)}% (6% &minus; 3%&times;threat)</div>
            <div>Reject: &ge; {(adap.reject_at * 100).toFixed(1)}% (11% &minus; 4%&times;threat)</div>
            {threatScore >= 0.8 && (
              <div className="text-[9px] font-bold text-[#DC4446] mt-2">
                High threat ({threatScore.toFixed(2)} &ge; 0.8): Escalated MONITOR &rarr; REJECT
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="mt-4 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
        <span className="font-semibold text-[#172033] dark:text-white">Verdict reason: </span>
        {adap.reason}
      </div>
    </Card>
  )
}

export function ProtectedRecordSection({
  record,
  verdict,
  stats,
}: {
  record: RunResponse['record']
  verdict: Verdict
  stats: RunResponse['stats']
}) {
  const accepted = verdict === 'ACCEPT' && record.status === 'delivered'

  return (
    <Card className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
            Record Protection & AES-256-GCM
          </div>
          <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">
            {accepted ? 'Cryptographic Protection & Delivery Verification' : 'Biomedical Resource Transmission Blocked'}
          </h2>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-[10px] font-bold ${accepted
            ? 'bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
            : 'bg-[#FDEBEC] dark:bg-[#DC4446]/15 text-[#C33E42] dark:text-[#FF9292]'
            }`}
        >
          {accepted ? 'RECORD DELIVERED' : 'RECORD BLOCKED'}
        </span>
      </div>

      {accepted ? (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Plaintext record */}
          <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.02] p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD]">
                Original Synthetic Patient Record
              </span>
              <span className="text-[9px] text-[#22A06B] font-semibold">Verified</span>
            </div>
            <pre className="overflow-x-auto text-[11px] leading-5 text-[#172033] dark:text-[#E2E8F0] font-mono bg-white dark:bg-[#07111F] p-3 rounded-lg border border-[#E3EAF1] dark:border-white/10 max-h-48">
              {record.plaintext}
            </pre>
          </div>

          {/* Ciphertext */}
          <div className="rounded-xl border border-[#2563EB]/30 dark:border-[#2563EB]/40 bg-[#F5FAFF] dark:bg-[#2563EB]/10 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB] dark:text-[#67E8F9]">
                AES-256-GCM Encrypted Ciphertext
              </span>
              <span className="text-[9px] text-[#2563EB] font-mono">
                {record.ciphertext_bytes} bytes · Nonce: {record.nonce_hex?.slice(0, 8)}...
              </span>
            </div>
            <pre className="overflow-x-auto text-[10px] leading-4 text-[#2563EB] dark:text-[#67E8F9] font-mono bg-white dark:bg-[#07111F] p-3 rounded-lg border border-[#CFE3F7] dark:border-white/10 max-h-48 break-all select-all">
              {record.ciphertext_hex}
            </pre>
          </div>

          {/* Decryption status */}
          <div className="col-span-2 rounded-xl border border-[#B9E5D0] dark:border-[#22C55E]/30 bg-[#F3FBF6] dark:bg-[#22C55E]/10 p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-[#E8F7EF] dark:bg-[#22C55E]/20 text-[#22A06B]">
                <CheckCircle2 className="size-5" />
              </div>
              <div>
                <div className="text-[12px] font-bold text-[#172033] dark:text-white">
                  Destination Decryption Verified (AES-256-GCM)
                </div>
                <div className="text-[10px] text-[#64748B] dark:text-[#9AAABD]">
                  Decrypted plaintext matches original synthetic biomedical data exactly. Key material protected.
                </div>
              </div>
            </div>
            <div className="text-right text-[10px] font-mono text-[#198657] dark:text-[#7BE3A0]">
              VERIFIED MATCH (SHA-256)
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-[#F2BFC2] dark:border-[#DC4446]/30 bg-[#FFF9F9] dark:bg-[#DC4446]/10 p-5">
          <div className="flex items-start gap-4">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-[#FDEBEC] text-[#DC4446]">
              <LockKeyhole className="size-6" />
            </div>
            <div>
              <div className="text-[13px] font-bold text-[#DC4446] dark:text-[#FF9292]">
                Zero-Leakage Security Enforcement
              </div>
              <p className="mt-1 text-[11px] leading-5 text-[#64748B] dark:text-[#9AAABD]">
                Because the security policy evaluated to <span className="font-bold text-[#DC4446]">{verdict}</span>,
                quantum key release was blocked. No AES-256 encryption occurred, and zero patient data was transmitted.
              </p>
              <div className="mt-3 flex items-center gap-4 text-[10px] text-[#4D6075] dark:text-[#A8BACB]">
                <span>Ciphertext: NULL</span>
                <span>Nonce: NULL</span>
                <span>Destination: NOT CONTACTED</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

export function SecurityAnalysisExperience() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<RunResponse | null>(null)
  const [transferContext, setTransferContext] = useState<any>(null)

  const executeAnalysis = async (params: RunParams, context = transferContext) => {
    setLoading(true)
    setError(null)
    try {
      const linkState = await fetchLinkState()
      const effectiveParams = linkState?.eve ? { ...params, eve: true } : params
      const res = await runSimulation(effectiveParams)
      setResponse(res)

      // Save to local transfer history
      const now = new Date()
      const historyItem: TransferHistoryItem = {
        id: `BQS-${now.getFullYear()}-${Math.floor(100000 + Math.random() * 900000)}`,
        timestamp: formatTransferTimestamp(now),
        createdAt: now.toISOString(),
        patient: context?.patient?.name || 'Synthetic Patient',
        patientId: context?.patient?.id || 'PT-2048',
        department: context?.patient?.department || 'Cardiology',
        data: context?.documents ? context.documents.join(' · ') : 'Clinical Summary',
        destination: context?.destination || 'Fortis Hospital Network',
        scope: context?.scope || 'Hospital Network',
        branch: context?.branch,
        verdict: res.decision.verdict,
        status: res.decision.verdict === 'ACCEPT' ? 'Delivered' : 'Blocked',
        threatScore: res.threat ? res.threat.score : 0.0,
        qber: parseFloat((res.stats.qber_est * 100).toFixed(1)),
        keyBits: res.stats.final_key_bits,
        runResponse: res,
      }
      saveTransferToHistory(historyItem)
      await publishDemoTransfer({
        transferId: historyItem.id,
        patient: historyItem.patient,
        patientId: historyItem.patientId,
        department: historyItem.department,
        data: historyItem.data,
        destination: historyItem.destination,
        verdict: historyItem.verdict,
        status: historyItem.status,
        threatScore: historyItem.threatScore,
        qber: historyItem.qber,
        timestamp: historyItem.timestamp,
      })
    } catch (err: any) {
      setError(err?.message || 'Failed to complete security analysis.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let p: RunParams = {
      n_qubits: 8192,
      noise: 0.02,
      eve: false,
      eve_rate: 1.0,
      eve_start: 0.0,
      traffic: 'benign',
      adaptive: true,
      seed: 1,
    }

    if (typeof window !== 'undefined') {
      const stored = sessionStorage.getItem('bioqshield_active_transfer')
      if (stored) {
        try {
          const parsed = JSON.parse(stored)
          setTransferContext(parsed)
          if (parsed.params) p = parsed.params
          executeAnalysis(p, parsed)
          return
        } catch { }
      }
    }
    executeAnalysis(p)
  }, [])

  if (loading) {
    return (
      <main className="mx-auto max-w-[1240px] px-10 py-12">
        <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-12 text-center shadow-lg">
          <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-[#EAF2FF] dark:bg-[#2563EB]/20 text-[#2563EB]">
            <Radio className="size-8 animate-pulse text-[#2563EB]" />
          </div>
          <div className="mt-6 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
            Quantum Security Engine Active
          </div>
          <h2 className="mt-2 text-[26px] font-bold text-[#172033] dark:text-white">
            Evaluating Biomedical Network Security
          </h2>
          <p className="mx-auto mt-2 max-w-md text-[13px] text-[#64748B] dark:text-[#9AAABD]">
            Running NSL-KDD threat classifier &rarr; BB84 Qiskit transmission &rarr; QBER estimation &rarr; Cascade error correction &rarr; Adaptive policy.
          </p>
          <div className="mx-auto mt-8 h-2 max-w-sm overflow-hidden rounded-full bg-[#E8EEF3] dark:bg-white/10">
            <div className="h-full w-2/3 animate-indeterminate bg-[#2563EB]" />
          </div>
          <div className="mt-4 text-[11px] text-[#8A9AAD]">Simulating quantum channel on Qiskit Aer...</div>
        </div>
      </main>
    )
  }

  if (error || !response) {
    return (
      <main className="mx-auto max-w-[1240px] px-10 py-12">
        <div className="rounded-2xl border border-[#DC4446]/30 bg-white dark:bg-[#0B1726] p-10 text-center">
          <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-[#FDEBEC] text-[#DC4446]">
            <AlertTriangle className="size-7" />
          </div>
          <h2 className="mt-4 text-2xl font-bold text-[#172033] dark:text-white">Security Analysis Error</h2>
          <p className="mx-auto mt-2 max-w-md text-[13px] text-[#64748B] dark:text-[#9AAABD]">{error}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() =>
                executeAnalysis({
                  n_qubits: 8192,
                  noise: 0.02,
                  eve: false,
                  eve_rate: 1.0,
                  eve_start: 0.0,
                  traffic: 'benign',
                  adaptive: true,
                  seed: 1,
                })
              }
              className="rounded-xl bg-[#2563EB] px-5 py-2.5 text-xs font-semibold text-white"
            >
              Retry Analysis
            </button>
            <Link
              href="/secure-transfer/"
              className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-5 py-2.5 text-xs font-semibold text-[#4D6075] dark:text-[#A8BACB]"
            >
              Back to Transfer
            </Link>
          </div>
        </div>
      </main>
    )
  }

  const verdict = response.decision.verdict

  return (
    <main className="mx-auto max-w-[1240px] px-10 py-8">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
            <span className="size-1.5 rounded-full bg-[#14B8A6]" />
            Live Security Analysis · Session ID: AQ-{response.elapsed_ms}
          </div>
          <h1 className="text-[30px] font-bold tracking-[-0.035em] text-[#172033] dark:text-white">
            {verdict === 'ACCEPT' ? 'Transfer Approved & Delivered' : 'Transfer Blocked by Security Policy'}
          </h1>
          <p className="mt-2 max-w-2xl text-[13px] text-[#64748B] dark:text-[#9AAABD]">
            {verdict === 'ACCEPT'
              ? 'All quantum channel requirements and classical network conditions passed. A 256-bit AES key was derived and verified.'
              : 'Security requirements were not satisfied. Data movement was safely halted.'}
          </p>
        </div>
        <div
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-[11px] font-bold ${verdict === 'ACCEPT'
            ? 'bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
            : 'bg-[#FDEBEC] dark:bg-[#DC4446]/15 text-[#C33E42] dark:text-[#FF9292]'
            }`}
        >
          {verdict === 'ACCEPT' ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
          VERDICT: {verdict}
        </div>
      </div>

      {/* Target summary bar */}
      <div className="mt-6 grid gap-3 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-4 text-[11px] md:grid-cols-4">
        <div>
          <span className="text-[#8A9AAD]">Subject</span>
          <div className="mt-1 font-bold text-[#172033] dark:text-white">
            {transferContext?.patient?.name || 'Synthetic Patient'} · {transferContext?.patient?.id || 'PT-2048'}
          </div>
        </div>
        <div>
          <span className="text-[#8A9AAD]">Biomedical Data</span>
          <div className="mt-1 font-bold text-[#172033] dark:text-white">
            {transferContext?.documents ? transferContext.documents.length : 3} Resources Selected
          </div>
        </div>
        <div>
          <span className="text-[#8A9AAD]">Authorized Destination</span>
          <div className="mt-1 font-bold text-[#172033] dark:text-white">
            {transferContext?.destination || 'Fortis Hospital Network'}
          </div>
        </div>
        <div>
          <span className="text-[#8A9AAD]">Elapsed Simulation</span>
          <div className="mt-1 font-bold text-[#2563EB] dark:text-[#67E8F9]">{response.elapsed_ms} ms</div>
        </div>
      </div>

      {/* Security Pipeline visual */}
      <div className="mt-6">
        <SecurityPipeline stages={response.stages} verdict={verdict} />
      </div>

      {/* Three telemetry cards: Threat, Quantum, QBER */}
      <div className="mt-5 grid gap-5 lg:grid-cols-3">
        <ThreatScoreCard threat={response.threat} />
        <QuantumChannelCard response={response} />
        <QBERCard response={response} />
      </div>

      {/* Static vs Adaptive comparison card */}
      <div className="mt-5">
        <PolicyComparisonCard response={response} />
      </div>

      {/* AES Protected Record / Blocked State */}
      <div className="mt-5">
        <ProtectedRecordSection record={response.record} verdict={verdict} stats={response.stats} />
      </div>

      <div className="mt-7 flex items-center justify-between">
        <Link
          href="/secure-transfer/"
          className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-5 py-3 text-[12px] font-semibold text-[#4D6075] dark:text-[#A8BACB] hover:bg-white dark:hover:bg-white/5 transition"
        >
          New Secure Transfer
        </Link>
        <div className="flex gap-3">
          <Link
            href="/scenario-comparison/"
            className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-5 py-3 text-[12px] font-semibold text-[#4D6075] dark:text-[#A8BACB] hover:bg-white dark:hover:bg-white/5 transition"
          >
            Scenario Comparison
          </Link>
          <Link
            href="/transfer-history/"
            className="rounded-xl bg-[#2563EB] px-5 py-3 text-[12px] font-semibold text-white shadow hover:bg-[#1D56D0] transition"
          >
            View Transfer History
          </Link>
        </div>
      </div>
    </main>
  )
}
