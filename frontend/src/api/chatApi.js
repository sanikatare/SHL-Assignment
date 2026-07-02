import axios from 'axios'

// Base URL is configurable via .env (VITE_API_BASE_URL) and falls back to
// the default local FastAPI dev server. No backend routes are changed here.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Custom error shape thrown by the API layer so the UI can render a
 * consistent error state regardless of whether the failure was a network
 * error, a timeout, or a non-2xx response from FastAPI.
 */
export class ChatApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message)
    this.name = 'ChatApiError'
    this.status = status
    this.detail = detail
  }
}

/**
 * GET /health
 * Returns true if the backend reports status "ok".
 */
export async function checkHealth() {
  try {
    const { data } = await client.get('/health')
    return data?.status === 'ok'
  } catch (err) {
    return false
  }
}

/**
 * POST /chat
 * @param {Array<{role: 'user'|'assistant', content: string}>} messages
 * @returns {Promise<{reply: string, recommendations: Array, end_of_conversation: boolean}>}
 */
export async function sendChatMessage(messages) {
  try {
    const { data } = await client.post('/chat', { messages })
    return {
      reply: data?.reply ?? '',
      recommendations: Array.isArray(data?.recommendations) ? data.recommendations : [],
      end_of_conversation: Boolean(data?.end_of_conversation),
      comparison: data?.comparison ?? null,
      needs_clarification: Boolean(data?.needs_clarification),
    }
  } catch (err) {
    if (err.response) {
      // FastAPI HTTPException style: { detail: "..." }
      const detail = err.response.data?.detail || 'The server could not process this request.'
      throw new ChatApiError(detail, { status: err.response.status, detail })
    }
    if (err.request) {
      throw new ChatApiError(
        'Could not reach the assessment agent. Check that the API server is running.',
        { status: 0 }
      )
    }
    throw new ChatApiError(err.message || 'Something went wrong sending your message.')
  }
}

export default client
