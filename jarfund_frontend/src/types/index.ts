// ═══════════════════════════════════════════════════════════════
//  JarFund — Shared TypeScript Types
//  Mirror the Django REST API response shapes exactly.
// ═══════════════════════════════════════════════════════════════

// ── Enums ────────────────────────────────────────────────────────

export type JarStatus = 'active' | 'completed' | 'expired' | 'withdrawn'
export type JarCategory =
  | 'humanitarian' | 'technology' | 'education'
  | 'environment'  | 'healthcare'  | 'gaming'
  | 'arts'         | 'community'   | 'research' | 'other'

export type TxStatus = 'pending' | 'confirmed' | 'failed' | 'replaced'

// ── User / Auth ──────────────────────────────────────────────────

export interface User {
  id:              number
  wallet_address:  string
  short_wallet:    string
  display_name:    string
  username:        string
  bio:             string
  avatar_url:      string
  is_verified:     boolean
  is_staff:        boolean
  total_donated:   string   // MATIC as decimal string
  total_raised:    string
  jars_count:      number
  donations_count: number
  created_at:      string   // ISO 8601
  last_login_at:   string | null
}

export interface AuthTokens {
  access:  string
  refresh: string
}

export interface AuthResponse {
  access:  string
  refresh: string
  user:    User
}

// ── Jar ──────────────────────────────────────────────────────────

export interface Jar {
  id:                    number
  chain_jar_id:          number | null
  title:                 string
  description:           string
  category:              JarCategory
  cover_emoji:           string
  cover_image_url:       string

  creator_wallet:        string
  creator_display_name:  string

  target_amount_matic:   string
  amount_raised_matic:   string

  deadline:              string   // ISO 8601
  status:                JarStatus

  is_verified_on_chain:  boolean
  creation_tx_hash:      string

  donor_count:           number

  // Computed
  progress_percentage:    number
  time_remaining_seconds: number
  can_withdraw:           boolean
  is_deadline_passed:     boolean
  explorer_url:           string

  created_at:             string
  updated_at?:            string

  // Detail only
  donations?:             Donation[]
  withdrawal_tx_hash?:    string
  withdrawn_at?:          string | null
}

export interface JarCreatePayload {
  title:               string
  description:         string
  category:            JarCategory
  cover_emoji:         string
  cover_image_url?:    string
  target_amount_matic: string
  deadline:            string
  creation_tx_hash?:   string
  chain_jar_id?:       number | null
}

export interface JarUpdatePayload {
  title?:          string
  description?:    string
  category?:       JarCategory
  cover_emoji?:    string
  cover_image_url?: string
}

export interface JarConfirmPayload {
  chain_jar_id:     number
  creation_tx_hash: string
}

export interface JarWithdrawPayload {
  withdrawal_tx_hash: string
}

export interface DonationStats {
  total_confirmed:    string
  total_pending:      string
  donor_count:        number
  donation_count:     number
  largest_donation:   string
  average_donation:   string
  latest_donation_at: string | null
}

// ── Donation ─────────────────────────────────────────────────────

export interface Donation {
  id:              number
  jar_id:          number
  jar_title:       string
  donor_wallet:    string   // 'Anonymous' if is_anonymous
  amount_matic:    string
  tx_hash:         string
  tx_status:       TxStatus
  is_verified:     boolean
  is_anonymous:    boolean
  message:         string
  block_number:    number | null
  confirmations:   number
  explorer_url:    string
  created_at:      string
  verified_at:     string | null

  // Detail only
  amount_wei?:          string
  block_timestamp?:     string | null
  gas_used?:            number | null
  gas_price_gwei?:      string | null
  verification_attempts?: number
  last_verified_at?:    string | null
  updated_at?:          string
}

export interface DonationCreatePayload {
  jar_id:       number
  donor_wallet: string
  amount_matic: string
  amount_wei:   string
  tx_hash:      string
  message?:     string
  is_anonymous?: boolean
}

export interface MyDonationStats {
  total_donated_matic: string
  confirmed_count:     number
  pending_count:       number
}

export interface LeaderboardEntry {
  donor_wallet:   string
  total_donated:  string
  donation_count: number
}

// ── Blockchain ───────────────────────────────────────────────────

export interface TxStatus_ {
  tx_hash:        string
  status:         TxStatus
  is_verified:    boolean
  block_number:   number | null
  confirmations:  number
  gas_used:       number | null
  gas_price_gwei: string | null
  verified_at:    string | null
  explorer_url:   string
  source:         'db' | 'rpc'
}

export interface ContractEvent {
  id:              number
  tx_hash:         string
  event_type:      string
  log_index:       number
  block_number:    number
  block_timestamp: string | null
  event_data:      Record<string, unknown>
  chain_jar_id:    number | null
  emitter_wallet:  string
  created_at:      string
}

export interface PlatformStats {
  total_jars:          number
  active_jars:         number
  completed_jars:      number
  total_raised_matic:  string
  total_donors:        number
  total_donations:     number
  verified_donations:  number
  donations_last_24h:  number
  raised_last_24h:     string
}

// ── API helpers ──────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count:       number
  total_pages: number
  next:        string | null
  previous:    string | null
  results:     T[]
}

export interface ApiSuccess<T> {
  success: true
  data:    T
  message?: string
  cached?: boolean
}

export interface ApiError {
  success: false
  error: {
    code:     string
    message:  string
    details?: Record<string, string[]>
  }
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError

// ── Filter / Query params ─────────────────────────────────────────

export interface JarFilters {
  status?:          JarStatus
  category?:        JarCategory
  search?:          string
  creator_wallet?:  string
  is_verified?:     boolean
  min_target?:      number
  max_target?:      number
  ordering?:        string
  page?:            number
  page_size?:       number
  include_all?:     boolean
}

// ── UI State ──────────────────────────────────────────────────────

export interface ToastOptions {
  type:     'success' | 'error' | 'info' | 'loading'
  title:    string
  message?: string
  duration?: number
  txHash?:  string   // shows explorer link
}

export type LoadingState = 'idle' | 'loading' | 'success' | 'error'
