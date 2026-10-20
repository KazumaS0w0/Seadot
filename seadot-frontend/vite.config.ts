import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: env.SEADOT_API_TARGET || 'http://127.0.0.1:17890',
          changeOrigin: true,
        },
      },
    },
  }
})
