<template>
  <div
    v-bind="$attrs"
    v-memo="[data.id, data.status, data.config, quickControlsHash, summaryText]"
    class="rule-node"
    :class="`category-${data.category}`"
    :data-status="data.status || 'idle'"
    @contextmenu.prevent="handleContextMenu"
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

    <!-- 节点摘要: 1-2 行关键配置值 -->
    <div
      v-if="summaryText"
      class="node-summary"
    >
      {{ summaryText }}
    </div>

    <!--
      Quick Controls: 默认隐藏, 节点壳 100% 纯净 (Phase A 用户决定)
      配置编辑全权由 NodeConfigEditor (右侧属性面板) 接管.
      如需启用, 把 v-if 改为 "enableQuickControls && quickControls.length > 0",
      并在 store 暴露 enableQuickControls 开关. 下方 quickControls / getQuickValue /
      updateQuick / quickControlsHash 已保留, 注释掉模板即可.
    -->
    <div
      v-if="false"
      class="node-quick-controls"
    >
      <div
        v-for="ctrl in quickControls"
        :key="ctrl.key"
        class="quick-ctrl"
        @mousedown.stop
      >
        <span class="quick-ctrl-label">{{ ctrl.schema.title || ctrl.key }}</span>

        <!-- Toggle -->
        <el-switch
          v-if="ctrl.schema.widget === 'toggle'"
          :model-value="!!getQuickValue(ctrl.key)"
          @update:model-value="updateQuick(ctrl.key, !!$event)"
        />

        <!-- Checkbox -->
        <el-checkbox
          v-else-if="ctrl.schema.widget === 'checkbox'"
          :model-value="!!getQuickValue(ctrl.key)"
          @update:model-value="updateQuick(ctrl.key, $event)"
        />

        <!-- Number -->
        <el-input-number
          v-else-if="ctrl.schema.widget === 'number'"
          :model-value="getQuickValue(ctrl.key) as number"
          :min="ctrl.schema.minimum"
          :max="ctrl.schema.maximum"
          :step="ctrl.schema.step"
          :controls="false"
          class="quick-ctrl-number"
          @update:model-value="(v: number | undefined) => updateQuick(ctrl.key, v ?? null)"
        />

        <!-- Short Dropdown (无 enum 的不显示, 留给完整面板) -->
        <el-select
          v-else-if="ctrl.schema.widget === 'dropdown' && ctrl.schema.enum"
          :model-value="getQuickValue(ctrl.key)"
          class="quick-ctrl-dropdown"
          @update:model-value="updateQuick(ctrl.key, $event)"
        >
          <el-option
            v-for="opt in ctrl.schema.enum"
            :key="opt"
            :value="opt"
            :label="opt"
          />
        </el-select>
      </div>
    </div>

    <!-- 端口区域 - 左进右出（自然连接流） -->
    <div
      v-if="(data.inputs?.length || 0) > 0 || (data.outputs?.length || 0) > 0"
      class="node-ports"
    >
      <!-- 输入端口：Handle 在左，文字在右（左对齐） -->
      <div
        v-for="input in data.inputs"
        :key="'in-' + input.name"
        class="port-item port-in"
      >
        <Handle
          :id="input.name"
          type="target"
          :position="Position.Left"
          :class="['node-handle', `type-${(input.type ?? 'any').toLowerCase()}`, { 'is-connected': isHandleConnected(input.name) }]"
        />
        <span class="port-label">{{ input.label || input.name }}</span>
      </div>
      <!-- 输出端口：文字在左，Handle 在右（右对齐） -->
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
          :class="['node-handle', `type-${(output.type ?? 'any').toLowerCase()}`, { 'is-connected': isHandleConnected(output.name) }]"
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
 * RuleNode - 轻量节点壳 (Phase A 改造)
 *
 * 节点体职责:
 * 1. 视觉: 标题、类型图标、状态指示、端口
 * 2. 摘要: 1-2 行关键配置值
 * 3. Quick Controls: 最多 3 个最轻量字段 (number/toggle/checkbox/short dropdown)
 * 4. 配置编辑全部移至 NodeConfigEditor.vue (右侧属性面板)
 */
import { computed } from 'vue'
import { Position } from '@vue-flow/core'
import { useRuleEngineStore } from '@/stores/ruleEngine'

/**
 * 关闭自动属性透传：Vue Flow 注入的 props (id/type/position/dimensions/dragging)
 * 不会触发 fragment 根警告。手动 v-bind="$attrs" 绑到节点 div。
 */
defineOptions({ inheritAttrs: false })

/** 节点配置值类型 */
type NodeConfigValue = string | number | boolean | (string | number)[] | null

interface ConfigSchemaProperty {
  type: string
  title?: string
  description?: string
  default?: NodeConfigValue
  minimum?: number
  maximum?: number
  step?: number
  enum?: string[]
  widget?: string
  /** multiselect 控件是否允许用户输入自定义选项（不限于 enum） */
  allow_create?: boolean
}

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
  configSchema?: Record<string, ConfigSchemaProperty>
  config?: Record<string, NodeConfigValue>
  status?: string
}

const props = defineProps<{
  data: NodeData
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'contextmenu', event: MouseEvent): void
  /**
   * Vue Flow 透传的节点内部更新事件 (节点大小/端口变化时通知父组件刷新 Handles)
   */
  (e: 'updateNodeInternals'): void
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

// ============ Handle 连接状态 (Phase B 连接索引优化前, 这里直接计算) ============

/** 已连接 handle id 集合 */
const connectedHandleIds = computed<Set<string>>(() => {
  const ids = new Set<string>()
  for (const e of store.edges) {
    if (e.source === props.data.id && e.sourceHandle) ids.add(e.sourceHandle)
    if (e.target === props.data.id && e.targetHandle) ids.add(e.targetHandle)
  }
  return ids
})

function isHandleConnected(handleId: string): boolean {
  return connectedHandleIds.value.has(handleId)
}

// ============ 节点摘要 (1-2 行关键配置) ============

/** 摘要显示: 选前 2 个有值的关键字段, 用 · 分隔 */
const summaryText = computed(() => {
  const config = props.data.config ?? {}
  const schema = props.data.configSchema ?? {}
  const parts: string[] = []
  for (const [key, prop] of Object.entries(schema)) {
    if (parts.length >= 2) break
    const val = config[key]
    if (val !== undefined && val !== null && val !== '') {
      // 数组只显示长度
      if (Array.isArray(val)) {
        if (val.length === 0) continue
        parts.push(`${prop.title || key}: [${val.length}]`)
      } else {
        // 数字保留 2 位小数
        const display = typeof val === 'number' ? Number(val.toFixed(2)) : val
        parts.push(`${prop.title || key}: ${display}`)
      }
    }
  }
  return parts.join(' · ')
})

// ============ Quick Controls (最多 3 个最轻量字段) ============

/** 轻量 widget 类型, 可在节点壳内直接渲染 (不需要复杂交互) */
const LIGHTWEIGHT_WIDGETS = new Set(['number', 'toggle', 'checkbox', 'dropdown'])

const quickControls = computed(() => {
  const schema = props.data.configSchema ?? {}
  const all = Object.entries(schema) as [string, ConfigSchemaProperty][]
  return all
    .filter(([_, s]) => LIGHTWEIGHT_WIDGETS.has(s.widget ?? ''))
    // toggle/checkbox/short-dropdown (无 enum 或 enum 较短) 优先
    .sort((a, b) => {
      const order = (s: ConfigSchemaProperty) => {
        if (s.widget === 'toggle' || s.widget === 'checkbox') return 0
        if (s.widget === 'dropdown' && (s.enum?.length ?? 0) <= 3) return 1
        return 2
      }
      return order(a[1]) - order(b[1])
    })
    .slice(0, 3)
    .map(([key, sch]) => ({ key, schema: sch }))
})

/** Quick Controls 配置值哈希 (用于 v-memo 引用比较) */
const quickControlsHash = computed(() => {
  if (quickControls.value.length === 0) return ''
  return quickControls.value.map(c => {
    const v = props.data.config?.[c.key]
    return `${c.key}:${v === undefined ? 'u' : JSON.stringify(v)}`
  }).join('|')
})

/** 拿 quick control 当前值 */
function getQuickValue(key: string): NodeConfigValue {
  return (props.data.config as Record<string, NodeConfigValue> | undefined)?.[key] ?? null
}

/** 更新 quick control 值 */
function updateQuick(key: string, value: NodeConfigValue) {
  store.updateNodeConfig(props.data.id, key, value)
}

// ============ 右键菜单 ============

function handleContextMenu(event: MouseEvent) {
  event.preventDefault()
  emit('contextmenu', event)
}
</script>

<style scoped lang="scss">
/* ============================================
 * 轻量节点壳样式 (Phase A)
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
  /* CSS containment: 隔离每个节点的布局/样式重算, 拖拽时不会级联触发兄弟节点 */
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

/* Quick Controls (Phase A 新增) */
.node-quick-controls {
  padding: 6px 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  contain: layout style paint;
}

.quick-ctrl {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-height: 24px;
}

.quick-ctrl-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.quick-ctrl-number {
  width: 90px;
  flex-shrink: 0;
}

.quick-ctrl-dropdown {
  width: 90px;
  flex-shrink: 0;
}

:deep(.quick-ctrl-number .el-input__wrapper),
:deep(.quick-ctrl-dropdown .el-select__wrapper) {
  min-height: 22px !important;
  max-height: 22px !important;
  padding: 0 6px !important;
}

:deep(.quick-ctrl-number .el-input__wrapper .el-input__inner) {
  height: 20px !important;
  line-height: 20px !important;
  font-size: 11px !important;
}

/* 节点悬停态 */
.rule-node:hover {
  border-color: #505055;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 16px rgba(0,0,0,0.4);
}

/* 节点执行状态高亮 (Phase 16.2) */
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
