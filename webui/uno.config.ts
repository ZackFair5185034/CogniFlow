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
    // === 按钮系统（对齐 Figma Design Token）===
    // Figma: button-primary — 黑色胶囊，无边框
    'vg-btn': 'px-4 py-2.5 rounded-[50px] bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] cursor-pointer transition-all duration-200 hover:border-[var(--accent-cyan)] hover:bg-[var(--bg-hover)]',
    // Figma: button-primary 黑色胶囊
    'vg-btn-primary': 'px-4 py-2.5 rounded-[50px] bg-[var(--color-primary)] text-[var(--color-on-primary)] border-none cursor-pointer transition-all duration-200 font-semibold',
    // 品牌强调按钮（保留 CogniFlow 特色）
    'vg-btn-brand': 'px-4 py-2.5 rounded-[50px] bg-[var(--accent-cyan)] text-black border-none cursor-pointer transition-all duration-200 hover:bg-[#00d4e0] hover:shadow-[var(--glow-cyan)]',
    'vg-btn-small': 'px-3 py-1.5 text-sm rounded-[50px] bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] cursor-pointer transition-all duration-200 hover:border-[var(--accent-cyan)]',
    'vg-btn-icon': 'w-10 h-10 flex items-center justify-center bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded-full transition-all duration-200 hover:bg-[var(--bg-hover)] hover:text-[var(--accent-cyan)]',

    // === 卡片系统 ===
    // Figma: pricing-card — hairline 边框，rounded-lg(24px)，无阴影
    'vg-card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-3xl',
    'vg-card-header': 'flex items-center gap-3 px-6 py-5 border-b border-[var(--border-color)]',
    'vg-card-content': 'p-6',

    // === 布局 ===
    'vg-flex': 'flex',
    'vg-flex-col': 'flex flex-col',
    'vg-items-center': 'items-center',
    'vg-justify-center': 'justify-center',
    'vg-justify-between': 'justify-between',
    'vg-gap-2': 'gap-2',
    'vg-gap-3': 'gap-3',
    'vg-gap-4': 'gap-4',
    'vg-gap-6': 'gap-6',

    // === 文字（对齐 Figma Typography Token）===
    // Figma body-sm: 16px, weight 330
    'vg-text-sm': 'text-base font-[330]',
    // Figma body: 18px, weight 320
    'vg-text-xs': 'text-sm font-[320]',
    'vg-text-lg': 'text-xl font-[330]',
    'vg-text-muted': 'text-[var(--text-muted)]',
    'vg-text-secondary': 'text-[var(--text-secondary)]',
    // Figma: JetBrains Mono 用于 caption/eyebrow
    'vg-font-mono': 'font-[var(--font-family-mono)]',
    'vg-font-bold': 'font-bold',

    // === 状态 ===
    'vg-badge': 'px-2 py-1 text-xs font-[var(--font-family-mono)] rounded border border-[var(--border-color)] text-[var(--text-muted)] uppercase tracking-wider',

    // === 输入 ===
    'vg-input': 'w-full px-3.5 py-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-sm outline-none focus:border-[var(--accent-cyan)] transition-colors',

    // === 动画 ===
    'vg-animate-fade-in': 'animate-fade-in',
    'vg-transition': 'transition-all duration-200',

    // === 项目通用组件样式 ===
    // 页面头部（统一结构）
    'vg-page-header': 'flex justify-between items-center gap-4 flex-shrink-0',
    // 对话框遮罩
    'vg-dialog-overlay': 'fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[1000]',
    // 对话框面板
    'vg-dialog-panel': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-3xl w-full max-w-[450px]',
    // 表格单元格滚动包装
    'vg-table-wrapper': 'w-full overflow-x-auto min-w-0',
    // 工具栏（标注页面等）
    'vg-toolbar': 'flex justify-between items-center',
    // 内容区（flex-1 overflow-hidden）
    'vg-content-area': 'flex flex-1 overflow-hidden',
    // 面板（固定宽度，sidebar）
    'vg-panel': 'flex flex-col flex-shrink-0 bg-[var(--bg-secondary)] border-[var(--border-color)]',
    // 加载状态
    'vg-loading': 'absolute inset-0 flex flex-col items-center justify-center',
    // 空状态
    'vg-empty': 'flex flex-col items-center justify-center py-15 px-5 text-center',
    // 滚动区域
    'vg-scroll-y': 'overflow-y-auto',
    // 滚动条样式
    'vg-scrollbar': '[&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar-track]:bg-[var(--bg-secondary)] [&::-webkit-scrollbar-thumb]:bg-[var(--border-color)] [&::-webkit-scrollbar-thumb]:rounded',
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
    // Figma 圆角 token
    borderRadius: {
      'xs': '2px',
      'sm': '6px',
      'md': '8px',
      'lg': '24px',
      'xl': '32px',
      'pill': '50px',
      'full': '9999px',
    },
  },
})
