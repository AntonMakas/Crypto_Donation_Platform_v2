import { useState, useCallback } from 'react'
import { useInfiniteQuery }       from '@tanstack/react-query'
import { motion }                 from 'framer-motion'
import { Search, SlidersHorizontal, X, ArrowUpDown } from 'lucide-react'

import JarCard        from '@/components/jar/JarCard'
import CategoryFilter from '@/components/jar/CategoryFilter'
import { JarCardSkeleton, EmptyState } from '@/components/ui/PageSpinner'
import { jarsApi }    from '@/lib/api'
import { QUERY_KEYS, DEFAULT_PAGE_SIZE } from '@/lib/constants'
import { useDebounce } from '@/hooks/useUtils'
import { cn }          from '@/utils/format'
import type { JarCategory, JarStatus } from '@/types'

const SORT_OPTIONS = [
  { value: '-created_at',        label: 'Newest'       },
  { value: '-amount_raised_matic', label: 'Most raised' },
  { value: '-donor_count',       label: 'Most donors'  },
  { value: 'deadline',           label: 'Ending soon'  },
]

const STATUS_TABS: Array<{ value: JarStatus | 'all'; label: string }> = [
  { value: 'all',       label: 'All'       },
  { value: 'active',    label: 'Active'    },
  { value: 'completed', label: 'Completed' },
]

export default function ExplorePage() {
  const [search,   setSearch]   = useState('')
  const [category, setCategory] = useState<JarCategory | 'all'>('all')
  const [status,   setStatus]   = useState<JarStatus | 'all'>('all')
  const [ordering, setOrdering] = useState('-created_at')
  const [showFilters, setShowFilters] = useState(false)

  const debouncedSearch = useDebounce(search, 350)

  const queryParams = {
    ...(debouncedSearch        ? { search: debouncedSearch }          : {}),
    ...(category !== 'all'     ? { category }                          : {}),
    ...(status   !== 'all'     ? { status }                            : { include_all: '1' }),
    ordering,
    page_size: DEFAULT_PAGE_SIZE,
  }

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey:  [...QUERY_KEYS.JARS, 'infinite', queryParams],
    queryFn:   ({ pageParam = 1 }) =>
      jarsApi.list({ ...queryParams, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (last: { total_pages: number }, allPages: unknown[]) =>
      allPages.length < last.total_pages ? allPages.length + 1 : undefined,
    staleTime: 30_000,
  })

  const allJars    = data?.pages.flatMap((p: { results: unknown[] }) => p.results) ?? []
  const totalCount = data?.pages[0]?.count ?? 0
  const hasFilters = debouncedSearch || category !== 'all' || status !== 'all'

  const clearFilters = () => {
    setSearch('')
    setCategory('all')
    setStatus('all')
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="mb-10">
        <p className="text-xs text-primary-400 font-semibold uppercase tracking-widest mb-2">Browse campaigns</p>
        <h1 className="font-display font-bold text-4xl text-text-primary">
          Explore Jars
        </h1>
        {totalCount > 0 && (
          <p className="text-text-muted text-sm mt-2">
            {totalCount} campaign{totalCount !== 1 ? 's' : ''} found
          </p>
        )}
      </motion.div>

      {/* Search + Controls bar */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="flex flex-col md:flex-row gap-3 mb-6">

        {/* Search input */}
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search jars by name or description…"
            className="input pl-9 pr-9"
          />
          {search && (
            <button onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Sort */}
        <select
          value={ordering}
          onChange={e => setOrdering(e.target.value)}
          className="select w-full md:w-48"
        >
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilters(v => !v)}
          className={cn(
            'btn-secondary flex items-center gap-2 whitespace-nowrap',
            showFilters && 'border-primary/40 text-primary-300'
          )}
        >
          <SlidersHorizontal size={14} />
          Filters
          {hasFilters && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
        </button>
      </motion.div>

      {/* Expanded filters */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="glass-panel p-5 mb-6 space-y-5"
        >
          {/* Status tabs */}
          <div>
            <p className="label mb-3">Status</p>
            <div className="flex gap-2 flex-wrap">
              {STATUS_TABS.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setStatus(value)}
                  className={cn(
                    'px-4 py-1.5 rounded-full text-xs font-semibold border transition-all',
                    status === value
                      ? 'bg-primary-dim border-primary/40 text-primary-300'
                      : 'border-border text-text-muted hover:border-border-bright'
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Category */}
          <div>
            <p className="label mb-3">Category</p>
            <CategoryFilter value={category} onChange={setCategory} />
          </div>

          {hasFilters && (
            <button onClick={clearFilters} className="btn-ghost text-xs text-danger/70 hover:text-danger">
              <X size={12} /> Clear all filters
            </button>
          )}
        </motion.div>
      )}

      {/* Category pills (always visible) */}
      {!showFilters && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
          className="mb-8">
          <CategoryFilter value={category} onChange={setCategory} />
        </motion.div>
      )}

      {/* Results grid */}
      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {[...Array(8)].map((_, i) => <JarCardSkeleton key={i} />)}
        </div>
      ) : allJars.length === 0 ? (
        <EmptyState
          icon="🫙"
          title="No jars found"
          message={hasFilters ? 'Try adjusting your filters or search term.' : 'Be the first to create a jar!'}
          action={hasFilters ? (
            <button onClick={clearFilters} className="btn-secondary text-sm px-4 py-2">Clear filters</button>
          ) : undefined}
        />
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {allJars.map((jar: unknown, i: number) => (
              <JarCard key={(jar as { id: number }).id} jar={jar as Parameters<typeof JarCard>[0]['jar']} index={i % DEFAULT_PAGE_SIZE} />
            ))}
          </div>

          {/* Load more */}
          {hasNextPage && (
            <div className="flex justify-center mt-12">
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="btn-secondary px-8 py-3"
              >
                {isFetchingNextPage ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-text-muted/30 border-t-text-muted animate-spin" />
                    Loading…
                  </span>
                ) : 'Load more'}
              </button>
            </div>
          )}

          {!hasNextPage && allJars.length > 0 && (
            <p className="text-center text-text-disabled text-xs mt-12">
              All {totalCount} campaigns shown
            </p>
          )}
        </>
      )}
    </div>
  )
}
