// ═══════════════════════════════════════════════════════════════
//  AuthContext
//
//  Manages:
//   · JWT access / refresh tokens (localStorage)
//   · Authenticated user profile
//   · MetaMask sign-in flow: nonce → sign → verify → store tokens
//   · Logout + token refresh
//   · Listens for 'jarfund:logout' event fired by axios interceptor
// ═══════════════════════════════════════════════════════════════

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useAccount, useSignMessage, useDisconnect } from 'wagmi'
import toast from 'react-hot-toast'
import { authApi, tokenStorage, extractApiError } from '@/lib/api'
import { STORAGE_KEYS } from '@/lib/constants'
import type { User } from '@/types'

// ── Types ─────────────────────────────────────────────────────────

type AuthStatus = 'idle' | 'signing' | 'verifying' | 'authenticated' | 'error'

interface AuthContextValue {
  user:          User | null
  status:        AuthStatus
  isAuthenticated: boolean
  isLoading:     boolean

  // Actions
  signIn:        () => Promise<void>
  signOut:       () => Promise<void>
  refreshProfile: () => Promise<void>
  updateProfile: (data: Partial<Pick<User, 'username' | 'bio' | 'avatar_url'>>) => Promise<void>
}

// ── Context ───────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

// ── Provider ──────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const { address, isConnected } = useAccount()
  const { signMessageAsync }     = useSignMessage()
  const { disconnect }           = useDisconnect()

  const [user,   setUser]   = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.USER)
      return stored ? JSON.parse(stored) : null
    } catch { return null }
  })
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStorage.getAccess() && localStorage.getItem(STORAGE_KEYS.USER)
      ? 'authenticated'
      : 'idle'
  )

  const signInInProgress = useRef(false)

  // ── Persist user to localStorage ─────────────────────────────

  const saveUser = useCallback((u: User | null) => {
    setUser(u)
    if (u) localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(u))
    else   localStorage.removeItem(STORAGE_KEYS.USER)
  }, [])

  // ── Listen for forced logout from axios interceptor ───────────

  useEffect(() => {
    const handleForceLogout = () => {
      saveUser(null)
      setStatus('idle')
      toast.error('Session expired. Please sign in again.')
    }
    window.addEventListener('jarfund:logout', handleForceLogout)
    return () => window.removeEventListener('jarfund:logout', handleForceLogout)
  }, [saveUser])

  // ── Verify existing token on mount ────────────────────────────

  useEffect(() => {
    if (!tokenStorage.getAccess() || user) return
    authApi.getProfile()
      .then(saveUser)
      .catch(() => {
        tokenStorage.clearTokens()
        setStatus('idle')
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Sign in ──────────────────────────────────────────────────

  const signIn = useCallback(async () => {
    if (!address || !isConnected) {
      toast.error('Connect your wallet first.')
      return
    }
    if (signInInProgress.current) return
    signInInProgress.current = true

    try {
      setStatus('signing')

      // 1. Get nonce from backend
      const { message } = await authApi.getNonce(address)

      // 2. Ask MetaMask to sign the message
      let signature: string
      try {
        signature = await signMessageAsync({ message })
      } catch (err: unknown) {
        const msg = (err as Error)?.message ?? ''
        if (msg.includes('User rejected') || msg.includes('denied')) {
          toast.error('Signature cancelled.')
        } else {
          toast.error('Signing failed. Please try again.')
        }
        setStatus('idle')
        return
      }

      // 3. Verify signature with backend → receive JWT tokens
      setStatus('verifying')
      const authData = await authApi.verify(address, signature)

      tokenStorage.setTokens({
        access:  authData.access,
        refresh: authData.refresh,
      })
      saveUser(authData.user)
      setStatus('authenticated')
      toast.success('Signed in successfully!')

    } catch (err) {
      setStatus('error')
      toast.error(extractApiError(err))
      setTimeout(() => setStatus('idle'), 2000)
    } finally {
      signInInProgress.current = false
    }
  }, [address, isConnected, signMessageAsync, saveUser])

  // ── Sign out ─────────────────────────────────────────────────

  const signOut = useCallback(async () => {
    const refresh = tokenStorage.getRefresh()
    if (refresh) {
      try { await authApi.logout(refresh) } catch { /* best-effort */ }
    }
    tokenStorage.clearTokens()
    saveUser(null)
    setStatus('idle')
    disconnect()
    toast.success('Signed out.')
  }, [saveUser, disconnect])

  // ── Refresh profile ───────────────────────────────────────────

  const refreshProfile = useCallback(async () => {
    if (!tokenStorage.getAccess()) return
    try {
      const fresh = await authApi.getProfile()
      saveUser(fresh)
    } catch (err) {
      console.error('Profile refresh failed:', err)
    }
  }, [saveUser])

  // ── Update profile ────────────────────────────────────────────

  const updateProfile = useCallback(async (
    data: Partial<Pick<User, 'username' | 'bio' | 'avatar_url'>>
  ) => {
    const updated = await authApi.updateProfile(data)
    saveUser(updated)
  }, [saveUser])

  const value: AuthContextValue = {
    user,
    status,
    isAuthenticated: status === 'authenticated' && !!user,
    isLoading:       status === 'signing' || status === 'verifying',
    signIn,
    signOut,
    refreshProfile,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ── Hook ──────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
