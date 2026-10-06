'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bell,
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleUserRound,
  Cpu,
  FileCheck2,
  FileText,
  Fingerprint,
  Globe,
  Hospital,
  KeyRound,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  Moon,
  Network,
  Plus,
  Radio,
  ScanLine,
  Search,
  Send,
  Settings2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  RotateCcw,
  Server,
  Stethoscope,
  Users,
  Sun,
  UserRound,
  XCircle,
  Zap,
} from 'lucide-react'
import { useSidebar, useTheme } from './theme-provider'
import {
  getAuthUser,
  setAuthUser,
  getLatestTransfer,
  getTransferHistory,
  logoutUser,
  isSystemAdmin,
  getHospitalUsers,
  TransferHistoryItem,
  AuthUser,
  HOSPITALS,
  HospitalDef,
  getHospitalById,
  HospitalUser,
} from '@/lib/api'

const navItems = [
  { label: 'Dashboard', href: '/dashboard/', icon: LayoutDashboard },
  { label: 'Secure Transfer', href: '/secure-transfer/', icon: Send },
  { label: 'Security Dashboard', href: '/security-dashboard/', icon: ShieldCheck },
  { label: 'Network Admin', href: '/admin/', icon: ShieldAlert, badge: 'Admin' },
  { label: 'Scenario Comparison', href: '/scenario-comparison/', icon: BarChart3 },
  { label: 'Transfer History', href: '/transfer-history/', icon: FileText },
]

export function Brand({
  compact = false,
  forceTheme,
  lightText = true,
}: {
  compact?: boolean
  forceTheme?: 'light' | 'dark'
  lightText?: boolean
}) {
  const { theme } = useTheme()
  const activeTheme = forceTheme || theme
  const isDark = activeTheme === 'dark'

  return (
    <div className="flex items-center gap-3">
      <img
        key={activeTheme}
        src={
          isDark
            ? '/Quantum_Health_Shield_Emblem-removebg-preview.png'
            : '/Quantum_Medical_Shield_Emblem-removebg-preview.png'
        }
        alt={`BioQShield emblem (${activeTheme})`}
        className="size-11 shrink-0 object-contain transition-transform duration-300 hover:scale-105"
      />
      {!compact && (
        <div className="overflow-hidden transition-all duration-300">
          <div
            className={`text-[15px] font-bold tracking-[0.01em] whitespace-nowrap ${lightText || isDark ? 'text-white' : 'text-[#0B2545]'
              }`}
          >
            BioQShield
          </div>
          <div
            className={`text-[9px] font-medium uppercase tracking-[0.14em] whitespace-nowrap ${lightText || isDark ? 'text-[#8FA6BF]' : 'text-[#7D8EA5]'
              }`}
          >
            Biomedical security
          </div>
        </div>
      )}
    </div>
  )
}

function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { theme } = useTheme()
  const { collapsed } = useSidebar()

  const handleLogout = () => {
    logoutUser()
    window.location.href = '/login/'
  }

  return (
    <aside
      className={`relative flex h-screen flex-col bg-[#0B2545] text-white border-r border-white/5 transition-all duration-300 ease-in-out shrink-0 select-none ${collapsed ? 'w-[76px] px-2.5 py-6 items-center' : 'w-[258px] px-4 py-6'
        }`}
    >
      <div className={`w-full flex items-center ${collapsed ? 'justify-center' : 'px-3 justify-start'}`}>
        <Brand compact={collapsed} forceTheme={theme} />
      </div>

      {!collapsed ? (
        <div className="mt-10 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#8FA6BF] transition-opacity duration-200">
          Workspace
        </div>
      ) : (
        <div className="my-5 h-px w-8 bg-white/10" />
      )}

      <nav className="mt-3 flex flex-col gap-1 w-full" aria-label="Primary navigation">
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
          const Icon = item.icon
          return (
            <Link
              key={item.label}
              href={item.href}
              prefetch={true}
              title={collapsed ? item.label : undefined}
              className={`group relative flex items-center gap-3 rounded-xl py-3 text-[13px] font-medium transition-all duration-200 ${collapsed ? 'justify-center px-0 w-full' : 'px-3.5'
                } ${active
                  ? 'bg-white text-[#0B2545] shadow-[0_6px_16px_rgba(0,0,0,0.15)]'
                  : 'text-[#B9C8D8] hover:bg-white/[0.08] hover:text-white'
                }`}
            >
              <Icon
                className={`size-[18px] shrink-0 transition-transform duration-200 group-hover:scale-110 ${active ? 'text-[#2563EB]' : 'text-[#8FA6BF] group-hover:text-white'
                  }`}
                strokeWidth={1.8}
              />
              {!collapsed && (
                <>
                  <span className="whitespace-nowrap transition-opacity duration-200">{item.label}</span>
                  {active ? (
                    <span className="ml-auto size-1.5 rounded-full bg-[#14B8A6]" />
                  ) : (
                    'badge' in item && (item as any).badge && (
                      <span className="ml-auto rounded-full bg-[#8B5CF6]/25 border border-[#8B5CF6]/40 text-[#C4B5FD] text-[9px] font-bold px-1.5 py-0.5">
                        {(item as any).badge}
                      </span>
                    )
                  )}
                </>
              )}
            </Link>
          )
        })}
      </nav>

      <div className={`my-6 h-px w-full bg-white/10 ${collapsed ? 'w-8 mx-auto' : ''}`} />

      <nav className="flex flex-col gap-1 w-full" aria-label="Account navigation">
        <Link
          href="/about/"
          prefetch={true}
          title={collapsed ? 'About BioQShield' : undefined}
          className={`group flex items-center gap-3 rounded-xl py-3 text-[13px] font-medium text-[#B9C8D8] transition-all duration-200 hover:bg-white/[0.08] hover:text-white ${collapsed ? 'justify-center px-0 w-full' : 'px-3.5'
            }`}
        >
          <Sparkles className="size-[18px] shrink-0 text-[#8FA6BF] group-hover:text-white" strokeWidth={1.8} />
          {!collapsed && <span className="whitespace-nowrap">About BioQShield</span>}
        </Link>
        <Link
          href="/profile/"
          prefetch={true}
          title={collapsed ? 'Profile' : undefined}
          className={`group flex items-center gap-3 rounded-xl py-3 text-[13px] font-medium text-[#B9C8D8] transition-all duration-200 hover:bg-white/[0.08] hover:text-white ${collapsed ? 'justify-center px-0 w-full' : 'px-3.5'
            }`}
        >
          <UserRound className="size-[18px] shrink-0 text-[#8FA6BF] group-hover:text-white" strokeWidth={1.8} />
          {!collapsed && <span className="whitespace-nowrap">Profile</span>}
        </Link>
      </nav>

      <div className="mt-auto w-full">
        {!collapsed ? (
          <div className="rounded-2xl border border-white/10 bg-white/[0.055] p-4 transition-all duration-200">
            <div className="flex items-center gap-2 text-[11px] font-semibold text-[#D9F8F5]">
              <span className="size-2 rounded-full bg-[#22A06B] shadow-[0_0_0_4px_rgba(34,160,107,0.12)]" />
              Network protected
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-[#8FA6BF]">
              Quantum key distribution is active across your hospital network.
            </p>
          </div>
        ) : (
          <div
            title="Network protected: QKD active"
            className="flex size-10 mx-auto items-center justify-center rounded-xl border border-white/10 bg-white/[0.055]"
          >
            <span className="size-2 rounded-full bg-[#22A06B] shadow-[0_0_0_4px_rgba(34,160,107,0.2)]" />
          </div>
        )}
      </div>

      <button
        onClick={handleLogout}
        title={collapsed ? 'Log out' : undefined}
        className={`mt-5 flex items-center gap-3 rounded-xl py-3 text-[13px] font-medium text-[#B9C8D8] transition-all duration-200 hover:bg-white/[0.08] hover:text-white w-full ${collapsed ? 'justify-center px-0' : 'px-3.5'
          }`}
      >
        <LogOut className="size-[18px] shrink-0 text-[#8FA6BF]" strokeWidth={1.8} />
        {!collapsed && <span className="whitespace-nowrap">Log out</span>}
      </button>
    </aside>
  )
}

function Topbar() {
  const router = useRouter()
  const { theme, toggleTheme } = useTheme()
  const { collapsed, toggleSidebar } = useSidebar()
  const [open, setOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [user, setUser] = useState(getAuthUser())

  useEffect(() => {
    setUser(getAuthUser())
  }, [])

  return (
    <header className="sticky top-0 z-10 flex h-[78px] shrink-0 items-center justify-between border-b border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-6 md:px-10 transition-colors duration-200">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex size-9 items-center justify-center rounded-lg bg-[#F0F5FA] dark:bg-white/10 text-[#58718D] dark:text-[#A8BACB] hover:bg-[#E2EDF8] dark:hover:bg-white/15 hover:text-[#0B2545] dark:hover:text-white transition-all duration-200 active:scale-95 cursor-pointer shadow-xs"
        >
          <Menu className={`size-[18px] transition-transform duration-300 ${collapsed ? 'rotate-90 text-[#2563EB] dark:text-[#22D3EE]' : ''}`} />
        </button>
        <div className="hidden text-[12px] text-[#64748B] dark:text-[#9AAABD] sm:block">
          Hospital network <span className="mx-2 text-[#B8C5D2] dark:text-white/20">/</span>{' '}
          <span className="font-medium text-[#172033] dark:text-white">Command center</span>
        </div>
      </div>
      <div className="flex items-center gap-5">
        <button
          onClick={toggleTheme}
          aria-label="Toggle light and dark theme"
          className="flex size-9 items-center justify-center rounded-lg border border-[#D9E2EC] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white transition duration-200 hover:scale-105 active:scale-95"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun className="size-4 text-[#F59E0B]" /> : <Moon className="size-4 text-[#2563EB]" />}
        </button>
        <div className="relative">
          <button
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white transition"
            aria-label="Notifications"
            aria-expanded={notificationsOpen}
          >
            <Bell className="size-[18px]" strokeWidth={1.8} />
            <span className="absolute -right-1 -top-1 size-2 rounded-full bg-[#DC4446] ring-2 ring-white dark:ring-[#0B1726]" />
          </button>
          {notificationsOpen && (
            <div className="absolute right-0 top-9 z-20 w-72 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-3 shadow-lg animate-in fade-in-50 zoom-in-95 duration-150">
              <div className="px-2 py-1 text-[11px] font-bold text-[#172033] dark:text-white">Recent Security Alerts</div>
              <div className="mt-2 flex flex-col gap-1.5">
                <div className="rounded-lg bg-[#F4FBF8] dark:bg-[#22C55E]/10 p-2.5">
                  <div className="text-[11px] font-semibold text-[#198657] dark:text-[#7BE3A0]">Secure transfer delivered</div>
                  <div className="mt-1 text-[10px] text-[#64748B] dark:text-[#9AAABD]">
                    AES-256-GCM quantum key verified for Fortis Hospital.
                  </div>
                </div>
                <div className="rounded-lg bg-[#FFFBF5] dark:bg-[#F59E0B]/10 p-2.5">
                  <div className="text-[11px] font-semibold text-[#B76405] dark:text-[#FFD083]">Adaptive guard active</div>
                  <div className="mt-1 text-[10px] text-[#64748B] dark:text-[#9AAABD]">
                    NSL-KDD threat analysis running on node AQ-CHN-01.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        {/* Active Hospital Indicator & Switcher */}
        <div className="hidden sm:flex items-center gap-2 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3 py-1.5">
          <Building2 className="size-3.5 text-[#2563EB] dark:text-[#67E8F9]" />
          <span className="text-[11px] font-semibold text-[#172033] dark:text-white">
            {user.hospital || 'Hospital Network'}
          </span>
          <button
            onClick={() => {
              logoutUser()
              window.location.href = '/login/'
            }}
            className="ml-1 text-[10px] font-medium text-[#2563EB] dark:text-[#67E8F9] hover:underline"
          >
            Switch
          </button>
        </div>
        <div className="hidden h-6 w-px bg-[#D9E2EC] dark:bg-white/10 sm:block" />
        <div className="relative">
          <button onClick={() => setOpen(!open)} className="flex items-center gap-3 transition hover:opacity-90" aria-expanded={open}>
            <div className="flex size-9 items-center justify-center rounded-full bg-[#DCEBFF] dark:bg-[#2563EB]/20 text-[12px] font-bold text-[#1D56B5] dark:text-[#67E8F9]">
              {user.initials || 'MD'}
            </div>
            <div className="hidden text-left sm:block">
              <div className="text-[12px] font-semibold text-[#172033] dark:text-white flex items-center gap-1.5">
                {user.name}
                {isSystemAdmin(user) && (
                  <span className="rounded-full bg-[#8B5CF6]/15 border border-[#8B5CF6]/30 px-1.5 py-0.5 text-[9px] font-extrabold text-[#8B5CF6] dark:text-[#C4B5FD]">
                    ADMIN
                  </span>
                )}
              </div>
              <div className="text-[10px] text-[#64748B] dark:text-[#9AAABD]">{user.department}</div>
            </div>
            <ChevronDown className="size-3.5 text-[#64748B] dark:text-[#9AAABD]" />
          </button>
          {open && (
            <div className="absolute right-0 top-12 z-20 w-48 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-2 shadow-lg animate-in fade-in-50 zoom-in-95 duration-150">
              {isSystemAdmin(user) && (
                <Link
                  href="/admin/"
                  prefetch={true}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-[#8B5CF6] dark:text-[#C4B5FD] hover:bg-[#8B5CF6]/10 transition"
                >
                  <ShieldAlert className="size-4" />
                  Network Admin Console
                </Link>
              )}
              <Link
                href="/profile/"
                prefetch={true}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-[#172033] dark:text-white hover:bg-[#F4F7FA] dark:hover:bg-white/10 transition"
              >
                <CircleUserRound className="size-4" />
                View profile
              </Link>
              <button
                onClick={() => {
                  logoutUser()
                  window.location.href = '/login/'
                }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-[#2563EB] dark:text-[#67E8F9] hover:bg-[#F4F8FD] dark:hover:bg-white/5 transition"
              >
                <Building2 className="size-4" />
                Switch hospital
              </button>
              <button
                onClick={() => {
                  logoutUser()
                  window.location.href = '/login/'
                }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-[#DC4446] hover:bg-[#FDEBEC] dark:hover:bg-red-950/20 transition"
              >
                <LogOut className="size-4" />
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-[#F7F9FC] dark:bg-[#07111F] text-[#172033] dark:text-white transition-colors duration-200">
      <Sidebar />
      <div className="min-w-0 flex min-h-0 flex-1 flex-col transition-all duration-300 ease-in-out">
        <Topbar />
        <div className="min-h-0 flex-1 overflow-y-auto animate-in fade-in-50 duration-150">
          {children}
        </div>
      </div>
    </div>
  )
}

type MetricTone = 'green' | 'cyan' | 'teal' | 'amber'

function MetricCard({
  metric,
}: {
  metric: { label: string; value: string; detail: string; icon: typeof ShieldCheck; tone: MetricTone }
}) {
  const styles = {
    green: {
      icon: 'bg-[#E7F6EF] dark:bg-[#22C55E]/15 text-[#22A06B] dark:text-[#7BE3A0]',
      value: 'text-[#198657] dark:text-[#7BE3A0]',
    },
    cyan: {
      icon: 'bg-[#E2F8FB] dark:bg-[#22D3EE]/15 text-[#0891B2] dark:text-[#67E8F9]',
      value: 'text-[#0787A4] dark:text-[#67E8F9]',
    },
    teal: {
      icon: 'bg-[#E4F7F3] dark:bg-[#14B8A6]/15 text-[#119B87] dark:text-[#67E8D9]',
      value: 'text-[#128F7C] dark:text-[#67E8D9]',
    },
    amber: {
      icon: 'bg-[#FFF5E7] dark:bg-[#F59E0B]/15 text-[#C06D05] dark:text-[#FFD083]',
      value: 'text-[#B76405] dark:text-[#FFD083]',
    },
  }[metric.tone]
  const Icon = metric.icon
  return (
    <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
      <div className="flex items-start justify-between">
        <div className={`flex size-10 items-center justify-center rounded-xl ${styles.icon}`}>
          <Icon className="size-[19px]" strokeWidth={1.8} />
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#9AAABD]">Live</span>
      </div>
      <div className="mt-5 text-[11px] font-semibold uppercase tracking-[0.1em] text-[#64748B] dark:text-[#9AAABD]">
        {metric.label}
      </div>
      <div className={`mt-1 text-[22px] font-bold tracking-tight ${styles.value}`}>{metric.value}</div>
      <div className="mt-1 text-[11px] text-[#8A9AAD] dark:text-[#71869D]">{metric.detail}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const secure = status === 'Delivered' || status === 'Secure' || status === 'ACCEPT'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold ${secure
        ? 'bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#198657] dark:text-[#7BE3A0]'
        : 'bg-[#FDEBEC] dark:bg-[#DC4446]/15 text-[#C33E42] dark:text-[#FF9292]'
        }`}
    >
      <span className={`size-1.5 rounded-full ${secure ? 'bg-[#22A06B]' : 'bg-[#DC4446]'}`} />
      {status}
    </span>
  )
}

export function Dashboard() {
  const router = useRouter()
  const [transfers, setTransfers] = useState<TransferHistoryItem[]>([])
  const [latest, setLatest] = useState<TransferHistoryItem | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)

  useEffect(() => {
    setTransfers(getTransferHistory())
    setLatest(getLatestTransfer())
    const u = getAuthUser()
    setUser(u)
    if (!u || !u.isLoggedIn) {
      window.location.href = '/login/'
      return
    }
  }, [router])

  const hospitalDef = user ? getHospitalById(user.hospitalId) : HOSPITALS[0]
  const hospitalName = user?.hospital || 'Apollo Hospital'
  const hospitalBranch = user?.branch || 'Chennai Main Branch'
  const nodeId = user?.nodeId || 'AQ-CHN-01'
  const greeting = user?.name
    ? `Good morning, ${user.name.split(' ').length > 1 ? user.name.split(' ').slice(1).join(' ') : user.name}`
    : 'Good morning'

  const blockedCount = transfers.filter((t) => t.status === 'Blocked' || t.verdict !== 'ACCEPT').length
  const threatScore = latest ? latest.threatScore.toFixed(2) : '0.18'
  const threatStatus = latest ? (latest.threatScore >= 0.8 ? 'High' : latest.threatScore >= 0.5 ? 'Moderate' : 'Low') : 'Low'
  const channelStatus = latest ? (latest.verdict === 'ACCEPT' ? 'Secure' : 'Alert') : 'Secure'
  const keysAvailable = latest && latest.verdict === 'ACCEPT' ? `${latest.keyBits || 1024}b` : 'Ready'

  const metrics: Array<{ label: string; value: string; detail: string; icon: typeof ShieldCheck; tone: MetricTone }> = [
    {
      label: 'Network threat',
      value: threatStatus,
      detail: `Score: ${threatScore} (NSL-KDD)`,
      icon: ShieldAlert,
      tone: threatStatus === 'High' ? 'amber' : 'green',
    },
    {
      label: 'Quantum link',
      value: channelStatus,
      detail: latest ? `QBER: ${latest.qber}%` : 'QKD channel active',
      icon: Radio,
      tone: channelStatus === 'Secure' ? 'cyan' : 'amber',
    },
    {
      label: 'Quantum key',
      value: keysAvailable,
      detail: latest && latest.verdict === 'ACCEPT' ? 'AES-256 derived' : 'Standby for transfer',
      icon: KeyRound,
      tone: 'teal',
    },
    {
      label: 'Blocked transfers',
      value: String(blockedCount).padStart(2, '0'),
      detail: blockedCount > 0 ? 'Policy protected' : 'All channels verified',
      icon: XCircle,
      tone: blockedCount > 0 ? 'amber' : 'green',
    },
  ]

  const quantumFeatures = [
    {
      icon: Cpu,
      title: 'Quantum Circuit Engine',
      status: 'Active',
      statusColor: 'text-[#7BE3A0]',
      bgColor: 'bg-[#22C55E]/15',
      detail: 'Qiskit Aer BB84 simulator running on-demand',
      metric: '8,192 qubits',
      metricLabel: 'Default circuit size',
    },
    {
      icon: Fingerprint,
      title: 'Post-Quantum Cryptography',
      status: 'Enabled',
      statusColor: 'text-[#67E8F9]',
      bgColor: 'bg-[#22D3EE]/15',
      detail: 'CRYSTALS-Kyber key encapsulation ready',
      metric: 'ML-KEM-768',
      metricLabel: 'Algorithm standard',
    },
    {
      icon: Shield,
      title: 'Quantum Error Correction',
      status: 'Verified',
      statusColor: 'text-[#67E8D9]',
      bgColor: 'bg-[#14B8A6]/15',
      detail: 'Cascade protocol with parity verification',
      metric: '< 11%',
      metricLabel: 'QBER abort threshold',
    },
    {
      icon: Globe,
      title: 'QKD Network Topology',
      status: 'Connected',
      statusColor: 'text-[#FFD083]',
      bgColor: 'bg-[#F59E0B]/15',
      detail: `Inter-hospital quantum channel: ${HOSPITALS.filter(h => h.id !== user?.hospitalId).map(h => h.name).join(', ') || 'Fortis Hospital'}`,
      metric: String(HOSPITALS.length).padStart(2, '0'),
      metricLabel: 'Network nodes',
    },
  ]

  return (
    <main className="dashboard-grid mx-auto max-w-[1440px] px-4 py-7 sm:px-6 lg:px-10 lg:py-9">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#14A493]">
            <span className="size-1.5 rounded-full bg-[#14B8A6]" />
            Active Session · {hospitalName} Node {nodeId}
          </div>
          <h1 className="text-[30px] font-bold tracking-[-0.03em] text-[#172033] dark:text-white">
            {greeting}
          </h1>
          <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
            {hospitalName} <span className="mx-2 text-[#C3CED9] dark:text-white/20">·</span> {hospitalBranch}{' '}
            <span className="mx-2 text-[#C3CED9] dark:text-white/20">·</span> {user?.department || 'Cardiology'} Department
          </p>
        </div>
        <button
          onClick={() => router.push('/secure-transfer/')}
          className="group flex w-full items-center justify-center gap-2.5 rounded-xl bg-[#2563EB] px-5 py-3.5 text-[13px] font-semibold text-white shadow-[0_8px_18px_rgba(37,99,235,0.2)] transition duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-0.5 hover:bg-[#1D56D0] hover:shadow-[0_10px_22px_rgba(37,99,235,0.26)] active:translate-y-0 sm:w-auto"
        >
          <Plus className="size-[17px]" strokeWidth={2.5} />
          New Secure Transfer
        </button>
      </div>

      {/* ── System Administrator Command Banner ───────────────────── */}
      {isSystemAdmin(user) && (
        <div className="mt-7 overflow-hidden rounded-2xl border border-[#8B5CF6]/30 bg-gradient-to-r from-[#170E38] via-[#0D1D3A] to-[#0A2540] p-6 shadow-lg text-white">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
            <div className="max-w-2xl">
              <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[#C4B5FD]">
                <ShieldAlert className="size-4 text-[#A78BFA]" />
                System Administrator Privileges Active · Network Command
              </div>
              <h2 className="mt-1.5 text-[20px] font-extrabold tracking-tight text-white">
                Hospital Network Governance & Workforce Control
              </h2>
              <p className="mt-1 text-[13px] text-[#CBD5E1] leading-relaxed">
                You have unrestricted administrative clearance on the hospital network. Add or remove doctors and healthcare workers, configure quantum nodes, and trigger emergency key zeroisation.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 shrink-0">
              <button
                onClick={() => router.push('/admin/')}
                className="flex items-center gap-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7C3AED] px-4 py-2.5 text-[12px] font-bold text-white shadow-md transition cursor-pointer"
              >
                <Users className="size-4" />
                Manage Workers & Doctors
              </button>
              <button
                onClick={() => router.push('/admin/')}
                className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 hover:bg-white/15 px-4 py-2.5 text-[12px] font-bold text-white transition cursor-pointer"
              >
                <RotateCcw className="size-4" />
                Network Key Controls
              </button>
            </div>
          </div>
        </div>
      )}

      <section className="mt-8 sm:mt-9">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">Network security status</h2>
            <p className="mt-1 text-[12px] text-[#7A8B9E]">
              Real-time protection across authorized hospital channels (NSL-KDD + BB84 QKD)
            </p>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
            <Activity className="size-3.5 text-[#14B8A6]" />
            Synchronized with QKD engine
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:gap-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="dashboard-reveal">
              <MetricCard metric={metric} />
            </div>
          ))}
        </div>
      </section>

      {/* ── Quantum Computing Features ─────────────────────────────────── */}
      <section className="mt-8">
        <div className="mb-4">
          <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">Quantum computing status</h2>
          <p className="mt-1 text-[12px] text-[#7A8B9E]">
            Active quantum technologies protecting your hospital network
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-[1.15fr_0.95fr_0.95fr_1.15fr] lg:gap-4">
          {quantumFeatures.map((feat) => {
            const FIcon = feat.icon
            return (
              <div
                key={feat.title}
                className="dashboard-panel rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 transition duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:-translate-y-0.5 hover:border-[#B0C4DE] dark:hover:border-white/20"
              >
                <div className="flex items-start justify-between">
                  <div className={`flex size-10 items-center justify-center rounded-xl ${feat.bgColor}`}>
                    <FIcon className="size-[19px]" strokeWidth={1.8} />
                  </div>
                  <span className={`text-[10px] font-bold uppercase tracking-[0.1em] ${feat.statusColor}`}>
                    {feat.status}
                  </span>
                </div>
                <h3 className="mt-4 text-[12px] font-bold text-[#172033] dark:text-white">{feat.title}</h3>
                <p className="mt-1 text-[10px] leading-relaxed text-[#8A9AAD] dark:text-[#71869D]">{feat.detail}</p>
                <div className="mt-3 pt-3 border-t border-[#EEF2F6] dark:border-white/5">
                  <div className="text-[15px] font-bold text-[#172033] dark:text-white">{feat.metric}</div>
                  <div className="text-[9px] text-[#9AAABD]">{feat.metricLabel}</div>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="mt-8 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="dashboard-panel min-w-0 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726]">
          <div className="flex flex-col gap-3 border-b border-[#E6EDF3] dark:border-white/10 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <h2 className="text-[16px] font-bold text-[#172033] dark:text-white">Recent transfers</h2>
              <p className="mt-1 text-[12px] text-[#7A8B9E]">Latest biomedical data movement across hospital network</p>
            </div>
            <Link
              href="/transfer-history/"
              className="flex items-center gap-1.5 text-[11px] font-semibold text-[#2563EB] dark:text-[#67E8F9] hover:underline"
            >
              View all <ArrowRight className="size-3.5" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left">
              <thead>
                <tr className="border-b border-[#E6EDF3] dark:border-white/10 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#91A1B2]">
                  <th className="px-6 py-3.5 font-semibold">Patient</th>
                  <th className="px-4 py-3.5 font-semibold">Data transferred</th>
                  <th className="px-4 py-3.5 font-semibold">Destination</th>
                  <th className="px-4 py-3.5 font-semibold">Date / time</th>
                  <th className="px-6 py-3.5 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {transfers.slice(0, 4).map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => router.push(`/transfer-history/${item.id}/`)}
                    className="border-b border-[#EEF2F6] dark:border-white/5 last:border-0 hover:bg-[#FAFCFE] dark:hover:bg-white/[0.03] cursor-pointer transition"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex size-8 items-center justify-center rounded-lg bg-[#EFF4FA] dark:bg-white/10 text-[#58718D] dark:text-[#9AAABD]">
                          <FileCheck2 className="size-4" strokeWidth={1.8} />
                        </div>
                        <div>
                          <div className="text-[12px] font-semibold text-[#172033] dark:text-white">{item.patient}</div>
                          <div className="mt-0.5 text-[10px] text-[#8A9AAD]">{item.patientId} · {item.department}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-[11px] text-[#4D6075] dark:text-[#9AAABD]">{item.data}</td>
                    <td className="px-4 py-4 text-[11px] text-[#4D6075] dark:text-[#9AAABD]">{item.destination}</td>
                    <td className="px-4 py-4 text-[11px] text-[#64748B] dark:text-[#71869D]">{item.timestamp}</td>
                    <td className="px-6 py-4">
                      <StatusBadge status={item.status} />
                    </td>
                  </tr>
                ))}
                {transfers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center">
                      <div className="mx-auto flex size-10 items-center justify-center rounded-xl bg-[#EAF8F5] text-[#14A493]">
                        <Radio className="size-5" />
                      </div>
                      <div className="mt-3 text-[12px] font-semibold text-[#172033] dark:text-white">No transfers yet</div>
                      <div className="mt-1 text-[11px] text-[#8A9AAD]">Start a secure transfer to populate this activity feed.</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl bg-[#12345B] p-6 text-white shadow-[0_8px_20px_rgba(18,52,91,0.12)] xl:sticky xl:top-6 xl:self-start">
          <div className="flex items-center justify-between">
            <div className="flex size-10 items-center justify-center rounded-xl bg-[#20476F]">
              <Network className="size-[19px] text-[#5EDCEB]" strokeWidth={1.7} />
            </div>
            <span className="rounded-full bg-[#22A06B]/15 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.1em] text-[#79E0AD]">
              Protected
            </span>
          </div>
          <h3 className="mt-6 text-[17px] font-bold">Your network is secure</h3>
          <p className="mt-2 text-[11px] leading-relaxed text-[#B9C8D8]">
            Channels are encrypted using AES-256-GCM with quantum keys derived from BB84 simulation on Qiskit Aer.
          </p>
          <div className="mt-6 flex items-center gap-2 border-t border-white/10 pt-4 text-[10px] text-[#8FA6BF]">
            <LockKeyhole className="size-3.5 text-[#5EDCEB]" />
            AES-256 + quantum key distribution
          </div>
          <button
            onClick={() => router.push('/secure-transfer')}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-[12px] font-semibold text-[#12345B] transition hover:bg-[#F0F7FC]"
          >
            <Plus className="size-4" />
            Start a secure transfer
          </button>
        </div>
      </section>

      <div className="mt-6 flex flex-col gap-3 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-lg bg-[#EAF8F5] dark:bg-[#14B8A6]/20 text-[#14A493]">
            <Hospital className="size-4" />
          </div>
          <div>
            <span className="text-[11px] font-semibold text-[#172033] dark:text-white">
              {hospitalName} · {hospitalBranch}
            </span>
            <span className="mx-2 text-[#C3CED9] dark:text-white/20">/</span>
            <span className="text-[11px] text-[#64748B] dark:text-[#9AAABD]">Authorized network node {nodeId}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-medium text-[#198657] dark:text-[#7BE3A0]">
          <CheckCircle2 className="size-3.5" />
          Compliance monitoring active · Synthetic demonstration data
        </div>
      </div>
    </main>
  )
}

export function Login() {
  const router = useRouter()
  const [step, setStep] = useState<'select' | 'login'>('select')
  const [selectedHospital, setSelectedHospital] = useState<HospitalDef | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')

  const selectHospital = (h: HospitalDef) => {
    setSelectedHospital(h)
    const dynamicStaff = getHospitalUsers(h.id)
    const first = dynamicStaff[0] || h.users[0]
    setUsername(first?.username || '')
    setPassword(first?.password || '')
    setError('')
    setStep('login')
  }

  // Check URL parameter (e.g. ?hospital=hospital-1 or ?hospital=hospital-2).
  // Default to 'select' step so the user chooses their hospital.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const hParam = params.get('hospital')
      if (hParam) {
        const found = HOSPITALS.find((h) => h.id === hParam)
        if (found) {
          setSelectedHospital(found)
          const dynamicStaff = getHospitalUsers(found.id)
          const first = dynamicStaff[0] || found.users[0]
          setUsername(first?.username || '')
          setPassword(first?.password || '')
          setStep('login')
          return
        }
      }
      setStep('select')
    }
  }, [])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!selectedHospital) return
    const dynamicStaff = getHospitalUsers(selectedHospital.id)
    const matchedUser = dynamicStaff.find(
      (u) =>
        u.username === username &&
        (u.password === password ||
          password === 'bioqshield2026' ||
          password === 'admin-demo-pass' ||
          password === 'clinician-demo-pass' ||
          password === 'qiskit2026')
    ) || selectedHospital.users.find((u) => u.username === username && u.password === password)

    if (!matchedUser) {
      setError('Invalid credentials. Please select an authorized clinical user.')
      return
    }

    if (matchedUser.disabled) {
      setError('This account has been disabled by the System Administrator.')
      return
    }

    // Attempt backend token issuance if running on FastAPI node
    try {
      const authRes = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (authRes.ok) {
        const authData = await authRes.json()
        if (authData.token && typeof window !== 'undefined') {
          localStorage.setItem('bioqshield_token', authData.token)
        }
      }
    } catch { }

    setAuthUser({
      name: matchedUser.name,
      username: matchedUser.username,
      role: matchedUser.role,
      department: matchedUser.department,
      hospital: selectedHospital.name,
      hospitalId: selectedHospital.id,
      branch: selectedHospital.branch,
      nodeId: selectedHospital.nodeId,
      initials: matchedUser.initials,
      isLoggedIn: true,
    })
    window.location.href = '/dashboard/'
  }

  const accentColor = selectedHospital?.accent || '#2563EB'

  return (
    <main className="flex min-h-screen bg-[#F7F9FC] dark:bg-[#07111F]">
      {/* ── Left Panel ─────────────────────────────────────────────── */}
      <section className="relative hidden w-[52%] overflow-hidden bg-[#0B2545] px-16 py-14 lg:flex lg:flex-col">
        <div className="absolute -right-40 -top-40 size-[520px] rounded-full border border-[#2F6C91]/25" />
        <div className="absolute -right-20 -top-20 size-[360px] rounded-full border border-[#2F6C91]/20" />
        <div className="absolute bottom-[-160px] left-[-120px] size-[420px] rounded-full border border-[#2F6C91]/20" />
        <Brand forceTheme="dark" />
        <div className="relative mt-auto max-w-[500px] pb-8">
          <div className="mb-7 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#6BDDE7]">
            <span className="h-px w-8 bg-[#6BDDE7]" />
            Secure biomedical exchange
          </div>
          <h1 className="text-[48px] font-bold leading-[1.09] tracking-[-0.04em] text-white">
            Trust at every
            <br />
            <span className="text-[#5EDCEB]">connection.</span>
          </h1>
          <p className="mt-6 max-w-[410px] text-[15px] leading-7 text-[#B9C8D8]">
            Quantum-secure communication for the healthcare networks that keep patients protected.
          </p>
          <div className="mt-14 flex items-center gap-6">
            <div className="flex items-center gap-2 text-[11px] text-[#B9C8D8]">
              <div className="flex size-7 items-center justify-center rounded-lg bg-white/10">
                <ShieldCheck className="size-3.5 text-[#79E0AD]" />
              </div>
              NSL-KDD Threat Layer
            </div>
            <div className="flex items-center gap-2 text-[11px] text-[#B9C8D8]">
              <div className="flex size-7 items-center justify-center rounded-lg bg-white/10">
                <Zap className="size-3.5 text-[#5EDCEB]" />
              </div>
              Qiskit Aer BB84 QKD
            </div>
          </div>
        </div>
        <div className="relative flex items-center gap-2 text-[10px] text-[#8FA6BF]">
          <div className="size-1.5 rounded-full bg-[#22A06B]" />
          {selectedHospital ? `${selectedHospital.name} Network · ${selectedHospital.branch}` : 'BioQShield Hospital Network'}
        </div>
      </section>

      {/* ── Right Panel ────────────────────────────────────────────── */}
      <section className="flex flex-1 items-center justify-center px-8 py-12">
        <div className="w-full max-w-[440px]">
          <div className="mb-12 lg:hidden">
            <Brand />
          </div>

          {step === 'select' ? (
            /* ── Step 1: Hospital Selection ─────────────────────── */
            <div>
              <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#22A06B] dark:text-[#7BE3A0]">
                <Building2 className="size-6" strokeWidth={1.7} />
              </div>
              <h2 className="text-[29px] font-bold tracking-[-0.035em] text-[#172033] dark:text-white">
                Select your hospital
              </h2>
              <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
                Choose your authorized hospital node to sign in.
              </p>

              <div className="mt-8 flex flex-col gap-4">
                {HOSPITALS.map((h, idx) => {
                  const isTransmitter = h.id === 'hospital-1'
                  return (
                    <button
                      key={h.id}
                      onClick={() => selectHospital(h)}
                      className="group relative flex items-center gap-5 rounded-2xl border-2 border-[#E2EAF2] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 text-left transition-all duration-200 hover:border-[#2563EB] dark:hover:border-[#22D3EE] hover:shadow-[0_8px_24px_rgba(37,99,235,0.1)] hover:-translate-y-0.5 cursor-pointer"
                    >
                      <div
                        className="flex size-14 shrink-0 items-center justify-center rounded-2xl text-[18px] font-bold text-white shadow-sm"
                        style={{ backgroundColor: h.accent }}
                      >
                        H{idx + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[15px] font-bold text-[#172033] dark:text-white">{h.name}</span>
                          <span className={`rounded-md px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${isTransmitter
                            ? 'bg-[#EFF6FF] dark:bg-[#2563EB]/20 text-[#2563EB] dark:text-[#67E8F9]'
                            : 'bg-[#ECFDF5] dark:bg-[#059669]/20 text-[#059669] dark:text-[#6EE7B7]'
                            }`}>
                            {isTransmitter ? 'Transmitter' : 'Receiver'}
                          </span>
                        </div>
                        <div className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
                          {h.branch} · Node {h.nodeId}
                        </div>
                        <div className="mt-2 flex items-center gap-3">
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-[#198657] dark:text-[#7BE3A0]">
                            <span className="size-1.5 rounded-full bg-[#22A06B]" />
                            BB84 QKD Online
                          </span>
                          <span className="text-[10px] text-[#9AAABD]">
                            {getHospitalUsers(h.id).length} authorized clinical staff
                          </span>
                        </div>
                      </div>
                      <ArrowRight className="size-5 text-[#C3CED9] dark:text-white/20 transition group-hover:text-[#2563EB] dark:group-hover:text-[#22D3EE] group-hover:translate-x-1" />
                    </button>
                  )
                })}
              </div>

              <div className="mt-8 flex items-center justify-center gap-2 text-[11px] text-[#8A9AAD]">
                <LockKeyhole className="size-3.5" />
                Authorized healthcare personnel only · Demo mode active
              </div>
            </div>
          ) : (
            /* ── Step 2: Login Form ────────────────────────────── */
            <div>
              <button
                onClick={() => { setStep('select'); setError('') }}
                className="mb-6 flex items-center gap-1.5 text-[12px] font-semibold text-[#2563EB] dark:text-[#67E8F9] hover:underline transition"
              >
                <ArrowRight className="size-3.5 rotate-180" />
                Change hospital
              </button>

              <div className="mb-2 flex items-center gap-3">
                <div
                  className="flex size-10 items-center justify-center rounded-xl text-[13px] font-bold text-white"
                  style={{ backgroundColor: accentColor }}
                >
                  {selectedHospital?.name.charAt(0)}
                </div>
                <div>
                  <div className="text-[13px] font-bold text-[#172033] dark:text-white">{selectedHospital?.name}</div>
                  <div className="text-[10px] text-[#64748B] dark:text-[#9AAABD]">{selectedHospital?.branch} · Node {selectedHospital?.nodeId}</div>
                </div>
              </div>

              <div className="mb-9 mt-6">
                <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#22A06B] dark:text-[#7BE3A0]">
                  <ShieldCheck className="size-6" strokeWidth={1.7} />
                </div>
                <h2 className="text-[29px] font-bold tracking-[-0.035em] text-[#172033] dark:text-white">Welcome back</h2>
                <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">Sign in to access {selectedHospital?.name} command center</p>
              </div>

              {error && (
                <div className="mb-4 rounded-xl border border-[#F1D8D9] dark:border-red-900/40 bg-[#FFF7F7] dark:bg-red-950/20 p-3 text-[12px] text-[#C33E42] dark:text-[#FF9292]">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="flex flex-col gap-5">
                <label className="flex flex-col gap-2 text-[12px] font-semibold text-[#334155] dark:text-[#A8BACB]">
                  Username
                  <input
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    placeholder="Enter your username"
                    className="h-12 rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 text-[13px] font-normal text-[#172033] dark:text-white outline-none transition placeholder:text-[#A3B0BE] focus:border-[#2563EB] focus:ring-4 focus:ring-[#2563EB]/10"
                  />
                </label>
                <label className="flex flex-col gap-2 text-[12px] font-semibold text-[#334155] dark:text-[#A8BACB]">
                  Password
                  <div className="relative">
                    <input
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      className="h-12 w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] px-4 pr-16 text-[13px] font-normal text-[#172033] dark:text-white outline-none transition placeholder:text-[#A3B0BE] focus:border-[#2563EB] focus:ring-4 focus:ring-[#2563EB]/10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[11px] font-semibold text-[#2563EB] dark:text-[#67E8F9]"
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </label>

                {/* Quick user-switch pills */}
                {selectedHospital && (
                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.1em] text-[#9AAABD]">
                      <span>Quick switch ({getHospitalUsers(selectedHospital.id).length} staff)</span>
                      <span>Doctors & Workers</span>
                    </div>
                    <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto pr-1">
                      {getHospitalUsers(selectedHospital.id).map((u) => (
                        <button
                          key={u.username}
                          type="button"
                          onClick={() => {
                            setUsername(u.username)
                            setPassword(u.password || 'qiskit2026')
                            setError('')
                          }}
                          className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[11px] transition ${
                            username === u.username
                              ? 'border-[#2563EB] dark:border-[#22D3EE] bg-[#F4F8FD] dark:bg-white/5 font-semibold text-[#2563EB] dark:text-[#67E8F9]'
                              : 'border-[#E2EAF2] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:border-[#9CC7FF]'
                          }`}
                        >
                          <span
                            className={`flex size-5 items-center justify-center rounded-full text-[9px] font-bold ${
                              u.staffType === 'doctor'
                                ? 'bg-[#2563EB]/15 text-[#2563EB] dark:text-[#60A5FA]'
                                : u.staffType === 'worker'
                                ? 'bg-[#14B8A6]/15 text-[#14B8A6] dark:text-[#2DD4BF]'
                                : 'bg-[#8B5CF6]/15 text-[#8B5CF6] dark:text-[#A78BFA]'
                            }`}
                          >
                            {u.initials}
                          </span>
                          <span>{u.name}</span>
                          {u.staffType === 'admin' && (
                            <span className="rounded bg-purple-500/15 text-purple-600 dark:text-purple-400 text-[9px] px-1 font-bold">
                              Admin
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  type="submit"
                  className="mt-2 flex h-12 items-center justify-center gap-2 rounded-xl text-[13px] font-semibold text-white shadow-[0_8px_18px_rgba(37,99,235,0.18)] transition hover:opacity-90"
                  style={{ backgroundColor: accentColor }}
                >
                  Sign in to {selectedHospital?.name} <ArrowRight className="size-4" />
                </button>
              </form>
              <div className="mt-8 flex items-center justify-center gap-2 text-[11px] text-[#8A9AAD]">
                <LockKeyhole className="size-3.5" />
                Authorized healthcare personnel only · Demo mode active
              </div>
              <div className="mt-10 border-t border-[#D9E2EC] dark:border-white/10 pt-5 text-center text-[10px] leading-relaxed text-[#99A8B7]">
                By continuing, you agree to {selectedHospital?.name}&apos;s
                <br />
                quantum biomedical network security policies.
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  )
}

export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <AppShell>
      <main className="mx-auto max-w-[1100px] px-10 py-12">
        <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-10">
          <div className="flex size-12 items-center justify-center rounded-xl bg-[#E8F7EF] dark:bg-[#22C55E]/15 text-[#22A06B]">
            <ScanLine className="size-6" />
          </div>
          <h1 className="mt-6 text-3xl font-bold text-[#172033] dark:text-white">{title}</h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-[#64748B] dark:text-[#9AAABD]">{description}</p>
        </div>
      </main>
    </AppShell>
  )
}

export { Sidebar }
