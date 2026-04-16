import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, Loader2, ExternalLink, X } from 'lucide-react'
import { useTxStatus } from '@/hooks/useQueries'
import { explorerTxUrl, shortAddress, cn } from '@/utils/format'

interface TxStatusBannerProps {
  txHash:     string
  onClose?:   () => void
  label?:     string
  className?: string
}

export default function TxStatusBanner({ txHash, onClose, label = 'Transaction', className }: TxStatusBannerProps) {
  const { data } = useTxStatus(txHash)
  const status   = data?.status ?? 'pending'

  const cfgMap = {
    pending:   { icon: <Loader2 size={15} className="animate-spin" />, color: '#60a5fa', bg: 'rgba(59,130,246,0.1)',  text: 'Awaiting confirmation…' },
    confirmed: { icon: <CheckCircle2 size={15} />,                     color: '#10b981', bg: 'rgba(16,185,129,0.1)', text: 'Confirmed on-chain!'    },
    failed:    { icon: <XCircle size={15} />,                          color: '#ef4444', bg: 'rgba(239,68,68,0.1)',   text: 'Transaction failed'      },
    replaced:  { icon: <XCircle size={15} />,                          color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', text: 'Transaction replaced'    },
  } as const
  const cfg = cfgMap[status as keyof typeof cfgMap]
    ?? { icon: <Loader2 size={15} className="animate-spin" />, color: '#60a5fa', bg: 'rgba(59,130,246,0.1)', text: 'Awaiting confirmation…' }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0,  scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.98 }}
        className={cn('rounded-xl px-4 py-3 flex items-center gap-3', className)}
        style={{ background: cfg.bg, border: `1px solid ${cfg.color}30`, color: cfg.color }}
      >
        {cfg.icon}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold">{label}: {cfg.text}</p>
          <a
            href={explorerTxUrl(txHash)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs opacity-70 hover:opacity-100 flex items-center gap-1 mt-0.5 transition-opacity"
            style={{ color: cfg.color }}
          >
            <span className="font-mono">{shortAddress(txHash, 6)}</span>
            <ExternalLink size={10} />
          </a>
        </div>
        {data?.confirmations != null && (
          <span className="text-xs font-mono shrink-0 opacity-70">
            {data.confirmations} conf{data.confirmations !== 1 ? 's' : ''}
          </span>
        )}
        {onClose && (
          <button onClick={onClose} className="opacity-50 hover:opacity-100 transition-opacity ml-1">
            <X size={14} />
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
