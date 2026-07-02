import { useEffect, useState } from 'react'
import { checkHealth } from '../api/chatApi'

/**
 * Polls GET /health periodically so the UI can show a live connection
 * indicator without blocking the chat itself.
 */
export function useHealthCheck(intervalMs = 30000) {
  const [status, setStatus] = useState('checking') // 'checking' | 'online' | 'offline'

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      const ok = await checkHealth()
      if (!cancelled) setStatus(ok ? 'online' : 'offline')
    }

    run()
    const id = setInterval(run, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [intervalMs])

  return status
}
