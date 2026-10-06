import Link from 'next/link'
import { AppShell, Brand } from '@/components/bioqshield'
import { Activity, ArrowRight, Database, LockKeyhole, Network, ScanLine, ShieldCheck, Zap } from 'lucide-react'

const steps = [
  ['01', 'ANALYZE', 'Network traffic is evaluated using our NSL-KDD machine learning classifier to estimate threat levels.', Activity],
  ['02', 'ESTABLISH', 'Simulated BB84 Quantum Key Distribution using Qiskit Aer prepares and exchanges quantum state bases.', Network],
  ['03', 'VERIFY', 'Quantum Bit Error Rate (QBER) and Cascade error correction assess transmission channel integrity.', ScanLine],
  ['04', 'POLICY', 'Static and adaptive security policies determine if the quantum channel is safe (ACCEPT, MONITOR, REJECT).', ShieldCheck],
  ['05', 'ENCRYPT', 'Only upon verification, AES-256-GCM encrypts synthetic records; otherwise keys and data are strictly blocked.', LockKeyhole],
] as const

export default function AboutPage() {
  return (
    <AppShell>
      <main className="mx-auto max-w-[1180px] px-10 py-10">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
              Product overview
            </div>
            <h1 className="mt-3 text-[30px] font-bold tracking-[-0.03em] text-[#172033] dark:text-white">
              About BioQShield
            </h1>
            <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
              Quantum-Secure Communication for Biomedical Networks · Qiskit Fall Fest 2026
            </p>
          </div>
          <Brand compact />
        </div>

        <section className="mt-8 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-8 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
          <div className="max-w-3xl">
            <h2 className="text-[20px] font-bold text-[#172033] dark:text-white">
              Secure biomedical communication, made clear.
            </h2>
            <p className="mt-4 text-[14px] leading-7 text-[#64748B] dark:text-[#9AAABD]">
              BioQShield is an advanced quantum-secure communication architecture designed to protect sensitive biomedical data—such as patient EHR records, diagnostic imaging reports, and electronic prescriptions—during transit across authorized hospital networks. By fusing classical network threat intelligence with quantum key distribution, BioQShield dynamically adapts its security posture to protect critical healthcare infrastructure against modern and quantum eavesdropping threats.
            </p>
          </div>

          <div className="mt-10">
            <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">
              How BioQShield protects biomedical data
            </h2>
            <div className="mt-5 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {steps.map(([number, title, copy, Icon]) => (
                <div
                  key={number}
                  className="rounded-xl border border-[#E4EBF2] dark:border-white/10 bg-[#FBFCFE] dark:bg-[#07111F] p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-[#2563EB] dark:text-[#67E8F9]">{number}</span>
                      <Icon className="size-4 text-[#14A493]" />
                    </div>
                    <h3 className="mt-4 text-[11px] font-bold tracking-[0.08em] text-[#172033] dark:text-white">
                      {title}
                    </h3>
                    <p className="mt-2 text-[11px] leading-5 text-[#64748B] dark:text-[#9AAABD]">{copy}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mt-5 grid grid-cols-1 md:grid-cols-[1.2fr_0.8fr] gap-5">
          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-7 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">Security Architecture & Protocols</h2>
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
              {[
                ['Network Threat Layer', 'NSL-KDD Trained Classical Classifier'],
                ['Quantum Key Protocol', 'BB84 (Bennett-Brassard 1984)'],
                ['Quantum Simulation Engine', 'Qiskit Aer (AerSimulator)'],
                ['Post-Processing', 'Cascade Error Correction + Toeplitz PA'],
                ['Symmetric Cryptography', 'AES-256-GCM with 96-bit Random IV'],
                ['Decision Policy', 'Static (11% threshold) + Adaptive Policy'],
              ].map(([label, value]) => (
                <div key={label} className="border-b border-[#EEF2F6] dark:border-white/5 pb-3">
                  <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD]">{label}</div>
                  <div className="mt-1 text-[13px] font-semibold text-[#172033] dark:text-white">{value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl bg-[#12345B] dark:bg-[#08182B] p-7 text-white flex flex-col justify-between">
            <div>
              <div className="flex size-10 items-center justify-center rounded-xl bg-white/10">
                <ShieldCheck className="size-5 text-[#6BDDE7]" />
              </div>
              <h2 className="mt-5 text-[18px] font-bold">Built for secure healthcare networks</h2>
              <p className="mt-3 text-[12px] leading-6 text-[#B9C8D8]">
                Sensitive biomedical information is only released when the quantum channel and network conditions satisfy rigorous clinical safety thresholds. If intrusion or elevated noise is detected, data transmission is immediately blocked at the source.
              </p>
            </div>
            <Link
              href="/secure-transfer/"
              className="mt-6 inline-flex items-center gap-2 text-[12px] font-semibold text-[#6BDDE7] hover:underline"
            >
              Launch Secure Transfer <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </section>
      </main>
    </AppShell>
  )
}
