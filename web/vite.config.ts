import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev: Vite(5173) が /api を FastAPI(8000) へプロキシする（同一オリジン扱いで CORS 不要）。
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
