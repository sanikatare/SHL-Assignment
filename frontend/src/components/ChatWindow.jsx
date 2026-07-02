import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'
import EmptyState from './EmptyState'
import ErrorBanner from './ErrorBanner'

export default function ChatWindow({
  messages,
  isLoading,
  error,
  onRetry,
  streamingMessageId,
  finishStreaming,
  onSelectPrompt,
}) {
  const bottomRef = useRef(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, isLoading, error])

  if (messages.length === 0 && !isLoading && !error) {
    return (
      <div className="flex-1 overflow-y-auto scroll-thin">
        <EmptyState onSelectPrompt={onSelectPrompt} disabled={isLoading} />
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-thin px-3 py-5 sm:px-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isStreaming={msg.id === streamingMessageId}
            onStreamDone={finishStreaming}
          />
        ))}

        {isLoading && (
          <div className="flex items-start gap-2.5 animate-fade-up">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-white">
              <span className="h-2 w-2 rounded-full bg-white" />
            </div>
            <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-3 shadow-card dark:border-night-border dark:bg-night-surface">
              <TypingIndicator />
            </div>
          </div>
        )}

        {error && <ErrorBanner message={error} onRetry={onRetry} isRetrying={isLoading} />}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
