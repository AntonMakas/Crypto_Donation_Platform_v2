import { Outlet, NavLink } from 'react-router-dom'
import { useState } from 'react'
import { motion, AnimatePresence }      from 'framer-motion'
import {
  Wallet, Menu, X, Plus,
  TrendingUp, Compass, User, LogOut,
} from 'lucide-react'
import { useAccount, useConnect } from 'wagmi'

import { useAuth }       from '@/contexts/AuthContext'
import { ROUTES }        from '@/lib/constants'
import { shortAddress }  from '@/utils/format'
import { cn }            from '@/utils/format'

// ── Nav items ─────────────────────────────────────────────────────
const NAV = [
  { to: ROUTES.HOME,    label: 'Home',    icon: TrendingUp },
  { to: ROUTES.EXPLORE, label: 'Explore', icon: Compass    },
  { to: ROUTES.CREATE,  label: 'Create',  icon: Plus       },
]

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { address, isConnected }     = useAccount()
  const { connect, connectors } = useConnect()
  const { isAuthenticated, isLoading, signIn, signOut } = useAuth()

  return (
    <div className="min-h-screen flex flex-col relative overflow-x-hidden">
      {/* ── Background orbs ─────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden>
        <div className="orb-primary w-[600px] h-[600px] -top-64 -left-64 animate-orb-drift opacity-60" />
        <div className="orb-accent  w-[500px] h-[500px] top-1/2 -right-48 animate-orb-drift opacity-50"
             style={{ animationDelay: '-4s' }} />
        <div className="orb-primary w-[400px] h-[400px] bottom-0 left-1/3 animate-orb-drift opacity-40"
             style={{ animationDelay: '-8s' }} />
      </div>

      {/* ── Navbar ──────────────────────────────────────────── */}
      <header className="sticky top-0 z-50">
        <div
          className="border-b border-border backdrop-blur-xl"
          style={{ background: 'rgba(8,6,18,0.85)' }}
        >
          <nav className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">

            {/* Logo */}
            <NavLink to={ROUTES.HOME} className="flex items-center gap-2 shrink-0 group">
              <span className="text-2xl">🫙</span>
              <span className="font-display font-bold text-xl text-text-primary group-hover:text-gradient transition-all">
                JarFund
              </span>
            </NavLink>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              {NAV.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) => cn(
                    'flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-150',
                    isActive
                      ? 'bg-primary-dim text-primary-300 border border-primary/20'
                      : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                  )}
                >
                  <Icon size={15} />
                  {label}
                </NavLink>
              ))}
            </div>

            {/* Right side: wallet + profile */}
            <div className="flex items-center gap-3">

              {!isConnected ? (
                <button
                  onClick={() => {
                    const metamask = connectors.find(c => c.id === 'injected') ?? connectors[0]
                    if (!metamask) {
                      window.open('https://metamask.io/download/', '_blank')
                      return
                    }
                    connect({ connector: metamask })
                  }}
                  className="btn-primary text-sm px-4 py-2"
                >
                  <Wallet size={15} />
                  Connect Wallet
                </button>
              ) : !isAuthenticated ? (
                <button
                  onClick={signIn}
                  disabled={isLoading}
                  className="btn-primary text-sm px-4 py-2"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-1.5">
                      <span className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                      Signing…
                    </span>
                  ) : (
                    <>
                      <Wallet size={15} />
                      Sign In
                    </>
                  )}
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <NavLink
                    to={ROUTES.PROFILE}
                    className={({ isActive }) => cn(
                      'flex items-center gap-2 px-3 py-2 rounded-xl transition-all text-sm',
                      isActive
                        ? 'bg-primary-dim text-primary-300'
                        : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                    )}
                  >
                    <div className="w-6 h-6 rounded-full bg-primary-dim border border-primary/30 flex items-center justify-center">
                      <User size={12} className="text-primary-300" />
                    </div>
                    <span className="font-mono text-xs hidden sm:block">
                      {shortAddress(address ?? '')}
                    </span>
                  </NavLink>
                  <button
                    onClick={() => void signOut()}
                    className="hidden sm:inline-flex btn-ghost text-sm px-3 py-2"
                  >
                    <LogOut size={15} />
                    Sign Out
                  </button>
                </div>
              )}

              {/* Mobile menu toggle */}
              <button
                onClick={() => setMobileOpen(v => !v)}
                className="md:hidden btn-ghost p-2"
                aria-label="Toggle menu"
              >
                {mobileOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </nav>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15 }}
              className="md:hidden border-b border-border"
              style={{ background: 'rgba(13,10,30,0.97)' }}
            >
              <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col gap-1">
                {NAV.map(({ to, label, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) => cn(
                      'flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium',
                      isActive
                        ? 'bg-primary-dim text-primary-300'
                        : 'text-text-secondary'
                    )}
                  >
                    <Icon size={16} />
                    {label}
                  </NavLink>
                ))}
                {isAuthenticated && (
                  <button
                    onClick={() => { signOut(); setMobileOpen(false) }}
                    className="btn-ghost text-sm text-danger/70 hover:text-danger mt-1"
                  >
                    Disconnect
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ── Page content ────────────────────────────────────── */}
      <main className="flex-1 relative">
        <Outlet />
      </main>

      {/* ── Footer ──────────────────────────────────────────── */}
      <footer className="border-t border-border mt-auto">
        <div
          className="py-8 px-4"
          style={{ background: 'rgba(8,6,18,0.9)' }}
        >
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-text-muted">
            <div className="flex items-center gap-2">
              <span>🫙</span>
              <span className="font-display font-semibold text-text-secondary">JarFund</span>
              <span>— Secure crypto donations on Polygon</span>
            </div>
            <div className="flex items-center gap-4">
              <span>Bachelor Thesis · KTU · 2026</span>
              <a
                href="https://amoy.polygonscan.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-text-secondary transition-colors"
              >
                PolygonScan ↗
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
