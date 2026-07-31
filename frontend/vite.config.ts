import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Loaded from frontend/.env (see .env.example), not exposed to client
  // code - only used here to authenticate the dev proxy against the backend.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      // Proxy API calls to the backend during local development so the SPA
      // can use relative URLs (same as in production behind nginx). nginx
      // attaches X-API-Key in production (see ../frontend/nginx.conf.template);
      // here the dev server does the same using API_KEY from .env.
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              if (env.API_KEY) {
                proxyReq.setHeader('X-API-Key', env.API_KEY)
              }
            })
          },
        },
        '/health': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
