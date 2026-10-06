import { AppShell } from '@/components/bioqshield'
import { SecureTransferWorkflow } from '@/components/secure-transfer'

export default function SecureTransferPage() {
  return <AppShell><SecureTransferWorkflow /></AppShell>
}

export const metadata = {
  title: 'New Secure Transfer | BioQShield',
  description: 'Select and review biomedical data for a secure transfer to an authorized hospital network.',
}

// The workflow is intentionally client-side for this prototype generation; all records are synthetic demo data.

