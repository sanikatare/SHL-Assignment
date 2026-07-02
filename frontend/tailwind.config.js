/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#F3F5F1',
          alt: '#ECEFE9',
        },
        ink: {
          DEFAULT: '#131714',
          soft: '#5B6660',
          faint: '#8A938C',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          dark: '#16201B',
        },
        primary: {
          50: '#EAF3EE',
          100: '#D1E6DA',
          400: '#2E8A69',
          500: '#1F6F54',
          600: '#195A44',
          700: '#144A38',
          900: '#0C2E22',
        },
        accent: {
          DEFAULT: '#D98A2B',
          soft: '#F6E3C4',
          dark: '#B26E1C',
        },
        danger: {
          DEFAULT: '#B3432B',
          soft: '#F3DED6',
        },
        border: {
          DEFAULT: '#DDE3DA',
          dark: '#26312B',
        },
        night: {
          bg: '#0E1512',
          surface: '#16201B',
          ink: '#E9EDE7',
          soft: '#9AA69D',
          border: '#26312B',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(19, 23, 20, 0.04), 0 8px 24px -12px rgba(19, 23, 20, 0.12)',
        card: '0 1px 2px rgba(19, 23, 20, 0.05), 0 4px 16px -6px rgba(19, 23, 20, 0.10)',
        'card-hover': '0 2px 4px rgba(19, 23, 20, 0.06), 0 12px 28px -8px rgba(19, 23, 20, 0.18)',
        bar: '0 -4px 20px -8px rgba(19, 23, 20, 0.12)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 80%, 100%': { opacity: '0.25' },
          '40%': { opacity: '1' },
        },
        'toast-in': {
          '0%': { opacity: '0', transform: 'translateY(-8px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.35s cubic-bezier(0.16, 1, 0.3, 1) both',
        'toast-in': 'toast-in 0.25s cubic-bezier(0.16, 1, 0.3, 1) both',
      },
    },
  },
  plugins: [],
}
