// ═══════════════════════════════════════════════════════════════
//  JarFund — Axios API Client
//  Handles:
//   · Base URL config
//   · JWT access token attachment
//   · Automatic token refresh on 401
//   · Typed request/response helpers
//   · Error normalisation
// ═══════════════════════════════════════════════════════════════

import axios, {
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
  isAxiosError,
} from 'axios'
import { API_BASE_URL, STORAGE_KEYS } from '@/lib/constants'
import type { ApiError, AuthTokens } from '@/types'

// ── Axios instance ────────────────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL:         API_BASE_URL,
  timeout:         15_000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
})

// ── Token helpers ─────────────────────────────────────────────────

export const tokenStorage = {
  getAccess():    string | null { return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) },
  getRefresh():   string | null { return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN) },
  setTokens(t: AuthTokens): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN,  t.access)
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, t.refresh)
  },
  clearTokens(): void {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
  },
}

// ── Request interceptor — attach Bearer token ─────────────────────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccess()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response interceptor — auto-refresh on 401 ────────────────────

let isRefreshing = false
let pendingQueue: Array<{
  resolve: (token: string) => void
  reject:  (err: unknown)  => void
}> = []

function drainQueue(error: unknown, token: string | null): void {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else       resolve(token!)
  })
  pendingQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    // Only attempt refresh on 401, and only once per request
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      const refreshToken = tokenStorage.getRefresh()
      if (!refreshToken) {
        tokenStorage.clearTokens()
        window.dispatchEvent(new Event('jarfund:logout'))
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Queue this request until the ongoing refresh completes
        return new Promise((resolve, reject) => {
          pendingQueue.push({ resolve, reject })
        }).then((newToken) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return apiClient(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post<{ success: boolean; data: { access: string } }>(
          `${API_BASE_URL}/auth/refresh/`,
          { refresh: refreshToken },
        )
        const newAccess = data.data.access
        localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, newAccess)
        drainQueue(null, newAccess)
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        drainQueue(refreshError, null)
        tokenStorage.clearTokens()
        window.dispatchEvent(new Event('jarfund:logout'))
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

// ── Typed response unwrapper ──────────────────────────────────────

/**
 * Unwraps the { success, data } envelope from every API response.
 * Throws a normalised ApiError on failure.
 */
function unwrap<T>(response: AxiosResponse<{ success: true; data: T }>): T {
  return response.data.data
}

/**
 * Extract a human-readable error message from an axios error.
 */
export function extractApiError(err: unknown): string {
  if (isAxiosError(err)) {
    const data = err.response?.data as ApiError | undefined
    if (data?.error?.message) return data.error.message
    if (err.response?.status === 404) return 'Resource not found.'
    if (err.response?.status === 403) return 'You don\'t have permission to do that.'
    if (err.response?.status === 429) return 'Too many requests. Please slow down.'
    if (err.message) return err.message
  }
  if (err instanceof Error) return err.message
  return 'Something went wrong. Please try again.'
}

/**
 * Extract field-level validation errors.
 */
export function extractFieldErrors(err: unknown): Record<string, string> {
  if (isAxiosError(err)) {
    const data = err.response?.data as ApiError | undefined
    if (data?.error?.details) {
      return Object.fromEntries(
        Object.entries(data.error.details).map(([k, v]) => [k, v[0]])
      )
    }
  }
  return {}
}

// ── Auth endpoints ────────────────────────────────────────────────

export const authApi = {
  getNonce: (wallet: string) =>
    apiClient.get<{ wallet: string; nonce: string; message: string }>(
      '/auth/nonce/',
      { params: { wallet } }
    ).then(r => r.data),

  verify: (wallet: string, signature: string) =>
    apiClient.post('/auth/verify/', { wallet, signature })
      .then(r => r.data.data),

  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh/', { refresh: refreshToken })
      .then(r => r.data.data),

  logout: (refreshToken: string) =>
    apiClient.post('/auth/logout/', { refresh: refreshToken }),

  getProfile: () =>
    apiClient.get('/auth/profile/').then(r => r.data.data),

  updateProfile: (data: { username?: string; bio?: string; avatar_url?: string }) =>
    apiClient.patch('/auth/profile/', data).then(r => r.data.data),
}

// ── Jar endpoints ─────────────────────────────────────────────────

export const jarsApi = {
  list: (params?: Record<string, unknown>) =>
    apiClient.get('/jars/', { params }).then(r => r.data),

  get: (id: number) =>
    apiClient.get(`/jars/${id}/`).then(r => r.data.data),

  create: (payload: unknown) =>
    apiClient.post('/jars/', payload).then(r => r.data.data),

  update: (id: number, payload: unknown) =>
    apiClient.patch(`/jars/${id}/`, payload).then(r => r.data.data),

  confirm: (id: number, payload: { chain_jar_id: number; creation_tx_hash: string }) =>
    apiClient.post(`/jars/${id}/confirm/`, payload).then(r => r.data.data),

  withdraw: (id: number, payload: { withdrawal_tx_hash: string }) =>
    apiClient.post(`/jars/${id}/withdraw/`, payload).then(r => r.data.data),

  getDonations: (id: number, params?: Record<string, unknown>) =>
    apiClient.get(`/jars/${id}/donations/`, { params }).then(r => r.data),

  getStats: (id: number) =>
    apiClient.get(`/jars/${id}/stats/`).then(r => r.data.data),

  myJars: (params?: Record<string, unknown>) =>
    apiClient.get('/jars/my/', { params }).then(r => r.data),
}

// ── Donations endpoints ───────────────────────────────────────────

export const donationsApi = {
  create: (payload: unknown) =>
    apiClient.post('/donations/', payload).then(r => r.data.data),

  list: (params?: Record<string, unknown>) =>
    apiClient.get('/donations/', { params }).then(r => r.data),

  get: (id: number) =>
    apiClient.get(`/donations/${id}/`).then(r => r.data.data),

  myDonations: (params?: Record<string, unknown>) =>
    apiClient.get('/donations/my/', { params }).then(r => r.data),

  leaderboard: (limit = 10) =>
    apiClient.get('/donations/leaderboard/', { params: { limit } }).then(r => r.data.data),
}

// ── Blockchain endpoints ──────────────────────────────────────────

export const blockchainApi = {
  verify: (txHash: string) =>
    apiClient.post('/blockchain/verify/', { tx_hash: txHash }).then(r => r.data.data),

  getTxStatus: (txHash: string) =>
    apiClient.get(`/blockchain/tx/${txHash}/`).then(r => r.data.data),

  getEvents: (params?: Record<string, unknown>) =>
    apiClient.get('/blockchain/events/', { params }).then(r => r.data),

  getStats: () =>
    apiClient.get('/blockchain/stats/').then(r => r.data.data),
}

export default apiClient
