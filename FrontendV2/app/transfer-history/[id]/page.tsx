import { TransferDetailClient } from '@/components/transfer-detail-client'

export function generateStaticParams() {
  return [
    { id: 'BQS-2026-004821' },
    { id: 'BQS-2026-004820' },
    { id: 'BQS-2026-004819' },
    { id: 'BQS-2026-004818' },
    { id: 'BQS-2026-004817' },
  ]
}

export default async function TransferDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  return <TransferDetailClient initialId={id} />
}
