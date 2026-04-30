// ═══════════════════════════════════════════════════════════════
//  JarFund — App Constants
// ═══════════════════════════════════════════════════════════════

import type { JarCategory, JarStatus } from '@/types'

// ── Environment ──────────────────────────────────────────────────

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string
  ?? 'http://localhost:8000/api/v1'

export const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS as string ?? ''
export const CHAIN_ID         = Number(import.meta.env.VITE_CHAIN_ID ?? 80002)
export const CHAIN_NAME       = import.meta.env.VITE_CHAIN_NAME as string ?? 'amoy'
export const EXPLORER_URL     = import.meta.env.VITE_EXPLORER_URL as string
  ?? 'https://amoy.polygonscan.com'
export const RPC_URL          = import.meta.env.VITE_RPC_URL as string
  ?? 'https://rpc-amoy.polygon.technology'
export const WALLETCONNECT_PROJECT_ID = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID as string ?? ''
export const DEBUG            = import.meta.env.VITE_DEBUG === 'true'

// ── Polygon Amoy chain definition ────────────────────────────────

export const POLYGON_AMOY_CHAIN = {
  id:        80002,
  name:      'Polygon Amoy',
  nativeCurrency: {
    name:     'POL',
    symbol:   'POL',
    decimals: 18,
  },
  rpcUrls: {
    default:  { http: ['https://rpc-amoy.polygon.technology'] },
    public:   { http: ['https://rpc-amoy.polygon.technology'] },
  },
  blockExplorers: {
    default: {
      name: 'PolygonScan',
      url:  'https://amoy.polygonscan.com',
    },
  },
  testnet: true,
} as const

export const POLYGON_MAINNET_CHAIN = {
  id:        137,
  name:      'Polygon',
  nativeCurrency: {
    name:     'POL',
    symbol:   'POL',
    decimals: 18,
  },
  rpcUrls: {
    default: { http: ['https://polygon-rpc.com'] },
    public:  { http: ['https://polygon-rpc.com'] },
  },
  blockExplorers: {
    default: {
      name: 'PolygonScan',
      url:  'https://polygonscan.com',
    },
  },
} as const

// ── Donation / Jar constraints (mirrors smart contract) ──────────

export const MIN_DONATION_MATIC  = 0.001
export const MIN_TARGET_MATIC    = 0.01
export const MAX_TARGET_MATIC    = 10_000_000
export const MIN_DEADLINE_HOURS  = 1
export const MAX_DEADLINE_DAYS   = 365
export const MAX_TITLE_LENGTH    = 120
export const MAX_DESCRIPTION_LENGTH = 1000
export const MAX_MESSAGE_LENGTH  = 280
export const PLATFORM_FEE_BPS    = 100    // 1%

// ── Jar categories ────────────────────────────────────────────────

export const JAR_CATEGORIES: Array<{
  value: JarCategory
  label: string
  emoji: string
}> = [
  { value: 'humanitarian', label: 'Humanitarian', emoji: '🤝' },
  { value: 'technology',   label: 'Technology',   emoji: '💻' },
  { value: 'education',    label: 'Education',     emoji: '🎓' },
  { value: 'environment',  label: 'Environment',   emoji: '🌱' },
  { value: 'healthcare',   label: 'Healthcare',    emoji: '❤️'  },
  { value: 'gaming',       label: 'Gaming',        emoji: '🎮' },
  { value: 'arts',         label: 'Arts & Culture',emoji: '🎨' },
  { value: 'community',    label: 'Community',     emoji: '🏘️' },
  { value: 'research',     label: 'Research',      emoji: '🔬' },
  { value: 'other',        label: 'Other',         emoji: '✨' },
]

// ── Jar status display ────────────────────────────────────────────

export const JAR_STATUS_CONFIG: Record<JarStatus, {
  label:  string
  color:  string
  bgColor: string
  dot:    string
}> = {
  active:    { label: 'Active',    color: '#34d399', bgColor: 'rgba(16,185,129,0.15)',  dot: 'bg-success'  },
  completed: { label: 'Completed', color: '#c084fc', bgColor: 'rgba(124,58,237,0.15)',  dot: 'bg-primary'  },
  expired:   { label: 'Expired',   color: '#fbbf24', bgColor: 'rgba(245,158,11,0.15)',  dot: 'bg-warning'  },
  withdrawn: { label: 'Withdrawn', color: '#f87171', bgColor: 'rgba(239,68,68,0.12)',   dot: 'bg-danger'   },
}

// ── Routes ────────────────────────────────────────────────────────

export const ROUTES = {
  HOME:       '/',
  EXPLORE:    '/explore',
  JAR:        (id: number | string) => `/jar/${id}`,
  CREATE:     '/create',
  PROFILE:    '/profile',
  TX:         (hash: string) => `/tx/${hash}`,
} as const

// ── Local storage keys ────────────────────────────────────────────

export const STORAGE_KEYS = {
  ACCESS_TOKEN:  'jarfund_access',
  REFRESH_TOKEN: 'jarfund_refresh',
  USER:          'jarfund_user',
  THEME:         'jarfund_theme',
} as const

// ── Query cache keys ──────────────────────────────────────────────

export const QUERY_KEYS = {
  JARS:           ['jars'] as const,
  JAR:            (id: number) => ['jar', id] as const,
  MY_JARS:        ['my-jars'] as const,
  JAR_DONATIONS:  (id: number) => ['jar-donations', id] as const,
  JAR_STATS:      (id: number) => ['jar-stats', id] as const,
  DONATIONS:      ['donations'] as const,
  MY_DONATIONS:   ['my-donations'] as const,
  LEADERBOARD:    ['leaderboard'] as const,
  PLATFORM_STATS: ['platform-stats'] as const,
  TX_STATUS:      (hash: string) => ['tx-status', hash] as const,
  PROFILE:        ['profile'] as const,
  USER:           (wallet: string) => ['user', wallet] as const,
} as const

// ── Animation durations (ms) ──────────────────────────────────────

export const ANIMATION = {
  FAST:   150,
  NORMAL: 300,
  SLOW:   500,
  STAGGER: 75,
} as const

// ── Pagination ────────────────────────────────────────────────────

export const DEFAULT_PAGE_SIZE = 12

// ── Polling intervals ─────────────────────────────────────────────

export const POLL_INTERVALS = {
  TX_PENDING:    10_000,  // 10s — poll for pending tx confirmation
  PLATFORM_STATS: 60_000,  // 60s — refresh landing page stats
  JAR_DETAIL:    30_000,  // 30s — refresh jar raised amount
} as const
