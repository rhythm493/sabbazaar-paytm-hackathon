import { clsx } from 'clsx'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizeClass = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-10 h-10 border-4',
  }[size]

  return (
    <div
      className={clsx(
        'rounded-full border-blue-500 border-t-transparent animate-spin',
        sizeClass,
        className,
      )}
      role="status"
      aria-label="Loading"
    />
  )
}

interface LoadingStateProps {
  message?: string
}

export function LoadingState({ message = 'Loading…' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-500">
      <Spinner size="lg" />
      <p className="text-sm">{message}</p>
    </div>
  )
}
