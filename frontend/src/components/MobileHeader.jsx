import { ClipboardCheck, Menu } from 'lucide-react'

export default function MobileHeader({ onOpenMenu }) {
  return (
    <header className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3 dark:border-night-border dark:bg-night-surface lg:hidden">
      <button
        onClick={onOpenMenu}
        aria-label="Open menu"
        className="btn-focus-ring rounded-md p-1.5 text-ink hover:bg-paper-alt dark:text-night-ink dark:hover:bg-night-border"
      >
        <Menu size={20} />
      </button>
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-500 text-white">
          <ClipboardCheck size={14} />
        </span>
        <p className="font-display text-sm font-semibold text-ink dark:text-night-ink">Talent Match</p>
      </div>
    </header>
  )
}
