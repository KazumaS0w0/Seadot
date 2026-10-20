/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        inter: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        // Deep Slate/Near-Black backgrounds
        background: '#0F0F11',
        foreground: '#fafaff',
        card: '#0B0F19',
        'card-hover': '#0c1221',
        
        // Electric accent colors
        violet: {
          DEFAULT: '#8b5cf6',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
        },
        cyan: {
          DEFAULT: '#22d3ee',
          400: '#2dd4bf',
          500: '#22d3ee',
          600: '#14b8a6',
        },
        emerald: {
          DEFAULT: '#10b981',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
        },
        orange: {
          DEFAULT: '#fb923c',
          400: '#fbbf24',
          500: '#fb923c',
          600: '#ea580c',
        },
        
        // Custom dark palette
        'sea-dark': {
          900: '#0a0a0c',
          800: '#101014',
          700: '#15151b',
          600: '#1a1a22',
        },
        'sea-blue': {
          DEFAULT: '#1e3a5f',
          500: '#2d5a85',
          400: '#4279a8',
        },
        
        // Gradients for UI elements
        'gradient-primary': 'linear-gradient(135deg, #8b5cf6 0%, #22d3ee 50%, #10b981 100%)',
        'gradient-violet-to-cyan': 'linear-gradient(135deg, #8b5cf6 0%, #22d3ee 100%)',
      },
      borderRadius: {
        xl: '1rem', // 16px
        lg: '0.875rem', // 14px
        md: '0.75rem', // 12px
        sm: '0.5rem', // 8px
      },
      boxShadow: {
        'glow-violet': '0 0 20px rgba(139, 92, 246, 0.3)',
        'glow-cyan': '0 0 20px rgba(34, 211, 238, 0.3)',
        'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.3)',
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}