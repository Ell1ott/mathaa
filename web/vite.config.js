import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { dataServer } from './dataServer.js'

export default defineConfig({
  plugins: [react(), dataServer()],
})
