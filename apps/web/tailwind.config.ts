import type { Config } from 'tailwindcss'
import defaultTheme from 'tailwindcss/defaultTheme'

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter', ...defaultTheme.fontFamily.sans],
        // App shell + authenticated screens only (scoped by .app-theme / font-app); marketing keeps Inter.
        app: ['var(--font-plex)', 'IBM Plex Sans', 'Segoe UI', ...defaultTheme.fontFamily.sans],
        mono: ['var(--font-plex-mono)', 'IBM Plex Mono', ...defaultTheme.fontFamily.mono],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        success: '#28A745',
        warning: '#FFC107',
        info: '#17A2B8',
        // Semantic tokens from app-theme.css (generated from the design canvas dc.py TOKENS).
        // Defined only under .app-theme, so they resolve on app screens, not marketing pages.
        ink3: 'var(--ink-3)',
        line2: 'var(--line-2)',
        sev: {
          crit: { DEFAULT: 'var(--sev-crit)', soft: 'var(--sev-crit-soft)' },
          high: { DEFAULT: 'var(--sev-high)', soft: 'var(--sev-high-soft)' },
          med: { DEFAULT: 'var(--sev-med)', soft: 'var(--sev-med-soft)' },
          low: { DEFAULT: 'var(--sev-low)', soft: 'var(--sev-low-soft)' },
          info: { DEFAULT: 'var(--sev-info)', soft: 'var(--sev-info-soft)' },
        },
        ok: { DEFAULT: 'var(--ok)', soft: 'var(--ok-soft)' },
        violet: { DEFAULT: 'var(--violet)', soft: 'var(--violet-soft)' },
        na: 'var(--na)',
        'amber-bg': 'var(--amber-bg)',
        'accent-soft': 'var(--accent-soft)',
      },
      transitionTimingFunction: {
        app: 'var(--ease)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
export default config
