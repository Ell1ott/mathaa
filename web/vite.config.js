import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/questions.json': 'http://127.0.0.1:8765',
      '/cut': 'http://127.0.0.1:8765',
      '/fig': 'http://127.0.0.1:8765',
      '/scheme': 'http://127.0.0.1:8765',
      '/pdf': 'http://127.0.0.1:8765',
    },
  },
})
