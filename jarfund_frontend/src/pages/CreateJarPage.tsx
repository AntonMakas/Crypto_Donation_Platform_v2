import { useState }         from 'react'
import { useNavigate }       from 'react-router-dom'
import { useForm }           from 'react-hook-form'
import { zodResolver }       from '@hookform/resolvers/zod'
import { z }                 from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, ArrowLeft, CheckCircle2, Wallet, Info } from 'lucide-react'
import { useAccount, useConnect, useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { decodeEventLog, parseEther } from 'viem'
import { injected }          from 'wagmi/connectors'
import toast                 from 'react-hot-toast'

import { useAuth }           from '@/contexts/AuthContext'
import { useCreateJar, useConfirmJar } from '@/hooks/useQueries'
import { InlineSpinner }     from '@/components/ui/PageSpinner'
import TxStatusBanner        from '@/components/blockchain/TxStatusBanner'
import { JAR_CATEGORIES, ROUTES, MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH, CONTRACT_ADDRESS } from '@/lib/constants'
import { JARFUND_ABI }       from '@/lib/wagmi'
import { cn }                from '@/utils/format'
import type { JarCategory }  from '@/types'

// ── Schema ────────────────────────────────────────────────────────

const schema = z.object({
  title:       z.string().min(3, 'At least 3 characters').max(MAX_TITLE_LENGTH),
  description: z.string().min(20, 'At least 20 characters').max(MAX_DESCRIPTION_LENGTH),
  category:    z.string().min(1, 'Pick a category'),
  cover_emoji: z.string().optional(),
  target_amount_matic: z.string().refine(v => parseFloat(v) >= 0.01, 'Minimum target is 0.01 MATIC'),
  deadline:    z.string().refine(v => new Date(v) > new Date(Date.now() + 3_600_000), 'Must be at least 1 hour from now'),
})
type FormValues = z.infer<typeof schema>

// ── Steps ─────────────────────────────────────────────────────────

const STEPS = [
  { n: 1, label: 'Details'    },
  { n: 2, label: 'Deploy'     },
  { n: 3, label: 'Confirm'    },
]

export default function CreateJarPage() {
  const navigate    = useNavigate()
  const [step, setStep] = useState(1)
  const [createdJarId, setCreatedJarId] = useState<number | null>(null)
  const [txHash, setTxHash] = useState<string | null>(null)
  const [onChainJarId, setOnChainJarId] = useState<number | null>(null)

  const { isAuthenticated, isLoading: authLoading, signIn } = useAuth()
  const { address, isConnected }   = useAccount()
  const { connect, connectors } = useConnect()
  const createJar                  = useCreateJar()
  const confirmJar                 = useConfirmJar(createdJarId ?? 0)

  const { writeContractAsync }     = useWriteContract()
  const { data: receipt, isLoading: waitingForReceipt } = useWaitForTransactionReceipt({
    hash: txHash as `0x${string}` | undefined,
  })

  const { register, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { cover_emoji: '🫙', category: '', target_amount_matic: '1', deadline: '' },
  })

  const title    = watch('title') ?? ''
  const category = watch('category')
  const emoji    = watch('cover_emoji')

  // ── Not connected ────────────────────────────────────────────

  if (!isConnected) {
    return (
      <div className="max-w-md mx-auto px-4 py-24 text-center space-y-6">
        <div className="glass-card p-10 space-y-5">
          <Wallet size={40} className="mx-auto text-primary-300" />
          <h1 className="font-display font-bold text-2xl text-text-primary">Connect your wallet</h1>
          <p className="text-text-muted text-sm">You need MetaMask to create a jar on Polygon.</p>
          <button onClick={() => connect({ connector: connectors.find(c => c.id === 'injected') ?? connectors[0] })} className="btn-primary w-full">Connect Wallet</button>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-md mx-auto px-4 py-24 text-center space-y-6">
        <div className="glass-card p-10 space-y-5">
          <span className="text-5xl block">🔏</span>
          <h1 className="font-display font-bold text-2xl text-text-primary">Sign in first</h1>
          <p className="text-text-muted text-sm">Verify wallet ownership to create a jar.</p>
          <button onClick={signIn} disabled={authLoading} className="btn-primary w-full">
            {authLoading ? <InlineSpinner size={16} /> : 'Sign In with Wallet'}
          </button>
        </div>
      </div>
    )
  }

  // ── Step 1: Fill details ──────────────────────────────────────

  const onSubmitDetails = async (values: FormValues) => {
    const jar = await createJar.mutateAsync({
      title:               values.title,
      description:         values.description,
      category:            values.category as JarCategory,
      cover_emoji:         values.cover_emoji ?? '🫙',
      target_amount_matic: values.target_amount_matic,
      deadline:            new Date(values.deadline).toISOString(),
    })
    setCreatedJarId(jar.id)
    setStep(2)
  }

  // ── Step 2: Deploy on-chain ───────────────────────────────────

  const deployOnChain = async () => {
    const values = watch()
    try {
      const deadlineTs = Math.floor(new Date(values.deadline).getTime() / 1000)
      const targetWei  = parseEther(values.target_amount_matic)

      const hash = await writeContractAsync({
        address:      CONTRACT_ADDRESS as `0x${string}`,
        abi:          JARFUND_ABI,
        functionName: 'createJar',
        args: [
          values.title,
          values.description,
          targetWei,
          BigInt(deadlineTs),
        ],
      })
      setTxHash(hash)
      toast.success('Transaction submitted! Waiting for confirmation…')
      setStep(3)
    } catch (err: unknown) {
      const msg = (err as Error)?.message ?? ''
      if (!msg.includes('rejected')) toast.error('Transaction failed.')
    }
  }

  // ── Step 3: Confirm once receipt arrives ──────────────────────

  const handleConfirm = async () => {
    if (!receipt || !createdJarId || !txHash) return

    let jarIdFromEvent: number | null = null

    for (const log of receipt.logs) {
      try {
        const decoded = decodeEventLog({
          abi: JARFUND_ABI,
          data: log.data,
          topics: log.topics,
        })

        if (decoded.eventName === 'JarCreated') {
          jarIdFromEvent = Number(decoded.args.jarId)
          break
        }
      } catch {
        // Ignore unrelated logs in the same transaction receipt.
      }
    }

    if (!jarIdFromEvent) {
      toast.error('Could not read the jar ID from the transaction receipt.')
      return
    }

    try {
      await confirmJar.mutateAsync({
        chain_jar_id:     jarIdFromEvent,
        creation_tx_hash: txHash,
      })
      toast.success('🎉 Jar is live on Polygon!')
      navigate(ROUTES.JAR(createdJarId))
    } catch {
      toast.error('Confirmation failed.')
    }
  }

  const minDeadline = new Date(Date.now() + 3_600_000).toISOString().slice(0, 16)
  const maxDeadline = new Date(Date.now() + 365 * 86_400_000).toISOString().slice(0, 16)

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
        <p className="text-xs text-primary-400 font-semibold uppercase tracking-widest mb-2">New campaign</p>
        <h1 className="font-display font-bold text-4xl text-text-primary">Create a Jar</h1>
      </motion.div>

      {/* Step indicator */}
      <div className="flex items-center gap-0 mb-10">
        {STEPS.map(({ n, label }, i) => (
          <div key={n} className="flex items-center flex-1 last:flex-none">
            <div className="flex items-center gap-2">
              <div className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all',
                step > n
                  ? 'bg-success border-success text-white'
                  : step === n
                  ? 'border-primary bg-primary-dim text-primary-300'
                  : 'border-border text-text-muted'
              )}>
                {step > n ? <CheckCircle2 size={14} /> : n}
              </div>
              <span className={cn('text-xs font-medium hidden sm:block transition-colors',
                step === n ? 'text-text-primary' : 'text-text-muted')}>{label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn('flex-1 h-px mx-3 transition-colors', step > n ? 'bg-success/50' : 'bg-border')} />
            )}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">

        {/* ── STEP 1: Details ──────────────────────────────── */}
        {step === 1 && (
          <motion.div key="step1" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
            <form onSubmit={handleSubmit(onSubmitDetails)} className="glass-card p-8 space-y-6">

              {/* Emoji picker */}
              <div>
                <label className="label">Cover emoji</label>
                <div className="flex items-center gap-3">
                  <span className="text-4xl">{emoji || '🫙'}</span>
                  <input {...register('cover_emoji')} type="text" maxLength={2} className="input w-20 text-center text-xl" placeholder="🫙" />
                  <div className="flex gap-2 flex-wrap">
                    {['🫙', '❤️', '🎓', '💻', '🌱', '🎨', '🏘️', '🔬', '🎮'].map(e => (
                      <button key={e} type="button" onClick={() => setValue('cover_emoji', e)}
                        className={cn('w-8 h-8 rounded-lg flex items-center justify-center text-lg transition-all border',
                          emoji === e ? 'border-primary/40 bg-primary-dim' : 'border-border hover:border-border-bright')}>
                        {e}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Title */}
              <div>
                <label className="label">Campaign title</label>
                <input {...register('title')} type="text" placeholder="Help us build a community garden" className={`input ${errors.title ? 'error' : ''}`} />
                <div className="flex justify-between mt-1">
                  {errors.title ? <p className="text-xs text-danger">{errors.title.message}</p> : <span />}
                  <span className="text-xs text-text-disabled">{title.length}/{MAX_TITLE_LENGTH}</span>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="label">Description</label>
                <textarea {...register('description')} rows={4} placeholder="Tell donors what you're raising for and how funds will be used…" className={`textarea ${errors.description ? 'error' : ''}`} />
                {errors.description && <p className="text-xs text-danger mt-1">{errors.description.message}</p>}
              </div>

              {/* Category */}
              <div>
                <label className="label">Category</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {JAR_CATEGORIES.map(cat => (
                    <button key={cat.value} type="button" onClick={() => setValue('category', cat.value)}
                      className={cn('flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm border transition-all',
                        category === cat.value
                          ? 'border-primary/40 bg-primary-dim text-primary-300'
                          : 'border-border text-text-secondary hover:border-border-bright hover:text-text-primary')}>
                      <span>{cat.emoji}</span>
                      <span className="text-xs">{cat.label}</span>
                    </button>
                  ))}
                </div>
                {errors.category && <p className="text-xs text-danger mt-2">{errors.category.message}</p>}
              </div>

              {/* Target + Deadline */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="label">Target amount</label>
                  <div className="relative">
                    <input {...register('target_amount_matic')} type="number" step="0.01" min="0.01" placeholder="10" className={`input pr-16 ${errors.target_amount_matic ? 'error' : ''}`} />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-muted font-mono">MATIC</span>
                  </div>
                  {errors.target_amount_matic && <p className="text-xs text-danger mt-1">{errors.target_amount_matic.message}</p>}
                </div>
                <div>
                  <label className="label">Deadline</label>
                  <input {...register('deadline')} type="datetime-local" min={minDeadline} max={maxDeadline} className={`input ${errors.deadline ? 'error' : ''}`} />
                  {errors.deadline && <p className="text-xs text-danger mt-1">{errors.deadline.message}</p>}
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button type="submit" disabled={isSubmitting} className="btn-primary px-8">
                  {isSubmitting ? <InlineSpinner size={16} /> : <>Continue <ArrowRight size={16} /></>}
                </button>
              </div>
            </form>
          </motion.div>
        )}

        {/* ── STEP 2: Deploy ────────────────────────────────── */}
        {step === 2 && (
          <motion.div key="step2" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
            <div className="glass-card p-8 space-y-6 text-center">
              <span className="text-5xl">{emoji || '🫙'}</span>
              <div>
                <h2 className="font-display font-bold text-2xl text-text-primary mb-2">Deploy to Polygon</h2>
                <p className="text-text-muted text-sm max-w-sm mx-auto">
                  Sign the MetaMask transaction to register your jar on the JarFund smart contract.
                  A small gas fee applies.
                </p>
              </div>

              <div className="glass-panel p-4 text-left space-y-2 text-sm">
                {[
                  { k: 'Title',    v: watch('title') },
                  { k: 'Target',   v: `${watch('target_amount_matic')} MATIC` },
                  { k: 'Deadline', v: watch('deadline') ? new Date(watch('deadline')).toLocaleDateString() : '—' },
                  { k: 'Network',  v: 'Polygon Amoy (testnet)' },
                ].map(({ k, v }) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-text-muted">{k}</span>
                    <span className="text-text-primary font-medium">{v}</span>
                  </div>
                ))}
              </div>

              <div className="flex items-start gap-2 text-left glass-panel p-3">
                <Info size={14} className="text-info/60 mt-0.5 shrink-0" />
                <p className="text-xs text-text-muted">
                  Your jar details are saved in our database. The on-chain transaction registers it with the smart contract so donations can be received.
                </p>
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(1)} className="btn-secondary flex-1 flex items-center justify-center gap-2">
                  <ArrowLeft size={14} /> Back
                </button>
                <button onClick={deployOnChain} className="btn-primary flex-1">
                  Deploy on Polygon
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── STEP 3: Confirm ───────────────────────────────── */}
        {step === 3 && (
          <motion.div key="step3" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
            <div className="glass-card p-8 space-y-6">
              <div className="text-center">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="text-5xl mb-3 inline-block"
                >
                  {receipt ? '🎉' : '⏳'}
                </motion.div>
                <h2 className="font-display font-bold text-2xl text-text-primary mb-2">
                  {receipt ? 'Transaction confirmed!' : 'Awaiting confirmation…'}
                </h2>
                <p className="text-text-muted text-sm">
                  {receipt
                    ? 'Your jar is live on the blockchain. Click below to finish.'
                    : 'This usually takes 10–30 seconds on Polygon Amoy.'
                  }
                </p>
              </div>

              {txHash && <TxStatusBanner txHash={txHash} label="Jar creation" />}

              {receipt ? (
                <button onClick={handleConfirm} disabled={confirmJar.isPending} className="btn-primary w-full py-4">
                  {confirmJar.isPending ? <InlineSpinner size={16} /> : <>View your jar <ArrowRight size={16} /></>}
                </button>
              ) : (
                <div className="text-center text-sm text-text-muted">
                  {waitingForReceipt && (
                    <span className="flex items-center justify-center gap-2">
                      <InlineSpinner size={14} /> Waiting for block confirmation…
                    </span>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
