'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Activity, AlertTriangle, Check, ChevronDown, CircleAlert, LockKeyhole, Radio, ShieldCheck, X } from 'lucide-react'
import { AppShell } from '@/components/bioqshield'

export const colors = { navy: '#0B2545', blue: '#2563EB', cyan: '#22D3EE', teal: '#14B8A6', green: '#22C55E', amber: '#F59E0B', red: '#EF4444' }

export function TechnicalPage({ title, subtitle, children, action }: { title: string; subtitle: string; children: React.ReactNode; action?: React.ReactNode }) {
  return <AppShell><main className="min-h-[calc(100vh-78px)] bg-[#07111F] px-5 py-7 text-white md:px-10 md:py-9"><div className="mx-auto max-w-[1440px]"><div className="flex flex-wrap items-start justify-between gap-5"><div><div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#67DAD2]"><span className="size-1.5 rounded-full bg-[#22C55E]" />BioQShield Security Layer Active</div><h1 className="text-3xl font-bold tracking-[-0.035em] md:text-[34px]">{title}</h1><p className="mt-2 text-sm text-[#9AAABD]">{subtitle}</p></div>{action}</div>{children}</div></main></AppShell>
}

export function TechCard({ title, eyebrow, children, className = '' }: { title: string; eyebrow?: string; children: React.ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-white/10 bg-[#0B1726] p-5 shadow-[0_8px_24px_rgba(0,0,0,0.12)] ${className}`}><div className="mb-5 flex items-start justify-between gap-4"><div><h2 className="text-sm font-semibold text-white">{title}</h2>{eyebrow && <p className="mt-1 text-[11px] text-[#7F93A8]">{eyebrow}</p>}</div></div>{children}</section>
}

export function StatusBadge({ value }: { value: 'ACCEPT' | 'MONITOR' | 'REJECT' | 'SECURE' | 'BLOCKED' | 'AVAILABLE' | 'NOT RELEASED' }) {
  const style = value === 'ACCEPT' || value === 'SECURE' || value === 'AVAILABLE' ? 'border-[#22C55E]/25 bg-[#22C55E]/10 text-[#7BE3A0]' : value === 'MONITOR' ? 'border-[#F59E0B]/25 bg-[#F59E0B]/10 text-[#FFD083]' : 'border-[#EF4444]/25 bg-[#EF4444]/10 text-[#FF9292]'
  const Icon = value === 'ACCEPT' || value === 'SECURE' || value === 'AVAILABLE' ? Check : value === 'MONITOR' ? CircleAlert : X
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold tracking-[0.08em] ${style}`}><Icon className="size-3" />{value}</span>
}

export function Metric({ label, value, detail, tone = 'cyan' }: { label: string; value: string; detail: string; tone?: 'cyan' | 'teal' | 'green' | 'amber' }) {
  const toneClass = { cyan: 'text-[#67E8F9] bg-[#22D3EE]/10', teal: 'text-[#67E8D9] bg-[#14B8A6]/10', green: 'text-[#7BE3A0] bg-[#22C55E]/10', amber: 'text-[#FFD083] bg-[#F59E0B]/10' }[tone]
  return <div className="rounded-2xl border border-white/10 bg-[#0B1726] p-4"><div className={`mb-4 flex size-8 items-center justify-center rounded-lg ${toneClass}`}><Activity className="size-4" /></div><div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#7F93A8]">{label}</div><div className="mt-1 text-2xl font-bold tracking-tight text-white">{value}</div><div className="mt-1 text-[10px] text-[#7F93A8]">{detail}</div></div>
}

export function LineChart({ values, threshold, color = '#22D3EE', labels }: { values: number[]; threshold?: number; color?: string; labels?: string[] }) {
  const max = Math.max(...values, threshold ?? 0, 1); const points = values.map((v, i) => `${(i / (values.length - 1)) * 100},${100 - (v / max) * 82 - 8}`).join(' ')
  return <div className="relative h-44"><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-32 w-full overflow-visible"><path d="M0 90 H100" stroke="white" strokeOpacity=".08" strokeDasharray="1 2" /><path d="M0 50 H100" stroke="white" strokeOpacity=".08" strokeDasharray="1 2" />{threshold !== undefined && <path d={`M0 ${100 - (threshold / max) * 82 - 8} H100`} stroke="#F59E0B" strokeOpacity=".7" strokeDasharray="2 2" strokeWidth=".8" /> }<polyline points={points} fill="none" stroke={color} strokeWidth="1.8" vectorEffect="non-scaling-stroke" />{values.map((v, i) => <circle key={i} cx={`${(i / (values.length - 1)) * 100}`} cy={`${100 - (v / max) * 82 - 8}`} r="1.8" fill={color} />)}</svg><div className="flex justify-between text-[10px] text-[#71869D]">{(labels ?? values.map((_, i) => `${i + 1}`)).map((label) => <span key={label}>{label}</span>)}</div>{threshold !== undefined && <div className="absolute right-0 top-1 text-[10px] text-[#F59E0B]">threshold {threshold}%</div>}</div>
}

export function PolicyNote() { return <div className="flex items-start gap-3 rounded-xl border border-[#14B8A6]/15 bg-[#14B8A6]/[0.06] p-3 text-[11px] leading-5 text-[#A8C8CC]"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-[#54D6C5]" />Protecting biomedical data during hospital-to-hospital transfer.</div> }

export function QuantumFlow({ eve = false }: { eve?: boolean }) { return <div className="flex flex-col items-center gap-3 rounded-xl border border-white/10 bg-[#07111F] px-4 py-6 sm:flex-row sm:justify-between sm:gap-2"><Node label="ALICE" detail="Source · Apollo" tone="teal" /><FlowLine /><>{eve && <><Node label="EVE" detail="Intercepting" tone="red" /><FlowLine /></>}</><div className="flex flex-col items-center gap-2 text-center"><div className="flex size-16 items-center justify-center rounded-full border border-[#22D3EE]/40 bg-[#22D3EE]/10"><Radio className="size-6 text-[#67E8F9]" /></div><span className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#67E8F9]">Quantum channel</span></div><FlowLine /><Node label="BOB" detail="Destination" tone="blue" /></div> }
function Node({ label, detail, tone }: { label: string; detail: string; tone: 'teal' | 'red' | 'blue' }) { return <div className="flex min-w-[100px] flex-col items-center gap-2 text-center"><div className={`flex size-12 items-center justify-center rounded-xl border ${tone === 'red' ? 'border-[#EF4444]/40 bg-[#EF4444]/10 text-[#FF9292]' : tone === 'teal' ? 'border-[#14B8A6]/40 bg-[#14B8A6]/10 text-[#67E8D9]' : 'border-[#2563EB]/40 bg-[#2563EB]/10 text-[#8DB5FF]'}`}><LockKeyhole className="size-5" /></div><div className="text-xs font-bold tracking-[0.12em]">{label}</div><div className="text-[10px] text-[#7F93A8]">{detail}</div></div> }
function FlowLine() { return <div className="hidden h-px min-w-[35px] flex-1 bg-gradient-to-r from-[#14B8A6]/40 via-[#22D3EE] to-[#2563EB]/40 sm:block" /> }

export const qubits = Array.from({ length: 12 }, (_, i) => ({ id: String(i + 1).padStart(2, '0'), aliceBasis: ['X', 'Z', 'X', 'X', 'Z', 'Z', 'X', 'Z', 'X', 'X', 'Z', 'X'][i], aliceBit: ['0', '1', '1', '0', '1', '0', '1', '1', '0', '1', '0', '1'][i], bobBasis: ['X', 'X', 'X', 'Z', 'Z', 'X', 'X', 'Z', 'X', 'Z', 'Z', 'X'][i], bobResult: ['0', '1', '1', '0', '0', '0', '1', '1', '0', '0', '0', '1'][i] }))

export function TogglePill({ label, value, active, onClick }: { label: string; value: string; active: boolean; onClick: () => void }) { return <button onClick={onClick} className={`flex items-center justify-between rounded-xl border px-3 py-2.5 text-left transition ${active ? 'border-[#22D3EE]/40 bg-[#22D3EE]/10' : 'border-white/10 bg-[#07111F] hover:border-white/20'}`}><span className="text-[11px] text-[#9AAABD]">{label}</span><span className={`text-[11px] font-bold ${active ? 'text-[#67E8F9]' : 'text-white'}`}>{value}</span></button> }

export function SelectScenario({ selected, setSelected, scenarios }: { selected: string; setSelected: (value: string) => void; scenarios: { name: string }[] }) { return <div className="relative"><select value={selected} onChange={(event) => setSelected(event.target.value)} className="appearance-none rounded-xl border border-white/10 bg-[#0B1726] px-4 py-2.5 pr-9 text-xs font-semibold text-white outline-none"><option className="bg-[#0B1726]">{scenarios.find((s) => s.name === selected)?.name}</option>{scenarios.filter((s) => s.name !== selected).map((scenario) => <option key={scenario.name} className="bg-[#0B1726]">{scenario.name}</option>)}</select><ChevronDown className="pointer-events-none absolute right-3 top-3 size-3.5 text-[#7F93A8]" /></div> }

export { AlertTriangle }
export { Link }
export const demoDisclaimer = 'Synthetic demonstration data · No patient records or cryptographic material displayed'

export function TechnicalLink({ href, children }: { href: string; children: React.ReactNode }) { return <Link href={href} className="text-[#67E8F9] hover:underline">{children}</Link> }

export function StatusDot({ label }: { label: string }) { return <span className="inline-flex items-center gap-2 text-[11px] text-[#A8BACB]"><span className="size-2 rounded-full bg-[#22C55E]" />{label}</span> }

export function AccessibilityStatus({ label, tone = 'green' }: { label: string; tone?: 'green' | 'amber' | 'red' }) { const Icon = tone === 'green' ? Check : tone === 'amber' ? CircleAlert : X; return <span className={`inline-flex items-center gap-1.5 text-[11px] ${tone === 'green' ? 'text-[#7BE3A0]' : tone === 'amber' ? 'text-[#FFD083]' : 'text-[#FF9292]'}`}><Icon className="size-3.5" />{label}</span> }
