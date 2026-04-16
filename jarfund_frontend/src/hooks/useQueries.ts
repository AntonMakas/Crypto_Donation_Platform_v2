// ═══════════════════════════════════════════════════════════════
//  JarFund — React Query data hooks
//  Covers: jars, donations, blockchain stats, tx polling
// ═══════════════════════════════════════════════════════════════

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { jarsApi, donationsApi, blockchainApi, extractApiError } from '@/lib/api'
import {
  QUERY_KEYS,
  POLL_INTERVALS,
  DEFAULT_PAGE_SIZE,
} from '@/lib/constants'
import type {
  Jar,
  JarFilters,
  JarCreatePayload,
  JarUpdatePayload,
  JarConfirmPayload,
  JarWithdrawPayload,
  Donation,
  DonationCreatePayload,
  PlatformStats,
} from '@/types'

// ── JAR HOOKS ─────────────────────────────────────────────────────

/** Paginated jar list with filtering + search */
export function useJars(filters?: JarFilters) {
  return useQuery({
    queryKey: [...QUERY_KEYS.JARS, filters],
    queryFn:  () => jarsApi.list(filters as Record<string, unknown>),
    staleTime: 30_000,
  })
}

/** Infinite-scroll jar list (for Explore page) */
export function useInfiniteJars(filters?: Omit<JarFilters, 'page'>) {
  return useInfiniteQuery({
    queryKey:  [...QUERY_KEYS.JARS, 'infinite', filters],
    queryFn:   ({ pageParam = 1 }) =>
      jarsApi.list({ ...filters, page: pageParam, page_size: DEFAULT_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (last: { total_pages: number }, allPages: unknown[]) =>
      allPages.length < last.total_pages ? allPages.length + 1 : undefined,
    staleTime: 30_000,
  })
}

/** Single jar detail — refetches every 30 s while active */
export function useJar(id: number | null) {
  return useQuery({
    queryKey:        QUERY_KEYS.JAR(id!),
    queryFn:         () => jarsApi.get(id!),
    enabled:         !!id,
    refetchInterval: POLL_INTERVALS.JAR_DETAIL,
    staleTime:       10_000,
  })
}

/** Jars created by the current user */
export function useMyJars() {
  return useQuery({
    queryKey: QUERY_KEYS.MY_JARS,
    queryFn:  () => jarsApi.myJars(),
    staleTime: 60_000,
  })
}

/** Donation stats for a jar */
export function useJarStats(jarId: number | null) {
  return useQuery({
    queryKey: QUERY_KEYS.JAR_STATS(jarId!),
    queryFn:  () => jarsApi.getStats(jarId!),
    enabled:  !!jarId,
    staleTime: 30_000,
  })
}

// ── JAR MUTATIONS ─────────────────────────────────────────────────

/** Create a new jar */
export function useCreateJar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: JarCreatePayload) => jarsApi.create(payload),
    onSuccess:  (jar: Jar) => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.JARS })
      qc.invalidateQueries({ queryKey: QUERY_KEYS.MY_JARS })
      qc.setQueryData(QUERY_KEYS.JAR(jar.id), jar)
      toast.success('Jar created!')
    },
    onError: (err) => toast.error(extractApiError(err)),
  })
}

/** Update jar metadata */
export function useUpdateJar(jarId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: JarUpdatePayload) => jarsApi.update(jarId, payload),
    onSuccess:  (updated: Jar) => {
      qc.setQueryData(QUERY_KEYS.JAR(jarId), updated)
      toast.success('Jar updated.')
    },
    onError: (err) => toast.error(extractApiError(err)),
  })
}

/** Confirm jar creation on-chain */
export function useConfirmJar(jarId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: JarConfirmPayload) => jarsApi.confirm(jarId, payload),
    onSuccess:  (updated: Jar) => {
      qc.setQueryData(QUERY_KEYS.JAR(jarId), updated)
      qc.invalidateQueries({ queryKey: QUERY_KEYS.MY_JARS })
      toast.success('Jar confirmed on-chain!')
    },
    onError: (err) => toast.error(extractApiError(err)),
  })
}

/** Record jar withdrawal */
export function useWithdrawJar(jarId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: JarWithdrawPayload) => jarsApi.withdraw(jarId, payload),
    onSuccess:  (updated: Jar) => {
      qc.setQueryData(QUERY_KEYS.JAR(jarId), updated)
      qc.invalidateQueries({ queryKey: QUERY_KEYS.MY_JARS })
      toast.success('Withdrawal recorded!')
    },
    onError: (err) => toast.error(extractApiError(err)),
  })
}

// ── DONATION HOOKS ────────────────────────────────────────────────

/** Paginated donations list — optionally scoped to a jar */
export function useDonations(params?: { jar_id?: number; donor_wallet?: string; tx_status?: string }) {
  return useQuery({
    queryKey: [...QUERY_KEYS.DONATIONS, params],
    queryFn:  () => donationsApi.list(params as Record<string, unknown>),
    staleTime: 15_000,
  })
}

/** Current user's donations with stats */
export function useMyDonations() {
  return useQuery({
    queryKey: QUERY_KEYS.MY_DONATIONS,
    queryFn:  () => donationsApi.myDonations(),
    staleTime: 30_000,
  })
}

/** Leaderboard */
export function useLeaderboard(limit = 10) {
  return useQuery({
    queryKey: [...QUERY_KEYS.LEADERBOARD, limit],
    queryFn:  () => donationsApi.leaderboard(limit),
    staleTime: 5 * 60_000,
  })
}

// ── DONATION MUTATIONS ────────────────────────────────────────────

/** Submit a donation (called after MetaMask tx submitted) */
export function useSubmitDonation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: DonationCreatePayload) => donationsApi.create(payload),
    onSuccess:  (donation: Donation) => {
      // Optimistically invalidate the jar so it starts polling
      qc.invalidateQueries({ queryKey: QUERY_KEYS.JAR(donation.jar_id) })
      qc.invalidateQueries({ queryKey: QUERY_KEYS.MY_DONATIONS })
      qc.invalidateQueries({ queryKey: QUERY_KEYS.DONATIONS })
    },
    onError: (err) => toast.error(extractApiError(err)),
  })
}

// ── BLOCKCHAIN HOOKS ──────────────────────────────────────────────

/** Platform-wide stats — auto-refreshes every 60 s */
export function usePlatformStats() {
  return useQuery<PlatformStats>({
    queryKey:        QUERY_KEYS.PLATFORM_STATS,
    queryFn:         () => blockchainApi.getStats(),
    staleTime:       55_000,
    refetchInterval: POLL_INTERVALS.PLATFORM_STATS,
  })
}

/** Poll a tx hash until confirmed or failed */
export function useTxStatus(txHash: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.TX_STATUS(txHash!),
    queryFn:  () => blockchainApi.getTxStatus(txHash!),
    enabled:  !!txHash,
    // Keep polling while still pending
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || status === 'pending') return POLL_INTERVALS.TX_PENDING
      return false // stop polling once confirmed or failed
    },
    staleTime: 5_000,
  })
}
