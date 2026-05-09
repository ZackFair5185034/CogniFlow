import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import { resolve } from 'path'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      UnoCSS(),
      createSvgIconsPlugin({
        iconDirs: [resolve(__dirname, 'src/icons')],
        symbolId: 'icon-[name]',
      }),
    ],

    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },

    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT) || 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/uploads': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/inference_output': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_API_TARGET?.replace('http://', 'ws://') || 'ws://localhost:8000',
          ws: true,
        },
      },
    },

    build: {
      target: 'esnext',
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true,
        },
      },
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
