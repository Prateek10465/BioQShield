'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardList,
  Cpu,
  FileCheck2,
  FileSearch,
  FileText,
  History,
  Image as ImageIcon,
  LockKeyhole,
  NotebookPen,
  Pill,
  Radio,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Upload,
  X,
  Zap,
} from 'lucide-react'
import { RunParams } from '@/lib/api'

const patients = [
  { name: 'Synthetic Patient', id: 'PT-2048', department: 'Cardiology', note: 'Primary Demo Record' },
  { name: 'John Doe', id: 'PT-20491', department: 'Cardiology', note: 'Hypertension Followup' },
  { name: 'Sarah Wilson', id: 'PT-18372', department: 'Neurology', note: 'Diagnostic Scan' },
  { name: 'Michael Carter', id: 'PT-17283', department: 'Oncology', note: 'Clinical Notes' },
]

const documentTypes = [
  { name: 'Medical Record', meta: 'Synthetic clinical summary', icon: FileText },
  { name: 'Prescription', meta: 'Metformin 500mg, Amlodipine 5mg', icon: ClipboardList },
  { name: 'Diagnostic Report', meta: 'Cardiology examination', icon: FileSearch },
  { name: 'Lab Report', meta: 'Biochemical blood panel', icon: Activity },
  { name: 'Imaging Report', meta: 'Echocardiogram series', icon: ImageIcon },
  { name: 'Discharge Summary', meta: 'Inpatient discharge notes', icon: FileCheck2 },
  { name: 'Clinical Notes', meta: 'Physician observations', icon: NotebookPen },
  { name: 'Medication Record', meta: 'Active drug list', icon: Pill },
  { name: 'Patient History', meta: 'Longitudinal record', icon: History },
]

const destinations = [
  'Apollo Hospital — Chennai Main Branch',
  'Fortis Hospital Network',
  'Apollo Hospital — Adyar Branch',
  'MedCare Hospital Group',
  'CityCare Medical Network',
]
const branches = ['Chennai Main Branch', 'Adyar Branch', 'Guindy Branch', 'Greams Road Node']
const steps = ['Patient', 'Medical Data', 'Destination', 'Quantum Security', 'Review']

export function TransferStepper({ currentStep }: { currentStep: number }) {
  return (
    <div
      className="flex items-center rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-7 py-5 shadow-[0_3px_12px_rgba(18,52,91,0.035)]"
      aria-label={`Step ${currentStep} of 5`}
    >
      {steps.map((step, index) => {
        const number = index + 1
        const complete = number < currentStep
        const current = number === currentStep
        return (
          <div key={step} className="flex min-w-0 flex-1 items-center">
            <div className="flex items-center gap-3">
              <div
                className={`flex size-8 shrink-0 items-center justify-center rounded-full border text-[12px] font-bold ${
                  complete
                    ? 'border-[#22A06B] bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
                    : current
                    ? 'border-[#2563EB] bg-[#2563EB] text-white shadow-[0_4px_10px_rgba(37,99,235,0.2)]'
                    : 'border-[#D9E2EC] dark:border-white/10 bg-[#F7F9FC] dark:bg-white/5 text-[#8A9AAD]'
                }`}
              >
                {complete ? <Check className="size-4" strokeWidth={2.5} /> : number}
              </div>
              <div className="hidden min-w-0 sm:block">
                <div
                  className={`text-[11px] font-semibold ${
                    current
                      ? 'text-[#172033] dark:text-white'
                      : complete
                      ? 'text-[#198657] dark:text-[#7BE3A0]'
                      : 'text-[#8A9AAD]'
                  }`}
                >
                  {step}
                </div>
                <div className="mt-0.5 text-[9px] uppercase tracking-[0.08em] text-[#A0AEBB]">
                  {complete ? 'Complete' : current ? 'Current' : 'Upcoming'}
                </div>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div
                className={`mx-4 h-px flex-1 ${
                  complete ? 'bg-[#9BD8B8] dark:bg-[#22C55E]/30' : 'bg-[#E5EBF1] dark:bg-white/10'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

function SectionHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description?: string }) {
  return (
    <div className="mb-6">
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">{eyebrow}</div>
      <h2 className="text-[21px] font-bold tracking-[-0.025em] text-[#172033] dark:text-white">{title}</h2>
      {description && <p className="mt-2 text-[12px] leading-5 text-[#64748B] dark:text-[#9AAABD]">{description}</p>}
    </div>
  )
}

export function PatientSelector({
  selected,
  onSelect,
  error,
}: {
  selected: (typeof patients)[number] | null
  onSelect: (patient: (typeof patients)[number] | null) => void
  error?: string
}) {
  const [query, setQuery] = useState('')
  const results = patients.filter((patient) =>
    `${patient.name} ${patient.id} ${patient.department}`.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div>
      <SectionHeader
        eyebrow="Step 1"
        title="Select Biomedical Resource Subject"
        description="Search authorized hospital patient database or select the default synthetic demonstration record."
      />
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-[#8A9AAD]" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by patient name or ID (e.g. PT-2048)"
          className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] py-3.5 pl-11 pr-4 text-[13px] text-[#172033] dark:text-white outline-none transition focus:border-[#2563EB] focus:ring-4 focus:ring-[#2563EB]/10"
        />
      </div>

      <div className="mt-3 overflow-hidden rounded-xl border border-[#E3EAF1] dark:border-white/10 bg-white dark:bg-[#0B1726]">
        {results.map((patient) => (
          <button
            key={patient.id}
            onClick={() => onSelect(patient)}
            className={`flex w-full items-center justify-between border-b border-[#EEF2F6] dark:border-white/5 px-4 py-3.5 text-left last:border-0 hover:bg-[#F8FBFF] dark:hover:bg-white/[0.04] ${
              selected?.id === patient.id ? 'bg-[#F2F7FF] dark:bg-white/10' : ''
            }`}
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-[#172033] dark:text-white">{patient.name}</span>
                <span className="rounded bg-[#EAF8F5] dark:bg-[#14B8A6]/20 px-1.5 py-0.5 text-[9px] font-bold text-[#14A493]">
                  SYNTHETIC
                </span>
              </div>
              <div className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
                Patient ID: {patient.id}
                <span className="mx-2 text-[#C3CED9] dark:text-white/20">·</span>
                {patient.department}
                <span className="mx-2 text-[#C3CED9] dark:text-white/20">·</span>
                {patient.note}
              </div>
            </div>
            {selected?.id === patient.id && <CheckCircle2 className="size-5 text-[#22A06B]" />}
          </button>
        ))}
      </div>

      {selected && (
        <div className="mt-5 rounded-xl border border-[#B9E5D0] dark:border-[#22C55E]/30 bg-[#F3FBF6] dark:bg-[#22C55E]/10 p-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#198657] dark:text-[#7BE3A0]">
            Patient record selected (Synthetic demonstration data)
          </div>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <div className="text-[14px] font-bold text-[#172033] dark:text-white">{selected.name}</div>
              <div className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
                {selected.id}
                <span className="mx-2 text-[#C3CED9] dark:text-white/20">·</span>
                {selected.department}
              </div>
            </div>
            <button
              onClick={() => onSelect(null)}
              className="rounded-lg p-2 text-[#7A8B9E] hover:bg-white dark:hover:bg-white/10"
              aria-label="Deselect patient"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-[11px] font-medium text-[#C33E42]">{error}</p>}
    </div>
  )
}

export function MedicalDataSelector({
  selected,
  onToggle,
  error,
}: {
  selected: string[]
  onToggle: (name: string) => void
  error?: string
}) {
  return (
    <div>
      <SectionHeader
        eyebrow="Step 2"
        title="Select Biomedical Resources"
        description="Choose the biomedical resources (records, reports, prescriptions) to be protected and transferred."
      />
      <div className="grid grid-cols-2 gap-3">
        {documentTypes.map((item) => {
          const active = selected.includes(item.name)
          const Icon = item.icon
          return (
            <button
              key={item.name}
              onClick={() => onToggle(item.name)}
              className={`flex items-center gap-3 rounded-xl border p-3.5 text-left transition ${
                active
                  ? 'border-[#8CCFE0] dark:border-[#22D3EE]/50 bg-[#F2FBFD] dark:bg-[#22D3EE]/10 shadow-[0_2px_8px_rgba(6,182,212,0.06)]'
                  : 'border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] hover:border-[#B9C9D8]'
              }`}
            >
              <div
                className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
                  active
                    ? 'bg-[#DDF7FA] dark:bg-[#22D3EE]/20 text-[#0787A4] dark:text-[#67E8F9]'
                    : 'bg-[#F0F5FA] dark:bg-white/10 text-[#58718D] dark:text-[#A8BACB]'
                }`}
              >
                <Icon className="size-[17px]" strokeWidth={1.8} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[12px] font-semibold text-[#172033] dark:text-white">{item.name}</div>
                <div className="mt-1 text-[10px] text-[#8A9AAD]">{item.meta}</div>
              </div>
              <div
                className={`flex size-5 items-center justify-center rounded-md border ${
                  active ? 'border-[#2563EB] bg-[#2563EB] text-white' : 'border-[#C7D3DF] dark:border-white/20 bg-white dark:bg-transparent'
                }`}
              >
                {active && <Check className="size-3.5" strokeWidth={3} />}
              </div>
            </button>
          )
        })}
      </div>
      <div className="mt-4 flex items-center gap-2 text-[11px] font-semibold text-[#4D6075] dark:text-[#A8BACB]">
        <CheckCircle2 className="size-4 text-[#22A06B]" />
        {selected.length} biomedical resource{selected.length === 1 ? '' : 's'} selected
      </div>
      {error && <p className="mt-2 text-[11px] font-medium text-[#C33E42]">{error}</p>}
    </div>
  )
}

export function DestinationSelector({
  destination,
  setDestination,
  scope,
  setScope,
  branch,
  setBranch,
  error,
}: {
  destination: string
  setDestination: (value: string) => void
  scope: string
  setScope: (value: string) => void
  branch: string
  setBranch: (value: string) => void
  error?: string
}) {
  return (
    <div>
      <SectionHeader
        eyebrow="Step 3"
        title="Select Destination Hospital / Authorized Network"
        description="Choose the authorized hospital or hospital network node where biomedical data will be securely transferred."
      />
      <div className="grid grid-cols-[1fr_1fr] gap-5">
        <label className="block">
          <span className="mb-2 block text-[11px] font-semibold text-[#4D6075] dark:text-[#A8BACB]">
            Destination Hospital / Network
          </span>
          <div className="relative">
            <select
              value={destination}
              onChange={(event) => setDestination(event.target.value)}
              className="w-full appearance-none rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 py-3 text-[12px] text-[#172033] dark:text-white outline-none focus:border-[#2563EB]"
            >
              <option value="">Select destination hospital / network</option>
              {destinations.map((item) => (
                <option key={item} value={item} className="dark:bg-[#0B1726]">
                  {item}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-4 top-1/2 size-4 -translate-y-1/2 text-[#8A9AAD]" />
          </div>
        </label>
        <div>
          <div className="mb-2 text-[11px] font-semibold text-[#4D6075] dark:text-[#A8BACB]">Destination Scope</div>
          <div className="flex rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-1">
            <button
              onClick={() => setScope('Specific Branch')}
              className={`flex-1 rounded-lg px-3 py-2.5 text-[11px] font-semibold ${
                scope === 'Specific Branch'
                  ? 'bg-[#EAF2FF] dark:bg-[#2563EB]/20 text-[#2563EB] dark:text-[#67E8F9]'
                  : 'text-[#64748B] dark:text-[#9AAABD]'
              }`}
            >
              Specific Branch
            </button>
            <button
              onClick={() => setScope('Hospital Network')}
              className={`flex-1 rounded-lg px-3 py-2.5 text-[11px] font-semibold ${
                scope === 'Hospital Network'
                  ? 'bg-[#EAF8F5] dark:bg-[#14B8A6]/20 text-[#128F7C] dark:text-[#67E8D9]'
                  : 'text-[#64748B] dark:text-[#9AAABD]'
              }`}
            >
              Hospital Network
            </button>
          </div>
        </div>
      </div>

      {scope === 'Specific Branch' ? (
        <label className="mt-5 block max-w-[48%]">
          <span className="mb-2 block text-[11px] font-semibold text-[#4D6075] dark:text-[#A8BACB]">Branch Location</span>
          <div className="relative">
            <select
              value={branch}
              onChange={(event) => setBranch(event.target.value)}
              className="w-full appearance-none rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 py-3 text-[12px] text-[#172033] dark:text-white outline-none focus:border-[#2563EB]"
            >
              <option value="">Select branch</option>
              {branches.map((item) => (
                <option key={item} value={item} className="dark:bg-[#0B1726]">
                  {item}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-4 top-1/2 size-4 -translate-y-1/2 text-[#8A9AAD]" />
          </div>
        </label>
      ) : (
        <div className="mt-5 rounded-xl border border-[#B9E5E0] dark:border-[#14B8A6]/30 bg-[#F1FBF9] dark:bg-[#14B8A6]/10 p-4 text-[11px] leading-5 text-[#3D716C] dark:text-[#A8C8CC]">
          Biomedical resources will move directly into the authorized hospital network node and will be accessible only by
          authorized healthcare practitioners following institutional access policies.
        </div>
      )}

      {destination && (
        <div className="mt-5 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#64748B] dark:text-[#9AAABD]">
            Destination Node
          </div>
          <div className="mt-2 text-[14px] font-bold text-[#172033] dark:text-white">{destination}</div>
          <div className="mt-2 text-[11px] text-[#4D6075] dark:text-[#A8BACB]">
            Scope: {scope} {scope === 'Specific Branch' ? `· ${branch || 'Selected Branch'}` : ''} · Authorized database
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-[11px] font-medium text-[#C33E42]">{error}</p>}
    </div>
  )
}

export function QuantumSecurityPolicyConfigurator({
  params,
  setParams,
}: {
  params: RunParams
  setParams: React.Dispatch<React.SetStateAction<RunParams>>
}) {
  const [priority, setPriority] = useState<'standard' | 'urgent'>('standard')
  const [policyLevel, setPolicyLevel] = useState<'strict' | 'standard'>('strict')

  return (
    <div>
      <SectionHeader
        eyebrow="Step 4"
        title="Quantum Security & Transfer Policy"
        description="Automated BB84 quantum key distribution and real-time AI threat monitoring protecting this biomedical transmission."
      />

      {/* ── Active Quantum Security Infrastructure (Enforced & Read-Only) ── */}
      <div className="mb-6">
        <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-[#64748B] dark:text-[#9AAABD]">
          Active Quantum Security Infrastructure
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: BB84 QKD Encryption */}
          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-5 shadow-xs">
            <div className="flex items-start justify-between">
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#22A06B] dark:text-[#7BE3A0]">
                <Cpu className="size-5" />
              </div>
              <span className="rounded-full bg-[#E8F7EF] dark:bg-[#22C55E]/15 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-[#198657] dark:text-[#7BE3A0]">
                Active & Armed
              </span>
            </div>
            <h3 className="mt-4 text-[13px] font-bold text-[#172033] dark:text-white">
              BB84 Quantum Key Derivation
            </h3>
            <p className="mt-1 text-[11px] leading-relaxed text-[#64748B] dark:text-[#9AAABD]">
              Biomedical data is encrypted using AES-256-GCM with symmetric session keys derived from live BB84 photon polarization exchange.
            </p>
            <div className="mt-3 pt-3 border-t border-[#EEF2F6] dark:border-white/5 text-[10px] text-[#2563EB] dark:text-[#67E8F9] font-medium">
              Carrier: 8,192 Qubit Pool · Cascade Parity Verified
            </div>
          </div>

          {/* Card 2: NSL-KDD AI IDS Guard */}
          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-5 shadow-xs">
            <div className="flex items-start justify-between">
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#E2F8FB] dark:bg-[#22D3EE]/15 text-[#0891B2] dark:text-[#67E8F9]">
                <Activity className="size-5" />
              </div>
              <span className="rounded-full bg-[#E2F8FB] dark:bg-[#22D3EE]/15 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-[#0787A4] dark:text-[#67E8F9]">
                Continuous Guard
              </span>
            </div>
            <h3 className="mt-4 text-[13px] font-bold text-[#172033] dark:text-white">
              NSL-KDD Neural Intrusion Defense
            </h3>
            <p className="mt-1 text-[11px] leading-relaxed text-[#64748B] dark:text-[#9AAABD]">
              Classical link traffic is continuously evaluated across 41 network flow dimensions to detect reconnaissance, replay, and DoS attacks.
            </p>
            <div className="mt-3 pt-3 border-t border-[#EEF2F6] dark:border-white/5 text-[10px] text-[#14A493] font-medium">
              Threat Model: Real-Time Anomaly Scoring Active
            </div>
          </div>

          {/* Card 3: Eavesdropping Abort Interlock */}
          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-5 shadow-xs">
            <div className="flex items-start justify-between">
              <div className="flex size-10 items-center justify-center rounded-xl bg-[#F0F5FA] dark:bg-white/10 text-[#2563EB] dark:text-[#67E8F9]">
                <ShieldCheck className="size-5" />
              </div>
              <span className="rounded-full bg-[#E8F7EF] dark:bg-[#22C55E]/15 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-[#198657] dark:text-[#7BE3A0]">
                QBER Interlock Enforced
              </span>
            </div>
            <h3 className="mt-4 text-[13px] font-bold text-[#172033] dark:text-white">
              Eavesdropping Detection & Zeroise
            </h3>
            <p className="mt-1 text-[11px] leading-relaxed text-[#64748B] dark:text-[#9AAABD]">
              Quantum Bit Error Rate (QBER) safety interlock. Any optical interception or eavesdropping automatically aborts transmission.
            </p>
            <div className="mt-3 pt-3 border-t border-[#EEF2F6] dark:border-white/5 text-[10px] text-[#198657] dark:text-[#7BE3A0] font-medium">
              Safety Threshold: 11.0% Abort Threshold
            </div>
          </div>
        </div>
      </div>

      {/* ── Realistic Clinical Configuration Controls ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-6">
        {/* Control 1: Clinical Priority */}
        <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5">
          <label className="block text-[12px] font-bold text-[#172033] dark:text-white mb-1">
            Clinical Transmission Priority
          </label>
          <p className="text-[11px] text-[#64748B] dark:text-[#9AAABD] mb-3">
            Determines quantum channel allocation priority and physician alert routing.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setPriority('standard')}
              className={`rounded-xl border p-3 text-left transition ${
                priority === 'standard'
                  ? 'border-[#2563EB] bg-[#F4F8FD] dark:bg-white/5 text-[#2563EB] dark:text-[#67E8F9] font-semibold'
                  : 'border-[#D9E2EC] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:border-[#B0C4DE]'
              }`}
            >
              <div className="text-[12px]">Standard Clinical</div>
              <div className="text-[10px] opacity-75 mt-0.5">Routine medical synchronization</div>
            </button>
            <button
              type="button"
              onClick={() => setPriority('urgent')}
              className={`rounded-xl border p-3 text-left transition ${
                priority === 'urgent'
                  ? 'border-[#2563EB] bg-[#F4F8FD] dark:bg-white/5 text-[#2563EB] dark:text-[#67E8F9] font-semibold'
                  : 'border-[#D9E2EC] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:border-[#B0C4DE]'
              }`}
            >
              <div className="text-[12px]">STAT / Emergency</div>
              <div className="text-[10px] opacity-75 mt-0.5">Immediate critical care priority</div>
            </button>
          </div>
        </div>

        {/* Control 2: Institutional Security Policy */}
        <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5">
          <label className="block text-[12px] font-bold text-[#172033] dark:text-white mb-1">
            Institutional Security Enforcement
          </label>
          <p className="text-[11px] text-[#64748B] dark:text-[#9AAABD] mb-3">
            Adaptive policy dynamically tightens QBER limits based on real-time NSL-KDD anomaly scores.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => {
                setPolicyLevel('strict')
                setParams((p) => ({ ...p, adaptive: true }))
              }}
              className={`rounded-xl border p-3 text-left transition ${
                policyLevel === 'strict'
                  ? 'border-[#22A06B] bg-[#F0FAF5] dark:bg-white/5 text-[#198657] dark:text-[#7BE3A0] font-semibold'
                  : 'border-[#D9E2EC] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:border-[#B0C4DE]'
              }`}
            >
              <div className="text-[12px]">Maximum Assurance</div>
              <div className="text-[10px] opacity-75 mt-0.5">Adaptive threat escalation active</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setPolicyLevel('standard')
                setParams((p) => ({ ...p, adaptive: false }))
              }}
              className={`rounded-xl border p-3 text-left transition ${
                policyLevel === 'standard'
                  ? 'border-[#2563EB] bg-[#F4F8FD] dark:bg-white/5 text-[#2563EB] dark:text-[#67E8F9] font-semibold'
                  : 'border-[#D9E2EC] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:border-[#B0C4DE]'
              }`}
            >
              <div className="text-[12px]">Standard Policy</div>
              <div className="text-[10px] opacity-75 mt-0.5">Static 11% QBER threshold</div>
            </button>
          </div>
        </div>

        {/* Control 3: Key Destruction & Forward Secrecy */}
        <div className="col-span-1 md:col-span-2 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-[#EAF8F5] dark:bg-[#14B8A6]/20 text-[#14A493]">
              <LockKeyhole className="size-4" />
            </div>
            <div>
              <div className="text-[12px] font-bold text-[#172033] dark:text-white">
                One-Time Session Key Destruction (Forward Secrecy)
              </div>
              <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD]">
                Quantum key is permanently destroyed and zeroised immediately post-decryption. No key reuse permitted.
              </div>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#E8F7EF] dark:bg-[#22C55E]/15 px-3 py-1 text-[10px] font-semibold text-[#198657] dark:text-[#7BE3A0]">
            <CheckCircle2 className="size-3.5" /> Enforced by Hardware QKD
          </span>
        </div>
      </div>
    </div>
  )
}

export { QuantumSecurityPolicyConfigurator as ChannelConfigurator }

export function TransferReview({
  patient,
  documents,
  destination,
  scope,
  branch,
  params,
}: {
  patient: (typeof patients)[number]
  documents: string[]
  destination: string
  scope: string
  branch: string
  params: RunParams
}) {
  return (
    <div>
      <SectionHeader
        eyebrow="Step 5"
        title="Review & Security Verification Plan"
        description="Verify biomedical resources, authorized hospital destination, and quantum communication parameters before execution."
      />
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8A9AAD]">Patient Subject</div>
          <div className="mt-3 text-[13px] font-bold text-[#172033] dark:text-white">{patient.name}</div>
          <div className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
            {patient.id} · {patient.department}
          </div>
          <div className="mt-2 rounded bg-[#EAF8F5] dark:bg-[#14B8A6]/20 px-2 py-0.5 text-[9px] font-bold text-[#14A493] inline-block">
            SYNTHETIC DATA
          </div>
        </div>

        <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8A9AAD]">Biomedical Data</div>
          <div className="mt-3 flex flex-col gap-1">
            {documents.map((item) => (
              <div key={item} className="flex items-center gap-1.5 text-[11px] font-medium text-[#4D6075] dark:text-[#A8BACB]">
                <Check className="size-3.5 text-[#22A06B]" />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FBFD] dark:bg-white/[0.03] p-4">
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8A9AAD]">Authorized Destination</div>
          <div className="mt-3 text-[13px] font-bold text-[#172033] dark:text-white">{destination}</div>
          <div className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
            {scope}
            {scope === 'Specific Branch' ? ` · ${branch}` : ''}
          </div>
          <div className="mt-2 text-[10px] text-[#14A493] font-semibold">Authorized Hospital Database</div>
        </div>
      </div>

      {/* Realistic Quantum Security & Policy summary */}
      <div className="mt-4 rounded-xl border border-[#CFE3F7] dark:border-white/10 bg-[#F5FAFF] dark:bg-white/[0.02] p-4">
        <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#2563EB] dark:text-[#67E8F9] mb-2">
          Quantum Cryptography & Policy Summary
        </div>
        <div className="grid grid-cols-4 gap-3 text-[11px]">
          <div>
            <span className="text-[#8A9AAD]">Encryption:</span>
            <span className="ml-1 font-bold text-[#172033] dark:text-white">AES-256-GCM + BB84</span>
          </div>
          <div>
            <span className="text-[#8A9AAD]">Key Source:</span>
            <span className="ml-1 font-bold text-[#172033] dark:text-white">Live Quantum Pool</span>
          </div>
          <div>
            <span className="text-[#8A9AAD]">AI Threat Guard:</span>
            <span className="ml-1 font-bold text-[#198657] dark:text-[#7BE3A0]">NSL-KDD Active</span>
          </div>
          <div>
            <span className="text-[#8A9AAD]">Safety Threshold:</span>
            <span className="ml-1 font-bold text-[#172033] dark:text-white">&lt; 11% QBER Abort</span>
          </div>
        </div>
      </div>

      <div className="my-5 flex items-center gap-3 rounded-xl border border-[#E3EAF1] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 py-3 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
        <div className="flex size-7 items-center justify-center rounded-lg bg-[#EAF8F5] dark:bg-[#14B8A6]/20 text-[#14A493]">
          <LockKeyhole className="size-3.5" />
        </div>
        <span>Apollo Hospital (Source)</span>
        <ArrowRight className="size-3.5 text-[#9AAABD]" />
        <span className="font-semibold text-[#2563EB] dark:text-[#67E8F9]">BioQShield QKD + Policy Verification</span>
        <ArrowRight className="size-3.5 text-[#9AAABD]" />
        <span>{destination}</span>
      </div>
    </div>
  )
}

export function SecureTransferWorkflow() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [patient, setPatient] = useState<(typeof patients)[number] | null>(patients[0]) // Defaults to Synthetic Patient
  const [documents, setDocuments] = useState<string[]>(['Medical Record', 'Prescription', 'Diagnostic Report'])
  const [destination, setDestination] = useState('Fortis Hospital Network')
  const [scope, setScope] = useState('Hospital Network')
  const [branch, setBranch] = useState('')
  const [error, setError] = useState('')
  const [cancelOpen, setCancelOpen] = useState(false)

  const [channelParams, setChannelParams] = useState<RunParams>({
    n_qubits: 8192,
    noise: 0.02,
    eve: false,
    eve_rate: 1.0,
    eve_start: 0.0,
    traffic: 'benign',
    adaptive: true,
    seed: 1,
  })

  const canReview = useMemo(
    () => Boolean(patient && documents.length && destination && (scope === 'Hospital Network' || branch)),
    [patient, documents, destination, scope, branch]
  )

  const toggleDocument = (name: string) =>
    setDocuments((current) => (current.includes(name) ? current.filter((item) => item !== name) : [...current, name]))

  const goNext = () => {
    setError('')
    if (step === 1 && !patient) return setError('Select a patient record to continue.')
    if (step === 2 && !documents.length) return setError('Select at least one biomedical document to continue.')
    if (step === 3 && (!destination || (scope === 'Specific Branch' && !branch)))
      return setError('Select a destination hospital and scope to continue.')
    setStep((current) => Math.min(5, current + 1))
  }

  const goBack = () => {
    setError('')
    setStep((current) => Math.max(1, current - 1))
  }

  const beginSecurityCheck = () => {
    if (!canReview || !patient) return
    // Persist full execution configuration to sessionStorage so security analysis executes live
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(
        'bioqshield_active_transfer',
        JSON.stringify({
          patient,
          documents,
          destination,
          scope,
          branch,
          params: channelParams,
        })
      )
    }
    router.push('/security-analysis/')
  }

  return (
    <main className="mx-auto max-w-[1160px] px-10 py-8">
      <div className="flex items-start justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
            <span className="size-1.5 rounded-full bg-[#14B8A6]" />
            Secure biomedical exchange
          </div>
          <h1 className="text-[30px] font-bold tracking-[-0.035em] text-[#172033] dark:text-white">New Secure Transfer</h1>
          <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
            Select biomedical resources, destination hospital, and review automated quantum security verification.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-[#E8F7EF] dark:bg-[#22C55E]/15 px-3 py-2 text-[10px] font-semibold text-[#198657] dark:text-[#7BE3A0]">
          <span className="size-1.5 rounded-full bg-[#22A06B]" />
          Protected workspace
        </div>
      </div>

      <div className="mt-7">
        <TransferStepper currentStep={step} />
      </div>

      <div className="mt-6 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-7 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
        <div className="max-w-[880px]">
          {step === 1 && <PatientSelector selected={patient} onSelect={setPatient} error={error} />}
          {step === 2 && <MedicalDataSelector selected={documents} onToggle={toggleDocument} error={error} />}
          {step === 3 && (
            <DestinationSelector
              destination={destination}
              setDestination={setDestination}
              scope={scope}
              setScope={setScope}
              branch={branch}
              setBranch={setBranch}
              error={error}
            />
          )}
          {step === 4 && <QuantumSecurityPolicyConfigurator params={channelParams} setParams={setChannelParams} />}
          {step === 5 && patient && (
            <TransferReview
              patient={patient}
              documents={documents}
              destination={destination}
              scope={scope}
              branch={branch}
              params={channelParams}
            />
          )}
        </div>

        <div className="mt-8 flex items-center justify-between border-t border-[#E8EEF3] dark:border-white/10 pt-5">
          <button
            onClick={() => setCancelOpen(true)}
            className="text-[11px] font-semibold text-[#8A9AAD] hover:text-[#C33E42]"
          >
            Cancel Transfer
          </button>
          <div className="flex items-center gap-3">
            {step > 1 && (
              <button
                onClick={goBack}
                className="flex items-center gap-2 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 py-3 text-[11px] font-semibold text-[#4D6075] dark:text-[#A8BACB] hover:bg-[#F7F9FC] dark:hover:bg-white/5"
              >
                <ArrowLeft className="size-3.5" />
                Back
              </button>
            )}
            {step < 5 ? (
              <button
                onClick={goNext}
                className="flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-3 text-[11px] font-semibold text-white shadow-[0_7px_16px_rgba(37,99,235,0.18)] hover:bg-[#1D56D0]"
              >
                Continue
                <ArrowRight className="size-3.5" />
              </button>
            ) : (
              <button
                onClick={beginSecurityCheck}
                disabled={!canReview}
                className="flex items-center gap-2 rounded-xl bg-[#2563EB] px-6 py-3.5 text-[12px] font-semibold text-white shadow-[0_7px_16px_rgba(37,99,235,0.18)] hover:bg-[#1D56D0] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Run Security Analysis
                <ShieldCheck className="size-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {cancelOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0B2545]/40 p-6 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            className="w-full max-w-[360px] rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-2xl"
          >
            <div className="flex size-10 items-center justify-center rounded-xl bg-[#FDEBEC] dark:bg-[#EF4444]/20 text-[#DC4446]">
              <X className="size-5" />
            </div>
            <h2 className="mt-4 text-[18px] font-bold text-[#172033] dark:text-white">Cancel secure transfer?</h2>
            <p className="mt-2 text-[12px] leading-5 text-[#64748B] dark:text-[#9AAABD]">
              Your current transfer selections will be discarded.
            </p>
            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => setCancelOpen(false)}
                className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-4 py-2.5 text-[11px] font-semibold text-[#4D6075] dark:text-[#A8BACB]"
              >
                Keep Editing
              </button>
              <button
                onClick={() => router.push('/')}
                className="rounded-xl bg-[#DC4446] px-4 py-2.5 text-[11px] font-semibold text-white"
              >
                Discard & Exit
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}

export { patients }
