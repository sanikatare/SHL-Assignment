import { ArrowUpRight, Scale } from 'lucide-react'

// Renders the structured `comparison` payload the backend attaches to a
// ChatResponse when the turn was a comparison request. Falls back to
// nothing if no comparison is present (kept purely additive).
export default function ComparisonTable({ comparison }) {
  if (!comparison || !comparison.rows?.length) return null

  const { columns, rows } = comparison

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-border bg-surface shadow-card dark:border-night-border dark:bg-night-surface animate-fade-up">
      <div className="flex items-center gap-2 border-b border-border bg-paper-alt px-4 py-2.5 dark:border-night-border dark:bg-night-border/30">
        <Scale size={14} className="text-primary-600 dark:text-primary-400" />
        <span className="text-xs font-medium uppercase tracking-wide text-ink-soft dark:text-night-soft">
          Assessment comparison
        </span>
      </div>

      <div className="overflow-x-auto scroll-thin">
        <table className="w-full min-w-[720px] text-left text-xs">
          <thead>
            <tr className="border-b border-border dark:border-night-border">
              {columns.map((col) => (
                <th
                  key={col}
                  className="whitespace-nowrap px-3 py-2 font-medium text-ink-faint dark:text-night-soft"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={row.url || i}
                className="border-b border-border last:border-0 align-top dark:border-night-border"
              >
                {columns.map((col) => (
                  <td key={col} className="max-w-[220px] px-3 py-2.5 text-ink dark:text-night-ink">
                    {col === 'Assessment Name' && row.url ? (
                      <a
                        href={row.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-primary-600 hover:underline dark:text-primary-400"
                      >
                        {row[col]}
                        <ArrowUpRight size={11} />
                      </a>
                    ) : (
                      <span className="leading-relaxed">{row[col]}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
