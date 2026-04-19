import {
  defineConfig,
  presetUno,
  presetIcons,
  transformerDirectives,
  transformerVariantGroup,
} from 'unocss'

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
  theme: {
    colors: {
      primary: 'var(--accent-cyan)',
      secondary: 'var(--accent-magenta)',
      success: 'var(--accent-green)',
      warning: 'var(--accent-yellow)',
      danger: '#ff4466',
    },
  },
  shortcuts: {
    'vg-btn': 'px-4 py-2 rounded-md border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] cursor-pointer transition-all duration-200 hover:border-[var(--accent-cyan)] hover:bg-[var(--bg-hover)]',
    'vg-btn-primary': 'px-4 py-2 rounded-md bg-[var(--accent-cyan)] border border-[var(--accent-cyan)] text-black cursor-pointer transition-all duration-200 hover:bg-[#00d4e0]',
    'vg-card': 'bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl',
  },
  safelist: [
    'i-carbon-save',
    'i-carbon-trash-can',
    'i-carbon-close',
    'i-carbon-chevron-left',
    'i-carbon-chevron-right',
    'i-carbon-plus',
    'i-carbon-arrow-left',
  ],
})
