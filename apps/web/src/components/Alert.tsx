import { AlertTriangle, Info, XCircle, CheckCircle, X } from 'lucide-react'
import { clsx } from 'clsx'

type AlertType = 'error' | 'warning' | 'info' | 'success'

const STYLES: Record<AlertType, { container: string; icon: string }> = {
  error:   { container: 'bg-red-50 border-red-300 text-red-800',   icon: 'text-red-500' },
  warning: { container: 'bg-yellow-50 border-yellow-300 text-yellow-800', icon: 'text-yellow-500' },
  info:    { container: 'bg-blue-50 border-blue-300 text-blue-800',  icon: 'text-blue-500' },
  success: { container: 'bg-green-50 border-green-300 text-green-800', icon: 'text-green-500' },
}

const ICONS = {
  error:   XCircle,
  warning: AlertTriangle,
  info:    Info,
  success: CheckCircle,
}

interface AlertProps {
  type: AlertType
  title?: string
  message: string
  onDismiss?: () => void
  className?: string
  action?: React.ReactNode
}

export function Alert({ type, title, message, onDismiss, className, action }: AlertProps) {
  const Icon = ICONS[type]
  const { container, icon } = STYLES[type]

  return (
    <div className={clsx('flex gap-3 rounded-lg border p-4', container, className)}>
      <Icon className={clsx('w-5 h-5 flex-shrink-0 mt-0.5', icon)} />
      <div className="flex-1 min-w-0">
        {title && <p className="font-semibold text-sm mb-0.5">{title}</p>}
        <p className="text-sm leading-relaxed">{message}</p>
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity">
          <X className="w-4 h-4" />
        </button>
      )}
      {action && <div className="flex-shrink-0 self-start">{action}</div>}
    </div>
  )
}

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 px-4 text-center">
      {icon && <div className="text-gray-300">{icon}</div>}
      <h3 className="font-semibold text-gray-700">{title}</h3>
      {description && <p className="text-sm text-gray-500 max-w-xs">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
