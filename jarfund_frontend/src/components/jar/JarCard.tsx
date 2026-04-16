import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Clock, Users, TrendingUp, CheckCircle2 } from 'lucide-react'
import { StatusBadge, ProgressBar } from '@/components/ui/PageSpinner'
import { formatMatic, formatDeadline, clampProgress } from '@/utils/format'
import { ROUTES, JAR_CATEGORIES } from '@/lib/constants'
import type { Jar } from '@/types'

interface JarCardProps {
  jar:     Jar
  index?:  number   // for stagger animation
  compact?: boolean
}

export default function JarCard({ jar, index = 0, compact = false }: JarCardProps) {
  const { label: deadlineLabel, urgency } = formatDeadline(jar.deadline)
  const pct      = clampProgress(jar.progress_percentage)
  const category = JAR_CATEGORIES.find(c => c.value === jar.category)

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: [0.23, 1, 0.32, 1] }}
      whileHover={{ y: -4 }}
    >
      <Link
        to={ROUTES.JAR(jar.id)}
        className="glass-card block p-5 group cursor-pointer transition-all duration-300 h-full"
      >
        {/* ── Header ─────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-3xl shrink-0 group-hover:scale-110 transition-transform duration-300">
              {jar.cover_emoji || category?.emoji || '🫙'}
            </span>
            <div className="min-w-0">
              <h3 className="font-display font-semibold text-sm text-text-primary truncate group-hover:text-gradient transition-all">
                {jar.title}
              </h3>
              <span className="text-xs text-text-muted">
                {category?.label ?? jar.category}
              </span>
            </div>
          </div>
          <StatusBadge status={jar.status} />
        </div>

        {/* ── Description ────────────────────────────────────── */}
        {!compact && (
          <p className="text-xs text-text-muted leading-relaxed mb-4 line-clamp-2">
            {jar.description}
          </p>
        )}

        {/* ── Progress ────────────────────────────────────────── */}
        <div className="mb-4 space-y-2">
          <ProgressBar value={pct} height="sm" animated />
          <div className="flex justify-between items-baseline">
            <div>
              <span className="text-sm font-display font-bold text-text-primary">
                {formatMatic(jar.amount_raised_matic, { compact: true, suffix: false })}
              </span>
              <span className="text-xs text-text-muted ml-1">
                / {formatMatic(jar.target_amount_matic, { compact: true })}
              </span>
            </div>
            <span
              className="text-xs font-semibold"
              style={{ color: pct >= 100 ? '#10b981' : pct >= 75 ? '#a855f7' : '#a89bc2' }}
            >
              {pct.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* ── Footer meta ──────────────────────────────────────── */}
        <div className="flex items-center justify-between text-xs text-text-muted pt-3 border-t border-border">
          <span className="flex items-center gap-1">
            <Users size={11} />
            {jar.donor_count} donor{jar.donor_count !== 1 ? 's' : ''}
          </span>

          <span
            className={[
              'flex items-center gap-1',
              urgency === 'critical' ? 'text-danger/70' :
              urgency === 'warning'  ? 'text-warning/70' : '',
            ].join(' ')}
          >
            {jar.is_deadline_passed
              ? <TrendingUp size={11} />
              : <Clock size={11} />
            }
            {deadlineLabel}
          </span>
        </div>

        {/* ── Verified badge ────────────────────────────────────── */}
        {jar.is_verified_on_chain && (
          <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <CheckCircle2 size={14} className="text-success/60" />
          </div>
        )}
      </Link>
    </motion.div>
  )
}
