// ═══════════════════════════════════════════════════════════════
//  JarFund — Core UI Primitives
//  PageSpinner · StatusBadge · TxLink · ProgressBar
//  Skeleton   · EmptyState  · WalletAddress · StatCard
// ═══════════════════════════════════════════════════════════════

import { ExternalLink, Copy, Check, AlertCircle, Inbox } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn, shortAddress, progressColor, clampProgress } from '@/utils/format'
import { useClipboard } from '@/hooks/useUtils'
import { JAR_STATUS_CONFIG } from '@/lib/constants'
import type { JarStatus } from '@/types'

// ── PageSpinner ───────────────────────────────────────────────────

export function PageSpinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center gap-4 bg-bg z-50">
      <div className="relative w-14 h-14">
        <div className="absolute inset-0 rounded-full border-2 border-primary/20" />
        <div className="absolute inset-0 rounded-full border-2 border-t-primary border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        <span className="absolute inset-0 flex items-center justify-center text-xl">🫙</span>
      </div>
      <p className="text-sm text-text-muted font-body">{label}</p>
    </div>
  )
}

// ── InlineSpinner ─────────────────────────────────────────────────

export function InlineSpinner({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={cn('animate-spin text-current', className)}
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

// ── StatusBadge ───────────────────────────────────────────────────

export function StatusBadge({ status }: { status: JarStatus }) {
  const cfg = JAR_STATUS_CONFIG[status]
  return (
    <span
      className="badge text-xs font-semibold"
      style={{ background: cfg.bgColor, color: cfg.color, border: `1px solid ${cfg.color}30` }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: cfg.color }}
      />
      {cfg.label}
    </span>
  )
}

// ── TxLink ────────────────────────────────────────────────────────

export function TxLink({ hash, label }: { hash: string; label?: string }) {
  const { copy, copied } = useClipboard()
  const short = label ?? `${hash.slice(0, 8)}…${hash.slice(-6)}`
  const url   = `https://amoy.polygonscan.com/tx/${hash}`

  return (
    <span className="inline-flex items-center gap-1.5">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="tx-link inline-flex items-center gap-1"
      >
        <span className="font-mono">{short}</span>
        <ExternalLink size={11} />
      </a>
      <button
        onClick={() => copy(hash)}
        className="text-text-muted hover:text-text-secondary transition-colors"
        title="Copy hash"
      >
        {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
      </button>
    </span>
  )
}

// ── ProgressBar ───────────────────────────────────────────────────

interface ProgressBarProps {
  value:     number       // 0–100
  height?:   'xs' | 'sm' | 'md'
  animated?: boolean
  label?:    boolean
  className?: string
}

export function ProgressBar({
  value,
  height  = 'sm',
  animated = true,
  label    = false,
  className,
}: ProgressBarProps) {
  const pct       = clampProgress(value)
  const completed = pct >= 100
  const h = { xs: 'h-1', sm: 'h-1.5', md: 'h-2.5' }[height]

  return (
    <div className={className}>
      <div className={cn('progress-track', h)}>
        <motion.div
          className={cn('progress-fill', progressColor(pct), h)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: animated ? 0.8 : 0, ease: 'easeOut' }}
        />
      </div>
      {label && (
        <div className="flex justify-between mt-1">
          <span className="text-xs text-text-muted">{pct.toFixed(1)}%</span>
          {completed && <span className="text-xs text-success font-semibold">Goal reached! 🎉</span>}
        </div>
      )}
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} />
}

export function JarCardSkeleton() {
  return (
    <div className="glass-card p-5 space-y-4">
      <Skeleton className="h-8 w-8 rounded-full" />
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-1.5 w-full rounded-full" />
      <div className="flex justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  )
}

// ── EmptyState ────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?:     React.ReactNode
  title:     string
  message?:  string
  action?:   React.ReactNode
  className?: string
}

export function EmptyState({ icon, title, message, action, className }: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex flex-col items-center justify-center text-center py-16 px-8',
        className
      )}
    >
      {icon ? (
        <div className="mb-4 text-5xl">{icon}</div>
      ) : (
        <Inbox size={48} className="mb-4 text-text-disabled" />
      )}
      <h3 className="font-display font-semibold text-lg text-text-secondary mb-2">{title}</h3>
      {message && <p className="text-sm text-text-muted max-w-xs">{message}</p>}
      {action && <div className="mt-6">{action}</div>}
    </motion.div>
  )
}

// ── ErrorState ────────────────────────────────────────────────────

export function ErrorState({
  message = 'Something went wrong.',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <AlertCircle size={40} className="text-danger/60" />
      <p className="text-sm text-text-muted text-center max-w-xs">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-sm px-4 py-2">
          Try again
        </button>
      )}
    </div>
  )
}

// ── WalletAddress ─────────────────────────────────────────────────

export function WalletAddress({ address, chars = 4 }: { address: string; chars?: number }) {
  const { copy, copied } = useClipboard()
  if (!address || address === 'Anonymous') {
    return <span className="text-text-muted text-xs italic">Anonymous</span>
  }
  return (
    <button
      onClick={() => copy(address)}
      className="wallet-address inline-flex items-center gap-1.5 group"
      title={address}
    >
      <span>{shortAddress(address, chars)}</span>
      {copied
        ? <Check size={11} className="text-success" />
        : <Copy size={11} className="opacity-0 group-hover:opacity-100 transition-opacity" />
      }
    </button>
  )
}

// ── StatCard ──────────────────────────────────────────────────────

interface StatCardProps {
  label:     string
  value:     string | number
  sub?:      string
  icon?:     React.ReactNode
  accent?:   string
  className?: string
}

export function StatCard({ label, value, sub, icon, accent, className }: StatCardProps) {
  return (
    <div className={cn('glass-panel p-4 flex flex-col gap-2', className)}>
      {icon && (
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center mb-1"
          style={{ background: accent ?? 'rgba(124,58,237,0.15)' }}
        >
          {icon}
        </div>
      )}
      <div className="text-2xl font-display font-bold text-text-primary">{value}</div>
      <div className="text-xs text-text-muted">{label}</div>
      {sub && <div className="text-xs text-text-disabled">{sub}</div>}
    </div>
  )
}

// ── Divider ───────────────────────────────────────────────────────

export function Divider({ className }: { className?: string }) {
  return <div className={cn('divider', className)} />
}
