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
    // === 按钮系统（来源 _common.scss .ui-btn 系列）===
    // 全局基础样式：13px / 500 / 6px 圆角 / 8px-16px padding / 1px border
    // 注：UnoCSS shortcut 不支持类名递归引用，每个变体必须独立写完整 utility
    'ui-btn': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)] hover:border-[var(--text-muted)]',
    'ui-btn-primary': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 bg-[var(--accent-blue)] text-white border border-[var(--accent-blue)] hover:bg-[var(--accent-blue-hover)] hover:border-[var(--accent-blue-hover)]',
    'ui-btn-success': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 bg-[var(--color-success)] text-white border border-[var(--color-success)] hover:bg-[#16a34a] hover:border-[#16a34a]',
    'ui-btn-danger': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 bg-[var(--color-danger)] text-white border border-[var(--color-danger)] hover:bg-[#dc2626] hover:border-[#dc2626]',
    'ui-btn-small': 'inline-flex items-center justify-center gap-1.5 px-2.5 py-1 text-xs bg-[var(--bg-card)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)]',
    'ui-btn-xs': 'inline-flex items-center justify-center gap-1.5 px-2 py-0.5 text-[11px] rounded-sm bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)]',
    'ui-btn-icon': 'w-[34px] h-[34px] flex items-center justify-center bg-transparent border-none rounded-md text-[var(--text-secondary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',

    // === 卡片系统（来源 _common.scss .ui-card 系列）===
    'ui-card': 'bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg overflow-hidden',
    'ui-card-header': 'flex items-center gap-3 px-5 py-4 border-b border-[var(--border-color)]',
    'ui-card-content': 'p-5',

    // === 标签系统（来源 _common.scss .ui-tag 系列）===
    'ui-tag': 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium leading-[1.5]',
    'ui-tag-blue': 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium leading-[1.5] bg-[var(--color-info-bg)] text-[var(--accent-blue)]',
    'ui-tag-green': 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium leading-[1.5] bg-[var(--color-success-bg)] text-[var(--color-success)]',
    'ui-tag-yellow': 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium leading-[1.5] bg-[var(--color-warning-bg)] text-[var(--color-warning)]',
    'ui-tag-red': 'inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-medium leading-[1.5] bg-[var(--color-danger-bg)] text-[var(--color-danger)]',

    // === 输入系统（来源 _common.scss .ui-input 系列）===
    // 注：placeholder 颜色留 SCSS 块处理（UNOCSS-EXCEPTION: 4 伪元素）
    'ui-input': 'w-full px-3.5 py-2.5 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] text-[13px] transition-colors duration-150 focus:outline-none focus:border-[var(--accent-blue)]',

    // === 徽章系统（来源 _common.scss .ui-badge 系列）===
    'ui-badge': 'px-2 py-0.5 font-[var(--font-family-mono)] text-[10px] text-[var(--text-muted)] tracking-wider bg-[var(--bg-secondary)] rounded-sm border border-[var(--border-color)]',

    // === 滚动条系统（来源 _common.scss .ui-scrollbar 系列）===
    'ui-scrollbar': 'scrollbar-thin [scrollbar-color:var(--border-color)_transparent] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-[var(--border-color)] [&::-webkit-scrollbar-thumb]:rounded',

    // === LoadingSpinner 子元素（已加，保留） ===
    'cf-loading': 'flex items-center justify-center',
    'cf-loading--overlay': 'absolute inset-0 bg-[rgba(13,13,20,0.85)] z-[100]',
    'cf-loading__container': 'flex flex-col items-center gap-3',
    // 旋转圆环 — utility 能表达的写 shortcut，尺寸变体留 SCSS
    // 0.8s duration UnoCSS animate-spin 默认 1s，这里用 [0.8s] 覆盖
    'cf-loading__ring': 'rounded-full border-solid border border-[var(--border-color)] border-t-[var(--accent-blue)] animate-[spin_0.8s_linear_infinite]',
    'cf-loading__text': 'text-[13px] text-[var(--text-secondary)] whitespace-nowrap',

    // === 文字渐变（保留：6 view header 实际在用） ===
    'cf-gradient-text': 'bg-[linear-gradient(90deg,var(--text-primary),var(--accent-blue))] [-webkit-background-clip:text] [background-clip:text] [-webkit-text-fill-color:transparent]',
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
