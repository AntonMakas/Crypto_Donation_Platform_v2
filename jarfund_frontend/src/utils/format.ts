// ═══════════════════════════════════════════════════════════════
//  JarFund — Formatting Utilities
// ═══════════════════════════════════════════════════════════════

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format, isPast, differenceInDays } from 'date-fns'
import { EXPLORER_URL } from '@/lib/constants'

// ── Tailwind class merger ─────────────────────────────────────────

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// ── MATIC / Currency formatting ───────────────────────────────────

/**
 * Format a MATIC amount for display.
 * @example formatMatic("1.5")        → "1.5 MATIC"
 * @example formatMatic("0.001234")   → "0.0012 MATIC"
 * @example formatMatic("1000.5")     → "1,000.5 MATIC"
 */
export function formatMatic(
  value: string | number,
  opts?: { compact?: boolean; decimals?: number; suffix?: boolean }
): string {
  const { compact = false, decimals, suffix = true } = opts ?? {}
  const num = typeof value === 'string' ? parseFloat(value) : value

  if (isNaN(num)) return '—'

  let formatted: string

  if (compact && num >= 1_000_000) {
    formatted = `${(num / 1_000_000).toFixed(2)}M`
  } else if (compact && num >= 1_000) {
    formatted = `${(num / 1_000).toFixed(1)}K`
  } else {
    const dp = decimals ?? (num < 0.001 ? 6 : num < 1 ? 4 : num < 1000 ? 2 : 1)
    formatted = num.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: dp,
    })
  }

  return suffix ? `${formatted} MATIC` : formatted
}

/**
 * Parse a MATIC string to a float, returning 0 on failure.
 */
export function parseMatic(value: string): number {
  const parsed = parseFloat(value)
  return isNaN(parsed) ? 0 : parsed
}

// ── Ethereum address formatting ───────────────────────────────────

/**
 * Shorten a wallet address for display.
 * @example shortAddress("0x71C7656EC7ab88b098defB751B7401B5f6d8976F") → "0x71C7…976F"
 */
export function shortAddress(address: string, chars = 4): string {
  if (!address || address === 'Anonymous') return address
  if (address.length < 10) return address
  return `${address.slice(0, chars + 2)}…${address.slice(-chars)}`
}

/**
 * Check if a string looks like a valid 0x Ethereum address.
 */
export function isEthAddress(value: string): boolean {
  return /^0x[0-9a-fA-F]{40}$/.test(value)
}

/**
 * Check if a string looks like a valid tx hash.
 */
export function isTxHash(value: string): boolean {
  return /^0x[0-9a-fA-F]{64}$/.test(value)
}

// ── Explorer URLs ─────────────────────────────────────────────────

export function explorerTxUrl(hash: string): string {
  return `${EXPLORER_URL}/tx/${hash}`
}

export function explorerAddressUrl(address: string): string {
  return `${EXPLORER_URL}/address/${address}`
}

// ── Date / time formatting ────────────────────────────────────────

/**
 * Human-readable relative time.
 * @example timeAgo("2026-02-28T10:00:00Z") → "2 days ago"
 */
export function timeAgo(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return formatDistanceToNow(d, { addSuffix: true })
}

/**
 * Format a deadline as a countdown or "Ended X ago".
 */
export function formatDeadline(deadline: string): {
  label:     string
  isExpired: boolean
  urgency:   'normal' | 'warning' | 'critical'
} {
  const d       = new Date(deadline)
  const expired = isPast(d)

  if (expired) {
    return {
      label:     `Ended ${formatDistanceToNow(d, { addSuffix: true })}`,
      isExpired: true,
      urgency:   'normal',
    }
  }

  const daysLeft = differenceInDays(d, new Date())
  const label    = daysLeft > 1
    ? `${daysLeft} days left`
    : daysLeft === 1
    ? '1 day left'
    : `${formatDistanceToNow(d)} left`

  return {
    label,
    isExpired: false,
    urgency:   daysLeft <= 1 ? 'critical' : daysLeft <= 3 ? 'warning' : 'normal',
  }
}

/**
 * Format a datetime for display in cards.
 * @example formatDate("2026-03-01T10:00:00Z") → "Mar 1, 2026"
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return format(d, 'MMM d, yyyy')
}

/**
 * Format datetime with time.
 * @example formatDateTime("2026-03-01T10:00:00Z") → "Mar 1, 2026 at 10:00 AM"
 */
export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return format(d, "MMM d, yyyy 'at' h:mm a")
}

// ── Progress helpers ──────────────────────────────────────────────

/**
 * Clamp progress percentage to 0–100.
 */
export function clampProgress(value: number): number {
  return Math.min(100, Math.max(0, value))
}

/**
 * Return the progress bar colour class based on percentage.
 */
export function progressColor(pct: number): string {
  if (pct >= 100) return 'completed'
  return ''
}

// ── Number helpers ────────────────────────────────────────────────

/**
 * Format a large integer with commas.
 * @example formatNumber(12345) → "12,345"
 */
export function formatNumber(value: number): string {
  return value.toLocaleString('en-US')
}

/**
 * Compact-format a number for stat displays.
 * @example compactNumber(15420) → "15.4K"
 */
export function compactNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000)     return `${(value / 1_000).toFixed(1)}K`
  return value.toString()
}

// ── String helpers ────────────────────────────────────────────────

/**
 * Truncate text with an ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 1)}…`
}

/**
 * Capitalise the first letter.
 */
export function capitalise(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

// ── Clipboard ─────────────────────────────────────────────────────

/**
 * Copy text to clipboard and return success/failure.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback for older browsers
    try {
      const el = document.createElement('textarea')
      el.value = text
      el.style.position = 'fixed'
      el.style.opacity  = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      return true
    } catch {
      return false
    }
  }
}

// ── MATIC → Wei conversion (pure string math, no BigInt rounding) ─

/**
 * Convert MATIC amount (string) to wei (string) without float precision loss.
 * Relies on viem's parseEther in components that have it; this is a fallback.
 */
export function maticToWeiString(matic: string): string {
  try {
    const [int, frac = ''] = matic.split('.')
    const padded = frac.padEnd(18, '0').slice(0, 18)
    const wei    = BigInt(int) * BigInt(10 ** 18) + BigInt(padded)
    return wei.toString()
  } catch {
    return '0'
  }
}

/**
 * Convert wei (string) to MATIC (string).
 */
export function weiToMaticString(wei: string): string {
  try {
    const w   = BigInt(wei)
    const int = w / BigInt(10 ** 18)
    const rem = w % BigInt(10 ** 18)
    const frac = rem.toString().padStart(18, '0').replace(/0+$/, '')
    return frac ? `${int}.${frac}` : int.toString()
  } catch {
    return '0'
  }
}
