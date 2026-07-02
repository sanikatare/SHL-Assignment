import { ArrowUpRight } from 'lucide-react'

// Deterministic color lane per test-type letter so badges stay consistent
// across renders without needing a lookup table maintained by hand.
function badgeTone(testType) {
  const code = (testType || '?').trim().charAt(0).toUpperCase()
  const tones = {
    K: 'bg-primary-50 text-primary-700 border-primary-100 dark:bg-primary-900/30 dark:text-primary-400 dark:border-primary-700/40',
    P: 'bg-accent-soft text-accent-dark border-accent/30 dark:bg-accent-dark/20 dark:text-accent dark:border-accent-dark/40',
    A: 'bg-danger-soft text-danger border-danger/20 dark:bg-danger/10 dark:text-red-300 dark:border-danger/30',
  }
  return tones[code] || 'bg-paper-alt text-ink-soft border-border dark:bg-night-border/40 dark:text-night-soft dark:border-night-border'
}

function typeCode(testType) {
  if (!testType) return '?'
  return testType.trim().charAt(0).toUpperCase()
}

export default function RecommendationCard({ rec, index }) {
  const scorePct = typeof rec.score === 'number' ? Math.round(rec.score * 100) : null

  return (
    <a
      href={rec.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative flex flex-col justify-between rounded-xl border border-border bg-surface p-4 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover hover:border-primary-400/50 dark:border-night-border dark:bg-night-surface animate-fade-up btn-focus-ring"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* Match rank tag — the "index card" signature detail */}
      <span className="absolute -top-2.5 left-4 rounded-full border border-border bg-paper px-2 py-0.5 font-mono text-[10px] tracking-wide text-ink-faint dark:border-night-border dark:bg-night-bg dark:text-night-soft">
        MATCH {String(index + 1).padStart(2, '0')}
      </span>

      <div className="mt-1.5">
        <div className="mb-2 flex items-start justify-between gap-2">
          <h4 className="font-display text-[15px] font-semibold leading-snug text-ink dark:text-night-ink">
            {rec.name}
          </h4>
          <span
            className={`shrink-0 rounded-md border px-1.5 py-0.5 font-mono text-[11px] font-medium ${badgeTone(rec.test_type)}`}
            title={rec.test_type}
          >
            {typeCode(rec.test_type)}
          </span>
        </div>

        <p className="mb-3 text-xs text-ink-soft dark:text-night-soft line-clamp-2">
          {rec.test_type}
        </p>

        {scorePct !== null && (
          <div className="mb-3">
            <div className="mb-1 flex items-center justify-between text-[11px] font-mono text-ink-faint dark:text-night-soft">
              <span>Relevance</span>
              <span>{scorePct}%</span>
            </div>
            <div className="h-1 w-full overflow-hidden rounded-full bg-paper-alt dark:bg-night-border">
              <div
                className="h-full rounded-full bg-accent transition-all duration-500"
                style={{ width: `${scorePct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="mt-1 flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400">
        View assessment
        <ArrowUpRight size={14} className="transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </div>
    </a>
  )
}
