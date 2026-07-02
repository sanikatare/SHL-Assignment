import { useEffect, useRef, useState } from 'react'

/**
 * Reveals `fullText` progressively, like ChatGPT's streaming effect.
 * Only animates when `active` is true; otherwise renders the full text
 * immediately (used for messages loaded from history / localStorage).
 */
export function useTypewriter(fullText, active, onDone) {
  const [displayed, setDisplayed] = useState(active ? '' : fullText)
  const indexRef = useRef(0)
  const doneRef = useRef(onDone)
  doneRef.current = onDone

  useEffect(() => {
    if (!active) {
      setDisplayed(fullText)
      return
    }
    indexRef.current = 0
    setDisplayed('')

    // Speed scales with length so long recommendation replies don't crawl.
    const chunk = fullText.length > 220 ? 4 : fullText.length > 100 ? 2 : 1
    const intervalMs = 12

    const id = setInterval(() => {
      indexRef.current = Math.min(indexRef.current + chunk, fullText.length)
      setDisplayed(fullText.slice(0, indexRef.current))
      if (indexRef.current >= fullText.length) {
        clearInterval(id)
        doneRef.current?.()
      }
    }, intervalMs)

    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullText, active])

  return displayed
}
