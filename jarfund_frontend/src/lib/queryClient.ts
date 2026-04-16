// ═══════════════════════════════════════════════════════════════
//  React Query client configuration
// ═══════════════════════════════════════════════════════════════

import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Re-fetch when window regains focus (user comes back to tab)
      refetchOnWindowFocus:      true,
      // Don't re-fetch on reconnect by default — explicit for polling queries
      refetchOnReconnect:        'always',
      // 5 min stale time for most data
      staleTime:                 5 * 60 * 1000,
      // 10 min cache time
      gcTime:                    10 * 60 * 1000,
      // Retry failed queries 2 times with exponential back-off
      retry:                     2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 15_000),
    },
    mutations: {
      // Don't retry mutations by default — user should re-submit explicitly
      retry: 0,
    },
  },
})
