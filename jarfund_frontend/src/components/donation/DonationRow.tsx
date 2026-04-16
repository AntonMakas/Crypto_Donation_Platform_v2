import { motion } from 'framer-motion'
import { ExternalLink, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { WalletAddress } from '@/components/ui/PageSpinner'
import { formatMatic, timeAgo, explorerTxUrl } from '@/utils/format'
import type { Donation, TxStatus } from '@/types'

interface DonationRowProps {
  donation: Donation
  index?:   number
  showJar?: boolean
}

const STATUS_ICON: Record<TxStatus, JSX.Element> = {
  confirmed: <CheckCircle2 size={13} className="text-success" />,
  pending:   <Loader2     size={13} className="text-info animate-spin" />,
  failed:    <XCircle     size={13} className="text-danger/70" />,
  replaced:  <XCircle     size={13} className="text-warning/70" />,
}

export default function DonationRow({ donation, index = 0, showJar = false }: DonationRowProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
      className="flex items-center justify-between gap-4 py-3 px-4 rounded-xl
                 hover:bg-white/[0.03] transition-colors group"
    >
      {/* Left: donor + message */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Status dot */}
        <div className="shrink-0">
          {STATUS_ICON[donation.tx_status] ?? STATUS_ICON.pending}
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <WalletAddress address={donation.donor_wallet} />
            {showJar && (
              <span className="text-xs text-text-disabled truncate max-w-[120px]">
                → {donation.jar_title}
              </span>
            )}
          </div>
          {donation.message && (
            <p className="text-xs text-text-muted mt-0.5 truncate max-w-[220px] italic">
              "{donation.message}"
            </p>
          )}
        </div>
      </div>

      {/* Right: amount + time + tx */}
      <div className="flex items-end flex-col gap-0.5 shrink-0 text-right">
        <span className="font-display font-semibold text-sm text-text-primary">
          {formatMatic(donation.amount_matic)}
        </span>
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <Clock size={10} />
          <span>{timeAgo(donation.created_at)}</span>
          <a
            href={explorerTxUrl(donation.tx_hash)}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-primary/60 hover:text-primary"
          >
            <ExternalLink size={10} />
          </a>
        </div>
      </div>
    </motion.div>
  )
}
