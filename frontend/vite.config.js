import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      react(),
      // PWA Support
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
        manifest: {
          name: 'RF Spectrum Monitor',
          short_name: 'RF Monitor',
          description: 'RF Spectrum Monitoring and Analysis Tool',
          theme_color: '#1976d2',
          background_color: '#121212',
          display: 'standalone',
          icons: [
            {
              src: '/icon-192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: '/icon-512.png',
              sizes: '512x512',
              type: 'image/png',
            },
            {
              src: '/icon-512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
        workbox: {
          // Cache strategies for different asset types
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/.*\.tile\.openstreetmap\.org\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'map-tiles',
                expiration: {
                  maxEntries: 500,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
            {
              urlPattern: /^https:\/\/.*\.basemaps\.cartocdn\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'carto-tiles',
                expiration: {
                  maxEntries: 500,
                  maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
                },
              },
            },
            {
              urlPattern: /\/api\/.*/i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 5, // 5 minutes
                },
                networkTimeoutSeconds: 10,
              },
            },
          ],
        },
      }),
    ],

    // Development server configuration
    server: {
      port: 5173,
      host: true, // Listen on all addresses
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        },
      },
    },

    // Build configuration
    build: {
      outDir: 'dist',
      sourcemap: mode === 'development',
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: mode === 'production',
          drop_debugger: mode === 'production',
        },
      },
      // Code splitting
      rollupOptions: {
        output: {
          manualChunks: {
            // Vendor chunks
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-mui': ['@mui/material', '@mui/icons-material'],
            'vendor-plotly': ['plotly.js', 'react-plotly.js'],
            'vendor-leaflet': ['leaflet', 'react-leaflet', 'leaflet.heat', 'leaflet.markercluster'],
            // App chunks
            'app-map': [
              './src/components/map/HeatmapLayer.jsx',
              './src/components/map/MeasurementCluster.jsx',
              './src/components/map/TrackViewer.jsx',
              './src/components/map/MapControls.jsx',
            ],
            'app-analysis': [
              './src/components/analysis/SignalAnalyzer.jsx',
              './src/components/analysis/TimeSeriesView.jsx',
              './src/components/analysis/BandStatistics.jsx',
            ],
          },
        },
      },
      // Chunk size warnings
      chunkSizeWarningLimit: 1000,
    },

    // Optimize dependencies
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@mui/material',
        '@mui/icons-material',
        'plotly.js',
        'react-plotly.js',
        'leaflet',
        'react-leaflet',
        'zustand',
        'axios',
      ],
    },

    // Define global constants
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
    },
  }
})
