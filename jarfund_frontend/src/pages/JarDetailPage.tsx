import { useState }             from 'react'
import { useParams, Link }      from 'react-router-dom'
import { motion }               from 'framer-motion'
import { ArrowLeft, ExternalLink, Share2, CheckCircle2, Clock, Users } from 'lucide-react'
import { useAccount, useWriteContract } from 'wagmi'
import toast                    from 'react-hot-toast'

import { useJar, useWithdrawJar } from '@/hooks/useQueries'
import { useCountdown }           from '@/hooks/useUtils'
import DonationForm               from '@/components/donation/DonationForm'
import DonationRow                from '@/components/donation/DonationRow'
import TxStatusBanner             from '@/components/blockchain/TxStatusBanner'
import { StatusBadge, ProgressBar, WalletAddress, Skeleton, ErrorState } from '@/components/ui/PageSpinner'
import { CONTRACT_ADDRESS, JAR_CATEGORIES, ROUTES } from '@/lib/constants'
import { JARFUND_ABI }            from '@/lib/wagmi'
import { formatMatic, formatDate, explorerTxUrl, cn } from '@/utils/format'
import type { Jar }               from '@/types'

export default function JarDetailPage() {
  const { id }  = useParams<{ id: string }>()
  const jarId   = Number(id)
  const { data: jar, isLoading, isError, refetch } = useJar(jarId)

  if (isLoading) return <JarDetailSkeleton />
  if (isError || !jar) return (
    <div className="max-w-2xl mx-auto py-24 px-4">
      <ErrorState message="Jar not found or failed to load." onRetry={() => refetch()} />
    </div>
  )

  return <JarDetail jar={jar} />
}

// ── Main detail component ─────────────────────────────────────────

function JarDetail({ jar }: { jar: Jar }) {
  const { address } = useAccount()
  const isCreator   = !!address && address.toLowerCase() === jar.creator_wallet?.toLowerCase()
  const category    = JAR_CATEGORIES.find(c => c.value === jar.category)
  const countdown   = useCountdown(jar.deadline)
  const pct         = Math.min(100, jar.progress_percentage)

  const [withdrawTxHash, setWithdrawTxHash] = useState<string | null>(null)
  const withdrawJar        = useWithdrawJar(jar.id)
  const { writeContractAsync } = useWriteContract()

  const handleWithdraw = async () => {
    if (!jar.chain_jar_id) return
    try {
      const txHash = await writeContractAsync({
        address: CONTRACT_ADDRESS as `0x${string}`,
        abi: JARFUND_ABI,
        functionName: 'withdraw',
        args: [BigInt(jar.chain_jar_id)],
      })
      setWithdrawTxHash(txHash)
      await withdrawJar.mutateAsync({ withdrawal_tx_hash: txHash })
      toast.success('Withdrawal submitted!')
    } catch {
      toast.error('Withdrawal failed.')
    }
  }

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    toast.success('Link copied!')
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">

      {/* Back */}
      <Link to={ROUTES.EXPLORE} className="btn-ghost text-sm inline-flex items-center gap-1.5 mb-8 -ml-2">
        <ArrowLeft size={14} /> Back to explore
      </Link>

      <div className="grid lg:grid-cols-[1fr_380px] gap-8 items-start">

        {/* ── LEFT COLUMN ──────────────────────────────────────── */}
        <div className="space-y-8">

          {/* Title block */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <StatusBadge status={jar.status} />
                  {jar.is_verified_on_chain && (
                    <span className="badge-verified text-xs">
                      <CheckCircle2 size={11} /> Verified on-chain
                    </span>
                  )}
                  <span className="text-xs text-text-muted">{category?.emoji} {category?.label}</span>
                </div>
                <h1 className="font-display font-bold text-3xl md:text-4xl text-text-primary leading-tight">
                  <span className="mr-3">{jar.cover_emoji}</span>
                  {jar.title}
                </h1>
              </div>
              <button onClick={handleShare} className="btn-ghost p-2 shrink-0" title="Share">
                <Share2 size={16} />
              </button>
            </div>

            <p className="text-text-secondary leading-relaxed">{jar.description}</p>
          </motion.div>

          {/* Progress block */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}
            className="glass-panel p-6 space-y-5"
          >
            <ProgressBar value={pct} height="md" animated label />

            <div className="grid grid-cols-3 gap-4">
              <div>
                <div className="font-display font-bold text-xl text-text-primary">
                  {formatMatic(jar.amount_raised_matic)}
                </div>
                <div className="text-xs text-text-muted mt-0.5">raised of {formatMatic(jar.target_amount_matic)}</div>
              </div>
              <div>
                <div className="font-display font-bold text-xl text-text-primary flex items-center gap-1.5">
                  <Users size={16} className="text-text-muted" />
                  {jar.donor_count}
                </div>
                <div className="text-xs text-text-muted mt-0.5">donors</div>
              </div>
              <div>
                <div className={cn(
                  'font-display font-bold text-xl',
                  countdown.isExpired ? 'text-warning' :
                  countdown.total < 86400 ? 'text-danger' : 'text-text-primary'
                )}>
                  {countdown.isExpired ? 'Ended' : countdown.days > 0
                    ? `${countdown.days}d ${countdown.hours}h`
                    : `${countdown.hours}h ${countdown.minutes}m`
                  }
                </div>
                <div className="text-xs text-text-muted mt-0.5 flex items-center gap-1">
                  <Clock size={10} />
                  {countdown.isExpired ? 'Campaign ended' : 'remaining'}
                </div>
              </div>
            </div>

            {/* Withdraw button for creator */}
            {isCreator && jar.can_withdraw && jar.status !== 'withdrawn' && (
              <div className="pt-2 border-t border-border">
                {withdrawTxHash && <TxStatusBanner txHash={withdrawTxHash} label="Withdrawal" className="mb-3" />}
                <button onClick={handleWithdraw} className="btn-primary w-full">
                  Withdraw Funds
                </button>
                <p className="text-xs text-text-muted text-center mt-2">
                  You'll receive funds minus 1% platform fee
                </p>
              </div>
            )}
          </motion.div>

          {/* Creator + meta */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}
            className="glass-panel p-5 flex flex-wrap gap-6 text-sm"
          >
            <div>
              <p className="label mb-1">Creator</p>
              <WalletAddress address={jar.creator_wallet} />
              {jar.creator_display_name && (
                <span className="text-xs text-text-muted ml-2">{jar.creator_display_name}</span>
              )}
            </div>
            <div>
              <p className="label mb-1">Created</p>
              <span className="text-text-secondary">{formatDate(jar.created_at)}</span>
            </div>
            <div>
              <p className="label mb-1">Deadline</p>
              <span className="text-text-secondary">{formatDate(jar.deadline)}</span>
            </div>
            {jar.creation_tx_hash && (
              <div>
                <p className="label mb-1">Contract TX</p>
                <a href={explorerTxUrl(jar.creation_tx_hash)} target="_blank" rel="noopener noreferrer"
                  className="tx-link inline-flex items-center gap-1">
                  View <ExternalLink size={11} />
                </a>
              </div>
            )}
          </motion.div>

          {/* Donation feed */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}
            className="space-y-3"
          >
            <h2 className="font-display font-semibold text-lg text-text-primary">
              Donations
              <span className="ml-2 text-sm text-text-muted font-body font-normal">({jar.donor_count})</span>
            </h2>

            {jar.donations && jar.donations.length > 0 ? (
              <div className="glass-panel p-2 space-y-0.5">
                {jar.donations.map((d, i) => (
                  <DonationRow key={d.id} donation={d} index={i} />
                ))}
              </div>
            ) : (
              <div className="glass-panel p-8 text-center text-text-muted">
                <p className="text-sm">No donations yet. Be the first!</p>
              </div>
            )}
          </motion.div>
        </div>

        {/* ── RIGHT COLUMN: Donation form ───────────────────────── */}
        <motion.div
          initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}
          className="lg:sticky lg:top-24"
        >
          <div className="glass-card p-6">
            <h2 className="font-display font-bold text-lg text-text-primary mb-5">
              Support this campaign
            </h2>
            <DonationForm jar={jar} />
          </div>
        </motion.div>

      </div>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────

function JarDetailSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <div className="h-8 w-24 mb-8"><Skeleton className="h-full w-full" /></div>
      <div className="grid lg:grid-cols-[1fr_380px] gap-8">
        <div className="space-y-6">
          <Skeleton className="h-10 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-32 w-full rounded-2xl" />
          <Skeleton className="h-20 w-full rounded-2xl" />
        </div>
        <Skeleton className="h-80 w-full rounded-3xl" />
      </div>
    </div>
  )
}
