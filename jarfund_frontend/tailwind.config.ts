import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],

  theme: {
    extend: {
      // ── Brand colours (from design spec) ──────────────────────
      colors: {
        // Canvas
        bg: {
          DEFAULT:  '#080612',
          surface:  '#0d0a1e',
          elevated: '#130f2a',
          glass:    'rgba(255,255,255,0.04)',
        },

        // Primary purple
        primary: {
          50:      '#faf5ff',
          100:     '#f3e8ff',
          200:     '#e9d5ff',
          300:     '#d8b4fe',
          400:     '#c084fc',
          500:     '#a855f7',
          600:     '#9333ea',
          700:     '#7c3aed',
          800:     '#6d28d9',
          900:     '#5b21b6',
          DEFAULT: '#7c3aed',
          dim:     'rgba(124,58,237,0.15)',
          glow:    'rgba(124,58,237,0.4)',
        },

        // Accent indigo
        accent: {
          DEFAULT: '#4f46e5',
          light:   '#818cf8',
          dim:     'rgba(79,70,229,0.15)',
        },

        // Status colours
        success:  '#10b981',
        warning:  '#f59e0b',
        danger:   '#ef4444',
        info:     '#3b82f6',

        // Neutral text
        text: {
          primary:   '#f8f8ff',
          secondary: '#a89bc2',
          muted:     '#6b6080',
          disabled:  '#3d3455',
        },

        // Borders
        border: {
          DEFAULT: 'rgba(255,255,255,0.08)',
          bright:  'rgba(255,255,255,0.15)',
          focus:   'rgba(124,58,237,0.6)',
        },
      },

      // ── Typography ─────────────────────────────────────────────
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        body:    ['DM Sans', 'sans-serif'],
        mono:    ['DM Mono', 'monospace'],
      },

      // ── Spacing ────────────────────────────────────────────────
      spacing: {
        '4.5':  '1.125rem',
        '18':   '4.5rem',
        '88':   '22rem',
        '128':  '32rem',
      },

      // ── Border radius ──────────────────────────────────────────
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },

      // ── Box shadows ────────────────────────────────────────────
      boxShadow: {
        'glow-sm':  '0 0 12px rgba(124,58,237,0.25)',
        'glow':     '0 0 24px rgba(124,58,237,0.35)',
        'glow-lg':  '0 0 48px rgba(124,58,237,0.45)',
        'card':     '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)',
        'card-hover': '0 8px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(124,58,237,0.3), inset 0 1px 0 rgba(255,255,255,0.08)',
        'input':    'inset 0 1px 0 rgba(255,255,255,0.05)',
      },

      // ── Backdrop blur ──────────────────────────────────────────
      backdropBlur: {
        xs: '2px',
        sm: '8px',
        DEFAULT: '16px',
        lg: '24px',
        xl: '40px',
      },

      // ── Animations ─────────────────────────────────────────────
      keyframes: {
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-in-right': {
          '0%':   { opacity: '0', transform: 'translateX(24px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-12px)' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 16px rgba(124,58,237,0.3)' },
          '50%':      { boxShadow: '0 0 32px rgba(124,58,237,0.6)' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'orb-drift': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '33%':      { transform: 'translate(30px, -20px) scale(1.05)' },
          '66%':      { transform: 'translate(-20px, 15px) scale(0.95)' },
        },
        'spin-slow': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'fade-up':         'fade-up 0.5s ease-out forwards',
        'fade-in':         'fade-in 0.4s ease-out forwards',
        'slide-in-right':  'slide-in-right 0.4s ease-out forwards',
        'float':           'float 6s ease-in-out infinite',
        'float-slow':      'float 9s ease-in-out infinite',
        'pulse-glow':      'pulse-glow 3s ease-in-out infinite',
        'shimmer':         'shimmer 2s linear infinite',
        'orb-drift':       'orb-drift 12s ease-in-out infinite',
        'spin-slow':       'spin-slow 20s linear infinite',
      },

      // ── Gradient stops ─────────────────────────────────────────
      backgroundImage: {
        'gradient-radial':        'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic':         'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'primary-gradient':       'linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)',
        'primary-gradient-soft':  'linear-gradient(135deg, rgba(124,58,237,0.2) 0%, rgba(79,70,229,0.2) 100%)',
        'card-gradient':          'linear-gradient(145deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
        'shimmer-gradient':       'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.04) 50%, transparent 100%)',
      },
    },
  },

  plugins: [],
} satisfies Config
