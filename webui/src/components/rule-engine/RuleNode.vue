<template>
  <!--
    v-memo (Phase B + LOD-1): 拖拽时只让 wrapper transform 变化,
    节点壳内部 vdom 完全跳过 patch, 50 节点场景渲染开销从 O(N) 降到 O(1).
    依赖选择依据: 拖动时 data.id/status/summaryText/category 都不变.
    lodLevel 也在依赖里: 缩放切换时强制 patch 一次, 之后稳定.
    selected 走 VueFlow wrapper 的 CSS class, 不需列入依赖.
  -->
  <div
    v-memo="[data.id, data.status, data.summaryText, data.category, lodLevel]"
    v-bind="$attrs"
    class="rule-node"
    :class="[`category-${data.category}`, `lod-${lodLevel}`]"
    :data-status="data.status || 'idle'"
    :data-lod="lodLevel"
    @contextmenu.prevent="emit('contextmenu', $event)"
  >
    <!-- ========== LOD 0/1 通用: 标题栏 ========== -->
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

    <!-- ========== LOD 1: 节点摘要 + 端口区域 (LOD 0 隐藏) ========== -->
    <template v-if="lodLevel >= 1">
      <!-- 节点摘要 -->
      <div
        v-if="data.summaryText"
        class="node-summary"
      >
        {{ data.summaryText }}
      </div>

      <!-- 端口区域 -->
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
        </div>
        <div
          v-for="output in data.outputs"
          :key="'out-' + output.name"
          class="port-item port-out"
        >
          <Handle
            :id="output.name"
            type="source"
            :position="Position.Right"
            :class="['node-handle', `type-${(output.type ?? 'any').toLowerCase()}`, { 'is-connected': isOutputConnected(output.name) }]"
          />
        </div>
      </div>
    </template>

    <!-- 执行状态指示 (所有级别) -->
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
 * RuleNode - 节点壳 (Phase LOD-1)
 *
 * 两级 LOD 渲染:
 *   LOD 0 (zoom < 0.5): 仅标题 + 图标 (极小, 不可连边)
 *   LOD 1 (zoom >= 0.5): 标题 + 端口 + 摘要 (默认)
 *
 * v-memo 依赖: [data.id, data.status, data.summaryText, data.category, lodLevel]
 * - 拖动时 4 个字段不变 → v-memo 命中 → 0 patch
 * - lodLevel 在依赖里: 缩放切换时强制 patch 一次, 之后稳定
 * - selected 走 CSS (outline) 不触发组件更新
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
  /** LOD 等级 0/1 (由父组件 RuleCanvas 计算传入, 可选 — 内部会用 store 回退) */
  lodLevel?: 0 | 1
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

// ============ LOD 默认值 + 派生属性 ============

/**
 * LOD 等级: 优先使用 prop (父组件计算传入), 否则从 store 全局 map 查询.
 * 来自 store 时是响应式的 — 缩放切换会触发重新计算.
 */
const lodLevel = computed<0 | 1>(() => {
  if (props.lodLevel !== undefined) return props.lodLevel
  return store.getLodLevel(props.data.id)
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
  /* === GPU 合成层提示 (Tier 0 性能优化) ===
     - contain: layout style  隔离子树对外部布局/样式影响 (去掉 paint! paint containment
       等同 overflow:hidden, 会裁切超出节点壳的 Handle 圆 → 老大反馈"只能看到半个圆")
     - will-change: transform  提示浏览器提前创建独立合成层
     - translateZ(0) + backface-visibility: hidden  兜底强制 layer,避免子像素抖动 */
  contain: layout style;
  will-change: transform;
  transform: translateZ(0);
  backface-visibility: hidden;
  overflow: visible !important;
}

/* 拖动期间彻底关闭 transition,避免每帧补间触发样式重算 */
.vue-flow__node.dragging .rule-node,
.vue-flow__node.selected.dragging .rule-node {
  transition: none !important;
}

/* P2-I (Phase 17.1): 节点状态切换瞬间禁用 transition
   执行期 50 节点从 idle → running → success 时, transition 期间浏览器 schedule paint
   ~3-5ms/帧. 选中态/拖动态走 .dragging/.selected 锁;
   这里补一刀: data-status 变化时也立即生效, 不补间. */
.rule-node[data-status='running'],
.rule-node[data-status='success'],
.rule-node[data-status='failed'] {
  transition: none !important;
}

/* 标题栏 */
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

/* 展开按钮 (LOD 1 提示) */
.node-expand-btn {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(0, 240, 255, 0.1);
    border-color: rgba(0, 240, 255, 0.3);
    color: #00f0ff;
  }
}

/* ========== LOD 0 极简模式 ========== */
.rule-node.lod-0 {
  width: 120px;
  min-height: 32px;
  border-radius: 4px;
  box-shadow: none;

  .node-header {
    padding: 4px 8px;
    border-bottom: none;
  }
  .node-icon {
    width: 16px;
    height: 16px;
  }
  .node-icon svg { width: 10px; height: 10px; }
  .node-label { font-size: 11px; }
  .node-summary { display: none; }
  .node-ports { display: none; }
  .node-config { display: none; }
}

/* ========== LOD 2 完整模式 ========== */
.rule-node.lod-2 {
  width: 280px;

  .node-config {
    padding: 8px 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
    background: rgba(0, 0, 0, 0.12);
  }
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
  /* 关键: .port-item 是 Handle 的父容器, 自身不应拦截鼠标事件,
     否则 mousedown 会落在 .port-item 而不是 .vue-flow__handle, 导致
     d3-drag filter 检测不到 handle, VueFlow Handle 的 onPointerDown 也不触发. */
  pointer-events: none;
  /* 必须: 让 Handle 的 position: absolute 相对于 port-item 而非 node wrapper,
     VueFlow 默认 .vue-flow__handle-right { top: 50% } 把所有右侧 handle 叠在节点中央,
     多个 handle 互相重叠导致 elementFromPoint 只能命中最后一个. */
  position: relative;
}

/* 端口文字 label 也不应拦截 — 只有 Handle 本身需要交互 */
.port-label {
  pointer-events: none;
}

/* 但 Handle 必须能接收事件 */
:deep(.vue-flow__handle) {
  pointer-events: all !important;
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

/* 显式确认 Handle 在有 connectable 标识时允许事件穿透。
   VueFlow 自带 CSS 中 .vue-flow__handle.connectable 设置 pointer-events: all，
   但 scoped :deep() 选择器优先级可能意外占优，此处重声明以确保交互性 */
:deep(.vue-flow__handle.connectable) {
  pointer-events: all;
  cursor: crosshair;
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
