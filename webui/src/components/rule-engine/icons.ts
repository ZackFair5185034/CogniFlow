// 规则引擎节点图标 - 与 RuleCanvas.vue 保持一致
import { h } from 'vue'

// Input 图标 - 箭头/分支样式
export const InputIcon = () => h('path', {
  d: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
})

// Detection 图标 - 圆形靶心
export const DetectionIcon = () => h('circle', {
  cx: '12',
  cy: '12',
  r: '10',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
})

// Processing 图标 - 齿轮
export const ProcessingIcon = () => h('g', {
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('circle', { cx: '12', cy: '12', r: '3' }),
  h('path', { d: 'M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83' })
])

// Action 图标 - 闪电/动作
export const ActionIcon = () => h('path', {
  d: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
})

// Logic 图标 - 条件分支
export const LogicIcon = () => h('g', {
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
}, [
  h('path', { d: 'M6 4v16M18 4v16' }),
  h('circle', { cx: '6', cy: '12', r: '2' }),
  h('circle', { cx: '18', cy: '12', r: '2' })
])

// Output 图标 - 输出/保存
export const OutputIcon = () => h('path', {
  d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12',
  fill: 'none',
  stroke: 'currentColor',
  'stroke-width': '2'
})

// 导出图标映射
export const categoryIcons = {
  input: InputIcon,
  detection: DetectionIcon,
  processing: ProcessingIcon,
  action: ActionIcon,
  logic: LogicIcon,
  output: OutputIcon
}
