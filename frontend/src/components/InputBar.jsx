import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Loader2 } from 'lucide-react'

const MAX_HEIGHT_PX = 160

export default function InputBar({ onSend, disabled, endOfConversation }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`
  }, [value])

  const handleSubmit = () => {
    if (!value.trim() || disabled) return
    onSend(value)
    setValue('')
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-border bg-paper/95 px-3 pb-3 pt-2.5 backdrop-blur dark:border-night-border dark:bg-night-bg/95 sm:px-6 sm:pb-5">
      <div className="mx-auto max-w-3xl">
        {endOfConversation && (
          <p className="mb-2 text-center text-xs text-ink-faint dark:text-night-soft">
            This conversation has concluded. Start a new message to continue.
          </p>
        )}
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface px-3 py-2 shadow-bar transition-colors focus-within:border-primary-400 dark:border-night-border dark:bg-night-surface">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            disabled={disabled}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the role you're hiring for..."
            aria-label="Message the assessment agent"
            className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-[15px] leading-relaxed text-ink placeholder:text-ink-faint focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:text-night-ink dark:placeholder:text-night-soft"
          />
          <button
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className="btn-focus-ring flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white transition hover:bg-primary-600 disabled:cursor-not-allowed disabled:bg-ink-faint/40 disabled:text-white/70 dark:disabled:bg-night-border"
          >
            {disabled ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
          </button>
        </div>
        <p className="mt-1.5 text-center text-[11px] text-ink-faint dark:text-night-soft">
          Press <kbd className="rounded border border-border px-1 py-0.5 font-mono dark:border-night-border">Enter</kbd> to send &middot;{' '}
          <kbd className="rounded border border-border px-1 py-0.5 font-mono dark:border-night-border">Shift+Enter</kbd> for a new line
        </p>
      </div>
    </div>
  )
}
