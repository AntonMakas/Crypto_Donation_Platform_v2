// ═══════════════════════════════════════════════════════════════
//  JarFund — Small Utility Hooks
// ═══════════════════════════════════════════════════════════════

import { useState, useEffect, useCallback, useRef } from 'react'
import { copyToClipboard } from '@/utils/format'

// ── useCountdown ──────────────────────────────────────────────────
// Counts down seconds from a deadline ISO string.
// Returns { days, hours, minutes, seconds, isExpired }.

interface CountdownResult {
  days:      number
  hours:     number
  minutes:   number
  seconds:   number
  isExpired: boolean
  total:     number  // total seconds remaining
}

export function useCountdown(deadline: string | null): CountdownResult {
  const calculate = useCallback((): CountdownResult => {
    if (!deadline) return { days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true, total: 0 }
    const diff = Math.max(0, Math.floor((new Date(deadline).getTime() - Date.now()) / 1000))
    return {
      days:      Math.floor(diff / 86400),
      hours:     Math.floor((diff % 86400) / 3600),
      minutes:   Math.floor((diff % 3600) / 60),
      seconds:   diff % 60,
      isExpired: diff === 0,
      total:     diff,
    }
  }, [deadline])

  const [state, setState] = useState(calculate)

  useEffect(() => {
    const tick = setInterval(() => {
      const next = calculate()
      setState(next)
      if (next.isExpired) clearInterval(tick)
    }, 1000)
    return () => clearInterval(tick)
  }, [calculate])

  return state
}

// ── useClipboard ──────────────────────────────────────────────────
// Copy text and show temporary "Copied!" state.

export function useClipboard(timeout = 1500) {
  const [copied, setCopied] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const copy = useCallback(async (text: string) => {
    const ok = await copyToClipboard(text)
    if (ok) {
      setCopied(true)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setCopied(false), timeout)
    }
    return ok
  }, [timeout])

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current)
  }, [])

  return { copy, copied }
}

// ── useLocalStorage ───────────────────────────────────────────────
// Type-safe localStorage with SSR safety.

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? (JSON.parse(item) as T) : initialValue
    } catch { return initialValue }
  })

  const set = useCallback((val: T | ((prev: T) => T)) => {
    try {
      const next = val instanceof Function ? val(value) : val
      window.localStorage.setItem(key, JSON.stringify(next))
      setValue(next)
    } catch (e) { console.warn('useLocalStorage set error:', e) }
  }, [key, value])

  const remove = useCallback(() => {
    try {
      window.localStorage.removeItem(key)
      setValue(initialValue)
    } catch (e) { console.warn('useLocalStorage remove error:', e) }
  }, [key, initialValue])

  return [value, set, remove] as const
}

// ── useDebounce ───────────────────────────────────────────────────
// Debounce a rapidly-changing value (search input, etc).

export function useDebounce<T>(value: T, delay = 400): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}

// ── useMediaQuery ─────────────────────────────────────────────────
// Reactive CSS media query hook.

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches
  )

  useEffect(() => {
    const mq = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [query])

  return matches
}

// Convenience breakpoint hooks
export const useIsMobile  = () => useMediaQuery('(max-width: 767px)')
export const useIsTablet  = () => useMediaQuery('(min-width: 768px) and (max-width: 1023px)')
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)')

// ── useScrollLock ─────────────────────────────────────────────────
// Lock body scroll when a modal is open.

export function useScrollLock(locked: boolean) {
  useEffect(() => {
    if (!locked) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [locked])
}

// ── useOnClickOutside ─────────────────────────────────────────────
// Fire callback when user clicks outside the given ref.

export function useOnClickOutside<T extends HTMLElement>(
  ref: React.RefObject<T>,
  handler: () => void
) {
  useEffect(() => {
    const listener = (e: MouseEvent | TouchEvent) => {
      if (!ref.current || ref.current.contains(e.target as Node)) return
      handler()
    }
    document.addEventListener('mousedown',  listener)
    document.addEventListener('touchstart', listener)
    return () => {
      document.removeEventListener('mousedown',  listener)
      document.removeEventListener('touchstart', listener)
    }
  }, [ref, handler])
}

// ── usePrevious ───────────────────────────────────────────────────
// Keep track of the previous value of a variable.

export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined)
  useEffect(() => { ref.current = value }, [value])
  return ref.current
}
