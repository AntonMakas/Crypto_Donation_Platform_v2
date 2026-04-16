# JarFund Frontend

React + Vite + TailwindCSS frontend for the JarFund crypto donation platform.

## Quick Start

```bash
# Install dependencies
npm install

# Copy env template
cp .env.example .env.local
# → Fill in VITE_WALLETCONNECT_PROJECT_ID and VITE_CONTRACT_ADDRESS

# Start dev server (proxies /api to Django on :8000)
npm run dev
```

Open: http://localhost:5173

## Stack

| Layer       | Library               | Purpose                         |
|-------------|----------------------|---------------------------------|
| Framework   | React 18 + Vite 5    | UI, fast HMR                    |
| Language    | TypeScript 5 (strict)| Type safety                     |
| Styles      | Tailwind CSS 3       | Utility-first CSS + design sys  |
| Web3        | wagmi v2 + viem      | Wallet connection, tx sending   |
| Data        | TanStack Query v5    | Server state, caching, polling  |
| HTTP        | Axios                | API client with JWT interceptors|
| Forms       | React Hook Form + Zod| Validation                      |
| Animation   | Framer Motion        | Page transitions, micro-motion  |
| Routing     | React Router v6      | Client-side routing             |
| Toast       | react-hot-toast      | Notifications                   |

## Design System

Font: **Syne** (display/headings) + **DM Sans** (body) + **DM Mono** (addresses)

Palette: Deep purple-black canvas with primary `#7c3aed` and accent `#4f46e5`

Key CSS classes (see `globals.css`):
- `.glass-card` — frosted glass surface card
- `.glass-panel` — lighter panel variant
- `.btn-primary` / `.btn-secondary` / `.btn-ghost`
- `.input` / `.textarea` / `.select`
- `.badge-active` / `.badge-completed` / `.badge-expired`
- `.progress-track` + `.progress-fill`
- `.orb-primary` / `.orb-accent` — decorative background glows
- `.text-gradient` — purple→indigo gradient text
- `.wallet-address` — mono address display

## Directory Structure

```
src/
├── components/
│   ├── ui/          # Primitives: Spinner, Badge, Button, etc.
│   ├── layout/      # AppLayout, Navbar, Footer
│   ├── jar/         # JarCard, JarGrid, CreateJarForm
│   ├── donation/    # DonationForm, DonationList, DonationRow
│   ├── blockchain/  # TxStatus, WalletConnect, ChainBadge
│   └── auth/        # ConnectButton, ProfileMenu
├── pages/           # Route-level components (lazy-loaded)
├── contexts/        # AuthContext (JWT + wallet sign-in)
├── hooks/           # useQueries, useCountdown, useClipboard, etc.
├── lib/             # api.ts, wagmi.ts, queryClient, constants
├── utils/           # format.ts (MATIC, addresses, dates)
├── types/           # Shared TypeScript interfaces
└── styles/          # globals.css (design tokens + component layer)
```

## Build

```bash
npm run build   # TypeScript check + Vite bundle → dist/
npm run preview # Preview production build
```
