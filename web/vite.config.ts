import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, the Python dashboard (python dashboard.py) serves the API on :8000.
const backend = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': backend,
      '/drivers': backend,
      '/ws': { target: backend, ws: true },
    },
  },
})
