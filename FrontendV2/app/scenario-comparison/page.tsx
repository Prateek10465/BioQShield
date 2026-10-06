'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, Play, RefreshCw, RotateCcw, ShieldCheck } from 'lucide-react'
import {
  demoDisclaimer,
  LineChart,
  PolicyNote,
  StatusBadge,
  TechCard,
  TechnicalPage,
} from '@/components/technical-security'
import { fetchScenarios, ScenarioItem } from '@/lib/api'

export default function ScenarioComparisonPage() {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const loadScenarios = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchScenarios()
      setScenarios(data)
    } catch (err: any) {
      setError(err?.message || 'Failed to load scenarios from backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadScenarios()
  }, [])

  const active = scenarios[selectedIndex] || scenarios[0]

  // Chart values from scenarios
  const chartValues = scenarios.length > 0
    ? scenarios.map((s) => parseFloat((s.qber * 100).toFixed(1)))
    : [2.0, 5.0, 8.0, 2.0, 5.0, 25.0, 25.0]

  const chartLabels = scenarios.length > 0
    ? scenarios.map((s, i) => `S${i + 1}`)
    : ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7']

  return (
    <TechnicalPage
      title="Scenario Comparison"
      subtitle="Compare BioQShield security decisions across network threats and quantum channel conditions."
      action={
        <div className="flex gap-2">
          <button
            onClick={loadScenarios}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-[#14B8A6] px-4 py-2.5 text-xs font-bold text-[#07111F] hover:bg-[#5EDCEB] transition disabled:opacity-50"
          >
            <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
            Run / Re-evaluate All Scenarios
          </button>
        </div>
      }
    >
      <div className="mt-3 text-[11px] text-[#7F93A8]">
        {demoDisclaimer} · Source: Live backend evaluation via GET /api/scenarios
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-[#EF4444]/40 bg-[#EF4444]/10 p-3 text-xs text-[#FF9292]">
          <AlertTriangle className="inline size-4 mr-2" />
          {error}
        </div>
      )}

      {/* Grid of Scenario Cards */}
      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {scenarios.slice(0, 4).map((scenario, index) => {
          const isSelected = selectedIndex === index
          const qberPct = (scenario.qber * 100).toFixed(1)
          const threatPct = scenario.threat.toFixed(2)
          const finalStatus = scenario.adaptive === 'ACCEPT' ? 'SECURE' : 'BLOCKED'

          return (
            <button
              key={scenario.scenario}
              onClick={() => setSelectedIndex(index)}
              className={`rounded-2xl border p-4 text-left transition ${
                isSelected
                  ? 'border-[#22D3EE]/60 bg-[#10283A]'
                  : 'border-white/10 bg-[#0B1726] hover:border-white/25'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-[11px] font-bold tracking-[0.08em] text-white uppercase line-clamp-1">
                  {scenario.scenario}
                </div>
                <StatusBadge value={finalStatus} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-y-2.5 text-[10px]">
                <Stat label="Threat Score" value={threatPct} />
                <Stat label="QBER" value={`${qberPct}%`} />
                <Stat label="Static Policy" value={scenario.static} />
                <Stat label="Adaptive Policy" value={scenario.adaptive} />
                <Stat label="Key Material" value={scenario.adaptive === 'ACCEPT' ? `${scenario.key_bits}b` : 'BLOCKED'} />
                <Stat label="Outcome" value={finalStatus} />
              </div>
            </button>
          )
        })}
      </div>

      {/* Detail section */}
      {active && (
        <div className="mt-5 grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
          <TechCard title="Selected Scenario Details" eyebrow={active.scenario}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl font-bold text-white">{active.scenario}</div>
                <div className="mt-1 text-[11px] text-[#9AAABD]">
                  Evaluated using live NSL-KDD classifier & BB84 simulation
                </div>
              </div>
              <StatusBadge value={active.adaptive === 'ACCEPT' ? 'SECURE' : 'BLOCKED'} />
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3 text-xs">
              {[
                ['Network Threat Score', active.threat.toFixed(2)],
                ['Estimated QBER', `${(active.qber * 100).toFixed(1)}%`],
                ['Static Decision (QBER only)', active.static],
                ['Adaptive Decision (Threat+QBER)', active.adaptive],
                ['Derived Secret Key Bits', active.adaptive === 'ACCEPT' ? `${active.key_bits} bits` : 'Not released (Blocked)'],
                ['Patient Record Security', active.adaptive === 'ACCEPT' ? 'AES-256-GCM Delivered' : 'Transmission Blocked'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl bg-[#07111F] p-3 border border-white/5">
                  <div className="text-[10px] text-[#7F93A8]">{label}</div>
                  <div className="mt-1 font-bold text-white">{value}</div>
                </div>
              ))}
            </div>
            <p className="mt-5 text-xs leading-5 text-[#A8BACB] border-t border-white/10 pt-4">
              <span className="font-semibold text-white">Policy Decision Reason: </span>
              {active.reason}
            </p>
          </TechCard>

          <TechCard
            title="QBER Distribution Across Scenarios"
            eyebrow="Comparison of all 7 predefined traffic x channel scenarios against 11% abort threshold"
          >
            <LineChart values={chartValues} threshold={11} color="#67E8F9" labels={chartLabels} />
            <div className="mt-4">
              <PolicyNote />
            </div>
          </TechCard>
        </div>
      )}

      {/* Comparison Table */}
      <TechCard title="All 7 Predefined Scenarios" eyebrow="Live comparison table from GET /api/scenarios" className="mt-5">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[950px] text-left text-[11px]">
            <thead className="border-b border-white/10 text-[10px] uppercase tracking-[0.1em] text-[#71869D]">
              <tr>
                <th className="px-3 py-3">Scenario</th>
                <th className="px-3 py-3">Threat</th>
                <th className="px-3 py-3">QBER</th>
                <th className="px-3 py-3">Key Bits</th>
                <th className="px-3 py-3">Static Verdict</th>
                <th className="px-3 py-3">Adaptive Verdict</th>
                <th className="px-3 py-3">Final Status</th>
                <th className="px-3 py-3">Reason</th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map((sc, i) => {
                const isSelected = selectedIndex === i
                const finalStatus = sc.adaptive === 'ACCEPT' ? 'SECURE' : 'BLOCKED'
                return (
                  <tr
                    key={sc.scenario}
                    onClick={() => setSelectedIndex(i)}
                    className={`border-b border-white/5 last:border-0 cursor-pointer hover:bg-white/[0.04] transition ${
                      isSelected ? 'bg-white/[0.05]' : ''
                    }`}
                  >
                    <td className="px-3 py-3 font-semibold text-white">{sc.scenario}</td>
                    <td className="px-3 py-3 text-[#9AAABD]">{sc.threat.toFixed(2)}</td>
                    <td className="px-3 py-3 text-[#67E8F9]">{(sc.qber * 100).toFixed(1)}%</td>
                    <td className="px-3 py-3 text-[#9AAABD]">{sc.adaptive === 'ACCEPT' ? `${sc.key_bits}b` : '0b'}</td>
                    <td className="px-3 py-3">
                      <StatusBadge value={sc.static as 'ACCEPT' | 'REJECT'} />
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge value={sc.adaptive as 'ACCEPT' | 'REJECT'} />
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge value={finalStatus} />
                    </td>
                    <td className="px-3 py-3 text-[10px] text-[#A8BACB] max-w-xs truncate" title={sc.reason}>
                      {sc.reason}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </TechCard>

      <details className="mt-5 rounded-2xl border border-white/10 bg-[#0B1726] p-5 text-white">
        <summary className="cursor-pointer text-sm font-semibold">
          Adaptive vs. Static Security Policy Mechanics
        </summary>
        <p className="mt-3 max-w-3xl text-xs leading-5 text-[#9AAABD]">
          While a static QKD policy only examines QBER against static 6% and 11% boundaries, BioQShield integrates NSL-KDD
          network flow threat intelligence. When an adversary attempts an attack or network probes are detected,
          the acceptance threshold dynamically drops (0.06 &minus; 0.03&times;threat), reject boundary tightens
          (0.11 &minus; 0.04&times;threat), and critical threat (&ge; 0.8) escalates any MONITOR state directly to REJECT.
        </p>
      </details>
    </TechnicalPage>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[#71869D]">{label}</div>
      <div className="mt-0.5 font-semibold text-[#D9E5F0]">{value}</div>
    </div>
  )
}
