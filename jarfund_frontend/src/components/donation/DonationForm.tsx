import { useEffect, useState }        from 'react'
import { useForm }          from 'react-hook-form'
import { zodResolver }      from '@hookform/resolvers/zod'
import { z }                from 'zod'
import { Wallet, Heart, EyeOff, AlertCircle } from 'lucide-react'
import { useAccount, useConnect, useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { parseEther }        from 'viem'
import { injected }          from 'wagmi/connectors'
import toast                 from 'react-hot-toast'

import { useAuth }           from '@/contexts/AuthContext'
import { useSubmitDonation } from '@/hooks/useQueries'
import { InlineSpinner }     from '@/components/ui/PageSpinner'
import { extractApiError }   from '@/lib/api'
import { CONTRACT_ADDRESS, MIN_DONATION_MATIC, CHAIN_ID, EXPLORER_URL } from '@/lib/constants'
import { JARFUND_ABI }       from '@/lib/wagmi'
import { maticToWeiString, formatMatic }         from '@/utils/format'
import type { Jar }          from '@/types'

const schema = z.object({
  amount:      z.string().refine(v => parseFloat(v) >= MIN_DONATION_MATIC, {
    message: `Minimum donation is ${MIN_DONATION_MATIC} MATIC`,
  }),
  message:     z.string().max(280).optional(),
  is_anonymous: z.boolean().optional(),
})

type FormValues = z.infer<typeof schema>

const QUICK_AMOUNTS = ['0.1', '0.5', '1', '5']

interface DonationFormProps {
  jar: Jar
}

export default function DonationForm({ jar }: DonationFormProps) {
  const [pendingTxHash, setPendingTxHash] = useState<string | null>(null)
  const [step, setStep] = useState<'form' | 'pending' | 'done'>('form')
  const [backendRecorded, setBackendRecorded] = useState(false)
  const [backendError, setBackendError] = useState<string | null>(null)

  const { isAuthenticated, signIn, isLoading: authLoading } = useAuth()
  const { address, isConnected } = useAccount()
  const { connect }              = useConnect()
  const { writeContractAsync }   = useWriteContract()
  const submitDonation           = useSubmitDonation()
  const { data: receipt, isLoading: waitingForReceipt } = useWaitForTransactionReceipt({
    hash: pendingTxHash as `0x${string}` | undefined,
    chainId: CHAIN_ID,
  })

  const { register, handleSubmit, setValue, watch, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { amount: '0.5', is_anonymous: false },
  })

  const amount = watch('amount')

  useEffect(() => {
    if (!receipt || step !== 'pending') return
    setStep('done')
    if (backendRecorded) {
      toast.success('Donation confirmed on-chain!')
    } else {
      toast.error('Donation confirmed on-chain, but backend recording failed.')
    }
  }, [receipt, step, backendRecorded])

  const onSubmit = async (values: FormValues) => {
    if (!address || !isAuthenticated) return

    try {
      // 1. Send on-chain transaction
      const amountFloat = parseFloat(values.amount)
      if (isNaN(amountFloat) || amountFloat < MIN_DONATION_MATIC) {
        toast.error(`Minimum donation is ${MIN_DONATION_MATIC} MATIC`)
        return
      }
      if (!jar.chain_jar_id) {
        toast.error('This jar is not linked on-chain yet.')
        return
      }
      if (address.toLowerCase() === jar.creator_wallet.toLowerCase()) {
        toast.error('Jar creators cannot donate to their own jar.')
        return
      }

      const txHash = await writeContractAsync({
        address: CONTRACT_ADDRESS as `0x${string}`,
        abi: JARFUND_ABI,
        functionName: 'donate',
        args: [BigInt(jar.chain_jar_id)],
        value: parseEther(values.amount),
      })

      setPendingTxHash(txHash)
      setStep('pending')
      setBackendRecorded(false)
      setBackendError(null)

      // 2. Record in backend
      try {
        await submitDonation.mutateAsync({
          jar_id:       jar.id,
          donor_wallet: address,
          amount_matic: values.amount,
          amount_wei:   maticToWeiString(values.amount),
          tx_hash:      txHash,
          message:      values.message ?? '',
          is_anonymous: values.is_anonymous ?? false,
        })
        setBackendRecorded(true)
        toast.success('Donation submitted! Verification in progress.')
      } catch (submitErr) {
        const message = extractApiError(submitErr)
        setBackendError(message)
        toast.error(message)
      }

    } catch (err: unknown) {
      const msg = (err as Error)?.message ?? ''
      if (msg.includes('rejected') || msg.includes('denied')) {
        toast.error('Transaction cancelled.')
      } else {
        toast.error('Transaction failed. Please try again.')
      }
      setStep('form')
    }
  }

  // Not connected
  if (!isConnected) {
    return (
      <div className="glass-panel p-6 text-center space-y-4">
        <Wallet size={32} className="mx-auto text-primary-300" />
        <p className="font-display font-semibold text-text-primary">Connect to donate</p>
        <p className="text-sm text-text-muted">You need a MetaMask wallet to send MATIC.</p>
        <button onClick={() => connect({ connector: injected() })} className="btn-primary w-full">
          Connect Wallet
        </button>
      </div>
    )
  }

  // Connected but not signed in
  if (!isAuthenticated) {
    return (
      <div className="glass-panel p-6 text-center space-y-4">
        <Heart size={32} className="mx-auto text-primary-300" />
        <p className="font-display font-semibold text-text-primary">Sign in to donate</p>
        <p className="text-sm text-text-muted">Verify your wallet ownership to proceed.</p>
        <button onClick={signIn} disabled={authLoading} className="btn-primary w-full">
          {authLoading ? <InlineSpinner size={16} /> : 'Sign In with Wallet'}
        </button>
      </div>
    )
  }

  // Jar not accepting donations
  if (jar.status !== 'active' || jar.is_deadline_passed) {
    return (
      <div className="glass-panel p-6 text-center space-y-3">
        <AlertCircle size={28} className="mx-auto text-warning/60" />
        <p className="font-display font-semibold text-text-primary">Donations closed</p>
        <p className="text-sm text-text-muted">
          This jar is {jar.status === 'completed' ? 'fully funded' : jar.status}.
        </p>
      </div>
    )
  }

  // Done state
  if (step === 'done' && pendingTxHash) {
    return (
      <div className="glass-panel p-6 space-y-4 text-center">
        <p className="font-display font-semibold text-text-primary">
          {receipt ? 'Donation confirmed on-chain' : 'Donation submitted'}
        </p>
        <p className="text-sm text-text-muted">
          {backendRecorded
            ? 'Your donation has been recorded and will be verified by the backend shortly.'
            : backendError ?? 'The blockchain transaction succeeded, but the backend could not record it automatically.'}
        </p>
        <a
          href={`${EXPLORER_URL}/tx/${pendingTxHash}`}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary w-full"
        >
          View on PolygonScan
        </a>
        <button onClick={() => { setStep('form'); setPendingTxHash(null) }}
          className="btn-ghost text-sm w-full">
          Donate again
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

      {/* Pending tx */}
      {step === 'pending' && pendingTxHash && (
        <div className="glass-panel p-4 text-sm text-text-muted text-center space-y-2">
          <p className="font-medium text-text-primary">Donation transaction submitted</p>
          <p>
            {waitingForReceipt
              ? 'Waiting for block confirmation...'
              : 'Waiting for the transaction receipt...'}
          </p>
          <a
            href={`${EXPLORER_URL}/tx/${pendingTxHash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-300 hover:text-primary-200 transition-colors"
          >
            View live on PolygonScan
          </a>
          {backendError && (
            <p className="text-danger text-xs">{backendError}</p>
          )}
        </div>
      )}

      {/* Amount */}
      <div>
        <label className="label">Amount (MATIC)</label>
        <div className="relative">
          <input
            {...register('amount')}
            type="number"
            step="0.001"
            min={MIN_DONATION_MATIC}
            placeholder="0.5"
            className={`input pr-16 ${errors.amount ? 'error' : ''}`}
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-text-muted">MATIC</span>
        </div>
        {errors.amount && (
          <p className="text-xs text-danger mt-1">{errors.amount.message}</p>
        )}

        {/* Quick amounts */}
        <div className="flex gap-2 mt-2">
          {QUICK_AMOUNTS.map(v => (
            <button
              key={v}
              type="button"
              onClick={() => setValue('amount', v)}
              className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                amount === v
                  ? 'border-primary/40 bg-primary-dim text-primary-300'
                  : 'border-border text-text-muted hover:border-border-bright'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Message */}
      <div>
        <label className="label">Message <span className="normal-case font-normal text-text-disabled">(optional)</span></label>
        <textarea
          {...register('message')}
          placeholder="Leave a message of support…"
          rows={2}
          className="textarea"
        />
      </div>

      {/* Anonymous */}
      <label className="flex items-center gap-3 cursor-pointer group">
        <input
          {...register('is_anonymous')}
          type="checkbox"
          className="w-4 h-4 rounded border-border bg-transparent accent-primary cursor-pointer"
        />
        <span className="flex items-center gap-1.5 text-sm text-text-secondary group-hover:text-text-primary transition-colors">
          <EyeOff size={14} />
          Donate anonymously
        </span>
      </label>

      {/* Submit */}
      <button
        type="submit"
        disabled={isSubmitting || step === 'pending'}
        className="btn-primary w-full py-4 text-base"
      >
        {isSubmitting || step === 'pending' ? (
          <span className="flex items-center gap-2">
            <InlineSpinner size={16} />
            {step === 'pending' ? 'Confirming…' : 'Sending…'}
          </span>
        ) : (
          <>
            <Heart size={16} fill="currentColor" />
            Donate {amount && parseFloat(amount) > 0 ? formatMatic(amount) : ''}
          </>
        )}
      </button>

      <p className="text-xs text-text-muted text-center">
        1% platform fee · Funds go directly to smart contract
      </p>
    </form>
  )
}
