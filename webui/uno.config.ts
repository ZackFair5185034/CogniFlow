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
    // 按钮
    'vg-btn': 'px-4 py-2 rounded-md border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] cursor-pointer transition-all duration-200 hover:border-[var(--accent-cyan)] hover:bg-[var(--bg-hover)]',
    'vg-btn-primary': 'px-4 py-2 rounded-md bg-[var(--accent-cyan)] border border-[var(--accent-cyan)] text-black cursor-pointer transition-all duration-200 hover:bg-[#00d4e0]',
    'vg-btn-small': 'px-2 py-1 text-sm rounded-md border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] cursor-pointer transition-all duration-200 hover:border-[var(--accent-cyan)]',
    'vg-btn-icon': 'w-6 h-6 flex items-center justify-center bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded transition-all duration-200 hover:bg-[var(--bg-hover)] hover:text-[var(--accent-cyan)]',

    // 卡片
    'vg-card': 'bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl',
    'vg-card-header': 'flex items-center gap-3 px-6 py-5 border-b border-[var(--border-color)]',
    'vg-card-content': 'p-6',

    // 布局
    'vg-flex': 'flex',
    'vg-flex-col': 'flex flex-col',
    'vg-items-center': 'items-center',
    'vg-justify-center': 'justify-center',
    'vg-justify-between': 'justify-between',
    'vg-gap-2': 'gap-2',
    'vg-gap-3': 'gap-3',
    'vg-gap-4': 'gap-4',
    'vg-gap-6': 'gap-6',

    // 文字
    'vg-text-sm': 'text-sm',
    'vg-text-xs': 'text-xs',
    'vg-text-lg': 'text-lg',
    'vg-text-muted': 'text-[var(--text-muted)]',
    'vg-text-secondary': 'text-[var(--text-secondary)]',
    'vg-font-mono': 'font-mono',
    'vg-font-bold': 'font-bold',

    // 状态
    'vg-badge': 'px-2 py-1 text-xs font-mono rounded bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-muted)]',

    // 输入
    'vg-input': 'w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] text-sm outline-none focus:border-[var(--accent-cyan)] transition-colors',

    // 动画
    'vg-animate-fade-in': 'animate-fade-in',
    'vg-transition': 'transition-all duration-200',
  },
  theme: {
    animation: {
      'fade-in': 'fadeIn 0.6s ease forwards',
      'dialog-in': 'dialogIn 0.2s ease',
    },
    keyframes: {
      fadeIn: {
        from: { opacity: '0', transform: 'translateY(20px)' },
        to: { opacity: '1', transform: 'translateY(0)' },
      },
      dialogIn: {
        from: { opacity: '0', transform: 'scale(0.95) translateY(-10px)' },
        to: { opacity: '1', transform: 'scale(1) translateY(0)' },
      },
    },
  },
})
