'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/bioqshield'
import { Building2, CheckCircle2, ChevronRight, LogOut, ShieldCheck, UserRound, X } from 'lucide-react'
import { getAuthUser, logoutUser, setAuthUser, AuthUser, HOSPITALS } from '@/lib/api'

const AVAILABLE_USERS = HOSPITALS.flatMap((h) =>
  h.users.map((u) => ({
    name: u.name,
    username: u.username,
    role: u.role,
    department: u.department,
    hospital: h.name,
    hospitalId: h.id,
    branch: h.branch,
    nodeId: h.nodeId,
    orgId: h.nodeId,
    initials: u.initials,
  }))
)

export default function ProfilePage() {
  const router = useRouter()
  const [currentUser, setCurrentUser] = useState(getAuthUser())
  const [switchOpen, setSwitchOpen] = useState(false)
  const [logoutOpen, setLogoutOpen] = useState(false)

  useEffect(() => {
    setCurrentUser(getAuthUser())
  }, [])

  const handleSelectUser = (u: (typeof AVAILABLE_USERS)[0]) => {
    setAuthUser({
      ...u,
      isLoggedIn: true,
    })
    setCurrentUser({ ...u, isLoggedIn: true } as AuthUser)
    setSwitchOpen(false)
  }

  const handleLogout = () => {
    logoutUser()
    setLogoutOpen(false)
    window.location.href = '/login/'
  }

  const initials = currentUser?.name
    ? currentUser.name
        .split(' ')
        .map((n: string) => n[0])
        .slice(1, 3)
        .join('') || currentUser.name.slice(0, 2).toUpperCase()
    : currentUser?.initials || 'AS'

  return (
    <AppShell>
      <main className="mx-auto max-w-[1120px] px-10 py-10">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#14A493]">
            Account context
          </div>
          <h1 className="mt-3 text-[30px] font-bold tracking-[-0.03em] text-[#172033] dark:text-white">
            Authorized Profile
          </h1>
          <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
            Your authorized BioQShield clinical identity and hospital network access privileges.
          </p>
        </div>

        <section className="mt-8 flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-7 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
          <div className="flex items-center gap-5">
            <div className="flex size-16 items-center justify-center rounded-2xl bg-[#DCEBFF] dark:bg-[#2563EB]/20 text-[20px] font-bold text-[#1D56B5] dark:text-[#67E8F9]">
              {initials}
            </div>
            <div>
              <h2 className="text-[19px] font-bold text-[#172033] dark:text-white">
                {currentUser?.name || 'Clinical User'}
              </h2>
              <p className="mt-1 text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                {currentUser?.username || 'user'} · {currentUser?.role || 'Staff'}
              </p>
              <p className="mt-2 text-[11px] font-semibold text-[#14A493]">
                {currentUser?.department || 'Medicine'} · {currentUser?.hospital || 'Hospital Network'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSwitchOpen(true)}
              className="flex items-center gap-2 rounded-xl border border-[#D9E2EC] dark:border-white/10 px-4 py-2.5 text-[12px] font-semibold text-[#2563EB] dark:text-[#67E8F9] hover:bg-[#F5F8FC] dark:hover:bg-white/5 transition"
            >
              Switch User <ChevronRight className="size-3.5" />
            </button>
            <button
              onClick={() => setLogoutOpen(true)}
              className="flex items-center gap-2 rounded-xl border border-[#F1D8D9] dark:border-red-900/40 px-4 py-2.5 text-[12px] font-semibold text-[#C33E42] dark:text-[#FF9292] hover:bg-[#FFF7F7] dark:hover:bg-red-950/20 transition"
            >
              <LogOut className="size-3.5" />
              Log out
            </button>
          </div>
        </section>

        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-5">
          <section className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center gap-2 text-[13px] font-bold text-[#172033] dark:text-white">
              <UserRound className="size-4 text-[#14A493]" />
              Personal Information
            </div>
            <div className="mt-5 flex flex-col gap-4">
              {[
                ['Name', currentUser.name],
                ['Username', currentUser.username],
                ['Role', currentUser.role],
                ['Department', currentUser.department],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#9AAABD]">
                    {label}
                  </div>
                  <div className="mt-1 text-[12px] font-medium text-[#172033] dark:text-white">
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center gap-2 text-[13px] font-bold text-[#172033] dark:text-white">
              <Building2 className="size-4 text-[#14A493]" />
              Organization
            </div>
            <div className="mt-5 flex flex-col gap-4">
              {[
                ['Hospital', currentUser.hospital || 'Apollo Hospital'],
                ['Branch', currentUser.branch || 'Chennai Main Branch'],
                ['Network Access', 'Authorized Inter-Hospital Node'],
                ['Organization ID', (currentUser as any).nodeId || (currentUser as any).orgId || 'AQ-CHN-01'],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#9AAABD]">
                    {label}
                  </div>
                  <div className="mt-1 text-[12px] font-medium text-[#172033] dark:text-white">
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center gap-2 text-[13px] font-bold text-[#172033] dark:text-white">
              <ShieldCheck className="size-4 text-[#14A493]" />
              Security Context
            </div>
            <div className="mt-5 flex flex-col gap-4">
              {[
                ['Authentication', 'Multi-Factor Quantum Passkey'],
                ['Account Status', 'Active & Verified'],
                ['Session Health', 'Secure Quantum Channel Ready'],
                ['Cryptographic Policy', 'Adaptive Threat Guard Enabled'],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#9AAABD]">
                    {label}
                  </div>
                  <div className="mt-1 text-[12px] font-medium text-[#172033] dark:text-white">
                    {value}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>

      {switchOpen && (
        <Modal
          title="Switch User"
          subtitle="Select an authorized healthcare professional."
          onClose={() => setSwitchOpen(false)}
        >
          <div className="flex flex-col gap-2">
            {AVAILABLE_USERS.map((u) => {
              const selected = u.username === currentUser.username
              return (
                <button
                  key={u.username}
                  onClick={() => handleSelectUser(u)}
                  className={`flex items-center justify-between rounded-xl border p-3 text-left transition ${
                    selected
                      ? 'border-[#2563EB] dark:border-[#22D3EE] bg-[#F4F8FD] dark:bg-white/5'
                      : 'border-[#E2EAF2] dark:border-white/10 hover:border-[#9CC7FF] hover:bg-[#F8FBFF] dark:hover:bg-white/[0.02]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex size-9 items-center justify-center rounded-full bg-[#DCEBFF] dark:bg-[#2563EB]/20 text-[11px] font-bold text-[#1D56B5] dark:text-[#67E8F9]">
                      {u.initials}
                    </div>
                    <div>
                      <div className="text-[12px] font-semibold text-[#172033] dark:text-white">
                        {u.name}
                      </div>
                      <div className="mt-0.5 text-[10px] text-[#64748B] dark:text-[#9AAABD]">
                        {u.role} · {u.department} · {u.hospital}
                      </div>
                    </div>
                  </div>
                  {selected && <CheckCircle2 className="size-4 text-[#2563EB] dark:text-[#22D3EE]" />}
                </button>
              )
            })}
          </div>
        </Modal>
      )}

      {logoutOpen && (
        <Modal
          title="Sign out of BioQShield?"
          subtitle="Your secure cryptographic session will be ended."
          onClose={() => setLogoutOpen(false)}
        >
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setLogoutOpen(false)}
              className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-4 py-2.5 text-[12px] font-semibold text-[#64748B] dark:text-[#9AAABD]"
            >
              Cancel
            </button>
            <button
              onClick={handleLogout}
              className="rounded-xl bg-[#DC4446] px-4 py-2.5 text-[12px] font-semibold text-white hover:bg-[#C33E42] transition"
            >
              Sign Out
            </button>
          </div>
        </Modal>
      )}
    </AppShell>
  )
}

function Modal({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string
  subtitle: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#07111F]/50 backdrop-blur-xs p-6">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-[470px] rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-[17px] font-bold text-[#172033] dark:text-white">{title}</h2>
            <p className="mt-1 text-[12px] text-[#64748B] dark:text-[#9AAABD]">{subtitle}</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="text-[#94A3B8] hover:text-[#172033] dark:hover:text-white"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  )
}
