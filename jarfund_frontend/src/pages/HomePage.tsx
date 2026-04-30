import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Shield, Zap, Globe, TrendingUp, Users, CheckCircle2, Coins } from 'lucide-react'
import { usePlatformStats, useJars } from '@/hooks/useQueries'
import JarCard from '@/components/jar/JarCard'
import AnimatedCounter from '@/components/ui/AnimatedCounter'
import { JarCardSkeleton, StatCard } from '@/components/ui/PageSpinner'
import { ROUTES } from '@/lib/constants'
import { formatMatic } from '@/utils/format'

const fadeUp = {
  hidden:  { opacity: 0, y: 32 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.12, duration: 0.6, ease: [0.23, 1, 0.32, 1] },
  }),
}

const HOW_IT_WORKS = [
  { step: '01', icon: '🔗', title: 'Connect wallet',  desc: 'Sign in with MetaMask using a cryptographic signature — no passwords, ever.' },
  { step: '02', icon: '🫙', title: 'Create your jar', desc: 'Set a goal, deadline, and description. Your campaign deploys to Polygon instantly.' },
  { step: '03', icon: '💸', title: 'Receive donations', desc: 'Anyone sends POL directly to your smart contract. Every transfer is verifiable.' },
  { step: '04', icon: '🏆', title: 'Withdraw funds',  desc: 'Once your goal is met or deadline passes, withdraw to your wallet in one transaction.' },
]

export default function HomePage() {
  const { data: stats, isLoading: statsLoading } = usePlatformStats()
  const { data: jarsData, isLoading: jarsLoading } = useJars({ status: 'active', ordering: '-created_at', page_size: 6 })
  const featuredJars = jarsData?.results ?? []

  return (
    <div className="relative">

      {/* HERO */}
      <section className="relative min-h-[92vh] flex flex-col items-center justify-center px-4 py-24 overflow-hidden">
        <div className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />

        {[...Array(6)].map((_, i) => (
          <motion.div key={i} className="absolute w-1 h-1 rounded-full bg-primary/40"
            style={{ left: `${15 + i * 15}%`, top: `${20 + (i % 3) * 25}%` }}
            animate={{ y: [0, -20, 0], opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 3 + i * 0.7, repeat: Infinity, delay: i * 0.5 }} />
        ))}

        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-8">
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/25 bg-primary-dim text-primary-300 text-xs font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Built on Polygon Amoy
          </motion.div>

          <motion.h1 custom={0} variants={fadeUp} initial="hidden" animate="visible"
            className="font-display font-extrabold leading-[1.05] tracking-tight"
            style={{ fontSize: 'clamp(3rem, 8vw, 6rem)' }}>
            Fundraise{' '}
            <span className="text-gradient">transparently</span>
            <br />on the blockchain
          </motion.h1>

          <motion.p custom={1} variants={fadeUp} initial="hidden" animate="visible"
            className="text-lg text-text-secondary max-w-xl mx-auto leading-relaxed">
            Create a jar, share the link, receive POL directly into a smart contract.
            Every donation is public, verifiable, and immutable.
          </motion.p>

          <motion.div custom={2} variants={fadeUp} initial="hidden" animate="visible"
            className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to={ROUTES.CREATE} className="btn-primary text-base px-8 py-4 gap-2">
              Create a jar <ArrowRight size={18} />
            </Link>
            <Link to={ROUTES.EXPLORE} className="btn-secondary text-base px-8 py-4">
              Explore campaigns
            </Link>
          </motion.div>

          {!statsLoading && stats && (
            <motion.div custom={3} variants={fadeUp} initial="hidden" animate="visible"
              className="flex items-center justify-center gap-10 pt-4 flex-wrap">
              {[
                { value: stats.total_jars,                         suffix: ' jars',   label: 'created'   },
                { value: parseFloat(stats.total_raised_matic),     suffix: ' POL',    label: 'raised'    },
                { value: stats.total_donors,                       suffix: ' donors', label: 'worldwide' },
              ].map(({ value, suffix, label }, i) => (
                <div key={i} className="text-center">
                  <div className="font-display font-bold text-2xl text-text-primary">
                    <AnimatedCounter to={value} suffix={suffix} />
                  </div>
                  <div className="text-xs text-text-muted">{label}</div>
                </div>
              ))}
            </motion.div>
          )}
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.4 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-text-disabled">
          <span className="text-xs tracking-widest uppercase">Scroll</span>
          <motion.div animate={{ y: [0, 6, 0] }} transition={{ duration: 1.5, repeat: Infinity }}
            className="w-px h-8 bg-gradient-to-b from-primary/40 to-transparent" />
        </motion.div>
      </section>

      {/* LIVE STATS BAR */}
      {stats && (
        <section className="border-y border-border" style={{ background: 'rgba(255,255,255,0.02)' }}>
          <div className="max-w-5xl mx-auto py-6 px-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: <Coins      size={18} className="text-primary-300" />, label: 'Total raised',    value: formatMatic(stats.total_raised_matic, { compact: true }), accent: 'rgba(124,58,237,0.15)' },
              { icon: <TrendingUp size={18} className="text-success/80"  />, label: 'Active jars',    value: String(stats.active_jars),                                 accent: 'rgba(16,185,129,0.1)'  },
              { icon: <Users      size={18} className="text-info/80"     />, label: 'Total donors',   value: stats.total_donors.toLocaleString(),                        accent: 'rgba(59,130,246,0.1)'  },
              { icon: <CheckCircle2 size={18} className="text-warning/80" />, label: 'Verified txns', value: stats.verified_donations.toLocaleString(),                 accent: 'rgba(245,158,11,0.1)'  },
            ].map(({ icon, label, value, accent }, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}>
                <StatCard label={label} value={value} icon={icon} accent={accent} />
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* FEATURED JARS */}
      <section className="py-24 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-12">
            <motion.div initial={{ opacity: 0, x: -16 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }}>
              <p className="text-xs text-primary-400 font-semibold uppercase tracking-widest mb-2">Live campaigns</p>
              <h2 className="section-heading">Active jars</h2>
            </motion.div>
            <Link to={ROUTES.EXPLORE} className="btn-ghost text-sm hidden sm:flex items-center gap-1">
              View all <ArrowRight size={14} />
            </Link>
          </div>

          {jarsLoading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {[...Array(6)].map((_, i) => <JarCardSkeleton key={i} />)}
            </div>
          ) : featuredJars.length > 0 ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {featuredJars.map((jar, i) => <JarCard key={jar.id} jar={jar} index={i} />)}
            </div>
          ) : (
            <div className="text-center py-16 text-text-muted">
              <span className="text-5xl mb-4 block">🫙</span>
              <p>No active jars yet. <Link to={ROUTES.CREATE} className="text-primary hover:underline">Create the first one!</Link></p>
            </div>
          )}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 px-4 relative overflow-hidden">
        <div className="absolute inset-0 opacity-30" style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 100%, rgba(124,58,237,0.12) 0%, transparent 70%)' }} />
        <div className="max-w-5xl mx-auto relative z-10">
          <motion.div className="text-center mb-16" initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <p className="text-xs text-primary-400 font-semibold uppercase tracking-widest mb-2">Simple process</p>
            <h2 className="section-heading">How JarFund works</h2>
          </motion.div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {HOW_IT_WORKS.map(({ step, icon, title, desc }, i) => (
              <motion.div key={step} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                className="glass-panel p-6 relative group">
                <div className="absolute top-4 right-4 font-display font-black text-4xl text-white/[0.04] select-none group-hover:text-white/[0.07] transition-colors">{step}</div>
                <span className="text-3xl mb-4 block">{icon}</span>
                <h3 className="font-display font-bold text-sm text-text-primary mb-2">{title}</h3>
                <p className="text-xs text-text-muted leading-relaxed">{desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            className="glass-card p-10 md:p-16 text-center relative overflow-hidden">
            <div className="orb-primary w-64 h-64 -top-20 -right-20 opacity-40" />
            <div className="orb-accent  w-48 h-48 -bottom-16 -left-16 opacity-30" />
            <div className="relative z-10 space-y-6">
              <div className="flex justify-center gap-6">
                <Shield size={28} className="text-success/80" />
                <Zap    size={28} className="text-warning/80" />
                <Globe  size={28} className="text-info/80" />
              </div>
              <h2 className="font-display font-bold text-3xl md:text-4xl text-text-primary">Trustless by design</h2>
              <p className="text-text-secondary max-w-xl mx-auto leading-relaxed">
                Smart contracts replace the middleman. Funds are held on-chain until withdrawal conditions are met. No company controls your money.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
                <Link to={ROUTES.CREATE} className="btn-primary px-8 py-3">Start your campaign</Link>
                <a href="https://amoy.polygonscan.com" target="_blank" rel="noopener noreferrer" className="btn-ghost text-sm">View on PolygonScan ↗</a>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
