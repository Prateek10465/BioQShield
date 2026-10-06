'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/bioqshield'
import {
  Users,
  UserPlus,
  Trash2,
  ShieldCheck,
  ShieldAlert,
  KeyRound,
  RotateCcw,
  Radio,
  Server,
  Building2,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  RefreshCw,
  Lock,
  Eye,
  EyeOff,
  Stethoscope,
  Activity,
  HeartPulse,
  ChevronRight,
  AlertTriangle,
  FileText,
  Sliders,
  Sparkles,
  Zap,
  ArrowUpRight,
} from 'lucide-react'
import {
  getAuthUser,
  setAuthUser,
  isSystemAdmin,
  getHospitalUsers,
  addHospitalUser,
  removeHospitalUser,
  toggleHospitalUserDisabled,
  rotateNetworkKeys,
  verifyNetworkAudit,
  fetchNetworkAuditLogs,
  fetchAdminNetworkOverview,
  HospitalUser,
  StaffType,
  HOSPITALS,
  AuthUser,
} from '@/lib/api'

export default function AdminPage() {
  const router = useRouter()
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null)
  const [staff, setStaff] = useState<HospitalUser[]>([])
  const [selectedHospitalId, setSelectedHospitalId] = useState<string>('all')
  const [activeTab, setActiveTab] = useState<'staff' | 'network' | 'audit' | 'policies'>('staff')
  const [staffFilter, setStaffFilter] = useState<'all' | 'doctor' | 'worker' | 'admin' | 'auditor'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  
  // Modals & confirmation dialogs
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [userToDelete, setUserToDelete] = useState<HospitalUser | null>(null)
  const [isRotateModalOpen, setIsRotateModalOpen] = useState(false)
  const [actionFeedback, setActionFeedback] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
  
  // Add User Form state
  const [newStaffName, setNewStaffName] = useState('')
  const [newStaffUsername, setNewStaffUsername] = useState('')
  const [newStaffPassword, setNewStaffPassword] = useState('bioqshield2026')
  const [showPassword, setShowPassword] = useState(false)
  const [newStaffType, setNewStaffType] = useState<StaffType>('doctor')
  const [newStaffRole, setNewStaffRole] = useState('Consultant Cardiologist')
  const [newStaffDepartment, setNewStaffDepartment] = useState('Cardiology')
  const [newStaffHospitalId, setNewStaffHospitalId] = useState('hospital-1')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Network Controls state
  const [isRotatingKeys, setIsRotatingKeys] = useState(false)
  const [keyRotationResult, setKeyRotationResult] = useState<string | null>(null)
  const [auditStatus, setAuditStatus] = useState<{ ok: boolean; checked: number } | null>(null)
  const [isVerifyingAudit, setIsVerifyingAudit] = useState(false)
  const [auditLogs, setAuditLogs] = useState<any[]>([])
  const [networkOverview, setNetworkOverview] = useState<any>(null)

  // Load initial data
  useEffect(() => {
    const auth = getAuthUser()
    setCurrentUser(auth)
    refreshStaff()
    loadNetworkData()
  }, [])

  const refreshStaff = () => {
    const users = getHospitalUsers()
    setStaff(users)
  }

  const loadNetworkData = async () => {
    try {
      const overview = await fetchAdminNetworkOverview()
      setNetworkOverview(overview)
      const logs = await fetchNetworkAuditLogs()
      setAuditLogs(logs)
    } catch {}
  }

  const showNotification = (type: 'success' | 'error' | 'info', message: string) => {
    setActionFeedback({ type, message })
    setTimeout(() => {
      setActionFeedback(null)
    }, 4500)
  }

  // Filter staff
  const filteredStaff = staff.filter((u) => {
    const matchesHospital = selectedHospitalId === 'all' || u.hospitalId === selectedHospitalId
    const matchesType = staffFilter === 'all' || u.staffType === staffFilter
    const query = searchQuery.toLowerCase().trim()
    const matchesSearch =
      !query ||
      u.name.toLowerCase().includes(query) ||
      u.username.toLowerCase().includes(query) ||
      u.department.toLowerCase().includes(query) ||
      u.role.toLowerCase().includes(query)
    return matchesHospital && matchesType && matchesSearch
  })

  // Quick stats
  const totalDoctors = staff.filter((u) => u.staffType === 'doctor').length
  const totalWorkers = staff.filter((u) => u.staffType === 'worker').length
  const totalAdmins = staff.filter((u) => u.staffType === 'admin').length

  // Handle adding user
  const handleAddUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newStaffName.trim() || !newStaffUsername.trim()) {
      showNotification('error', 'Please provide a valid full name and username.')
      return
    }

    setIsSubmitting(true)
    try {
      const created = await addHospitalUser({
        name: newStaffName,
        username: newStaffUsername,
        password: newStaffPassword,
        role: newStaffRole,
        department: newStaffDepartment,
        staffType: newStaffType,
        hospitalId: newStaffHospitalId,
      })
      refreshStaff()
      setIsAddModalOpen(false)
      // Reset form
      setNewStaffName('')
      setNewStaffUsername('')
      setNewStaffPassword('bioqshield2026')
      showNotification(
        'success',
        `Successfully added ${newStaffType === 'doctor' ? 'Doctor' : 'Healthcare Worker'} "${created.name}" (@${created.username}) to ${created.hospitalName}.`
      )
    } catch (err: any) {
      showNotification('error', err.message || 'Failed to add user.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle removing user
  const handleConfirmDelete = async () => {
    if (!userToDelete) return
    try {
      await removeHospitalUser(userToDelete.username)
      refreshStaff()
      showNotification('success', `Removed ${userToDelete.name} (@${userToDelete.username}) from hospital network.`)
      setIsDeleteModalOpen(false)
      setUserToDelete(null)
    } catch (err: any) {
      showNotification('error', err.message || 'Failed to remove user.')
    }
  }

  // Handle disabling / enabling user
  const handleToggleDisabled = async (targetUser: HospitalUser) => {
    try {
      const nextDisabled = !targetUser.disabled
      await toggleHospitalUserDisabled(targetUser.username, nextDisabled)
      refreshStaff()
      showNotification(
        'info',
        `Account for ${targetUser.name} has been ${nextDisabled ? 'temporarily disabled' : 're-activated'}.`
      )
    } catch (err: any) {
      showNotification('error', err.message || 'Action failed.')
    }
  }

  // Handle switching to user session (testing)
  const handleSwitchToUser = (targetUser: HospitalUser) => {
    setAuthUser({
      name: targetUser.name,
      username: targetUser.username,
      role: targetUser.role,
      department: targetUser.department,
      hospital: targetUser.hospitalName,
      hospitalId: targetUser.hospitalId,
      branch: targetUser.branch,
      nodeId: targetUser.hospitalId === 'hospital-1' ? 'AQ-CHN-01' : 'FT-CHN-02',
      initials: targetUser.initials,
      isLoggedIn: true,
    })
    showNotification('success', `Switched active session to ${targetUser.name} (${targetUser.role}).`)
    setTimeout(() => {
      window.location.href = '/dashboard/'
    }, 800)
  }

  // Handle emergency quantum key rotation
  const handleRotateKeys = async () => {
    setIsRotatingKeys(true)
    try {
      const res = await rotateNetworkKeys()
      setKeyRotationResult(res.message)
      showNotification('success', res.message)
      await loadNetworkData()
    } catch (err: any) {
      showNotification('error', 'Key rotation failed: ' + err.message)
    } finally {
      setIsRotatingKeys(false)
      setIsRotateModalOpen(false)
    }
  }

  // Handle audit verification
  const handleVerifyAudit = async () => {
    setIsVerifyingAudit(true)
    try {
      const res = await verifyNetworkAudit()
      setAuditStatus(res)
      showNotification('success', `Cryptographic Audit Chain verified: ${res.checked} entries validated without tamper.`)
    } catch (err: any) {
      showNotification('error', 'Audit verification failed: ' + err.message)
    } finally {
      setIsVerifyingAudit(false)
    }
  }

  // Role recommendations when changing staff type
  const handleTypeChange = (type: StaffType) => {
    setNewStaffType(type)
    if (type === 'doctor') {
      setNewStaffRole('Consultant Cardiologist')
      setNewStaffDepartment('Cardiology')
    } else if (type === 'worker') {
      setNewStaffRole('Senior ICU Specialist Nurse')
      setNewStaffDepartment('Critical Care')
    } else if (type === 'admin') {
      setNewStaffRole('Quantum Security Administrator')
      setNewStaffDepartment('Quantum IT & Network Governance')
    } else {
      setNewStaffRole('Compliance & Cryptographic Auditor')
      setNewStaffDepartment('Security Compliance')
    }
  }

  return (
    <AppShell>
      <main className="mx-auto max-w-[1240px] px-6 py-8 md:px-10 md:py-10">
        {/* ── Top Feedback Toast ─────────────────────────────────────── */}
        {actionFeedback && (
          <div
            className={`fixed top-6 right-6 z-50 flex items-center gap-3 rounded-2xl border px-5 py-3.5 shadow-xl transition-all duration-300 animate-in fade-in slide-in-from-top-4 ${
              actionFeedback.type === 'success'
                ? 'border-[#22C55E]/30 bg-[#0F291E] text-[#86EFAC]'
                : actionFeedback.type === 'error'
                ? 'border-[#EF4444]/30 bg-[#2E1214] text-[#FCA5A5]'
                : 'border-[#38BDF8]/30 bg-[#0C2438] text-[#7DD3FC]'
            }`}
          >
            {actionFeedback.type === 'success' && <CheckCircle2 className="size-5 shrink-0 text-[#4ADE80]" />}
            {actionFeedback.type === 'error' && <AlertTriangle className="size-5 shrink-0 text-[#F87171]" />}
            {actionFeedback.type === 'info' && <Sparkles className="size-5 shrink-0 text-[#38BDF8]" />}
            <span className="text-[13px] font-medium leading-tight">{actionFeedback.message}</span>
          </div>
        )}

        {/* ── Page Header & System Admin Beacon ──────────────────────── */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="flex items-center gap-1.5 rounded-full border border-[#22C55E]/30 bg-[#22C55E]/10 px-3 py-1 text-[11px] font-semibold text-[#198657] dark:text-[#86EFAC]">
                <span className="size-2 rounded-full bg-[#22C55E] animate-pulse" />
                System Administrator Privileges Active
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-[#64748B] dark:text-[#94A3B8]">
                Hospital Network Governance
              </span>
            </div>
            <h1 className="mt-2.5 text-[32px] font-extrabold tracking-[-0.03em] text-[#0B2545] dark:text-white">
              Hospital Network Command & Workforce Administration
            </h1>
            <p className="mt-1 text-[14px] text-[#58718D] dark:text-[#9AAABD]">
              Full administrative oversight to add or remove doctors and healthcare workers, govern quantum keys, configure network nodes, and audit hospital operations.
            </p>
          </div>

          {/* Quick Header Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setIsRotateModalOpen(true)}
              className="flex items-center gap-2 rounded-xl border border-[#EF4444]/30 bg-[#EF4444]/10 px-4 py-2.5 text-[12px] font-semibold text-[#DC2626] dark:text-[#F87171] hover:bg-[#EF4444]/20 transition-all cursor-pointer shadow-xs"
            >
              <RotateCcw className="size-3.5" />
              Emergency Key Rotation
            </button>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="flex items-center gap-2 rounded-xl bg-[#2563EB] px-4 py-2.5 text-[12px] font-semibold text-white hover:bg-[#1D4ED8] transition-all cursor-pointer shadow-md hover:shadow-lg"
            >
              <UserPlus className="size-4" />
              Add Doctor or Worker
            </button>
          </div>
        </div>

        {/* ── Network Summary Cards ──────────────────────────────────── */}
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748B] dark:text-[#9AAABD]">
                Doctors & Specialists
              </span>
              <div className="flex size-8 items-center justify-center rounded-xl bg-[#2563EB]/10 text-[#2563EB] dark:text-[#60A5FA]">
                <Stethoscope className="size-4" />
              </div>
            </div>
            <div className="mt-3 text-[28px] font-extrabold text-[#0B2545] dark:text-white">
              {totalDoctors}
            </div>
            <p className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
              Authorized clinical practitioners with record transfer privileges
            </p>
          </div>

          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748B] dark:text-[#9AAABD]">
                Healthcare Workers & Nurses
              </span>
              <div className="flex size-8 items-center justify-center rounded-xl bg-[#14B8A6]/10 text-[#14B8A6] dark:text-[#2DD4BF]">
                <HeartPulse className="size-4" />
              </div>
            </div>
            <div className="mt-3 text-[28px] font-extrabold text-[#0B2545] dark:text-white">
              {totalWorkers}
            </div>
            <p className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
              Active ICU nurses, lab technologists & clinical staff
            </p>
          </div>

          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748B] dark:text-[#9AAABD]">
                Quantum Key Pool
              </span>
              <div className="flex size-8 items-center justify-center rounded-xl bg-[#8B5CF6]/10 text-[#8B5CF6] dark:text-[#A78BFA]">
                <KeyRound className="size-4" />
              </div>
            </div>
            <div className="mt-3 text-[28px] font-extrabold text-[#0B2545] dark:text-white">
              {networkOverview?.pool?.available || 48} keys
            </div>
            <p className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
              BB84 256-bit AES OTP keys · Auto zeroised on use
            </p>
          </div>

          <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-5 shadow-[0_3px_12px_rgba(18,52,91,0.035)]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748B] dark:text-[#9AAABD]">
                Audit Integrity
              </span>
              <div className="flex size-8 items-center justify-center rounded-xl bg-[#10B981]/10 text-[#10B981] dark:text-[#34D399]">
                <ShieldCheck className="size-4" />
              </div>
            </div>
            <div className="mt-3 text-[28px] font-extrabold text-[#198657] dark:text-[#86EFAC]">
              {auditStatus?.ok !== false ? 'Verified' : 'Review'}
            </div>
            <p className="mt-1 text-[11px] text-[#64748B] dark:text-[#9AAABD]">
              SHA-256 cryptographic chain · Tamper-proof
            </p>
          </div>
        </div>

        {/* ── Main Navigation Tabs ───────────────────────────────────── */}
        <div className="mt-8 flex border-b border-[#D9E2EC] dark:border-white/10">
          <button
            onClick={() => setActiveTab('staff')}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-[14px] font-semibold transition-all cursor-pointer ${
              activeTab === 'staff'
                ? 'border-[#2563EB] text-[#2563EB] dark:border-[#60A5FA] dark:text-[#60A5FA]'
                : 'border-transparent text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white'
            }`}
          >
            <Users className="size-4" />
            Workers & Doctors Directory ({staff.length})
          </button>
          <button
            onClick={() => setActiveTab('network')}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-[14px] font-semibold transition-all cursor-pointer ${
              activeTab === 'network'
                ? 'border-[#2563EB] text-[#2563EB] dark:border-[#60A5FA] dark:text-[#60A5FA]'
                : 'border-transparent text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white'
            }`}
          >
            <Server className="size-4" />
            Hospital Network Nodes & Keys
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-[14px] font-semibold transition-all cursor-pointer ${
              activeTab === 'audit'
                ? 'border-[#2563EB] text-[#2563EB] dark:border-[#60A5FA] dark:text-[#60A5FA]'
                : 'border-transparent text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white'
            }`}
          >
            <FileText className="size-4" />
            Cryptographic Audit Chain
          </button>
          <button
            onClick={() => setActiveTab('policies')}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-[14px] font-semibold transition-all cursor-pointer ${
              activeTab === 'policies'
                ? 'border-[#2563EB] text-[#2563EB] dark:border-[#60A5FA] dark:text-[#60A5FA]'
                : 'border-transparent text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white'
            }`}
          >
            <Sliders className="size-4" />
            Security & QKD Policies
          </button>
        </div>

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── TAB 1: STAFF & WORKFORCE DIRECTORY ──────────────────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'staff' && (
          <div className="mt-6 space-y-6">
            {/* Filters & Search Bar */}
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-4 shadow-xs">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-[#9AAABD]" />
                <input
                  type="text"
                  placeholder="Search doctors, nurses, workers, usernames..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 pl-10 pr-4 py-2 text-[13px] text-[#0B2545] dark:text-white placeholder-[#9AAABD] focus:border-[#2563EB] focus:outline-none"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Hospital Node Filter */}
                <select
                  value={selectedHospitalId}
                  onChange={(e) => setSelectedHospitalId(e.target.value)}
                  className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3 py-2 text-[12px] font-semibold text-[#0B2545] dark:text-white focus:outline-none"
                >
                  <option value="all">All Hospital Nodes</option>
                  {HOSPITALS.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name} ({h.nodeId})
                    </option>
                  ))}
                </select>

                {/* Staff Type Pill Filters */}
                <div className="flex rounded-xl border border-[#D9E2EC] dark:border-white/10 p-0.5 bg-[#F8FAFC] dark:bg-white/5">
                  <button
                    onClick={() => setStaffFilter('all')}
                    className={`rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition cursor-pointer ${
                      staffFilter === 'all'
                        ? 'bg-white dark:bg-white/20 text-[#0B2545] dark:text-white shadow-xs'
                        : 'text-[#64748B] dark:text-[#9AAABD]'
                    }`}
                  >
                    All ({staff.length})
                  </button>
                  <button
                    onClick={() => setStaffFilter('doctor')}
                    className={`rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition cursor-pointer ${
                      staffFilter === 'doctor'
                        ? 'bg-white dark:bg-white/20 text-[#2563EB] dark:text-[#60A5FA] shadow-xs'
                        : 'text-[#64748B] dark:text-[#9AAABD]'
                    }`}
                  >
                    Doctors ({totalDoctors})
                  </button>
                  <button
                    onClick={() => setStaffFilter('worker')}
                    className={`rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition cursor-pointer ${
                      staffFilter === 'worker'
                        ? 'bg-white dark:bg-white/20 text-[#14B8A6] dark:text-[#2DD4BF] shadow-xs'
                        : 'text-[#64748B] dark:text-[#9AAABD]'
                    }`}
                  >
                    Workers ({totalWorkers})
                  </button>
                  <button
                    onClick={() => setStaffFilter('admin')}
                    className={`rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition cursor-pointer ${
                      staffFilter === 'admin'
                        ? 'bg-white dark:bg-white/20 text-[#8B5CF6] dark:text-[#A78BFA] shadow-xs'
                        : 'text-[#64748B] dark:text-[#9AAABD]'
                    }`}
                  >
                    Admins ({totalAdmins})
                  </button>
                </div>
              </div>
            </div>

            {/* Staff Table / Cards */}
            <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/[0.02] text-[11px] font-bold uppercase tracking-[0.08em] text-[#64748B] dark:text-[#8FA6BF]">
                      <th className="px-6 py-4">Staff Member & Credentials</th>
                      <th className="px-6 py-4">Classification</th>
                      <th className="px-6 py-4">Department</th>
                      <th className="px-6 py-4">Assigned Node</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Administrative Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D9E2EC] dark:divide-white/5 text-[13px]">
                    {filteredStaff.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-12 text-center text-[#64748B] dark:text-[#9AAABD]">
                          No staff found matching the selected filter criteria.
                        </td>
                      </tr>
                    ) : (
                      filteredStaff.map((u) => {
                        const isSelf = currentUser?.username === u.username
                        return (
                          <tr
                            key={u.username + u.hospitalId}
                            className={`hover:bg-[#F8FAFC] dark:hover:bg-white/[0.02] transition-colors ${
                              u.disabled ? 'opacity-60 bg-red-500/[0.02]' : ''
                            }`}
                          >
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div
                                  className={`flex size-10 shrink-0 items-center justify-center rounded-xl font-bold text-[13px] ${
                                    u.staffType === 'doctor'
                                      ? 'bg-[#2563EB]/15 text-[#2563EB] dark:text-[#60A5FA]'
                                      : u.staffType === 'worker'
                                      ? 'bg-[#14B8A6]/15 text-[#14B8A6] dark:text-[#2DD4BF]'
                                      : u.staffType === 'admin'
                                      ? 'bg-[#8B5CF6]/15 text-[#8B5CF6] dark:text-[#A78BFA]'
                                      : 'bg-[#F59E0B]/15 text-[#D97706] dark:text-[#FBBF24]'
                                  }`}
                                >
                                  {u.initials}
                                </div>
                                <div>
                                  <div className="font-semibold text-[#0B2545] dark:text-white flex items-center gap-1.5">
                                    {u.name}
                                    {isSelf && (
                                      <span className="rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[10px] px-1.5 py-0.5 font-bold">
                                        You
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD] font-mono">
                                    @{u.username}
                                  </div>
                                </div>
                              </div>
                            </td>

                            <td className="px-6 py-4">
                              <span
                                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                                  u.staffType === 'doctor'
                                    ? 'bg-[#2563EB]/10 text-[#2563EB] dark:text-[#60A5FA]'
                                    : u.staffType === 'worker'
                                    ? 'bg-[#14B8A6]/10 text-[#14B8A6] dark:text-[#2DD4BF]'
                                    : u.staffType === 'admin'
                                    ? 'bg-[#8B5CF6]/10 text-[#8B5CF6] dark:text-[#A78BFA]'
                                    : 'bg-[#F59E0B]/10 text-[#D97706] dark:text-[#FBBF24]'
                                }`}
                              >
                                {u.staffType === 'doctor' && <Stethoscope className="size-3" />}
                                {u.staffType === 'worker' && <HeartPulse className="size-3" />}
                                {u.staffType === 'admin' && <ShieldCheck className="size-3" />}
                                {u.role}
                              </span>
                            </td>

                            <td className="px-6 py-4 text-[#58718D] dark:text-[#CBD5E1]">
                              {u.department}
                            </td>

                            <td className="px-6 py-4">
                              <div className="text-[12px] font-medium text-[#0B2545] dark:text-white">
                                {u.hospitalName}
                              </div>
                              <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD]">
                                {u.branch}
                              </div>
                            </td>

                            <td className="px-6 py-4">
                              {u.disabled ? (
                                <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[11px] font-semibold text-red-600 dark:text-red-400">
                                  <XCircle className="size-3" />
                                  Disabled
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                                  <CheckCircle2 className="size-3" />
                                  Active
                                </span>
                              )}
                            </td>

                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end gap-2">
                                {/* Switch Identity button */}
                                <button
                                  onClick={() => handleSwitchToUser(u)}
                                  title="Test login as this user"
                                  className="rounded-lg border border-[#D9E2EC] dark:border-white/10 px-2.5 py-1 text-[11px] font-medium text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white hover:bg-[#F1F5F9] dark:hover:bg-white/10 transition cursor-pointer"
                                >
                                  Switch User
                                </button>

                                {/* Disable / Enable toggle */}
                                {!isSelf && u.username !== 'admin' && (
                                  <button
                                    onClick={() => handleToggleDisabled(u)}
                                    title={u.disabled ? 'Re-enable account' : 'Temporarily disable account'}
                                    className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition cursor-pointer ${
                                      u.disabled
                                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20'
                                        : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20'
                                    }`}
                                  >
                                    {u.disabled ? 'Enable' : 'Disable'}
                                  </button>
                                )}

                                {/* Remove Button */}
                                {!isSelf && u.username !== 'admin' && (
                                  <button
                                    onClick={() => {
                                      setUserToDelete(u)
                                      setIsDeleteModalOpen(true)
                                    }}
                                    title="Permanently remove worker or doctor from network"
                                    className="flex items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-[11px] font-semibold text-red-600 dark:text-red-400 hover:bg-red-500/20 transition cursor-pointer"
                                  >
                                    <Trash2 className="size-3" />
                                    Remove
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── TAB 2: NETWORK NODES & QUANTUM KEY GOVERNANCE ──────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'network' && (
          <div className="mt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Apollo Hospital Node */}
              <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-[#2563EB]/15 text-[#2563EB] dark:text-[#60A5FA]">
                      <Server className="size-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-[#0B2545] dark:text-white">
                        Apollo Hospital Network Node (AQ-CHN-01)
                      </h3>
                      <p className="text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                        Alice Transmitter Node · Chennai Main Hub
                      </p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                    <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Online
                  </span>
                </div>

                <div className="mt-5 space-y-3 text-[12px]">
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">QKD Protocol Engine:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Qiskit Aer BB84 Simulator</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Node Clearance Role:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">alice (Key Generator & Sender)</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Key Buffer Allocation:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">4,096 bit pool / AES-256 OTP</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Hardware KME Interface:</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">ETSI GS QKD 014 Ready</span>
                  </div>
                </div>
              </div>

              {/* Fortis Hospital Node */}
              <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-[#14B8A6]/15 text-[#14B8A6] dark:text-[#2DD4BF]">
                      <Server className="size-5" />
                    </div>
                    <div>
                      <h3 className="font-bold text-[#0B2545] dark:text-white">
                        Fortis Hospital Network Node (FT-CHN-02)
                      </h3>
                      <p className="text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                        Bob Receiver Node · Chennai Main Hub
                      </p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                    <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Online
                  </span>
                </div>

                <div className="mt-5 space-y-3 text-[12px]">
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">QKD Protocol Engine:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Measurement Basis Reconciliation</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Node Clearance Role:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">bob (Receiver & Decryptor)</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Encrypted Inbox Verification:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Zero-Knowledge Sealed at Rest</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Peer Link Latency:</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">1.8 ms (Local Quantum Fiber)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quantum Key Governance Controls */}
            <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-xs">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#D9E2EC] dark:border-white/10 pb-5">
                <div>
                  <h3 className="text-[17px] font-bold text-[#0B2545] dark:text-white flex items-center gap-2">
                    <KeyRound className="size-5 text-[#8B5CF6]" />
                    Quantum Key Zeroisation & Emergency Key Pool Governance
                  </h3>
                  <p className="mt-1 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
                    As System Administrator, you can zeroise all active encryption keys across both hospitals if an optical tap, tampering attempt, or Eve eavesdropping is detected.
                  </p>
                </div>
                <button
                  onClick={() => setIsRotateModalOpen(true)}
                  disabled={isRotatingKeys}
                  className="flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-[13px] font-bold text-white hover:bg-red-700 transition cursor-pointer shadow-md disabled:opacity-50"
                >
                  <RotateCcw className={`size-4 ${isRotatingKeys ? 'animate-spin' : ''}`} />
                  {isRotatingKeys ? 'Zeroising Keys...' : 'Rotate All Quantum Keys'}
                </button>
              </div>

              <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/[0.02] p-4">
                  <div className="text-[11px] font-semibold text-[#64748B] dark:text-[#9AAABD] uppercase">
                    Key Material Security Rule
                  </div>
                  <p className="mt-2 text-[12px] text-[#0B2545] dark:text-white leading-relaxed">
                    Raw quantum keys are never exposed in transit or stored plaintext. Keys are strictly consumed once per biomedical transfer.
                  </p>
                </div>

                <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/[0.02] p-4">
                  <div className="text-[11px] font-semibold text-[#64748B] dark:text-[#9AAABD] uppercase">
                    QBER Abort Boundary
                  </div>
                  <p className="mt-2 text-[12px] text-[#0B2545] dark:text-white leading-relaxed">
                    Sifting automatically halts if Quantum Bit Error Rate exceeds 11.0%, guaranteeing information-theoretic safety against eavesdroppers.
                  </p>
                </div>

                <div className="rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/[0.02] p-4">
                  <div className="text-[11px] font-semibold text-[#64748B] dark:text-[#9AAABD] uppercase">
                    ETSI & HIPAA Compliance
                  </div>
                  <p className="mt-2 text-[12px] text-[#0B2545] dark:text-white leading-relaxed">
                    Full compliance with ETSI GS QKD 014 and DISHA / HIPAA patient record confidentiality protocols.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── TAB 3: CRYPTOGRAPHIC AUDIT CHAIN ────────────────────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'audit' && (
          <div className="mt-6 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-xs">
              <div>
                <h3 className="text-[18px] font-bold text-[#0B2545] dark:text-white flex items-center gap-2">
                  <ShieldCheck className="size-5 text-emerald-500" />
                  SHA-256 Chained Ledger Verification
                </h3>
                <p className="mt-1 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
                  Every login, user addition, user deletion, key rotation, and biomedical transfer is appended to a tamper-proof cryptographic chain.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleVerifyAudit}
                  disabled={isVerifyingAudit}
                  className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-[12px] font-semibold text-white hover:bg-emerald-700 transition cursor-pointer shadow-sm disabled:opacity-50"
                >
                  <RefreshCw className={`size-4 ${isVerifyingAudit ? 'animate-spin' : ''}`} />
                  {isVerifyingAudit ? 'Verifying Chain...' : 'Verify Audit Chain Now'}
                </button>
              </div>
            </div>

            {/* Audit Log Stream */}
            <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] overflow-hidden shadow-xs">
              <div className="px-6 py-4 border-b border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/[0.02]">
                <h4 className="text-[13px] font-bold uppercase tracking-wider text-[#0B2545] dark:text-white">
                  Recent Administrative & Security Audit Trail
                </h4>
              </div>
              <div className="divide-y divide-[#D9E2EC] dark:divide-white/5">
                {auditLogs.map((log) => (
                  <div key={log.id} className="p-4 flex items-start justify-between gap-4 hover:bg-white/[0.02]">
                    <div className="flex items-start gap-3">
                      <div className="mt-1 flex size-7 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                        <FileText className="size-4" />
                      </div>
                      <div>
                        <div className="text-[13px] font-bold text-[#0B2545] dark:text-white">
                          Event: <span className="font-mono text-blue-500">{log.event}</span>
                        </div>
                        <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD] mt-0.5">
                          Actor: <span className="font-semibold text-emerald-500">{log.actor}</span> · {new Date(log.ts * 1000).toLocaleTimeString()}
                        </div>
                        <div className="mt-1 text-[11px] font-mono bg-black/5 dark:bg-white/5 px-2 py-1 rounded text-[#58718D] dark:text-[#CBD5E1]">
                          {JSON.stringify(log.detail)}
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-[#9AAABD]">ID: #{log.id}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── TAB 4: SECURITY & QKD POLICIES ─────────────────────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'policies' && (
          <div className="mt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-xs">
                <h3 className="font-bold text-[16px] text-[#0B2545] dark:text-white flex items-center gap-2">
                  <Sliders className="size-5 text-[#2563EB]" />
                  NSL-KDD Threat Classifier Policy
                </h3>
                <p className="mt-1 text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                  Machine learning model supervising incoming network traffic
                </p>

                <div className="mt-5 space-y-4">
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3.5">
                    <div className="font-semibold text-[12px] text-emerald-600 dark:text-emerald-400">
                      Accept Threshold: &lt; 0.35 Score
                    </div>
                    <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD] mt-0.5">
                      Normal medical data packet flow; immediate transfer permitted.
                    </div>
                  </div>

                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5">
                    <div className="font-semibold text-[12px] text-amber-600 dark:text-amber-400">
                      Adaptive Inspection: 0.35 - 0.70 Score
                    </div>
                    <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD] mt-0.5">
                      Triggers active eavesdropping probe and packet header verification.
                    </div>
                  </div>

                  <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3.5">
                    <div className="font-semibold text-[12px] text-red-600 dark:text-red-400">
                      Rejection Limit: &ge; 0.70 Score
                    </div>
                    <div className="text-[11px] text-[#64748B] dark:text-[#9AAABD] mt-0.5">
                      Transfer blocked automatically; security alert generated.
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-xs">
                <h3 className="font-bold text-[16px] text-[#0B2545] dark:text-white flex items-center gap-2">
                  <Radio className="size-5 text-[#14B8A6]" />
                  Quantum Optical Channel Specifications
                </h3>
                <p className="mt-1 text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                  BB84 fiber link operational configuration
                </p>

                <div className="mt-5 space-y-3 text-[12px]">
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Photon Emission:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Weak Coherent Pulse (Poissonian)</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Polarization Bases:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Rectilinear (Z) + Diagonal (X)</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Error Correction:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Interactive Cascade Protocol</span>
                  </div>
                  <div className="flex justify-between border-b border-[#D9E2EC]/50 dark:border-white/5 pb-2">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Privacy Amplification:</span>
                    <span className="font-semibold text-[#0B2545] dark:text-white">Toeplitz Matrix Universal Hashing</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748B] dark:text-[#9AAABD]">Cryptographic Cipher:</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">AES-256-GCM One-Time-Pad</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL: ADD DOCTOR OR HEALTHCARE WORKER ─────────────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {isAddModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
            <div className="w-full max-w-[560px] rounded-3xl border border-[#D9E2EC] dark:border-white/10 bg-white dark:bg-[#0B1726] p-6 shadow-2xl animate-in zoom-in-95 duration-200">
              <div className="flex items-center justify-between border-b border-[#D9E2EC] dark:border-white/10 pb-4">
                <div>
                  <h3 className="text-[18px] font-bold text-[#0B2545] dark:text-white flex items-center gap-2">
                    <UserPlus className="size-5 text-[#2563EB]" />
                    Add Doctor or Healthcare Worker
                  </h3>
                  <p className="text-[12px] text-[#64748B] dark:text-[#9AAABD]">
                    Authorize a new clinical practitioner or hospital staff member
                  </p>
                </div>
                <button
                  onClick={() => setIsAddModalOpen(false)}
                  className="rounded-full p-1.5 text-[#9AAABD] hover:bg-black/5 dark:hover:bg-white/10 cursor-pointer"
                >
                  <XCircle className="size-5" />
                </button>
              </div>

              <form onSubmit={handleAddUserSubmit} className="mt-5 space-y-4">
                {/* Staff Type Selector */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1.5">
                    Staff Classification *
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {(['doctor', 'worker', 'admin', 'auditor'] as StaffType[]).map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => handleTypeChange(type)}
                        className={`rounded-xl border p-2.5 text-center text-[12px] font-semibold transition cursor-pointer capitalize ${
                          newStaffType === type
                            ? 'border-[#2563EB] bg-[#2563EB]/10 text-[#2563EB] dark:border-[#60A5FA] dark:text-[#60A5FA]'
                            : 'border-[#D9E2EC] dark:border-white/10 text-[#64748B] dark:text-[#9AAABD] hover:bg-black/5 dark:hover:bg-white/5'
                        }`}
                      >
                        {type === 'doctor' && 'Doctor / Clinician'}
                        {type === 'worker' && 'Healthcare Worker'}
                        {type === 'admin' && 'Admin'}
                        {type === 'auditor' && 'Auditor'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Full Name */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1">
                    Full Legal Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder={newStaffType === 'doctor' ? 'e.g. Dr. Ananya Roy' : 'e.g. Nurse Vikram Mehta'}
                    value={newStaffName}
                    onChange={(e) => {
                      setNewStaffName(e.target.value)
                      // Auto suggest username
                      if (!newStaffUsername) {
                        const clean = e.target.value
                          .toLowerCase()
                          .replace(/^dr\.\s*/i, 'dr.')
                          .replace(/\s+/g, '.')
                          .replace(/[^a-z0-9._-]/g, '')
                        setNewStaffUsername(clean)
                      }
                    }}
                    className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3.5 py-2 text-[13px] text-[#0B2545] dark:text-white focus:border-[#2563EB] focus:outline-none"
                  />
                </div>

                {/* Username */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1">
                    System Username *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. dr.ananya.roy or nurse.vikram"
                    value={newStaffUsername}
                    onChange={(e) => setNewStaffUsername(e.target.value.toLowerCase().replace(/[^a-z0-9._-]/g, ''))}
                    className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3.5 py-2 text-[13px] font-mono text-[#0B2545] dark:text-white focus:border-[#2563EB] focus:outline-none"
                  />
                </div>

                {/* Password */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1">
                    Initial Credentials (Password) *
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={newStaffPassword}
                      onChange={(e) => setNewStaffPassword(e.target.value)}
                      className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 pl-3.5 pr-10 py-2 text-[13px] font-mono text-[#0B2545] dark:text-white focus:border-[#2563EB] focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Title / Role */}
                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1">
                      Professional Role Title *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Consultant Cardiologist"
                      value={newStaffRole}
                      onChange={(e) => setNewStaffRole(e.target.value)}
                      className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3.5 py-2 text-[13px] text-[#0B2545] dark:text-white focus:border-[#2563EB] focus:outline-none"
                    />
                  </div>

                  {/* Department */}
                  <div>
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1">
                      Department *
                    </label>
                    <select
                      value={newStaffDepartment}
                      onChange={(e) => setNewStaffDepartment(e.target.value)}
                      className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3.5 py-2 text-[13px] text-[#0B2545] dark:text-white focus:outline-none"
                    >
                      <option value="Cardiology">Cardiology</option>
                      <option value="Neurology">Neurology</option>
                      <option value="Critical Care">Critical Care / ICU</option>
                      <option value="Oncology">Oncology</option>
                      <option value="Radiology">Radiology</option>
                      <option value="Emergency Medicine">Emergency Medicine</option>
                      <option value="Pathology & Diagnostic Lab">Pathology & Lab</option>
                      <option value="Internal Medicine">Internal Medicine</option>
                      <option value="Quantum IT & Network Governance">Quantum IT & Security</option>
                    </select>
                  </div>
                </div>

                {/* Assigned Hospital */}
                <div>
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-[#64748B] dark:text-[#9AAABD] mb-1">
                    Assigned Hospital Network Node *
                  </label>
                  <select
                    value={newStaffHospitalId}
                    onChange={(e) => setNewStaffHospitalId(e.target.value)}
                    className="w-full rounded-xl border border-[#D9E2EC] dark:border-white/10 bg-[#F8FAFC] dark:bg-white/5 px-3.5 py-2 text-[13px] text-[#0B2545] dark:text-white focus:outline-none"
                  >
                    {HOSPITALS.map((h) => (
                      <option key={h.id} value={h.id}>
                        {h.name} ({h.branch} · {h.nodeId})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Submit Actions */}
                <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-[#D9E2EC] dark:border-white/10">
                  <button
                    type="button"
                    onClick={() => setIsAddModalOpen(false)}
                    className="rounded-xl px-4 py-2 text-[13px] font-medium text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex items-center gap-2 rounded-xl bg-[#2563EB] px-5 py-2 text-[13px] font-semibold text-white hover:bg-[#1D4ED8] transition cursor-pointer disabled:opacity-50"
                  >
                    {isSubmitting ? (
                      <>
                        <RefreshCw className="size-4 animate-spin" /> Adding...
                      </>
                    ) : (
                      <>
                        <UserPlus className="size-4" /> Add to Hospital Directory
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL: CONFIRM REMOVE STAFF MEMBER ─────────────────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {isDeleteModalOpen && userToDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
            <div className="w-full max-w-[440px] rounded-3xl border border-red-500/30 bg-white dark:bg-[#0B1726] p-6 shadow-2xl animate-in zoom-in-95 duration-200">
              <div className="flex size-12 items-center justify-center rounded-2xl bg-red-500/10 text-red-500 mx-auto">
                <Trash2 className="size-6" />
              </div>

              <div className="text-center mt-4">
                <h3 className="text-[18px] font-bold text-[#0B2545] dark:text-white">
                  Remove Staff Member
                </h3>
                <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
                  Are you sure you want to permanently revoke credentials and remove{' '}
                  <span className="font-semibold text-[#0B2545] dark:text-white">
                    {userToDelete.name} (@{userToDelete.username})
                  </span>{' '}
                  from the hospital network?
                </p>
                <div className="mt-3 rounded-xl bg-red-500/5 border border-red-500/15 p-2.5 text-[11px] text-red-600 dark:text-red-400">
                  This user will no longer be able to log in or initiate/receive medical transfers.
                </div>
              </div>

              <div className="mt-6 flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsDeleteModalOpen(false)
                    setUserToDelete(null)
                  }}
                  className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-4 py-2 text-[13px] font-medium text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  className="rounded-xl bg-red-600 px-5 py-2 text-[13px] font-semibold text-white hover:bg-red-700 transition cursor-pointer shadow-md"
                >
                  Yes, Remove User
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* ── MODAL: CONFIRM KEY ROTATION ────────────────────────────── */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {isRotateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
            <div className="w-full max-w-[460px] rounded-3xl border border-red-500/30 bg-white dark:bg-[#0B1726] p-6 shadow-2xl animate-in zoom-in-95 duration-200">
              <div className="flex size-12 items-center justify-center rounded-2xl bg-red-500/10 text-red-500 mx-auto">
                <AlertTriangle className="size-6" />
              </div>

              <div className="text-center mt-4">
                <h3 className="text-[18px] font-bold text-[#0B2545] dark:text-white">
                  Execute Quantum Key Rotation?
                </h3>
                <p className="mt-2 text-[13px] text-[#64748B] dark:text-[#9AAABD]">
                  This command immediately zeroises all available BB84 quantum keys on both Hospital A and Hospital B nodes. Unsent drafts will require fresh key distribution.
                </p>
                <div className="mt-3 rounded-xl bg-amber-500/10 border border-amber-500/20 p-2.5 text-[11px] text-amber-700 dark:text-amber-300">
                  Recommended after detected tampering, optical signal noise spike, or suspect eavesdropping attempts.
                </div>
              </div>

              <div className="mt-6 flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsRotateModalOpen(false)}
                  className="rounded-xl border border-[#D9E2EC] dark:border-white/10 px-4 py-2 text-[13px] font-medium text-[#64748B] dark:text-[#9AAABD] hover:text-[#0B2545] dark:hover:text-white cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleRotateKeys}
                  disabled={isRotatingKeys}
                  className="flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2 text-[13px] font-semibold text-white hover:bg-red-700 transition cursor-pointer shadow-md disabled:opacity-50"
                >
                  {isRotatingKeys ? 'Zeroising...' : 'Confirm Key Rotation'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </AppShell>
  )
}
