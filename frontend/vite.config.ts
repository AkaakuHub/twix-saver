import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  // Load env vars from both frontend and root directories
  const env = loadEnv(mode, process.cwd(), '')
  const rootEnv = loadEnv(mode, '../', '')
  const mergedEnv = { ...rootEnv, ...env }

  const VITE_BACKEND_PORT = Number(mergedEnv.VITE_BACKEND_PORT) || 8000
  const VITE_FRONTEND_PORT = Number(mergedEnv.VITE_FRONTEND_PORT) || 5173

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': '/src',
        '@/components': '/src/components',
        '@/hooks': '/src/hooks',
        '@/services': '/src/services',
        '@/stores': '/src/stores',
        '@/types': '/src/types',
        '@/utils': '/src/utils',
      },
    },
    server: {
      port: VITE_FRONTEND_PORT,
      host: true,
      proxy: {
        '/api': {
          target: `http://localhost:${VITE_BACKEND_PORT}`,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})
