import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '')

  console.log('🚀 Vite Config Loading:')
  console.log('  Mode:', mode)
  console.log('  Command:', command)
  console.log('  VITE_API_URL from env:', env.VITE_API_URL)
  console.log('  VITE_WS_URL from env:', env.VITE_WS_URL)
  console.log('  VITE_CAPTURE_URL from env:', env.VITE_CAPTURE_URL)

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      host: '0.0.0.0', // Allow external connections for Docker
      watch: {
        usePolling: true, // Better for Docker environments
      },
    },
    preview: {
      port: 3000,
      host: '0.0.0.0',
    },
    // Ensure environment variables are properly exposed
    define: {
      // Explicitly expose environment info for runtime access
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
    },
    // Environment variable handling - critical for Docker
    envPrefix: ['VITE_', 'SKYLAPSE_'], // Allow both VITE_ and SKYLAPSE_ prefixed vars
    envDir: '.', // Look for .env files in project root
  }
})
