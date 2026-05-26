/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Cream palette
        cream: {
          50:  '#FFFDF9',
          100: '#FAF8F3',
          200: '#F3EDE0',
          300: '#E8E0D0',
          400: '#D4C9B5',
          500: '#BDB09E',
          600: '#A09485',
        },
        // Teal / Bluish-green palette (primary)
        teal: {
          50:  '#E8F5F3',
          100: '#C5E8E3',
          200: '#8ECFC9',
          300: '#5BBDB5',
          400: '#3AACA3',
          500: '#2E9A91',
          600: '#267D75',
          700: '#1E6059',
          800: '#164540',
          900: '#0E2C29',
          950: '#071A18',
        },
        // Accent gold for highlights
        gold: {
          300: '#F0C97A',
          400: '#E8B84B',
          500: '#D4A017',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in':   'fadeIn 0.35s ease-in-out',
        'slide-in':  'slideIn 0.3s ease-out',
        'slide-up':  'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideIn: { '0%': { transform: 'translateX(-12px)', opacity: '0' }, '100%': { transform: 'translateX(0)', opacity: '1' } },
        slideUp: { '0%': { transform: 'translateY(14px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
      },
      boxShadow: {
        'cream': '0 4px 24px rgba(180, 160, 120, 0.12)',
        'teal':  '0 4px 24px rgba(46, 154, 145, 0.18)',
        'card':  '0 2px 12px rgba(100, 90, 70, 0.08)',
      },
    },
  },
  plugins: [],
}
