import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// El frontend corre como servidor propio (puerto 5173) y habla con Django
// (puerto 8000) por HTTP. En desarrollo se usa un proxy para que las llamadas
// salgan desde el mismo origen y no dependan de CORS ni de rutas absolutas.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/alertas': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
