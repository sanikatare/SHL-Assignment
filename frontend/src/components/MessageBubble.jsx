import { useState } from 'react'
import { Check, CircleHelp, Copy, Sparkles, User } from 'lucide-react'
import RecommendationGrid from './RecommendationGrid'
import ComparisonTable from './ComparisonTable'
import { useTypewriter } from '../hooks/useTypewriter'
import { useToast } from '../context/ToastContext'

function formatTime(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export default function MessageBubble({ message, isStreaming, onStreamDone }) {
  const isUser = message.role === 'user'
  const toast = useToast()
  const [copied, setCopied] = useState(false)

  const displayedText = useTypewriter(message.content, isStreaming, () => onStreamDone?.(message.id))
  const hasComparison = Boolean(message.comparison?.rows?.length)
  // The backend's `reply` embeds a full markdown table for plain API
  // consumers, but the UI renders that table via <ComparisonTable/>, so
  // only show the intro sentence here to avoid printing raw markdown pipes.
  const bubbleText = hasComparison ? message.content.split('\n\n')[0] : displayedText

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      toast.success('Message copied')
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Could not copy message')
    }
  }

  if (isUser) {
    return (
      <div className="flex justify-end gap-2.5 animate-fade-up">
        <div className="group flex max-w-[85%] flex-col items-end sm:max-w-[70%]">
          <div className="rounded-2xl rounded-tr-sm bg-primary-500 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-card">
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          <span className="mt-1 mr-1 text-[11px] text-ink-faint opacity-0 transition-opacity group-hover:opacity-100 dark:text-night-soft">
            {formatTime(message.createdAt)}
          </span>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink text-paper dark:bg-night-ink dark:text-night-bg">
          <User size={15} />
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-2.5 animate-fade-up">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white shadow-sm">
        <Sparkles size={15} />
      </div>
      <div className="group min-w-0 max-w-[85%] flex-1 sm:max-w-[80%]">
        {message.needs_clarification && (
          <div className="mb-1.5 ml-1 inline-flex items-center gap-1.5 rounded-full border border-primary-200 bg-primary-50 px-2.5 py-1 text-[11px] font-medium text-primary-700 dark:border-primary-700/40 dark:bg-primary-900/30 dark:text-primary-400">
            <CircleHelp size={12} />
            Clarifying question
          </div>
        )}
        <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-2.5 text-[15px] leading-relaxed text-ink shadow-card dark:border-night-border dark:bg-night-surface dark:text-night-ink">
          <p className="whitespace-pre-wrap break-words">
            {bubbleText}
            {isStreaming && !hasComparison && displayedText.length < message.content.length && (
              <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-primary-500 align-middle" />
            )}
          </p>
        </div>

        {(hasComparison || !isStreaming || displayedText.length >= message.content.length) && (
          <>
            <RecommendationGrid recommendations={message.recommendations} />
            <ComparisonTable comparison={message.comparison} />
          </>
        )}

        <div className="mt-1 ml-1 flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
          <span className="text-[11px] text-ink-faint dark:text-night-soft">{formatTime(message.createdAt)}</span>
          <button
            onClick={handleCopy}
            className="btn-focus-ring flex items-center gap-1 rounded-md px-1 text-[11px] text-ink-faint hover:text-primary-600 dark:text-night-soft dark:hover:text-primary-400"
            aria-label="Copy message"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
    </div>
  )
}
