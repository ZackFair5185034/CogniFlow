import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import globals from 'globals'
import vueParser from 'vue-eslint-parser'
import tsParser from '@typescript-eslint/parser'

export default tseslint.config(
  // 忽略文件
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '*.config.js',
      '*.config.ts',
      'uno.config.ts',
      'eslint.config.ts',
    ],
  },

  // JavaScript 基础规则
  js.configs.recommended,

  // Vue 规则
  ...vue.configs['flat/recommended'],

  // TypeScript 规则
  ...tseslint.configs.recommended,

  // TypeScript 类型感知规则（仅 .ts/.tsx）
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parserOptions: {
        projectService: true,
      },
    },
    rules: {
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
    },
  },

  // Vue SFC 解析器配置
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
    },
  },

  // 项目规则（通用）
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.vue'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // Vue 相关
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'warn',
      'vue/require-default-prop': 'off',
      'vue/require-explicit-emits': 'warn',
      'vue/v-on-event-hyphenation': 'warn',
      'vue/block-lang': ['warn', {
        script: { lang: 'ts' },
        style: { lang: 'scss' },
      }],

      // TypeScript 相关
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
      '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],

      // UnoCSS / Tailwind 相关（原子化 CSS）
      'multiline-ternary': 'off',

      // 常规
      'no-console': 'off',
      'no-debugger': 'error',
      'no-unused-vars': 'off',
      'prefer-const': 'error',
      'prefer-template': 'error',
      'object-shorthand': 'error',
      'quote-props': ['error', 'as-needed'],
    },
  },

  // Vue 单文件组件处理器
  {
    files: ['**/*.vue'],
    processor: vue.processors['.vue'],
  },
)
