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

    // Build optimization configuration
    build: {
      target: 'esnext',
      minify: 'esbuild',
      cssMinify: true,

      // Enable source maps for production debugging
      sourcemap: mode === 'development',

      // Chunk size warning limit
      chunkSizeWarningLimit: 1000,

      // Report compressed size for Docker builds
      reportCompressedSize: true,

      rollupOptions: {
        output: {
          // Manual chunk splitting for optimal caching
          manualChunks: {
            // React ecosystem
            'react-vendor': ['react', 'react-dom'],

            // Routing and state management
            'routing': ['react-router-dom', 'zustand'],

            // UI and animation libraries
            'ui-vendor': [
              '@heroicons/react',
              'framer-motion',
              'lucide-react',
              'react-hot-toast'
            ],

            // Charts and data visualization
            'charts': [
              'chart.js',
              'react-chartjs-2'
            ],

            // Utilities and date handling
            'utils': [
              'clsx',
              'date-fns'
            ],

            // Data fetching and real-time
            'data': [
              '@tanstack/react-query',
              'socket.io-client'
            ],

            // Styling (if not using Tailwind CDN)
            'styles': [
              'tailwindcss',
              'autoprefixer',
              'postcss'
            ]
          },

          // Optimize chunk naming for caching
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId
              ? chunkInfo.facadeModuleId.split('/').pop()?.replace('.tsx', '').replace('.ts', '')
              : 'chunk';
            return `assets/${facadeModuleId}-[hash].js`;
          },

          // Optimize asset naming
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name?.split('.') || ['asset'];
            const ext = info[info.length - 1];
            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext || '')) {
              return `assets/images/[name]-[hash][extname]`;
            }
            if (/woff2?|eot|ttf|otf/i.test(ext || '')) {
              return `assets/fonts/[name]-[hash][extname]`;
            }
            return `assets/[name]-[hash][extname]`;
          }
        }
      }
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
