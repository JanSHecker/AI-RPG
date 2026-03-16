import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        panel: 'hsl(var(--panel))',
        'panel-foreground': 'hsl(var(--panel-foreground))',
        accent: 'hsl(var(--accent))',
        'accent-soft': 'hsl(var(--accent-soft))',
        border: 'hsl(var(--border))',
        muted: 'hsl(var(--muted))',
        danger: 'hsl(var(--danger))',
      },
      borderRadius: {
        lg: '1rem',
        md: '0.75rem',
        sm: '0.5rem',
      },
      fontFamily: {
        mono: ['IBM Plex Mono', 'JetBrains Mono', 'Courier Prime', 'monospace'],
        display: ['Space Grotesk', 'IBM Plex Sans', 'Segoe UI', 'sans-serif'],
      },
      keyframes: {
        rise: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseLine: {
          '0%, 100%': { opacity: '0.25' },
          '50%': { opacity: '0.75' },
        },
      },
      animation: {
        rise: 'rise 260ms ease-out both',
        pulseLine: 'pulseLine 3.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

export default config
