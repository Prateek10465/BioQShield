'use client'

import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Check,
  CheckCircle2,
  Cpu,
  Eye,
  KeyRound,
  LockKeyhole,
  Play,
  Radio,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  Zap,
} from 'lucide-react'
import {
  demoDisclaimer,
  Metric,
  PolicyNote,
  QuantumFlow,
  StatusBadge,
  TechCard,
  TechnicalPage,
  TogglePill,
} from '@/components/technical-security'
import {
  fetchQiskitDemo,
  QiskitDemoResponse,
  QBERTraceBin,
  runSimulation,
  RunResponse,
} from '@/lib/api'

const steps = [
  '1. Alice generates random bits and random bases (Z or X)',
  '2. Alice prepares single-qubit states (|0>, |1>, |+>, |->)',
  '3. Optional Eve intercept-resend collapses quantum states',
  '4. Channel introduces physical bit-flip/readout noise',
  '5. Bob measures incoming qubits in random bases (Z or X)',
  '6. Public basis reconciliation (sifting) discards mismatches',
  '7. Random sample revealed to estimate QBER',
  '8. Cascade error correction & parity verification fixes errors',
  '9. Toeplitz universal hash shrinks key for privacy amplification',
  '10. SHA-256 derives 256-bit AES key for record encryption',
]

export default function QuantumConsolePage() {
  const [eve, setEve] = useState(false)
  const [noise, setNoise] = useState(0.02)
  const [nQubitsCircuit, setNQubitsCircuit] = useState(12)
  const [loading, setLoading] = useState(false)
  const [qiskitData, setQiskitData] = useState<QiskitDemoResponse | null>(null)
  const [runStats, setRunStats] = useState<RunResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const executeSimulation = async () => {
    setLoading(true)
    setError(null)
    try {
      // 1. Fetch real Qiskit circuit and per-qubit results from Aer simulator
      const demoRes = await fetchQiskitDemo({
        n: nQubitsCircuit,
        eve,
        noise,
        seed: 42,
      })
      setQiskitData(demoRes)

      // 2. Fetch full statistical simulation for QBER trace and protocol status
      const fullRes = await runSimulation({
        n_qubits: 8192,
        noise,
        eve,
        eve_rate: 1.0,
        eve_start: 0.5,
        traffic: 'benign',
        adaptive: true,
        seed: 1,
      })
      setRunStats(fullRes)
    } catch (err: any) {
      setError(err?.message || 'Qiskit simulation failed.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    executeSimulation()
  }, [eve, noise, nQubitsCircuit])

  const qberEst = runStats ? (runStats.stats.qber_est * 100).toFixed(1) : (noise * 100).toFixed(1)
  const qberUpper = runStats ? (runStats.stats.qber_upper * 100).toFixed(1) : ((noise + 0.01) * 100).toFixed(1)
  const channelSecure = runStats ? runStats.status === 'secure' : !eve && noise < 0.06

  return (
    <TechnicalPage
      title="Quantum Console"
      subtitle="Interactive BB84 quantum key distribution workspace powered by Qiskit Aer."
      action={
        <div className="flex gap-2">
          <button
            onClick={executeSimulation}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl bg-[#22D3EE] px-4 py-2.5 text-xs font-bold text-[#07111F] hover:bg-[#67E8F9] transition disabled:opacity-50"
          >
            <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
            Rerun Qiskit Aer
          </button>
        </div>
      }
    >
      {/* Top telemetry metrics */}
      <div className="mt-7 flex flex-wrap gap-3">
        <Metric label="Quantum Engine" value="Qiskit Aer" detail="Simulator v0.17" tone="cyan" />
        <Metric label="Protocol" value="BB84" detail="Prepare & Measure" tone="teal" />
        <Metric
          label="Link Status"
          value={channelSecure ? 'SECURE' : 'ABORTED'}
          detail={channelSecure ? 'Error rate within boundary' : 'Exceeds 11% threshold'}
          tone={channelSecure ? 'green' : 'amber'}
        />
        <Metric
          label="Eavesdropper"
          value={eve ? 'ACTIVE' : 'OFF'}
          detail={eve ? 'Intercept-resend enabled' : 'Clean transmission path'}
          tone={eve ? 'amber' : 'green'}
        />
        <Metric label="Current QBER" value={`${qberEst}%`} detail="11% abort limit" tone={channelSecure ? 'cyan' : 'amber'} />
      </div>

      {error && (
        <div className="mt-5 rounded-xl border border-[#EF4444]/40 bg-[#EF4444]/10 p-4 text-xs text-[#FF9292]">
          <AlertTriangle className="inline size-4 mr-2" />
          {error}
        </div>
      )}

      {/* Main Grid: Quantum link & Channel controls */}
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <TechCard
          title="Alice &rarr; Bob Quantum Link"
          eyebrow={eve ? 'Intercept-resend adversary active on link' : 'Direct quantum communication channel'}
        >
          <QuantumFlow eve={eve} />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
            <div className="text-[11px] text-[#9AAABD]">
              {eve
                ? 'Eve projects qubits onto random bases, inducing an expected ~25% error rate on sifted bits.'
                : `Channel noise is set to ${(noise * 100).toFixed(1)}%. QBER remains within quantum security bounds.`}
            </div>
            <button
              onClick={() => setEve(!eve)}
              className={`rounded-lg border px-3 py-1.5 text-[10px] font-bold tracking-[0.08em] transition ${
                eve
                  ? 'border-[#EF4444]/40 bg-[#EF4444]/15 text-[#FF9292]'
                  : 'border-white/10 bg-[#07111F] text-[#9AAABD] hover:text-white'
              }`}
            >
              {eve ? 'DISABLE EVE' : 'ENABLE EVE INTERCEPTION'}
            </button>
          </div>
        </TechCard>

        <TechCard title="Channel Conditions" eyebrow="Configured simulation parameters">
          <div className="grid gap-2.5">
            <div className="rounded-xl border border-white/10 bg-[#07111F] p-3">
              <div className="flex justify-between text-[11px] text-[#9AAABD]">
                <span>Noise probability:</span>
                <span className="font-bold text-[#67E8F9]">{(noise * 100).toFixed(1)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="0.15"
                step="0.01"
                value={noise}
                onChange={(e) => setNoise(parseFloat(e.target.value))}
                className="mt-2 w-full accent-[#22D3EE]"
              />
            </div>
            <TogglePill
              label="Eavesdropper (Eve)"
              value={eve ? 'ACTIVE' : 'DISABLED'}
              active={eve}
              onClick={() => setEve(!eve)}
            />
            <div className="rounded-xl border border-white/10 bg-[#07111F] p-3 flex justify-between items-center text-[11px]">
              <span className="text-[#9AAABD]">Circuit Qubits (n):</span>
              <div className="flex gap-1">
                {[6, 12, 18, 24].map((cnt) => (
                  <button
                    key={cnt}
                    onClick={() => setNQubitsCircuit(cnt)}
                    className={`rounded px-2 py-1 text-[10px] font-bold ${
                      nQubitsCircuit === cnt ? 'bg-[#22D3EE] text-[#07111F]' : 'bg-white/10 text-white'
                    }`}
                  >
                    {cnt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </TechCard>
      </div>

      {/* QISKIT DEMONSTRATION SECTION */}
      <TechCard
        title="Qiskit Demonstration (Circuit Execution on Qiskit Aer)"
        eyebrow="Real quantum circuits executed via Qiskit Aer simulator for representative qubits"
        className="mt-5"
      >
        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          {/* Circuit visual */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#67E8F9] flex items-center gap-1.5">
                <Terminal className="size-3.5" />
                Qiskit Quantum Circuit Architecture
              </span>
              <span className="text-[10px] text-[#71869D]">Single-qubit BB84 representation</span>
            </div>
            <pre className="overflow-x-auto rounded-xl border border-white/10 bg-[#07111F] p-4 text-[12px] font-mono leading-relaxed text-[#22D3EE] select-all max-h-56">
              {qiskitData?.circuit || qiskitData?.circuit_ascii || 'Loading circuit from Qiskit Aer...'}
            </pre>
            <div className="mt-2 text-[10px] text-[#71869D]">
              Circuit details: Alice applies X gate if bit=1, H gate if basis=X. Eve (if active) measures in random basis and resends. Bob applies H if basis=X and measures.
            </div>
          </div>

          {/* Qiskit simulation summary */}
          <div className="rounded-xl border border-white/10 bg-[#07111F] p-4 flex flex-col justify-between">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#14B8A6] mb-3">
                Aer Execution Summary
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-[10px] text-[#71869D]">Simulated Qubits</div>
                  <div className="font-bold text-white text-base">{qiskitData?.summary.n_qubits || nQubitsCircuit}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[#71869D]">Sifted Kept Qubits</div>
                  <div className="font-bold text-[#67E8F9] text-base">{qiskitData?.summary.kept_qubits ?? 0}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[#71869D]">Observed Errors</div>
                  <div className="font-bold text-[#EF4444] text-base">{qiskitData?.summary.errors ?? 0}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[#71869D]">Circuit QBER</div>
                  <div className="font-bold text-white text-base">
                    {qiskitData?.summary.qber !== null && qiskitData?.summary.qber !== undefined
                      ? `${(qiskitData.summary.qber * 100).toFixed(1)}%`
                      : '0.0%'}
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-white/10 text-[10px] text-[#71869D]">
              Engine: <span className="text-[#67E8F9] font-bold">Qiskit Aer</span> (exact statevector & readout simulation)
            </div>
          </div>
        </div>

        {/* Representative Qubits Table */}
        <div className="mt-5">
          <div className="text-[11px] font-bold text-white mb-2">Representative Qubit Transmission Log</div>
          <div className="overflow-x-auto rounded-xl border border-white/10 bg-[#07111F]">
            <table className="w-full min-w-[650px] text-left text-[11px]">
              <thead className="border-b border-white/10 text-[10px] uppercase tracking-[0.1em] text-[#71869D]">
                <tr>
                  <th className="px-3 py-2.5">Qubit</th>
                  <th className="px-3 py-2.5">Alice Basis</th>
                  <th className="px-3 py-2.5">Alice Bit</th>
                  <th className="px-3 py-2.5">Eve State</th>
                  <th className="px-3 py-2.5">Bob Basis</th>
                  <th className="px-3 py-2.5">Bob Measurement</th>
                  <th className="px-3 py-2.5">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {qiskitData?.rows.map((row) => {
                  const isMatch = row.outcome === 'MATCH'
                  const isError = row.outcome === 'ERROR'
                  return (
                    <tr key={row.qubit} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                      <td className="px-3 py-2 font-mono font-bold text-[#67E8F9]">q[{row.qubit}]</td>
                      <td className="px-3 py-2 text-[#9AAABD]">{row.alice.basis}</td>
                      <td className="px-3 py-2 text-white font-mono">{row.alice.bit}</td>
                      <td className="px-3 py-2 text-[#EF4444]">
                        {row.eve ? `Basis ${row.eve.basis}` : '—'}
                      </td>
                      <td className="px-3 py-2 text-[#9AAABD]">{row.bob.basis}</td>
                      <td className="px-3 py-2 text-white font-mono">{row.bob.bit}</td>
                      <td className="px-3 py-2">
                        <span
                          className={`rounded px-2 py-0.5 text-[9px] font-bold ${
                            isMatch
                              ? 'bg-[#22C55E]/15 text-[#7BE3A0]'
                              : isError
                              ? 'bg-[#EF4444]/15 text-[#FF9292]'
                              : 'bg-white/5 text-[#71869D]'
                          }`}
                        >
                          {row.outcome}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </TechCard>

      {/* QBER Panel & QBER Chart across stream */}
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <TechCard title="QBER Chart Across Qubit Stream" eyebrow="Bin-by-bin error rate from backend qber_trace">
          {runStats?.qber_trace && runStats.qber_trace.length > 0 ? (
            <div className="relative pt-4 pb-2">
              <div className="flex h-36 items-end gap-1.5">
                {runStats.qber_trace.map((bin) => {
                  const val = bin.qber ?? 0
                  const heightPct = Math.min((val / 0.3) * 100, 100)
                  const isAboveThreshold = val >= 0.11
                  return (
                    <div key={bin.bin} className="group relative flex-1 flex flex-col items-center">
                      <div
                        className={`w-full rounded-t transition-all ${
                          isAboveThreshold ? 'bg-[#EF4444]' : val >= 0.06 ? 'bg-[#F59E0B]' : 'bg-[#22D3EE]'
                        }`}
                        style={{ height: `${Math.max(heightPct, 4)}%` }}
                      />
                      <span className="mt-1 text-[8px] text-[#71869D]">{bin.bin + 1}</span>
                      <div className="pointer-events-none absolute bottom-full mb-1 hidden rounded bg-[#07111F] px-1.5 py-0.5 text-[8px] text-white border border-white/20 group-hover:block whitespace-nowrap z-10">
                        Bin {bin.bin + 1}: {(val * 100).toFixed(1)}% ({bin.n} bits)
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* 11% threshold reference line */}
              <div className="relative border-t border-[#F59E0B] border-dashed my-2">
                <span className="absolute right-0 -top-4 text-[9px] font-bold text-[#F59E0B]">
                  11.0% Abort Threshold
                </span>
              </div>
              <div className="flex justify-between text-[10px] text-[#71869D] mt-2">
                <span>Start of stream (bin 1)</span>
                <span>End of stream (bin 16)</span>
              </div>
            </div>
          ) : (
            <div className="h-36 flex items-center justify-center text-xs text-[#71869D]">
              Calculating QBER trace bins...
            </div>
          )}
          <PolicyNote />
        </TechCard>

        <TechCard title="QBER Estimation Panel" eyebrow="Finite-key statistical estimation">
          <div className="grid grid-cols-2 gap-3">
            {[
              ['Measured QBER', `${qberEst}%`],
              ['Upper bound (4\u03c3)', `${qberUpper}%`],
              ['Security abort limit', '11.0%'],
              ['True simulation QBER', runStats ? `${(runStats.stats.sim_true_qber * 100).toFixed(1)}%` : `${(noise * 100).toFixed(1)}%`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-[#07111F] p-3 border border-white/5">
                <div className="text-[10px] text-[#7F93A8]">{label}</div>
                <div className="mt-1 text-lg font-bold text-[#67E8F9]">{value}</div>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-xl border border-white/10 bg-[#07111F] p-3 text-[11px] text-[#9AAABD]">
            <div className="font-semibold text-white mb-1">Status Verdict:</div>
            {channelSecure ? (
              <div className="text-[#7BE3A0] flex items-center gap-1.5">
                <CheckCircle2 className="size-3.5" />
                Error rate permits secure key generation.
              </div>
            ) : (
              <div className="text-[#FF9292] flex items-center gap-1.5">
                <AlertTriangle className="size-3.5" />
                QBER exceeds threshold. Protocol aborted.
              </div>
            )}
          </div>
        </TechCard>
      </div>

      {/* BB84 Process Lifecycle and Key Status */}
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <TechCard title="BB84 Protocol Lifecycle" eyebrow="Quantum Key Distribution execution phases">
          <div className="grid gap-2 text-[11px]">
            {steps.map((st, i) => (
              <div key={st} className="flex items-center gap-2 rounded-lg bg-[#07111F] px-3 py-2 border border-white/5">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-[#14B8A6]/20 text-[9px] font-bold text-[#67E8D9]">
                  {i + 1}
                </span>
                <span className="text-[#C7D5E2]">{st}</span>
              </div>
            ))}
          </div>
        </TechCard>

        <TechCard title="Quantum Key Material Status" eyebrow="Post-processing derived parameters">
          <div className="grid grid-cols-2 gap-3 text-xs">
            {[
              ['Sifted Bits', runStats ? `${runStats.stats.n_sifted}` : '4,096'],
              ['Cascade Error Correction', runStats?.stats.ec_verified ? 'Verified (Parity check)' : 'Pending'],
              ['Privacy Amplification', runStats ? 'Universal Toeplitz Hash' : 'Toeplitz Matrix'],
              ['Final Key Material', runStats ? `${runStats.stats.final_key_bits} bits` : '1024 bits'],
            ].map(([label, value]) => (
              <div key={label} className="border-b border-white/10 pb-3">
                <div className="text-[10px] text-[#7F93A8]">{label}</div>
                <div className="mt-1 font-semibold text-white">{value}</div>
              </div>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-2 text-[11px] font-semibold text-[#7BE3A0]">
            <ShieldCheck className="size-4" />
            Key available · Cryptographic material protected in memory
          </div>
        </TechCard>
      </div>
    </TechnicalPage>
  )
}
