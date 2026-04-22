import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      UnoCSS(),
    ],

    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },

    server: {
      port: Number(env.VITE_PORT) || 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/uploads': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_WS_BASE_URL || 'ws://localhost:8000',
          ws: true,
        },
      },
    },

    build: {
      target: 'esnext',
      minify: 'esbuild',
      chunkSizeWarningLimit: 600,
      rolldownOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('element-plus')) {
              return 'element-plus'
            }
          },
        },
      },
    },

    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
        },
      },
    },

    optimizeDeps: {
      include: ['vue', 'vue-router', 'pinia', 'element-plus', 'axios'],
    },
  }
})
