import React from 'react'
import ReactDOM from 'react-dom/client'
import { WagmiProvider }       from 'wagmi'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster }             from 'react-hot-toast'

import { wagmiConfig }  from '@/lib/wagmi'
import { queryClient }  from '@/lib/queryClient'
import { AuthProvider } from '@/contexts/AuthContext'
import App              from './App'
import '@/styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <App />
        </AuthProvider>

        <Toaster
          position="bottom-right"
          gutter={12}
          toastOptions={{
            duration: 4000,
            style: {
              background:   '#130f2a',
              color:        '#f8f8ff',
              border:       '1px solid rgba(255,255,255,0.10)',
              borderRadius: '12px',
              fontFamily:   "'DM Sans', sans-serif",
              fontSize:     '14px',
              boxShadow:    '0 8px 32px rgba(0,0,0,0.5)',
              padding:      '12px 16px',
            },
            success: { iconTheme: { primary: '#10b981', secondary: '#080612' } },
            error:   { iconTheme: { primary: '#ef4444', secondary: '#080612' }, duration: 5000 },
          }}
        />
      </QueryClientProvider>
    </WagmiProvider>
  </React.StrictMode>,
)