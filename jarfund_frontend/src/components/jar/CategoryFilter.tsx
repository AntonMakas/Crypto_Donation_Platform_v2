import { motion } from 'framer-motion'
import { cn } from '@/utils/format'
import { JAR_CATEGORIES } from '@/lib/constants'
import type { JarCategory } from '@/types'

interface CategoryFilterProps {
  value?:    JarCategory | 'all'
  onChange:  (v: JarCategory | 'all') => void
  className?: string
}

export default function CategoryFilter({ value = 'all', onChange, className }: CategoryFilterProps) {
  const all = [{ value: 'all' as const, label: 'All', emoji: '✦' }, ...JAR_CATEGORIES]

  return (
    <div className={cn('flex items-center gap-2 flex-wrap', className)}>
      {all.map((cat) => {
        const active = value === cat.value
        return (
          <button
            key={cat.value}
            onClick={() => onChange(cat.value as JarCategory | 'all')}
            className={cn(
              'relative flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold',
              'transition-all duration-200 border',
              active
                ? 'text-primary-300 border-primary/40'
                : 'text-text-muted border-border hover:text-text-secondary hover:border-border-bright'
            )}
          >
            {active && (
              <motion.div
                layoutId="cat-pill"
                className="absolute inset-0 rounded-full"
                style={{ background: 'rgba(124,58,237,0.15)' }}
                transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
              />
            )}
            <span className="relative z-10">{cat.emoji}</span>
            <span className="relative z-10">{cat.label}</span>
          </button>
        )
      })}
    </div>
  )
}
