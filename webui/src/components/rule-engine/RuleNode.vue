<template>
  <div
    v-bind="$attrs"
    class="rule-node"
    :class="`category-${data.category}`"
    :data-status="data.status || 'idle'"
    @contextmenu.prevent="emit('contextmenu', $event)"
  >
    <!-- 标题栏 -->
    <div class="node-header">
      <div
        class="node-icon"
        :class="data.category"
      >
        <SvgIcon :name="data.category" />
      </div>
      <div class="node-title">
        <span class="node-label">{{ data.label || data.type }}</span>
      </div>
    </div>

    <!-- 节点摘要: 由父组件计算后传入，不依赖节点内部数据 -->
    <div
      v-if="data.summaryText"
      class="node-summary"
    >
      {{ data.summaryText }}
    </div>

    <!-- 端口区域 - 左进右出 -->
    <div
      v-if="(data.inputs?.length || 0) > 0 || (data.outputs?.length || 0) > 0"
      class="node-ports"
    >
      <div
        v-for="input in data.inputs"
        :key="'in-' + input.name"
        class="port-item port-in"
      >
        <Handle
          :id="input.name"
          type="target"
          :position="Position.Left"
          :class="['node-handle', `type-${(input.type ?? 'any').toLowerCase()}`, { 'is-connected': isInputConnected(input.name) }]"
        />
        <span class="port-label">{{ input.label || input.name }}</span>
      </div>
      <div
        v-for="output in data.outputs"
        :key="'out-' + output.name"
        class="port-item port-out"
      >
        <span class="port-label">{{ output.label || output.name }}</span>
        <Handle
          :id="output.name"
          type="source"
          :position="Position.Right"
          :class="['node-handle', `type-${(output.type ?? 'any').toLowerCase()}`, { 'is-connected': isOutputConnected(output.name) }]"
        />
      </div>
    </div>

    <!-- 执行状态指示 -->
    <div
      v-if="data.status && data.status !== 'idle'"
      class="node-status"
    >
      <div
        class="status-indicator"
        :class="data.status"
        :title="statusTitle"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * RuleNode - 轻量节点壳 (Phase B 重构)
 *
 * 终极瘦身版: 所有配置编辑全由 NodeConfigEditor (右侧属性面板) 接管。
 * 节点壳只负责:
 *   1. 视觉: 标题、类型图标、状态指示、端口
 *   2. 摘要: 由父组件计算后写入 data.summaryText, 避免内部 computed
 *   3. Quick Controls: 已彻底移除 (ENABLE_QUICK_CONTROLS = false)
 *   4. 无 el-* 控件, 无内部接口调用, 所有配置更新走右侧面板
 *
 * v-memo 依赖: [data.id, data.status, data.summaryText, data.category]
 * - data.status 不变 → 状态指示器不重渲染
 * - data.summaryText 不变 → 摘要文本不重渲染
 * - selected 等外部状态走 CSS (outline) 不触发组件更新
 */
import { computed } from 'vue'
import { Position, Handle } from '@vue-flow/core'
import { useRuleEngineStore } from '@/stores/ruleEngine'

defineOptions({ inheritAttrs: false })

interface Port {
  name: string
  label?: string
  type: string
}

interface NodeData {
  id: string
  type: string
  category: string
  label?: string
  description?: string
  inputs?: Port[]
  outputs?: Port[]
  status?: string
  /** 摘要文本 — 由父组件在写入 summaryText 前预计算好 */
  summaryText?: string
}

const props = defineProps<{
  data: NodeData
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'contextmenu', event: MouseEvent): void
}>()

const store = useRuleEngineStore()

// ============ 状态指示器 tooltip ============

const statusTitle = computed(() => {
  switch (props.data.status) {
    case 'running': return '正在执行...'
    case 'success': return '执行成功'
    case 'failed': return '执行失败'
    case 'timeout': return '执行超时'
    default: return ''
  }
})

// ============ Handle 连接状态 (store 全局索引 O(1) 查询) ============

function isInputConnected(handleId: string): boolean {
  return store.isHandleConnected(props.data.id, handleId, 'target')
}

function isOutputConnected(handleId: string): boolean {
  return store.isHandleConnected(props.data.id, handleId, 'source')
}
</script>

<style scoped lang="scss">
/* ============================================
 * 终极轻量节点壳样式 (Phase B 重构)
 * ============================================ */
.rule-node {
  background: linear-gradient(180deg, #2d2d30 0%, #252528 100%);
  border: 1px solid #404044;
  border-radius: 6px;
  width: 200px;
  font-size: 12px;
  color: #e0e0e0;
  position: relative;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 2px 8px rgba(0,0,0,0.3);
  contain: layout style;
  overflow: visible !important;
}

/* 标题栏 */
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.node-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-icon svg {
  width: 12px;
  height: 12px;
}

.node-title {
  flex: 1;
  min-width: 0;
}

.node-label {
  font-weight: 600;
  font-size: 12px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

/* 分类头部渐变 */
.category-input .node-header { background: linear-gradient(90deg, rgba(76,255,76,0.2), rgba(76,255,76,0.05)); }
.category-detection .node-header { background: linear-gradient(90deg, rgba(88,152,255,0.2), rgba(88,152,255,0.05)); }
.category-processing .node-header { background: linear-gradient(90deg, rgba(255,255,76,0.2), rgba(255,255,76,0.05)); }
.category-action .node-header { background: linear-gradient(90deg, rgba(255,127,76,0.2), rgba(255,127,76,0.05)); }
.category-logic .node-header { background: linear-gradient(90deg, rgba(220,79,220,0.2), rgba(220,79,220,0.05)); }
.category-output .node-header { background: linear-gradient(90deg, rgba(255,76,76,0.2), rgba(255,76,76,0.05)); }

/* 分类图标颜色 */
.category-input .node-icon { background: rgba(76, 255, 76, 0.15); color: #4CFF4C; }
.category-detection .node-icon { background: rgba(0, 240, 255, 0.15); color: #00f0FF; }
.category-processing .node-icon { background: rgba(255, 255, 76, 0.15); color: #FFFF4C; }
.category-action .node-icon { background: rgba(255, 127, 76, 0.2); color: #FF7F4C; }
.category-logic .node-icon { background: rgba(220, 79, 220, 0.15); color: #DC4FDC; }
.category-output .node-icon { background: rgba(255, 76, 76, 0.15); color: #FF4C4C; }

/* 节点摘要 */
.node-summary {
  padding: 4px 10px 6px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.55);
  font-family: 'JetBrains Mono', monospace;
  background: rgba(0, 0, 0, 0.15);
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  contain: layout style;
}

/* 节点悬停态 */
.rule-node:hover {
  border-color: #505055;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 16px rgba(0,0,0,0.4);
}

/* 节点执行状态高亮 */
.rule-node[data-status='running'] {
  border-color: #5898ff;
  box-shadow:
    inset 0 1px 0 rgba(88,152,255,0.15),
    0 0 0 1px rgba(88,152,255,0.4),
    0 0 18px rgba(88,152,255,0.25);
}
.rule-node[data-status='success'] {
  border-color: #4CFF4C;
  box-shadow:
    inset 0 1px 0 rgba(76,255,76,0.12),
    0 0 0 1px rgba(76,255,76,0.3),
    0 0 12px rgba(76,255,76,0.18);
}
.rule-node[data-status='failed'] {
  border-color: #FF4C4C;
  box-shadow:
    inset 0 1px 0 rgba(255,76,76,0.12),
    0 0 0 1px rgba(255,76,76,0.3),
    0 0 14px rgba(255,76,76,0.2);
}
.rule-node[data-status='timeout'] {
  border-color: #FFA500;
  box-shadow:
    inset 0 1px 0 rgba(255,165,0,0.12),
    0 0 0 1px rgba(255,165,0,0.3),
    0 0 14px rgba(255,165,0,0.2);
}

/* 端口区域 */
.node-ports {
  padding: 6px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.port-item {
  display: flex;
  align-items: center;
  padding: 0 8px;
  min-height: 20px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
}

.port-in {
  justify-content: flex-start;
}

.port-out {
  justify-content: flex-end;
}

.port-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

/* Handle (节点连接点) */
:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  border: 1.5px solid #404044;
  background: #1a1a20;
  transition: border-color 0.15s, background 0.15s;
  overflow: visible !important;
}

:deep(.vue-flow__handle.type-image) { border-color: #4CFF4C; }
:deep(.vue-flow__handle.type-bbox) { border-color: #00f0FF; }
:deep(.vue-flow__handle.type-model) { border-color: #FFA500; }
:deep(.vue-flow__handle.type-string) { border-color: #FFFF4C; }
:deep(.vue-flow__handle.type-control),
:deep(.vue-flow__handle.type-trigger) { border-color: #DC4FDC; }
:deep(.vue-flow__handle.type-any) { border-color: #888; }

:deep(.vue-flow__handle.is-connected) {
  background: currentColor;
}

/* 状态指示器 */
.node-status {
  position: absolute;
  top: 6px;
  right: 6px;
  pointer-events: none;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.running {
  background: #5898ff;
  box-shadow: 0 0 6px rgba(88, 152, 255, 0.7);
  animation: pulse 1.2s ease-in-out infinite;
}

.status-indicator.success {
  background: #4CFF4C;
  box-shadow: 0 0 6px rgba(76, 255, 76, 0.6);
}

.status-indicator.failed {
  background: #FF4C4C;
  box-shadow: 0 0 6px rgba(255, 76, 76, 0.6);
}

.status-indicator.timeout {
  background: #FFA500;
  box-shadow: 0 0 6px rgba(255, 165, 0, 0.6);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}
</style>
