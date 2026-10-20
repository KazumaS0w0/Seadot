/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          dark: '#0B0F19',
          light: '#F5F5F5',
        },
        accent: {
          violet: '#8B5CF6',
          indigo: '#6366F1',
          cyan: '#06B6D4',
          emerald: '#10B981',
          amber: '#F59E0B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}