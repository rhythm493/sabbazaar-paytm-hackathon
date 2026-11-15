import { clsx } from 'clsx'

type Variant = 'draft' | 'approved' | 'publishing' | 'live' | 'failed' | 'paused' | 'queued' | 'blocked' | 'pending' | 'processing' | 'completed' | 'rejected' | 'fixture'

const VARIANT_STYLES: Record<Variant, string> = {
  draft:      'bg-yellow-100 text-yellow-800 border-yellow-200',
  pending:    'bg-yellow-100 text-yellow-800 border-yellow-200',
  processing: 'bg-blue-100 text-blue-800 border-blue-200',
  approved:   'bg-green-100 text-green-800 border-green-200',
  completed:  'bg-green-100 text-green-800 border-green-200',
  publishing: 'bg-blue-100 text-blue-800 border-blue-200',
  queued:     'bg-blue-100 text-blue-800 border-blue-200',
  live:       'bg-emerald-100 text-emerald-800 border-emerald-200',
  failed:     'bg-red-100 text-red-800 border-red-200',
  paused:     'bg-orange-100 text-orange-800 border-orange-200',
  blocked:    'bg-red-100 text-red-800 border-red-200',
  rejected:   'bg-gray-100 text-gray-700 border-gray-200',
  fixture:    'bg-purple-100 text-purple-800 border-purple-200',
}

const VARIANT_LABELS: Record<Variant, string> = {
  draft:      'Draft',
  pending:    'Pending',
  processing: 'Processing',
  approved:   'Approved',
  completed:  'Completed',
  publishing: 'Publishing…',
  queued:     'Queued',
  live:       'Live',
  failed:     'Failed',
  paused:     'Paused',
  blocked:    'Blocked',
  rejected:   'Rejected',
  fixture:    'Fixture (Demo)',
}

interface StatusBadgeProps {
  status: string
  className?: string
  pulse?: boolean
}

export function StatusBadge({ status, className, pulse }: StatusBadgeProps) {
  const v = status as Variant
  const styles = VARIANT_STYLES[v] ?? 'bg-gray-100 text-gray-700 border-gray-200'
  const label = VARIANT_LABELS[v] ?? status

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
        styles,
        className,
      )}
    >
      {pulse && (status === 'publishing' || status === 'processing' || status === 'queued') && (
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      )}
      {label}
    </span>
  )
}
