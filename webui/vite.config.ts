import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import { resolve } from 'path'

export default defineConfig({
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
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },

  build: {
    target: 'esnext',
    minify: 'esbuild',
    chunkSizeWarningLimit: 600,
    // Vite 8 使用 Rolldown 作为打包引擎
    rolldownOptions: {
      output: {
        // 手动分包策略 - 函数形式
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
        // Vite 8 推荐使用 modern-compiler API
        api: 'modern-compiler',
      },
    },
  },

  // Vite 8 新增配置
  optimizeDeps: {
    // 预构建依赖配置
    include: ['vue', 'vue-router', 'pinia', 'element-plus', 'axios'],
  },
})
