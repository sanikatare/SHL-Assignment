import { useEffect, useState } from 'react'

/**
 * Persist arbitrary JSON-serializable state to localStorage.
 * Falls back gracefully if localStorage is unavailable (e.g. private mode).
 */
export function useLocalStorage(key, initialValue) {
  const [value, setValue] = useState(() => {
    try {
      const stored = window.localStorage.getItem(key)
      return stored !== null ? JSON.parse(stored) : initialValue
    } catch {
      return initialValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // Storage full or unavailable — fail silently, chat still works in-memory.
    }
  }, [key, value])

  return [value, setValue]
}
