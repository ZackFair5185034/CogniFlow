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
    //
    // ⚠️ 前景色规则（2026-09-12）：亮色底（品牌青 / 语义色）上一律用
    // --on-vibrant 深墨色，不要用 text-white —— 白字在 #5898ff 上仅 2.86:1、
    // 在 #22d3ee 上 1.81:1，均不可读；深墨色在五个底色上 5.50–10.24:1 全部达标。
    'ui-btn': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)] hover:border-[var(--text-muted)]',
    'ui-btn-primary': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 bg-[var(--accent)] text-[var(--on-vibrant)] border border-[var(--accent)] hover:bg-[var(--accent-hover)] hover:border-[var(--accent-hover)]',
    'ui-btn-success': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 bg-[var(--color-success)] text-[var(--on-vibrant)] border border-[var(--color-success)] hover:brightness-110',
    'ui-btn-danger': 'inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-md text-[13px] font-medium leading-[1.4] cursor-pointer transition-all duration-150 bg-[var(--color-danger)] text-[var(--on-vibrant)] border border-[var(--color-danger)] hover:brightness-110',
    'ui-btn-small': 'inline-flex items-center justify-center gap-1.5 px-2.5 py-1 text-xs bg-[var(--bg-card)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)]',
    'ui-btn-xs': 'inline-flex items-center justify-center gap-1.5 px-2 py-0.5 text-[11px] rounded-sm bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-primary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)]',
    'ui-btn-icon': 'w-[34px] h-[34px] flex items-center justify-center bg-transparent border-none rounded-md text-[var(--text-secondary)] cursor-pointer transition-all duration-150 hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',

    // === 按钮修饰符 ===
    // 用法：class="ui-btn ui-btn-primary ui-btn-sm" —— 修饰符与基础类组合。
    // 所有属性加 `!`（important）是必须的：UnoCSS 展开 shortcut 后，
    // 同名 utility（如 ui-btn-primary 的 px-4 与 ui-btn-sm 的 px-2.5）
    // 谁生效取决于生成顺序而非 class 书写顺序，加 ! 才能让修饰符稳定覆盖。
    'ui-btn-sm': 'px-2.5! py-1! text-xs! rounded-sm!',
    // 次要按钮：低对比底色 + 边框，hover 时点亮品牌青。
    // 原为 AtlasDetail.vue 局部实现，2026-09-12 提到全局（该局部块已删）。
    'ui-btn-secondary': 'bg-[var(--bg-secondary)]! border-[var(--border-color)]! text-[var(--text-primary)]! hover:border-[var(--accent)]! hover:text-[var(--accent)]!',
    // 注：ui-btn-small / ui-btn-xs 与 ui-btn-sm 语义重叠（三者都表"小"），
    // 本次不做合并以免影响既有 6 处调用，留待后续统一命名的一波处理。

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
    'cf-loading__ring': 'rounded-full border-solid border border-[var(--border-color)] border-t-[var(--accent)] animate-[spin_0.8s_linear_infinite]',
    'cf-loading__text': 'text-[13px] text-[var(--text-secondary)] whitespace-nowrap',

    // === 文字渐变（保留：6 view header 实际在用） ===
    'cf-gradient-text': 'bg-[linear-gradient(90deg,var(--text-primary),var(--accent))] [-webkit-background-clip:text] [background-clip:text] [-webkit-text-fill-color:transparent]',
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
