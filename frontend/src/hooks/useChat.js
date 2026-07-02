import { useCallback, useMemo, useRef, useState } from 'react'
import { sendChatMessage, ChatApiError } from '../api/chatApi'
import { useLocalStorage } from './useLocalStorage'

const STORAGE_KEY = 'shl-chat-history-v1'
let localIdCounter = 0
const nextId = () => `m_${Date.now()}_${++localIdCounter}`

/**
 * Owns the full chat conversation: message history, loading/error state,
 * persistence to localStorage, and talking to POST /chat.
 *
 * The backend is stateless and expects the FULL message history (role +
 * content only) on every request, so we strip local-only fields (id,
 * recommendations, createdAt) before sending.
 */
export function useChat() {
  const [messages, setMessages] = useLocalStorage(STORAGE_KEY, [])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [streamingMessageId, setStreamingMessageId] = useState(null)
  const pendingRetryText = useRef(null)

  const isEndOfConversation = useMemo(() => {
    const last = messages[messages.length - 1]
    return Boolean(last && last.role === 'assistant' && last.end_of_conversation)
  }, [messages])

  const toApiHistory = (msgList) =>
    msgList.map((m) => ({ role: m.role, content: m.content }))

  const dispatchToBackend = useCallback(async (historyForApi, userVisibleText) => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await sendChatMessage(historyForApi)
      const assistantMsg = {
        id: nextId(),
        role: 'assistant',
        content: res.reply,
        recommendations: res.recommendations,
        end_of_conversation: res.end_of_conversation,
        comparison: res.comparison,
        needs_clarification: res.needs_clarification,
        createdAt: Date.now(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setStreamingMessageId(assistantMsg.id)
      pendingRetryText.current = null
      return { ok: true }
    } catch (err) {
      const message =
        err instanceof ChatApiError
          ? err.message
          : 'Something went wrong. Please try again.'
      setError(message)
      pendingRetryText.current = userVisibleText
      return { ok: false, message }
    } finally {
      setIsLoading(false)
    }
  }, [setMessages])

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed || isLoading) return

      const userMsg = {
        id: nextId(),
        role: 'user',
        content: trimmed,
        createdAt: Date.now(),
      }
      const nextHistory = [...messages, userMsg]
      setMessages(nextHistory)
      await dispatchToBackend(toApiHistory(nextHistory), trimmed)
    },
    [messages, isLoading, dispatchToBackend, setMessages]
  )

  const retryLastMessage = useCallback(async () => {
    if (isLoading) return
    setError(null)
    await dispatchToBackend(toApiHistory(messages), pendingRetryText.current)
  }, [messages, isLoading, dispatchToBackend])

  const clearChat = useCallback(() => {
    setMessages([])
    setError(null)
    pendingRetryText.current = null
  }, [setMessages])

  const finishStreaming = useCallback((id) => {
    setStreamingMessageId((current) => (current === id ? null : current))
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    retryLastMessage,
    clearChat,
    isEndOfConversation,
    streamingMessageId,
    finishStreaming,
  }
}
