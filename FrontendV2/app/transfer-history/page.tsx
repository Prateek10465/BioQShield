'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { AppShell } from '@/components/bioqshield'
import { TransferDetailClient } from '@/components/transfer-detail-client'
import { CheckCircle2, Clock3, Eye, FileText, Search, ShieldAlert, XCircle } from 'lucide-react'
import { getTransferHistory, TransferHistoryItem } from '@/lib/api'

export default function TransferHistoryPage() {
  const pathname = usePathname()
  const [history, setHistory] = useState<TransferHistoryItem[]>([])
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [destinationFilter, setDestinationFilter] = useState('All')

  useEffect(() => {
    setHistory(getTransferHistory())
  }, [])

  const destinations = Array.from(new Set(history.map((r) => r.destination)))

  const filtered = history.filter((r) => {
    const matchesQuery =
      query === '' ||
      [r.id, r.patient, r.data, r.destination, r.patientId]
        .join(' ')
        .toLowerCase()
        .includes(query.toLowerCase())

    const matchesStatus =
      statusFilter === 'All' || r.status.toLowerCase() === statusFilter.toLowerCase()

    const matchesDestination =
      destinationFilter === 'All' || r.destination === destinationFilter

    return matchesQuery && matchesStatus && matchesDestination
  })

  const detailMatch = pathname.match(/^\/transfer-history\/([^/]+)\/?$/)
  if (detailMatch) {
    return <TransferDetailClient initialId={decodeURIComponent(detailMatch[1])} />
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1240px] px-10 py-10">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
              Audit trail
            </div>
            <h1 className="mt-3 text-[30px] font-bold tracking-[-0.03em] text-[#172033] dark:text-white">
              Transfer History
            </h1>
            <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
              Review previous biomedical data transfers and their security outcomes.
            </p>
          </div>
          <div className="flex items-center gap-2 text-[11px] font-medium text-[#198657] dark:text-[#7BE3A0]">
            <ShieldAlert className="size-4" />
            Synthetic demo records · Zero PII exposure
          </div>
        </div>

        <section className="mt-8 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
          <div className="flex flex-wrap items-center gap-3 border-b border-[#E6EDF3] dark:border-white/10 p-5">
            <div className="relative min-w-[280px] flex-1">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[#9AAABD]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search patient, transfer ID, or document type"
                className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-transparent py-2.5 pl-10 pr-3 text-[12px] text-[#172033] dark:text-white outline-none focus:border-[#8BB8F5] dark:focus:border-[#22D3EE]"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-3 py-2.5 text-[12px] text-[#64748B] dark:text-[#9AAABD] outline-none"
            >
              <option value="All">Status: All</option>
              <option value="Delivered">Delivered</option>
              <option value="Blocked">Blocked</option>
            </select>
            <select
              value={destinationFilter}
              onChange={(e) => setDestinationFilter(e.target.value)}
              className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-3 py-2.5 text-[12px] text-[#64748B] dark:text-[#9AAABD] outline-none"
            >
              <option value="All">Destination: All</option>
              {destinations.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#E6EDF3] dark:border-white/10 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#91A1B2] dark:text-[#7F93A8]">
                  <th className="px-6 py-4">Transfer ID</th>
                  <th className="px-4 py-4">Patient</th>
                  <th className="px-4 py-4">Data</th>
                  <th className="px-4 py-4">Destination</th>
                  <th className="px-4 py-4">Date / time</th>
                  <th className="px-4 py-4">Security verdict</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-4 py-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => {
                  const isAccept = row.verdict === 'ACCEPT'
                  const isMonitor = row.verdict === 'MONITOR'
                  const badgeClass = isAccept
                    ? 'bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
                    : isMonitor
                      ? 'bg-[#FFF5E7] dark:bg-[#F59E0B]/15 text-[#B76405] dark:text-[#FFD083]'
                      : 'bg-[#FDEBEC] dark:bg-[#EF4444]/15 text-[#C33E42] dark:text-[#FF9292]'
                  const Icon = isAccept ? CheckCircle2 : isMonitor ? Clock3 : XCircle

                  return (
                    <tr
                      key={row.id}
                      className="border-b border-[#EEF2F6] dark:border-white/5 last:border-0 hover:bg-[#FAFCFE] dark:hover:bg-white/[0.02]"
                    >
                      <td className="px-6 py-4 text-[11px] font-semibold text-[#2563EB] dark:text-[#67E8F9]">
                        <Link href={`/transfer-history/${row.id}`} className="hover:underline">
                          {row.id}
                        </Link>
                      </td>
                      <td className="px-4 py-4 text-[12px] font-semibold text-[#172033] dark:text-white">
                        {row.patient}
                      </td>
                      <td className="px-4 py-4 text-[11px] text-[#4D6075] dark:text-[#9AAABD]">
                        {row.data}
                      </td>
                      <td className="px-4 py-4 text-[11px] text-[#4D6075] dark:text-[#9AAABD]">
                        {row.destination}
                      </td>
                      <td className="px-4 py-4 text-[11px] text-[#64748B] dark:text-[#7F93A8]">
                        {row.timestamp}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${badgeClass}`}
                        >
                          <Icon className="size-3" />
                          {row.verdict}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-[11px] font-medium text-[#64748B] dark:text-[#9AAABD]">
                        <span
                          className={
                            row.status === 'Delivered'
                              ? 'text-[#198657] dark:text-[#7BE3A0] font-semibold'
                              : 'text-[#DC4446] dark:text-[#FF9292] font-semibold'
                          }
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <Link
                          href={`/transfer-history/${row.id}/`}
                          aria-label={`View ${row.id}`}
                          className="inline-flex items-center justify-center text-[#2563EB] dark:text-[#67E8F9] hover:opacity-80"
                        >
                          <Eye className="size-4" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {filtered.length === 0 && (
              <div className="p-12 text-center">
                <FileText className="mx-auto size-7 text-[#9AAABD]" />
                <h2 className="mt-3 text-[14px] font-bold text-[#172033] dark:text-white">
                  No Search Results
                </h2>
                <p className="mt-1 text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                  No matching records found.
                </p>
              </div>
            )}
          </div>
        </section>
      </main>
    </AppShell>
  )
}
