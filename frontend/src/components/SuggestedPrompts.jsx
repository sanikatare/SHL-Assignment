import { Briefcase, Users, GraduationCap } from 'lucide-react'

const PROMPTS = [
  {
    icon: Briefcase,
    label: 'Hiring a Java developer',
    text: 'I need to hire a Java developer. What assessment do you recommend?',
  },
  {
    icon: Users,
    label: 'Need a personality test',
    text: 'I need a personality test for a mid-level management role.',
  },
  {
    icon: GraduationCap,
    label: 'Entry level engineer assessment',
    text: 'What assessment should I use for an entry level software engineer role?',
  },
]

export default function SuggestedPrompts({ onSelect, disabled }) {
  return (
    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
      {PROMPTS.map(({ icon: Icon, label, text }) => (
        <button
          key={label}
          disabled={disabled}
          onClick={() => onSelect(text)}
          className="btn-focus-ring group flex flex-col items-start gap-2 rounded-xl border border-border bg-surface p-3.5 text-left shadow-card transition-all hover:-translate-y-0.5 hover:border-primary-400/50 hover:shadow-card-hover disabled:cursor-not-allowed disabled:opacity-50 dark:border-night-border dark:bg-night-surface"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
            <Icon size={16} />
          </span>
          <span className="text-sm font-medium leading-snug text-ink dark:text-night-ink">{label}</span>
        </button>
      ))}
    </div>
  )
}
