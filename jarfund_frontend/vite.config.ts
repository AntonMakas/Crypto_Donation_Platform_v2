import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@':           path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages':      path.resolve(__dirname, './src/pages'),
      '@contexts':   path.resolve(__dirname, './src/contexts'),
      '@hooks':      path.resolve(__dirname, './src/hooks'),
      '@lib':        path.resolve(__dirname, './src/lib'),
      '@utils':      path.resolve(__dirname, './src/utils'),
      '@types':      path.resolve(__dirname, './src/types'),
      '@styles':     path.resolve(__dirname, './src/styles'),
      '@assets':     path.resolve(__dirname, './src/assets'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      // Forward /api/* to Django dev server — avoids CORS in development
      '/api': {
        target:      'http://localhost:8000',
        changeOrigin: true,
        secure:      false,
      },
      '/health': {
        target:      'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  preview: {
    allowedHosts: ['.up.railway.app'],
  },

  build: {
    outDir:       'dist',
    sourcemap:    true,
    target:       'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor chunks for better caching
          'react-vendor':     ['react', 'react-dom', 'react-router-dom'],
          'web3-vendor':      ['wagmi', 'viem', 'ethers'],
          'query-vendor':     ['@tanstack/react-query', 'axios'],
          'ui-vendor':        ['framer-motion', 'lucide-react'],
          'charts-vendor':    ['recharts'],
          'forms-vendor':     ['react-hook-form', '@hookform/resolvers', 'zod'],
        },
      },
    },
  },

  // Expose env vars prefixed VITE_ to the frontend
  envPrefix: 'VITE_',
})
