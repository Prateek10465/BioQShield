'use client'

import { useEffect, useState } from 'react'
import { Activity, KeyRound, Radio, ShieldAlert } from 'lucide-react'
import {
  demoDisclaimer,
  LineChart,
  Metric,
  PolicyNote,
  StatusBadge,
  TechCard,
  TechnicalPage,
} from '@/components/technical-security'
import { formatTransferTimestamp, getLatestTransfer, getTransferHistory, TransferHistoryItem } from '@/lib/api'

export default function SecurityDashboardPage() {
  const [history, setHistory] = useState<TransferHistoryItem[]>([])
  const [latest, setLatest] = useState<TransferHistoryItem | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const hist = getTransferHistory()
    const lat = getLatestTransfer()
    setHistory(hist)
    setLatest(lat || hist[0] || null)
    setMounted(true)
  }, [])

  const currentItem = latest || {
    id: 'BQS-2026-004821',
    timestamp: formatTransferTimestamp(new Date(Date.now() - 42 * 60 * 1000)),
    patient: 'John Doe',
    patientId: 'PT-20491',
    department: 'Cardiology',
    data: 'Medical Record + Prescription',
    destination: 'Fortis Hospital Network',
    scope: 'Hospital Network',
    verdict: 'ACCEPT' as const,
    status: 'Delivered' as const,
    threatScore: 0.18,
    qber: 2.4,
    keyBits: 1024,
  }

  const threatLevel =
    currentItem.threatScore < 0.33 ? 'LOW' : currentItem.threatScore < 0.7 ? 'MODERATE' : 'HIGH'
  const threatTone =
    currentItem.threatScore < 0.33 ? 'green' : currentItem.threatScore < 0.7 ? 'amber' : 'amber'
  const threatClassDetail =
    currentItem.threatScore < 0.33
      ? 'Normal classification'
      : currentItem.threatScore < 0.7
        ? 'Mixed traffic anomaly'
        : 'Attack pattern detected'

  const totalTransfers = history.length || 3
  const acceptCount = history.filter((h) => h.verdict === 'ACCEPT').length || 2
  const monitorCount = history.filter((h) => h.verdict === 'MONITOR').length || 1
  const rejectCount = history.filter((h) => h.verdict === 'REJECT').length || 0
  const acceptPct = Math.round((acceptCount / totalTransfers) * 100)
  const monitorPct = Math.round((monitorCount / totalTransfers) * 100)
  const rejectPct = Math.max(0, 100 - acceptPct - monitorPct)

  const blockedCount = history.filter((h) => h.status === 'Blocked').length

  // Build chart values from latest run's QBER trace or dynamic samples
  const qberChartValues =
    currentItem.runResponse?.qber_trace && currentItem.runResponse.qber_trace.length > 0
      ? currentItem.runResponse.qber_trace.map((b) => Number(((b.qber ?? 0) * 100).toFixed(1)))
      : [
          Number((currentItem.qber * 0.9).toFixed(1)),
          Number((currentItem.qber * 1.15).toFixed(1)),
          Number((currentItem.qber * 0.95).toFixed(1)),
          Number((currentItem.qber * 1.2).toFixed(1)),
          Number((currentItem.qber * 1.0).toFixed(1)),
          Number((currentItem.qber * 1.05).toFixed(1)),
          Number((currentItem.qber * 0.92).toFixed(1)),
          Number(currentItem.qber.toFixed(1)),
        ]

  return (
    <TechnicalPage
      title="Security Dashboard"
      subtitle="Monitor network threat conditions and quantum communication security."
    >
      <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Metric
          label="Network threat"
          value={threatLevel}
          detail={threatClassDetail}
          tone={threatTone as any}
        />
        <Metric
          label="Threat score"
          value={currentItem.threatScore.toFixed(2)}
          detail={currentItem.threatScore < 0.33 ? 'Within safe range' : 'Elevated risk'}
          tone={currentItem.threatScore < 0.33 ? 'teal' : 'amber'}
        />
        <Metric
          label="Current QBER"
          value={`${currentItem.qber.toFixed(1)}%`}
          detail="11% threshold"
          tone={currentItem.qber <= 11 ? 'cyan' : 'amber'}
        />
        <Metric
          label="Quantum keys"
          value={
            currentItem.keyBits > 0
              ? String(Math.max(1, Math.floor(currentItem.keyBits / 128))).padStart(2, '0')
              : '00'
          }
          detail={currentItem.keyBits > 0 ? 'Available now' : 'Key blocked'}
          tone={currentItem.keyBits > 0 ? 'teal' : 'amber'}
        />
        <Metric
          label="Active QKD"
          value={String(totalTransfers).padStart(2, '0')}
          detail="Logged sessions"
          tone="cyan"
        />
        <Metric
          label="Blocked"
          value={String(blockedCount).padStart(2, '0')}
          detail={blockedCount > 0 ? 'Requires review' : 'Zero incidents'}
          tone={blockedCount > 0 ? 'amber' : 'green'}
        />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_1fr]">
        <TechCard title="Network Threat Overview" eyebrow="Threat classification from NSL-KDD analysis">
          <div className="flex items-end justify-between">
            <div>
              <div className="text-4xl font-bold text-white">{currentItem.threatScore.toFixed(2)}</div>
              <div className="mt-2 flex items-center gap-2">
                <StatusBadge
                  value={
                    currentItem.verdict === 'ACCEPT'
                      ? 'SECURE'
                      : currentItem.verdict === 'MONITOR'
                        ? 'MONITOR'
                        : 'BLOCKED'
                  }
                />
                <span className="text-[11px] text-[#7F93A8]">
                  {currentItem.threatScore < 0.33
                    ? 'NORMAL · LOW'
                    : currentItem.threatScore < 0.7
                      ? 'MIXED · MODERATE'
                      : 'ATTACK · HIGH'}
                </span>
              </div>
            </div>
            <div className="text-right text-[11px] text-[#9AAABD]">
              Current network conditions
              <br />
              <span className={currentItem.threatScore < 0.33 ? 'text-[#7BE3A0]' : 'text-[#FFD083]'}>
                {currentItem.threatScore < 0.33 ? 'within acceptable limits' : 'elevated risk threshold'}
              </span>
            </div>
          </div>
          <div className="mt-6">
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#22C55E] to-[#F59E0B]"
                style={{ width: `${Math.min(100, Math.max(5, Math.round(currentItem.threatScore * 100)))}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-[10px] text-[#7F93A8]">
              <span>LOW</span>
              <span>MODERATE</span>
              <span>HIGH</span>
            </div>
          </div>
        </TechCard>

        <TechCard title="Threat Score Over Time" eyebrow="Synthetic monitoring window">
          <LineChart
            values={[0.12, 0.15, 0.18, 0.21, 0.17, currentItem.threatScore]}
            color="#14B8A6"
            labels={['09:00', '09:15', '09:30', '09:45', '10:00', '10:15']}
          />
        </TechCard>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
        <TechCard title="Quantum Channel Health" eyebrow="QBER Across Qubit Stream">
          <div className="mb-3 flex items-end justify-between">
            <div className="text-3xl font-bold text-[#67E8F9]">{currentItem.qber.toFixed(1)}%</div>
            <div className="text-right text-[11px] text-[#9AAABD]">
              Security threshold
              <br />
              <span className="font-semibold text-[#FFD083]">11%</span>
            </div>
          </div>
          <LineChart
            values={qberChartValues}
            threshold={11}
            color="#22D3EE"
            labels={['01', '02', '03', '04', '05', '06', '07', '08'].slice(0, qberChartValues.length)}
          />
          <PolicyNote />
        </TechCard>

        <TechCard title="Transfer Security Outcomes" eyebrow="Distribution across recent sessions">
          <div className="flex flex-col gap-4">
            <Outcome label="ACCEPT" value={`${acceptPct}%`} color="bg-[#22C55E]" />
            <Outcome label="MONITOR" value={`${monitorPct}%`} color="bg-[#F59E0B]" />
            <Outcome label="REJECT" value={`${rejectPct}%`} color="bg-[#EF4444]" />
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-[#07111F] p-3">
              <div className="text-[10px] text-[#7F93A8]">Static policy</div>
              <div className="mt-1 text-sm font-bold">{acceptPct}% accept</div>
            </div>
            <div className="rounded-xl bg-[#07111F] p-3">
              <div className="text-[10px] text-[#7F93A8]">Adaptive policy</div>
              <div className="mt-1 text-sm font-bold text-[#67E8D9]">
                {Math.max(0, acceptPct - (currentItem.threatScore > 0.5 ? 10 : 0))}% accept
              </div>
            </div>
          </div>
        </TechCard>
      </div>

      <TechCard title="Recent Security Events" eyebrow={demoDisclaimer} className="mt-5">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-xs">
            <thead className="text-[10px] uppercase tracking-[0.12em] text-[#71869D]">
              <tr>
                {['Time', 'Event', 'Threat', 'QBER', 'Verdict'].map((head) => (
                  <th key={head} className="border-b border-white/10 pb-3 font-semibold">
                    {head}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.map((h) => {
                const timeStr = h.timestamp.includes('·') ? h.timestamp.split('·')[1].trim() : h.timestamp
                const tLevel = h.threatScore < 0.33 ? 'LOW' : h.threatScore < 0.7 ? 'MODERATE' : 'HIGH'
                return (
                  <tr key={h.id} className="border-b border-white/5 last:border-0">
                    <td className="py-4 text-[#9AAABD]">{timeStr}</td>
                    <td className="py-4 font-medium text-white">{h.data || 'Biomedical transfer'}</td>
                    <td className="py-4 text-[#9AAABD]">{tLevel}</td>
                    <td className="py-4 text-[#67E8F9]">{h.qber.toFixed(1)}%</td>
                    <td className="py-4">
                      <StatusBadge value={h.verdict} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </TechCard>
    </TechnicalPage>
  )
}

function Outcome({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div>
      <div className="mb-1.5 flex justify-between text-[11px]">
        <span className="font-semibold text-[#D9E5F0]">{label}</span>
        <span className="text-[#9AAABD]">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10">
        <div className={`h-full rounded-full ${color}`} style={{ width: value }} />
      </div>
    </div>
  )
}
