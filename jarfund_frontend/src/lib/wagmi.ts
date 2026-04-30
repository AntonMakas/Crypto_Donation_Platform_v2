// ═══════════════════════════════════════════════════════════════
//  wagmi + viem configuration
//  Chains: Polygon Amoy (testnet) + Polygon Mainnet
//  Connectors: MetaMask (injected) + WalletConnect
// ═══════════════════════════════════════════════════════════════

import { createConfig, http } from 'wagmi'
import { injected, walletConnect } from 'wagmi/connectors'
import { defineChain } from 'viem'
import { WALLETCONNECT_PROJECT_ID, RPC_URL } from '@/lib/constants'

const AMOY_RPC = RPC_URL || 'https://rpc-amoy.polygon.technology'
const POLYGON_MAINNET_RPC = RPC_URL || 'https://polygon-bor-rpc.publicnode.com'

// ── Define Polygon Amoy testnet ───────────────────────────────────

export const polygonAmoy = defineChain({
  id:   80002,
  name: 'Polygon Amoy',
  nativeCurrency: { name: 'POL', symbol: 'POL', decimals: 18 },
  rpcUrls: {
    default: { http: [AMOY_RPC] },
  },
  blockExplorers: {
    default: { name: 'PolygonScan', url: 'https://amoy.polygonscan.com' },
  },
  testnet: true,
})

export const polygonMainnet = defineChain({
  id:   137,
  name: 'Polygon',
  nativeCurrency: { name: 'POL', symbol: 'POL', decimals: 18 },
  rpcUrls: {
    default: { http: [POLYGON_MAINNET_RPC] },
  },
  blockExplorers: {
    default: { name: 'PolygonScan', url: 'https://polygonscan.com' },
  },
})

// ── Connectors ────────────────────────────────────────────────────

const connectors = [
  injected({ target: 'metaMask' }),
  ...(WALLETCONNECT_PROJECT_ID
    ? [walletConnect({ projectId: WALLETCONNECT_PROJECT_ID })]
    : []),
]

// ── wagmi config ──────────────────────────────────────────────────

export const wagmiConfig = createConfig({
  chains:     [polygonAmoy, polygonMainnet],
  connectors,
  transports: {
    [polygonAmoy.id]:     http(AMOY_RPC),
    [polygonMainnet.id]:  http(POLYGON_MAINNET_RPC),
  },
})

// ── Contract ABI (minimal — just the functions we call from frontend) ──

export const JARFUND_ABI = [
  // createJar(title, description, targetAmount, deadline) → jarId
  {
    inputs: [
      { internalType: 'string',  name: '_title',        type: 'string'  },
      { internalType: 'string',  name: '_description',  type: 'string'  },
      { internalType: 'uint256', name: '_targetAmount', type: 'uint256' },
      { internalType: 'uint256', name: '_deadline',     type: 'uint256' },
    ],
    name:            'createJar',
    outputs:         [{ internalType: 'uint256', name: 'jarId', type: 'uint256' }],
    stateMutability: 'nonpayable',
    type:            'function',
  },
  // donate(jarId) payable
  {
    inputs:          [{ internalType: 'uint256', name: 'jarId', type: 'uint256' }],
    name:            'donate',
    outputs:         [],
    stateMutability: 'payable',
    type:            'function',
  },
  // withdraw(jarId)
  {
    inputs:          [{ internalType: 'uint256', name: 'jarId', type: 'uint256' }],
    name:            'withdraw',
    outputs:         [],
    stateMutability: 'nonpayable',
    type:            'function',
  },
  // getJar(jarId) → Jar struct tuple
  {
    inputs:  [{ internalType: 'uint256', name: 'jarId', type: 'uint256' }],
    name:    'getJar',
    outputs: [{
      components: [
        { internalType: 'uint256', name: 'id',           type: 'uint256' },
        { internalType: 'address', name: 'creator',      type: 'address' },
        { internalType: 'string',  name: 'title',        type: 'string'  },
        { internalType: 'string',  name: 'description',  type: 'string'  },
        { internalType: 'uint256', name: 'targetAmount', type: 'uint256' },
        { internalType: 'uint256', name: 'amountRaised', type: 'uint256' },
        { internalType: 'uint256', name: 'deadline',     type: 'uint256' },
        { internalType: 'uint8',   name: 'status',       type: 'uint8'   },
        { internalType: 'uint256', name: 'donorCount',   type: 'uint256' },
        { internalType: 'uint256', name: 'createdAt',    type: 'uint256' },
      ],
      internalType: 'struct JarFund.Jar',
      name:         '',
      type:         'tuple',
    }],
    stateMutability: 'view',
    type:            'function',
  },
  // canWithdraw(jarId) → bool
  {
    inputs:          [{ internalType: 'uint256', name: 'jarId', type: 'uint256' }],
    name:            'canWithdraw',
    outputs:         [{ internalType: 'bool', name: '', type: 'bool' }],
    stateMutability: 'view',
    type:            'function',
  },
  // totalJars() → uint256
  {
    inputs:          [],
    name:            'totalJars',
    outputs:         [{ internalType: 'uint256', name: '', type: 'uint256' }],
    stateMutability: 'view',
    type:            'function',
  },
  // Events
  {
    anonymous: false,
    inputs: [
      { indexed: true,  internalType: 'uint256', name: 'jarId',        type: 'uint256' },
      { indexed: true,  internalType: 'address', name: 'creator',      type: 'address' },
      { indexed: false, internalType: 'string',  name: 'title',        type: 'string'  },
      { indexed: false, internalType: 'uint256', name: 'targetAmount', type: 'uint256' },
      { indexed: false, internalType: 'uint256', name: 'deadline',     type: 'uint256' },
    ],
    name: 'JarCreated',
    type: 'event',
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true,  internalType: 'uint256', name: 'jarId',     type: 'uint256' },
      { indexed: true,  internalType: 'address', name: 'donor',     type: 'address' },
      { indexed: false, internalType: 'uint256', name: 'amount',    type: 'uint256' },
      { indexed: false, internalType: 'uint256', name: 'newTotal',  type: 'uint256' },
      { indexed: false, internalType: 'uint256', name: 'timestamp', type: 'uint256' },
    ],
    name: 'DonationReceived',
    type: 'event',
  },
] as const
