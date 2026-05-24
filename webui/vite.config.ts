import { defineConfig, loadEnv } from 'vite'
/// <reference types="vitest" />
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { resolve } from 'path'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      UnoCSS(),
      AutoImport({
        imports: [
          // Vue 预设（包含所有 Composition API）
          'vue',
          'vue-router',
          'pinia',
          // Element Plus 常用函数
          {
            'element-plus': ['ElMessage', 'ElMessageBox', 'ElNotification', 'ElLoadingDirective'],
          },
          // VueFlow 核心
          {
            '@vue-flow/core': [
              'useVueFlow',
              'MarkerType',
              'SelectionMode',
              'VueFlow',
              'Handle',
              'Position',
            ],
          },
          {
            '@vue-flow/controls': ['Controls'],
          },
          {
            '@vue-flow/minimap': ['MiniMap'],
          },
          // Pinia stores
          {
            '@/stores/ruleEngine': ['useRuleEngineStore'],
          },
          // 工具函数
          {
            '@/utils/toast': ['registerToast'],
          },
        ],
        // API 模块按需显式导入（named exports 无法自动按名导入）
        eslintrc: {
          enabled: true,
        },
        dts: 'src/auto-imports.d.ts',
      }),
      Components({
        // Element Plus + VueFlow 组件自动导入
        resolvers: [
          (name) => {
            if (name.startsWith('El')) {
              return { name, from: 'element-plus' }
            }
            // VueFlow 核心组件
            if (['VueFlow', 'Handle'].includes(name)) {
              return { name, from: '@vue-flow/core' }
            }
            // VueFlow 小地图
            if (name === 'MiniMap') {
              return { name, from: '@vue-flow/minimap' }
            }
            // VueFlow 控制按钮
            if (name === 'Controls') {
              return { name, from: '@vue-flow/controls' }
            }
          },
        ],
        dts: 'src/components.d.ts',
      }),
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
      port: Number(env.VITE_PORT),
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET,
          changeOrigin: true,
        },
        '/uploads': {
          target: env.VITE_API_TARGET,
          changeOrigin: true,
        },
        '/inference_output': {
          target: env.VITE_API_TARGET,
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_API_TARGET,
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

    test: {
      globals: true,
      environment: 'happy-dom',
    },
  }
})
