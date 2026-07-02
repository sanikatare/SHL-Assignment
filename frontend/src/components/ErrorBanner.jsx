import { AlertTriangle, RotateCw } from 'lucide-react'

export default function ErrorBanner({ message, onRetry, isRetrying }) {
  return (
    <div className="mx-auto flex max-w-2xl items-start gap-3 rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger animate-fade-up dark:border-danger/40 dark:bg-danger/10 dark:text-red-300">
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1">
        <p className="font-medium">Something went wrong</p>
        <p className="mt-0.5 text-danger/90 dark:text-red-300/80">{message}</p>
      </div>
      <button
        onClick={onRetry}
        disabled={isRetrying}
        className="btn-focus-ring flex shrink-0 items-center gap-1.5 rounded-lg border border-danger/30 bg-surface px-3 py-1.5 text-xs font-medium text-danger transition hover:bg-danger/10 disabled:cursor-not-allowed disabled:opacity-60 dark:border-danger/40 dark:bg-night-surface dark:text-red-300"
      >
        <RotateCw size={13} className={isRetrying ? 'animate-spin' : ''} />
        Retry
      </button>
    </div>
  )
}
