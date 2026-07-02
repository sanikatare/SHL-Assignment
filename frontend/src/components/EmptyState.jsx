import { ClipboardCheck } from 'lucide-react'
import SuggestedPrompts from './SuggestedPrompts'

export default function EmptyState({ onSelectPrompt, disabled }) {
  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-4 py-10 text-center animate-fade-up">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-500 text-white shadow-card">
        <ClipboardCheck size={26} />
      </div>
      <h1 className="font-display text-2xl font-semibold text-ink dark:text-night-ink sm:text-[28px]">
        Describe the role. Get the right assessment.
      </h1>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-soft dark:text-night-soft">
        Tell me who you're hiring for &mdash; the role, seniority, and skills that
        matter &mdash; and I'll match it against the SHL catalog and rank the
        best-fit assessments.
      </p>

      <div className="mt-8 w-full">
        <p className="mb-3 text-left text-xs font-medium uppercase tracking-wide text-ink-faint dark:text-night-soft">
          Try one of these
        </p>
        <SuggestedPrompts onSelect={onSelectPrompt} disabled={disabled} />
      </div>
    </div>
  )
}
