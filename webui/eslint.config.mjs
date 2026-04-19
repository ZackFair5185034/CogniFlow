import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import globals from 'globals'

export default tseslint.config(
  // 忽略文件
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '*.config.js',
      'uno.config.ts',
    ],
  },

  // JavaScript 基础规则
  js.configs.recommended,

  // Vue 规则
  ...vue.configs['vue3-recommended'],

  // TypeScript 规则
  ...tseslint.configs.recommended,

  // 项目规则
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.vue'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    rules: {
      // Vue 相关
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'warn',
      'vue/require-default-prop': 'off',
      'vue/require-explicit-emits': 'warn',
      'vue/v-on-event-hyphenation': 'warn',
      'vue/block-lang': {
        style: {
          script: { lang: 'ts' },
          style: { lang: 'scss' },
        },
      },

      // TypeScript 相关
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
      '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',

      // UnoCSS / Tailwind 相关（原子化 CSS）
      'multiline-ternary': 'off',

      // 常规
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-unused-vars': 'off',
      'prefer-const': 'error',
      'prefer-template': 'error',
      'object-shorthand': 'error',
      'quote-props': ['error', 'as-needed'],

      // 格式化相关（由 Prettier 处理，这里仅做提示）
      'antfu/if-different-use-braces': 'warn',
    },
  },

  // Vue 单文件组件
  {
    files: ['**/*.vue'],
    processor: vue.processors['.vue'],
  }
)
