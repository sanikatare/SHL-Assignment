import { ClipboardCheck, Moon, Sun, Trash2, X } from 'lucide-react'
import SuggestedPrompts from './SuggestedPrompts'

function StatusDot({ status }) {
  const styles = {
    online: 'bg-primary-500',
    offline: 'bg-danger',
    checking: 'bg-accent animate-pulse',
  }
  const labels = {
    online: 'Agent online',
    offline: 'Agent unreachable',
    checking: 'Checking connection...',
  }
  return (
    <div className="flex items-center gap-1.5 text-xs text-ink-soft dark:text-night-soft">
      <span className={`h-1.5 w-1.5 rounded-full ${styles[status]}`} />
      {labels[status]}
    </div>
  )
}

export default function Sidebar({
  isDark,
  setIsDark,
  onClearChat,
  hasMessages,
  healthStatus,
  isOpen,
  onClose,
  onSelectPrompt,
  isLoading,
}) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <button
          aria-label="Close menu"
          onClick={onClose}
          className="fixed inset-0 z-30 bg-ink/40 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-border bg-surface transition-transform duration-300 dark:border-night-border dark:bg-night-surface lg:static lg:z-auto lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-5 pb-4 pt-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-500 text-white">
              <ClipboardCheck size={18} />
            </span>
            <div>
              <p className="font-display text-[15px] font-semibold leading-tight text-ink dark:text-night-ink">
                Talent Match
              </p>
              <p className="text-[11px] text-ink-faint dark:text-night-soft">SHL Assessment Agent</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="btn-focus-ring rounded-md p-1 text-ink-faint hover:text-ink dark:text-night-soft dark:hover:text-night-ink lg:hidden"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5">
          <StatusDot status={healthStatus} />
        </div>

        <div className="mt-5 flex-1 overflow-y-auto scroll-thin px-5">
          <button
            onClick={onClearChat}
            disabled={!hasMessages}
            className="btn-focus-ring mb-6 flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-paper px-3 py-2.5 text-sm font-medium text-ink transition hover:border-danger/40 hover:text-danger disabled:cursor-not-allowed disabled:opacity-50 dark:border-night-border dark:bg-night-bg dark:text-night-ink"
          >
            <Trash2 size={15} />
            Clear conversation
          </button>

          {hasMessages && (
            <div>
              <p className="mb-2.5 text-xs font-medium uppercase tracking-wide text-ink-faint dark:text-night-soft">
                Quick prompts
              </p>
              <div className="flex flex-col gap-2">
                <SuggestedPromptsList onSelect={onSelectPrompt} disabled={isLoading} />
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-border px-5 py-4 dark:border-night-border">
          <button
            onClick={() => setIsDark(!isDark)}
            className="btn-focus-ring flex w-full items-center justify-between rounded-xl border border-border bg-paper px-3 py-2.5 text-sm font-medium text-ink transition hover:border-primary-400/50 dark:border-night-border dark:bg-night-bg dark:text-night-ink"
          >
            <span className="flex items-center gap-2">
              {isDark ? <Moon size={15} /> : <Sun size={15} />}
              {isDark ? 'Dark mode' : 'Light mode'}
            </span>
            <span
              className={`relative h-5 w-9 rounded-full transition-colors ${
                isDark ? 'bg-primary-500' : 'bg-border dark:bg-night-border'
              }`}
            >
              <span
                className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                  isDark ? 'translate-x-4' : 'translate-x-0.5'
                }`}
              />
            </span>
          </button>
        </div>
      </aside>
    </>
  )
}

// Compact list variant used inside the sidebar (below the fold, once a
// conversation exists) rather than the larger card grid in EmptyState.
function SuggestedPromptsList({ onSelect, disabled }) {
  const prompts = [
    'Hiring a Java developer',
    'Need a personality test',
    'Entry level engineer assessment',
  ]
  const fullText = {
    'Hiring a Java developer': 'I need to hire a Java developer. What assessment do you recommend?',
    'Need a personality test': 'I need a personality test for a mid-level management role.',
    'Entry level engineer assessment': 'What assessment should I use for an entry level software engineer role?',
  }
  return (
    <>
      {prompts.map((p) => (
        <button
          key={p}
          disabled={disabled}
          onClick={() => onSelect(fullText[p])}
          className="btn-focus-ring rounded-lg border border-border bg-paper px-3 py-2 text-left text-xs text-ink-soft transition hover:border-primary-400/50 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50 dark:border-night-border dark:bg-night-bg dark:text-night-soft dark:hover:text-night-ink"
        >
          {p}
        </button>
      ))}
    </>
  )
}
