import { AppShell } from '@/components/bioqshield'
import { SecurityAnalysisExperience } from '@/components/security-analysis'

export const metadata = {
  title: 'Security Analysis | BioQShield',
  description: 'Quantum and network threat security evaluation for biomedical data transfer.',
}

export default function SecurityAnalysisPage() {
  return (
    <AppShell>
      <SecurityAnalysisExperience />
    </AppShell>
  )
}
