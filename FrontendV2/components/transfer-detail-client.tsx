'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AppShell } from '@/components/bioqshield'
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileCheck2,
  KeyRound,
  LockKeyhole,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import { formatTransferTimestamp, getTransferById, TransferHistoryItem } from '@/lib/api'

export function TransferDetailClient({ initialId }: { initialId: string }) {
  const id = initialId || 'BQS-2026-004821'

  const [item, setItem] = useState<TransferHistoryItem | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const found = getTransferById(id)
    if (found) {
      if (!found.timestamp || found.timestamp.trim().toLowerCase() === 'just now') {
        setItem({
          ...found,
          timestamp: formatTransferTimestamp(found.createdAt || new Date()),
        })
      } else {
        setItem(found)
      }
    } else {
      // Fallback seed for direct links
      const isBlocked = id.includes('820') || id.includes('819')
      setItem({
        id,
        timestamp: formatTransferTimestamp(new Date(Date.now() - 42 * 60 * 1000)),
        patient: 'John Doe',
        patientId: 'PT-20491',
        department: 'Cardiology',
        data: 'Medical Record + Prescription',
        destination: 'Fortis Hospital Network',
        scope: 'Hospital Network',
        verdict: isBlocked ? (id.includes('819') ? 'REJECT' : 'MONITOR') : 'ACCEPT',
        status: isBlocked ? 'Blocked' : 'Delivered',
        threatScore: isBlocked ? (id.includes('819') ? 0.92 : 0.65) : 0.18,
        qber: isBlocked ? (id.includes('819') ? 13.8 : 7.2) : 2.4,
        keyBits: isBlocked ? 0 : 1024,
      })
    }
    setLoading(false)
  }, [id])

  if (loading || !item) {
    return (
      <AppShell>
        <main className="mx-auto max-w-[1120px] px-10 py-10">
          <div className="text-sm text-[#64748B]">Loading transfer record...</div>
        </main>
      </AppShell>
    )
  }

  const isBlocked = item.status === 'Blocked' || item.verdict !== 'ACCEPT'
  const isReject = item.verdict === 'REJECT'

  return (
    <AppShell>
      <main className="mx-auto max-w-[1120px] px-10 py-10">
        <Link
          href="/transfer-history/"
          className="inline-flex items-center gap-2 text-[12px] font-semibold text-[#2563EB] dark:text-[#67E8F9] hover:underline"
        >
          <ArrowLeft className="size-4" />
          Back to Transfer History
        </Link>

        <div className="mt-7 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
              Transfer audit record
            </div>
            <h1 className="mt-3 text-[27px] font-bold tracking-[-0.03em] text-[#172033] dark:text-white">
              {item.id}
            </h1>
            <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
              Biomedical data transfer details and quantum cryptographic verification.
            </p>
          </div>
          <div
            className={`flex items-center gap-2 rounded-full px-3 py-2 text-[11px] font-bold ${
              isBlocked
                ? isReject
                  ? 'bg-[#FDEBEC] dark:bg-[#EF4444]/15 text-[#C33E42] dark:text-[#FF9292]'
                  : 'bg-[#FFF5E7] dark:bg-[#F59E0B]/15 text-[#B76405] dark:text-[#FFD083]'
                : 'bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
            }`}
          >
            {isBlocked ? (
              isReject ? (
                <XCircle className="size-4" />
              ) : (
                <Clock3 className="size-4" />
              )
            ) : (
              <CheckCircle2 className="size-4" />
            )}
            {isBlocked ? 'TRANSFER BLOCKED' : 'TRANSFER DELIVERED'}
          </div>
        </div>

        {isBlocked && (
          <div className="mt-7 rounded-2xl border border-[#F0D4B2] dark:border-[#F59E0B]/30 bg-[#FFFBF5] dark:bg-[#0B1726] p-5">
            <div className="flex items-center gap-2 text-[15px] font-bold text-[#8B4E05] dark:text-[#FFD083]">
              <ShieldAlert className="size-5" />
              Transfer Blocked by Adaptive Security Policy
            </div>
            <p className="mt-1 text-[12px] text-[#8B6B3D] dark:text-[#9AAABD]">
              No sensitive biomedical records or ciphertext were transmitted across the hospital
              network.
            </p>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
              <div>
                <span className="text-[#9A845F] dark:text-[#7F93A8]">Policy Reason</span>
                <p className="mt-1 font-semibold text-[#5C4930] dark:text-white">
                  {item.runResponse?.reason ||
                    (isReject
                      ? 'Elevated QBER / Intrusion threshold breached'
                      : 'Channel noise or threat elevated (MONITOR condition)')}
                </p>
              </div>
              <div>
                <span className="text-[#9A845F] dark:text-[#7F93A8]">Quantum Key Status</span>
                <p className="mt-1 font-semibold text-[#DC4446] dark:text-[#FF9292]">NOT RELEASED</p>
              </div>
              <div>
                <span className="text-[#9A845F] dark:text-[#7F93A8]">Network Release Status</span>
                <p className="mt-1 font-semibold text-[#DC4446] dark:text-[#FF9292]">
                  ZERO DATA EXPOSURE
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-5">
          <section className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <h2 className="text-[15px] font-bold text-[#172033] dark:text-white">
              Transfer Information
            </h2>
            <div className="mt-5 grid grid-cols-2 gap-5">
              {[
                ['Patient', `${item.patient} · ${item.patientId}`],
                ['Data Transferred', item.data],
                ['Source Hospital', 'Apollo Hospital · Chennai Main Branch'],
                ['Destination Network', item.destination],
                ['Timestamp', item.timestamp],
                ['Transfer Status', isBlocked ? 'BLOCKED AT SOURCE' : 'DELIVERED & VERIFIED'],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#9AAABD]">
                    {label}
                  </div>
                  <div className="mt-1 text-[12px] font-medium leading-5 text-[#172033] dark:text-white">
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <h2 className="text-[15px] font-bold text-[#172033] dark:text-white">
              Security Assessment
            </h2>
            <div className="mt-5 grid grid-cols-2 gap-5">
              {[
                [
                  'Security Verdict',
                  item.verdict,
                  ShieldCheck,
                  item.verdict === 'ACCEPT'
                    ? 'text-[#198657] dark:text-[#7BE3A0]'
                    : item.verdict === 'MONITOR'
                      ? 'text-[#B76405] dark:text-[#FFD083]'
                      : 'text-[#C33E42] dark:text-[#FF9292]',
                ],
                [
                  'Threat Classification',
                  item.threatScore < 0.33 ? 'LOW (NORMAL)' : item.threatScore < 0.7 ? 'MODERATE (ANOMALY)' : 'HIGH (ATTACK)',
                  ShieldAlert,
                  item.threatScore < 0.33 ? 'text-[#198657] dark:text-[#7BE3A0]' : 'text-[#DC4446] dark:text-[#FF9292]',
                ],
                [
                  'Threat Score',
                  item.threatScore.toFixed(2),
                  FileCheck2,
                  'text-[#172033] dark:text-white',
                ],
                [
                  'Quantum QBER',
                  `${item.qber.toFixed(1)}% (Threshold: 11%)`,
                  KeyRound,
                  item.qber <= 11 ? 'text-[#198657] dark:text-[#7BE3A0]' : 'text-[#DC4446] dark:text-[#FF9292]',
                ],
                [
                  'Quantum Key',
                  isBlocked ? 'NOT RELEASED' : 'VERIFIED (256-bit AES)',
                  KeyRound,
                  isBlocked ? 'text-[#DC4446] dark:text-[#FF9292]' : 'text-[#198657] dark:text-[#7BE3A0]',
                ],
                [
                  'Cipher Suite',
                  'AES-256-GCM',
                  LockKeyhole,
                  'text-[#172033] dark:text-white',
                ],
              ].map(([label, value, Icon, colorClass]) => (
                <div key={label as string}>
                  <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#9AAABD]">
                    <Icon className="size-3 text-[#14A493]" />
                    {label as string}
                  </div>
                  <div className={`mt-1 text-[12px] font-bold ${colorClass as string}`}>
                    {value as string}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Cryptographic Transmission Audit */}
        <section className="mt-5 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-bold text-[#172033] dark:text-white">
              Cryptographic Transmission Audit
            </h2>
            <span className="text-[11px] font-medium text-[#14A493]">
              AES-256-GCM authenticated encryption
            </span>
          </div>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-[#E6EDF3] dark:border-white/5 bg-[#FAFCFE] dark:bg-[#07111F] p-4">
              <div className="text-[11px] font-semibold text-[#172033] dark:text-white">
                Nonce (96-bit IV)
              </div>
              <div className="mt-2 font-mono text-[11px] break-all text-[#64748B] dark:text-[#9AAABD]">
                {item.runResponse?.record?.nonce_hex || (isBlocked ? 'null (suppressed)' : '4f8a19d2b7e530ac81e9f42b')}
              </div>
            </div>
            <div className="rounded-xl border border-[#E6EDF3] dark:border-white/5 bg-[#FAFCFE] dark:bg-[#07111F] p-4">
              <div className="text-[11px] font-semibold text-[#172033] dark:text-white">
                Ciphertext Transmission
              </div>
              <div className="mt-2 font-mono text-[11px] break-all text-[#64748B] dark:text-[#9AAABD]">
                {item.runResponse?.record?.ciphertext_hex ? (
                  `${item.runResponse.record.ciphertext_hex.slice(0, 48)}... (${item.runResponse.record.ciphertext_bytes ?? 0} bytes)`
                ) : isBlocked ? (
                  <span className="text-[#DC4446] dark:text-[#FF9292]">
                    [TRANSMISSION SUPPRESSED — ZERO BYTES DISPATCHED]
                  </span>
                ) : (
                  'c3f9a7210e5bd814e... (194 bytes delivered)'
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Security event timeline */}
        <section className="mt-5 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
          <h2 className="text-[15px] font-bold text-[#172033] dark:text-white">
            Security Event Pipeline Timeline
          </h2>
          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              ['01', 'Resource Verified', false],
              ['02', 'NSL-KDD Threat Scored', false],
              ['03', 'BB84 Quantum Sifted', false],
              ['04', 'QBER & EC Validated', isBlocked && item.qber > 11],
              ['05', 'Policy Verdict Evaluated', isBlocked],
              ['06', 'AES-256 Key Release', isBlocked],
              ['07', 'Hospital Network Receipt', isBlocked],
            ].map(([num, event, failed]) => (
              <div
                key={event as string}
                className={`flex flex-col items-start rounded-xl border p-3 ${
                  failed
                    ? 'border-[#F1D8D9] dark:border-red-900/30 bg-[#FFF7F7] dark:bg-red-950/10'
                    : 'border-[#E6EDF3] dark:border-white/5 bg-[#FAFCFE] dark:bg-white/[0.02]'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <div
                    className={`flex size-6 items-center justify-center rounded-full text-[10px] font-bold ${
                      failed
                        ? 'bg-[#FDEBEC] dark:bg-[#EF4444]/20 text-[#DC4446] dark:text-[#FF9292]'
                        : 'bg-[#E8F7EF] dark:bg-[#22C55E]/20 text-[#198657] dark:text-[#7BE3A0]'
                    }`}
                  >
                    {failed ? <XCircle className="size-3.5" /> : <CheckCircle2 className="size-3.5" />}
                  </div>
                  <span className="text-[10px] font-mono text-[#9AAABD]">{num as string}</span>
                </div>
                <p className="mt-2 text-[11px] font-medium leading-4 text-[#172033] dark:text-white">
                  {event as string}
                </p>
                <span
                  className={`mt-1 text-[9px] font-semibold uppercase ${
                    failed ? 'text-[#DC4446] dark:text-[#FF9292]' : 'text-[#198657] dark:text-[#7BE3A0]'
                  }`}
                >
                  {failed ? 'BLOCKED' : 'PASSED'}
                </span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </AppShell>
  )
}
