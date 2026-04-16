import { useState }           from 'react'
import { Link }               from 'react-router-dom'
import { motion }             from 'framer-motion'
import { useForm }            from 'react-hook-form'
import { zodResolver }        from '@hookform/resolvers/zod'
import { z }                  from 'zod'
import {
  User, Edit3, Save, X, Plus,
  Coins, TrendingUp, Heart, CheckCircle2,
  ExternalLink, Clock,
} from 'lucide-react'
import { useAccount } from 'wagmi'

import { useAuth }        from '@/contexts/AuthContext'
import { useMyJars, useMyDonations } from '@/hooks/useQueries'
import JarCard            from '@/components/jar/JarCard'
import DonationRow        from '@/components/donation/DonationRow'
import {
  StatusBadge, WalletAddress, Skeleton,
  EmptyState, InlineSpinner,
} from '@/components/ui/PageSpinner'
import { ROUTES }        from '@/lib/constants'
import { formatMatic, timeAgo, cn } from '@/utils/format'

// ── Edit profile schema ───────────────────────────────────────────
const editSchema = z.object({
  username:   z.string().max(30, 'Max 30 chars').optional().or(z.literal('')),
  bio:        z.string().max(200, 'Max 200 chars').optional().or(z.literal('')),
  avatar_url: z.string().url('Must be a valid URL').optional().or(z.literal('')),
})
type EditForm = z.infer<typeof editSchema>

// ── Tab type ──────────────────────────────────────────────────────
type Tab = 'jars' | 'donations'

export default function ProfilePage() {
  const { user, updateProfile, refreshProfile } = useAuth()
  const { address } = useAccount()
  const [editing, setEditing] = useState(false)
  const [saving,  setSaving]  = useState(false)
  const [tab, setTab] = useState<Tab>('jars')

  const { data: myJarsData,  isLoading: jarsLoading  } = useMyJars()
  const { data: myDonsData,  isLoading: donsLoading   } = useMyDonations()

  const myJars      = myJarsData?.results ?? []
  const myDonations = myDonsData?.donations?.results ?? []
  const donStats    = myDonsData?.stats

  const { register, handleSubmit, reset, formState: { errors } } = useForm<EditForm>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      username:   user?.username   ?? '',
      bio:        user?.bio        ?? '',
      avatar_url: user?.avatar_url ?? '',
    },
  })

  const onSave = async (data: EditForm) => {
    setSaving(true)
    try {
      await updateProfile({
        username:   data.username   || undefined,
        bio:        data.bio        || undefined,
        avatar_url: data.avatar_url || undefined,
      })
      await refreshProfile()
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const onCancel = () => {
    reset()
    setEditing(false)
  }

  if (!user) return null

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 space-y-10">

      {/* ── Profile header ─────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-8 relative overflow-hidden"
      >
        {/* Background orb */}
        <div className="orb-primary w-80 h-80 -top-24 -right-24 opacity-30" />

        <div className="relative z-10 flex flex-col sm:flex-row items-start gap-6">
          {/* Avatar */}
          <div className="relative shrink-0">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="Avatar"
                className="w-20 h-20 rounded-2xl object-cover border-2 border-primary/30" />
            ) : (
              <div className="w-20 h-20 rounded-2xl bg-primary-dim border-2 border-primary/20
                              flex items-center justify-center">
                <User size={32} className="text-primary-300" />
              </div>
            )}
            {user.is_verified && (
              <div className="absolute -bottom-1.5 -right-1.5 w-6 h-6 rounded-full bg-success
                              flex items-center justify-center border-2 border-bg">
                <CheckCircle2 size={12} className="text-white" />
              </div>
            )}
          </div>

          {/* Identity */}
          <div className="flex-1 min-w-0">
            {editing ? (
              <form onSubmit={handleSubmit(onSave)} className="space-y-3">
                <div className="grid sm:grid-cols-2 gap-3">
                  <div>
                    <label className="label">Display name</label>
                    <input {...register('username')} type="text"
                      placeholder="Your name" className="input" />
                    {errors.username && (
                      <p className="text-xs text-danger mt-1">{errors.username.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="label">Avatar URL</label>
                    <input {...register('avatar_url')} type="url"
                      placeholder="https://…" className="input" />
                    {errors.avatar_url && (
                      <p className="text-xs text-danger mt-1">{errors.avatar_url.message}</p>
                    )}
                  </div>
                </div>
                <div>
                  <label className="label">Bio</label>
                  <textarea {...register('bio')} rows={2}
                    placeholder="A short bio…" className="textarea" />
                  {errors.bio && (
                    <p className="text-xs text-danger mt-1">{errors.bio.message}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button type="submit" disabled={saving} className="btn-primary text-sm px-4 py-2">
                    {saving ? <InlineSpinner size={14} /> : <><Save size={13} /> Save</>}
                  </button>
                  <button type="button" onClick={onCancel} className="btn-secondary text-sm px-4 py-2">
                    <X size={13} /> Cancel
                  </button>
                </div>
              </form>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-1">
                  <h1 className="font-display font-bold text-2xl text-text-primary truncate">
                    {user.display_name || 'Anonymous'}
                  </h1>
                  <button
                    onClick={() => setEditing(true)}
                    className="btn-ghost p-1.5 text-text-muted hover:text-text-primary"
                    title="Edit profile"
                  >
                    <Edit3 size={14} />
                  </button>
                </div>
                <WalletAddress address={address ?? user.wallet_address} chars={6} />
                {user.bio && (
                  <p className="text-sm text-text-secondary mt-2 max-w-md">{user.bio}</p>
                )}
              </>
            )}
          </div>

          {/* Stats pills */}
          {!editing && (
            <div className="flex flex-wrap gap-3 shrink-0">
              {[
                { icon: <TrendingUp size={13} />, label: 'Raised',  value: formatMatic(user.total_raised, { compact: true })  },
                { icon: <Heart      size={13} />, label: 'Donated', value: formatMatic(user.total_donated, { compact: true }) },
                { icon: <Coins      size={13} />, label: 'Jars',    value: String(user.jars_count) },
              ].map(({ icon, label, value }) => (
                <div key={label}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border text-xs"
                  style={{ background: 'rgba(255,255,255,0.03)' }}
                >
                  <span className="text-text-muted">{icon}</span>
                  <span className="text-text-secondary">{label}:</span>
                  <span className="font-semibold text-text-primary">{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {/* ── Donation stats bar ──────────────────────────────────── */}
      {donStats && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="grid grid-cols-3 gap-4"
        >
          {[
            { label: 'Total donated',     value: formatMatic(donStats.total_donated_matic, { compact: true }), color: 'rgba(124,58,237,0.15)' },
            { label: 'Confirmed txns',    value: String(donStats.confirmed_count),                             color: 'rgba(16,185,129,0.1)'  },
            { label: 'Pending txns',      value: String(donStats.pending_count),                               color: 'rgba(59,130,246,0.1)'  },
          ].map(({ label, value, color }) => (
            <div key={label} className="glass-panel p-4 text-center"
              style={{ background: color }}>
              <div className="font-display font-bold text-xl text-text-primary">{value}</div>
              <div className="text-xs text-text-muted mt-1">{label}</div>
            </div>
          ))}
        </motion.div>
      )}

      {/* ── Tabs ────────────────────────────────────────────────── */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}>

        <div className="flex items-center justify-between mb-6">
          {/* Tab switcher */}
          <div className="flex gap-1 p-1 rounded-xl border border-border"
            style={{ background: 'rgba(255,255,255,0.02)' }}>
            {(['jars', 'donations'] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                  tab === t
                    ? 'bg-primary-dim text-primary-300 border border-primary/25'
                    : 'text-text-muted hover:text-text-secondary'
                )}
              >
                {t === 'jars' ? `My Jars (${myJars.length})` : `Donations (${myDonations.length})`}
              </button>
            ))}
          </div>

          {tab === 'jars' && (
            <Link to={ROUTES.CREATE} className="btn-primary text-sm px-4 py-2">
              <Plus size={14} /> New jar
            </Link>
          )}
        </div>

        {/* ── Jars tab ─────────────────────────────────────── */}
        {tab === 'jars' && (
          jarsLoading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="glass-panel p-5 space-y-3">
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-1.5 w-full rounded-full" />
                </div>
              ))}
            </div>
          ) : myJars.length === 0 ? (
            <EmptyState
              icon="🫙"
              title="No jars yet"
              message="Create your first fundraising campaign and start collecting donations."
              action={
                <Link to={ROUTES.CREATE} className="btn-primary text-sm px-6 py-2.5">
                  <Plus size={14} /> Create your first jar
                </Link>
              }
            />
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {myJars.map((jar, i) => (
                <JarCard key={jar.id} jar={jar} index={i} />
              ))}
            </div>
          )
        )}

        {/* ── Donations tab ──────────────────────────────────── */}
        {tab === 'donations' && (
          donsLoading ? (
            <div className="glass-panel p-4 space-y-1">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex justify-between items-center p-3">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ))}
            </div>
          ) : myDonations.length === 0 ? (
            <EmptyState
              icon="💸"
              title="No donations yet"
              message="Support a campaign and your donation history will appear here."
              action={
                <Link to={ROUTES.EXPLORE} className="btn-secondary text-sm px-6 py-2.5">
                  Explore campaigns
                </Link>
              }
            />
          ) : (
            <div className="glass-panel p-2 space-y-0.5">
              {myDonations.map((d, i) => (
                <DonationRow key={d.id} donation={d} index={i} showJar />
              ))}
            </div>
          )
        )}

      </motion.div>

    </div>
  )
}
