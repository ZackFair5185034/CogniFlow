import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import globals from 'globals'
import vueParser from 'vue-eslint-parser'
import tsParser from '@typescript-eslint/parser'
import autoImportGlobals from './.eslintrc-auto-import.json' with { type: 'json' }

/**
 * ESLint flat config: globals 是 readonly/writable
 * unplugin-auto-import 生成的 .eslintrc-auto-import.json 用 true/false 表示
 * 这里统一转换为 readonly (auto-import 生成的都是 const, 只读)
 */
const autoImportGlobalsReadonly: Record<string, 'readonly'> = Object.fromEntries(
  Object.entries(autoImportGlobals.globals as Record<string, boolean>).map(
    ([key]) => [key, 'readonly' as const],
  ),
)

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
        // unplugin-auto-import 注入的全局（来自 .eslintrc-auto-import.json）
        ...autoImportGlobalsReadonly,
        // main.ts 全局注册的 SvgIcon 组件 (auto-import 未覆盖)
        SvgIcon: 'readonly',
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

  // RuleCanvas 允许 any（动态图数据，运行时类型不确定）
  {
    files: ['**/RuleCanvas.vue'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
)
