/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#2563EB',
          600: '#1D4ED8',
          700: '#1E40AF',
          800: '#1E3A8A',
          900: '#172554',
        },
        accent: {
          DEFAULT: '#06B6D4',
          soft: '#14B8D4',
          dark: '#0E7490',
        },
        canvas: '#EDF2F7',
        surface: {
          DEFAULT: '#FFFFFF',
          alt: '#F8FAFC',
          border: '#E2E8F0',
          'border-light': '#F1F5F9',
        },
        ink: {
          DEFAULT: '#0F172A',
          muted: '#64748B',
          faint: '#94A3B8',
        },
        sidebar: {
          DEFAULT: '#0F172A',
          hover: '#1E293B',
          active: '#2563EB',
        },
        success: '#16A34A',
        warning: '#D97706',
        danger: '#DC2626',
      },
      fontFamily: {
        sans: [
          'Inter',
          'Segoe UI',
          'Roboto',
          'Arial',
          'sans-serif',
        ],
      },
      fontSize: {
        hero: ['2.25rem', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '600' }],
        'page-title': ['1.75rem', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '600' }],
        section: ['1.125rem', { lineHeight: '1.35', fontWeight: '600' }],
        card: ['0.9375rem', { lineHeight: '1.4', fontWeight: '600' }],
        body: ['0.9375rem', { lineHeight: '1.5', fontWeight: '400' }],
        small: ['0.8125rem', { lineHeight: '1.45', fontWeight: '400' }],
        caption: ['0.75rem', { lineHeight: '1.4', fontWeight: '500' }],
      },
      borderRadius: {
        sm: '8px',
        md: '12px',
        lg: '18px',
        xl: '24px',
      },
      boxShadow: {
        card: '0 2px 6px rgba(15,23,42,.05), 0 12px 28px rgba(15,23,42,.08)',
        float: '0 18px 40px rgba(15,23,42,.14)',
        drawer: '-8px 0 40px rgba(15,23,42,.12)',
      },
      spacing: {
        page: '3.5rem',
        section: '2rem',
      },
      maxWidth: {
        content: '72rem',
      },
      transitionTimingFunction: {
        horizon: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'backdrop-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out forwards',
        'slide-up': 'slide-up 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'slide-in-right': 'slide-in-right 0.35s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'backdrop-in': 'backdrop-in 0.25s ease-out forwards',
      },
      backgroundImage: {
        'hero-gradient':
          'linear-gradient(135deg, #2340C8 0%, #2563EB 50%, #14B8D4 100%)',
        'mesh-soft':
          'radial-gradient(at 12% 8%, rgba(37, 99, 235, 0.07) 0px, transparent 45%), radial-gradient(at 88% 0%, rgba(6, 182, 212, 0.06) 0px, transparent 40%)',
      },
    },
  },
  plugins: [],
};
