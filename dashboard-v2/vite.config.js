import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/live-data.json': {
        target: 'https://dz4lgcial54jx.cloudfront.net',
        changeOrigin: true,
        rewrite: () => '/demo-data.json',
      },
      '/live-data.js': {
        target: 'https://dz4lgcial54jx.cloudfront.net',
        changeOrigin: true,
        rewrite: () => '/demo-data.js',
      },
    },
  },
})
