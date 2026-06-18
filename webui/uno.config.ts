import { defineConfig, presetUno, presetIcons, transformerDirectives, transformerVariantGroup } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetIcons({
      scale: 1.2,
      cdn: 'https://esm.sh/',
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle',
      },
    }),
  ],
  transformers: [
    transformerDirectives(),
    transformerVariantGroup(),
  ],
  shortcuts: {
    // === 按钮系统（平面、小圆角、无发光）===
    'cf-btn': 'px-4 py-2 rounded-[6px] border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] text-sm font-medium cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)] hover:border-[var(--text-muted)]',
    'cf-btn-primary': 'px-4 py-2 rounded-[6px] border border-[var(--accent-blue)] bg-[var(--accent-blue)] text-white text-sm font-medium cursor-pointer transition-all duration-150 hover:bg-[var(--accent-blue-hover)]',
    'cf-btn-small': 'px-2.5 py-1.5 text-xs rounded-[4px] border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)]',
    'cf-btn-icon': 'w-9 h-9 flex items-center justify-center bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded-[6px] transition-all duration-150 hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]',

    // === 卡片系统 ===
    'cf-card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-[8px]',
    'cf-card-header': 'flex items-center gap-3 px-5 py-4 border-b border-[var(--border-color)]',
    'cf-card-content': 'p-5',

    // === 布局 ===
    'cf-flex': 'flex',
    'cf-flex-col': 'flex flex-col',
    'cf-items-center': 'items-center',
    'cf-justify-center': 'justify-center',
    'cf-justify-between': 'justify-between',
    'cf-gap-2': 'gap-2',
    'cf-gap-3': 'gap-3',
    'cf-gap-4': 'gap-4',
    'cf-gap-6': 'gap-6',

    // === 文字 ===
    'cf-text-xs': 'text-xs',
    'cf-text-sm': 'text-sm',
    'cf-text-lg': 'text-lg font-semibold',
    'cf-text-muted': 'text-[var(--text-muted)]',
    'cf-text-secondary': 'text-[var(--text-secondary)]',
    'cf-font-mono': 'font-[var(--font-family-mono)]',
    'cf-font-bold': 'font-bold',

    // === 状态 ===
    'cf-badge': 'px-2 py-0.5 text-[10px] font-[var(--font-family-mono)] rounded-[4px] border border-[var(--border-color)] text-[var(--text-muted)] uppercase tracking-wider',

    // === 输入 ===
    'cf-input': 'w-full px-3.5 py-2.5 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-[6px] text-[var(--text-primary)] text-sm outline-none focus:border-[var(--accent-blue)] transition-colors',

    // === 项目通用组件样式 ===
    'cf-page-header': 'flex justify-between items-center gap-4 flex-shrink-0',
    'cf-dialog-overlay': 'fixed inset-0 bg-black/70 flex items-center justify-center z-[1000]',
    'cf-dialog-panel': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-[8px] w-full max-w-[450px]',
    'cf-table-wrapper': 'w-full overflow-x-auto min-w-0',
    'cf-toolbar': 'flex justify-between items-center',
    'cf-content-area': 'flex flex-1 overflow-hidden',
    'cf-panel': 'flex flex-col flex-shrink-0 bg-[var(--bg-secondary)] border-[var(--border-color)]',
    'cf-loading': 'flex items-center justify-center',
    'cf-loading--overlay': 'absolute inset-0 bg-[rgba(13,13,20,0.85)] z-[100]',
    'cf-loading__container': 'flex flex-col items-center gap-3',
    // 旋转圆环 — utility 能表达的写 shortcut，尺寸变体留 SCSS
    // 0.8s duration UnoCSS animate-spin 默认 1s，这里用 [0.8s] 覆盖
    'cf-loading__ring': 'rounded-full border-solid border border-[var(--border-color)] border-t-[var(--accent-blue)] animate-[spin_0.8s_linear_infinite]',
    'cf-loading__text': 'text-[13px] text-[var(--text-secondary)] whitespace-nowrap',
    'cf-empty': 'flex flex-col items-center justify-center py-15 px-5 text-center',
    'cf-scroll-y': 'overflow-y-auto',
    'cf-scrollbar': '[&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-[var(--border-color)] [&::-webkit-scrollbar-thumb]:rounded',
  },
  theme: {
    borderRadius: {
      'xs': '2px',
      'sm': '4px',
      'md': '6px',
      'lg': '8px',
      'xl': '12px',
      'full': '9999px',
    },
  },
})
