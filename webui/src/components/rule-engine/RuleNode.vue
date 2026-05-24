<template>
  <div
    class="rule-node"
    :class="[`category-${data.category}`, { selected }]"
    @contextmenu.prevent="handleContextMenu"
    v-memo="[data.category, data.status, data.label, configSummary, selected]"
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
        <span class="node-type">{{ data.type }}</span>
      </div>
    </div>

    <!-- 配置控件区域 -->
    <div
      v-if="hasConfig"
      class="node-body"
    >
      <div
        v-for="(schema, key) in configProperties"
        :key="key"
        class="node-field"
      >
        <label class="field-label">{{ schema.title || key }}</label>
        <div class="field-control">
          <!-- Slider -->
          <template v-if="schema.widget === 'slider'">
            <el-slider
              :model-value="getNodeValue(key) as number"
              :min="schema.minimum"
              :max="schema.maximum"
              :step="schema.step"
              @update:model-value="(v: number | number[]) => updateConfig(key, Array.isArray(v) ? v[0] : v)"
            />
            <span class="slider-value">{{ getNodeValue(key) }}</span>
          </template>

          <!-- Number -->
          <template v-else-if="schema.widget === 'number'">
            <el-input-number
              :model-value="getNodeValue(key) as number"
              :min="schema.minimum"
              :max="schema.maximum"
              :step="schema.step"
              :controls="false"
              class="number-input"
              @update:model-value="(v: number | undefined) => updateConfig(key, v ?? null)"
            />
          </template>

          <!-- Dropdown -->
          <template v-else-if="schema.widget === 'dropdown'">
            <el-select
              :model-value="getNodeValue(key)"
              class="select-input"
              @update:model-value="updateConfig(key, $event)"
            >
              <el-option
                v-for="opt in schema.enum"
                :key="opt"
                :value="opt"
                :label="opt"
              />
            </el-select>
          </template>

          <!-- Model Select -->
          <template v-else-if="schema.widget === 'model-select'">
            <el-select
              :model-value="getNodeValue(key)"
              class="select-input model-select"
              placeholder="选择模型..."
              @update:model-value="updateConfig(key, $event)"
            >
              <el-option
                v-for="model in availableModels"
                :key="model.id"
                :value="model.id"
                :label="model.name"
              />
            </el-select>
          </template>

          <!-- Textarea -->
          <template v-else-if="schema.widget === 'textarea'">
            <el-input
              :model-value="(getNodeValue(key) as string | number | null) ?? ''"
              type="textarea"
              :placeholder="schema.description || ''"
              :rows="2"
              class="textarea-input"
              :ref="el => setInputRef(key, el)"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- Code -->
          <template v-else-if="schema.widget === 'code'">
            <el-input
              :model-value="(getNodeValue(key) as string | number | null) ?? ''"
              type="textarea"
              :placeholder="schema.description || ''"
              :rows="2"
              class="code-input"
              :ref="el => setInputRef(key, el)"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- Checkbox -->
          <template v-else-if="schema.widget === 'checkbox'">
            <el-checkbox
              :model-value="!!getNodeValue(key)"
              @update:model-value="updateConfig(key, $event)"
            >
              {{ schema.description || '' }}
            </el-checkbox>
          </template>

          <!-- Text / Default -->
          <template v-else>
            <el-input
              :model-value="String(getNodeValue(key) ?? '')"
              :placeholder="schema.description || ''"
              class="text-input"
              :ref="el => setInputRef(key, el)"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- 变量绑定按钮 -->
          <button
            v-if="schema.widget !== 'checkbox'"
            class="var-bind-btn"
            title="绑定变量"
            @click.stop="toggleVarMenu(key)"
          >
            📎
          </button>

          <!-- 变量下拉菜单 -->
          <div
            v-if="activeVarMenu === key && variables.length > 0"
            class="var-dropdown"
          >
            <div
              v-for="v in variables"
              :key="v.name"
              class="var-option"
              @click="bindVariable(key, v.name)"
            >
              {{ formatVarRef(v.name) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部配置摘要 -->
    <div
      v-if="configSummary"
      class="node-footer"
    >
      <span class="summary-text">{{ configSummary }}</span>
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
          :class="['node-handle', `type-${(input.type ?? 'any').toLowerCase()}`]"
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
          :class="['node-handle', `type-${(output.type ?? 'any').toLowerCase()}`]"
        />
      </div>
    </div>

    <!-- 执行状态指示 -->
    <div
      v-if="data.status"
      class="node-status"
    >
      <div
        class="status-indicator"
        :class="data.status"
      />
    </div>

    <!-- 删除按钮 -->
    <button
      class="node-delete-btn"
      title="删除节点"
      @click.stop="data.onDelete?.(data.id)"
    >
      ×
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import SvgIcon from '@/components/SvgIcon.vue'

/** 节点配置值类型（排除 boolean/null，文本输入无法处理） */
type NodeConfigValue = string | number | boolean | null

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
  onDelete?: (nodeId: string) => void
}

// 删除按钮点击回调 - 通过 props 传入
const props = defineProps<{
  data: NodeData
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:config', key: string, value: string | number | boolean | null): void
  (e: 'delete', nodeId: string): void
  (e: 'contextmenu', event: MouseEvent): void
}>()

function handleContextMenu(event: MouseEvent) {
  event.preventDefault()
  emit('contextmenu', event)
}

// 可用模型（model-select用）
const configProperties = computed((): Record<string, ConfigSchemaProperty> => {
  return props.data.configSchema ?? (Object.create(null) as Record<string, ConfigSchemaProperty>)
})

// 是否有配置
const hasConfig = computed(() => {
  return Object.keys(configProperties.value).length > 0
})

// 节点配置（合并默认值）
const nodeConfig = computed((): Record<string, NodeConfigValue> => {
  const defaults: Record<string, NodeConfigValue> = {}
  const schema = props.data.configSchema ?? {}
  for (const [key, prop] of Object.entries(schema)) {
    if ((prop as ConfigSchemaProperty).default !== undefined) {
      defaults[key] = (prop as ConfigSchemaProperty).default as NodeConfigValue
    }
  }
  return { ...defaults, ...(props.data.config as Record<string, NodeConfigValue>) }
})

/** 获取节点配置值（辅助方法，解决动态索引类型推断问题） */
function getNodeValue(key: string): string | number | boolean | null {
  return (nodeConfig.value as Record<string, string | number | boolean | null>)[key] ?? null
}

// 可用模型（model-select用）
const availableModels = inject<Array<{ id: number; name: string }>>('availableModels', [])

// 可用变量列表（从父组件注入）
interface Variable {
  name: string
  type: string
}
const variables = inject<Variable[]>('variables', [])

// 变量绑定菜单状态
const activeVarMenu = ref<string | null>(null)

// 输入框引用字典（用于获取光标位置）
const inputRefs = ref<Record<string, HTMLInputElement | HTMLTextAreaElement>>({})

// 设置输入框引用（el-input 内部有 .input 或 .textarea 属性指向原生元素）
function setInputRef(key: string, el: any) {
  if (!el) {
    delete inputRefs.value[key]
    return
  }
  // el-input 组件实例的 .input 或 .textarea 属性指向原生元素
  if (el.input) {
    inputRefs.value[key] = el.input
  } else if (el.textarea) {
    inputRefs.value[key] = el.textarea
  } else if (el.$el && (el.$el.tagName === 'INPUT' || el.$el.tagName === 'TEXTAREA')) {
    inputRefs.value[key] = el.$el
  }
}

function toggleVarMenu(key: string) {
  activeVarMenu.value = activeVarMenu.value === key ? null : key
}

function bindVariable(key: string, varName: string) {
  // 将变量插入到光标位置
  const currentValue = String(nodeConfig.value[key] || '')
  const varRef = `{{${varName}}}`

  // 检查重复引用
  if (currentValue.includes(varRef)) {
    // 变量已存在，静默忽略
    activeVarMenu.value = null
    return
  }

  // 获取输入框引用，尝试在光标位置插入
  const inputEl = inputRefs.value[key]
  let newValue: string

  if (inputEl && (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT')) {
    const start = inputEl.selectionStart ?? currentValue.length
    const end = inputEl.selectionEnd ?? currentValue.length
    // 在光标位置插入变量
    newValue = currentValue.slice(0, start) + varRef + currentValue.slice(end)
    // 更新输入框值和光标位置
    updateConfig(key, newValue)
    // 设置光标在变量引用之后
    setTimeout(() => {
      if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
        const newPos = start + varRef.length
        inputEl.setSelectionRange(newPos, newPos)
        inputEl.focus()
      }
    }, 0)
  } else {
    // 如果无法获取光标位置，则追加到末尾
    newValue = currentValue ? currentValue + varRef : varRef
    updateConfig(key, newValue)
  }

  activeVarMenu.value = null
}

// 格式化变量引用显示
function formatVarRef(name: string) {
  return `{{${name}}}`
}

// 底部配置摘要
const configSummary = computed(() => {
  const parts: string[] = []
  const schema = props.data.configSchema || {}
  const config = nodeConfig.value

  // 关键配置项：model_id, confidence, threshold 等
  const summaryKeys = ['model_id', 'confidence', 'iou_threshold', 'max_detections', 'device',
                        'interval_ms', 'delay_ms', 'expression', 'method', 'url']

  for (const key of summaryKeys) {
    if (schema[key] && config[key] !== undefined) {
      const val = config[key]
      const label = schema[key]?.title || key
      if (val !== '' && val !== null && val !== undefined) {
        // 截断过长值
        const displayVal = String(val).length > 12
          ? `${String(val).slice(0, 10)}...`
          : String(val)
        parts.push(`${label}: ${displayVal}`)
      }
    }
  }

  return parts.slice(0, 3).join(' | ') // 最多显示3项
})

// 更新配置
function updateConfig(key: string, value: string | number | boolean | null) {
  emit('update:config', key, value)
}

// 清理 inputRefs 避免内存泄漏
onBeforeUnmount(() => {
  inputRefs.value = {}
})
</script>

<style scoped lang="scss">
.rule-node,
:deep(.vue-flow__node) {
  overflow: visible !important;
}

.rule-node {
  background: linear-gradient(180deg, #2d2d30 0%, #252528 100%);
  border: 1px solid #404044;
  border-radius: 6px;
  min-width: 200px;
  max-width: 280px;
  font-size: 12px;
  color: #e0e0e0;
  position: relative;
  transition: all 0.2s ease;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 2px 8px rgba(0,0,0,0.3);
  /* 连接点和删除按钮需要溢出显示，但不能影响布局 */
  overflow: visible;
}

/* 确保节点容器不裁剪子元素 */
.rule-node-wrapper {
  overflow: visible;
}

/* Handle 使用 overflow: visible 避免被裁剪 */
.vue-flow__handle {
  overflow: visible !important;
}

.rule-node:hover {
  border-color: #505055;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 16px rgba(0,0,0,0.4);
}

.rule-node.selected {
  border-color: #5898ff;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 0 0 1px rgba(88,152,255,0.3),
    0 4px 16px rgba(0,0,0,0.4);
}

/* 标题栏 - 使用背景色区分类型 */
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.category-input .node-header { background: linear-gradient(90deg, rgba(76,255,76,0.2), rgba(76,255,76,0.05)); }
.category-detection .node-header { background: linear-gradient(90deg, rgba(88,152,255,0.2), rgba(88,152,255,0.05)); }
.category-processing .node-header { background: linear-gradient(90deg, rgba(255,255,76,0.2), rgba(255,255,76,0.05)); }
.category-action .node-header { background: linear-gradient(90deg, rgba(255,127,76,0.2), rgba(255,127,76,0.05)); }
.category-logic .node-header { background: linear-gradient(90deg, rgba(220,79,220,0.2), rgba(220,79,220,0.05)); }
.category-output .node-header { background: linear-gradient(90deg, rgba(255,76,76,0.2), rgba(255,76,76,0.05)); }

.node-icon {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-icon svg {
  width: 14px;
  height: 14px;
}

.category-input .node-icon { background: rgba(76, 255, 76, 0.15); color: #4CFF4C; }
.category-detection .node-icon { background: rgba(0, 240, 255, 0.15); color: #00f0FF; }
.category-processing .node-icon { background: rgba(255, 255, 76, 0.15); color: #FFFF4C; }
.category-action .node-icon { background: rgba(255, 127, 76, 0.2); color: #FF7F4C; }
.category-logic .node-icon { background: rgba(220, 79, 220, 0.2); color: #DC4FDC; }
.category-output .node-icon { background: rgba(255, 76, 76, 0.2); color: #FF4C4C; }

.node-title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-label {
  font-weight: 600;
  font-size: 13px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-type {
  font-size: 10px;
  color: #888;
  font-family: monospace;
}

/* 配置区域 */
.node-body {
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(0,0,0,0.15);
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.node-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 10px;
  color: #777;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.field-control {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 输入控件样式 */
.text-input,
.number-input,
.select-input {
  flex: 1;
  background: #1a1a1c;
  border: 1px solid #3a3a3c;
  border-radius: 4px;
  padding: 5px 8px;
  font-size: 12px;
  color: #e0e0e0;
  min-width: 0;
}

.text-input:focus,
.number-input:focus,
.select-input:focus {
  outline: none;
  border-color: #5898ff;
}

.slider-input {
  flex: 1;
  height: 4px;
  background: #3a3a4a;
  border-radius: 2px;
  -webkit-appearance: none;
}

.slider-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  background: #5898ff;
  border-radius: 50%;
  cursor: pointer;
}

.slider-value {
  font-size: 11px;
  color: #5898ff;
  min-width: 32px;
  text-align: right;
  font-family: monospace;
}

.select-input {
  cursor: pointer;
}

/* Textarea / Code */
.textarea-input,
.code-input {
  flex: 1;
  width: 100%;
  background: #1a1a24;
  border: 1px solid #3a3a4a;
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 11px;
  color: #e0e0e0;
  font-family: monospace;
  resize: vertical;
  min-height: 40px;
}

.code-input {
  background: #0a0a12;
  min-height: 36px;
}

.textarea-input:focus,
.code-input:focus {
  outline: none;
  border-color: #5898ff;
}


/* Checkbox */
.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.checkbox-input {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: #5898ff;
}

.checkbox-label {
  font-size: 11px;
  color: #aaa;
}

/* 变量绑定按钮 */
.var-bind-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 3px;
  color: #888;
  flex-shrink: 0;
}

.var-bind-btn:hover {
  background: #3a3a4a;
  color: #5898ff;
}

/* 变量下拉菜单 */
.var-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  background: #2a2a3a;
  border: 1px solid #3a3a4a;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 100;
  min-width: 120px;
  max-height: 150px;
  overflow-y: auto;
}

.var-option {
  padding: 6px 10px;
  font-size: 11px;
  font-family: monospace;
  color: #5898ff;
  cursor: pointer;
}

.var-option:hover {
  background: #3a3a4a;
}

.field-control {
  position: relative;
  flex-wrap: wrap;
}

/* 底部配置摘要 */
.node-footer {
  padding: 4px 12px;
  background: #16161e;
  border-top: 1px solid #2a2a3a;
  border-radius: 0 0 8px 8px;
}

.summary-text {
  font-size: 10px;
  color: #777;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

/* 端口区域 - 左进右出自然连接流 */
.node-ports {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0;
  min-height: 24px;
}

.port-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 2px 12px;
  position: relative;
}

/* 输入端口：Handle 在左，整体左对齐 */
.port-item.port-in {
  justify-content: flex-start;
}

/* 输出端口：Handle 在右，整体右对齐 */
.port-item.port-out {
  justify-content: flex-end;
}

/* VueFlow Handle 样式 - 确保连接点定位在节点边框上 */
.node-handle {
  width: 14px !important;
  height: 14px !important;
  background: #1e1e2e !important;
  border: 2px solid #5a5a6a !important;
  border-radius: 50% !important;
  cursor: crosshair !important;
  transition: all 0.15s ease !important;
  flex-shrink: 0;
}

/* 强制 Handle 定位到节点边框，垂直居中对齐 port-item */
:deep(.vue-flow__handle-left) {
  left: -7px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
}

:deep(.vue-flow__handle-right) {
  right: -7px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
}

/* 确保 handle 容器不裁剪 */
:deep(.vue-flow__handle) {
  position: absolute !important;
}

.node-handle:hover {
  width: 16px !important;
  height: 16px !important;
  border-color: #5898ff !important;
  box-shadow: 0 0 12px rgba(0, 240, 255, 0.6) !important;
}

/* 端口类型颜色 — 同色可连（Blender风格） */
.node-handle.type-image    { border-color: #4CFF4C; }   /* 绿色 */
.node-handle.type-bbox     { border-color: #00f0FF; }   /* 青色 */
.node-handle.type-mask     { border-color: #00f0FF; }   /* 青色 */
.node-handle.type-scores   { border-color: #FF7F4C; }   /* 橙色 */
.node-handle.type-trigger  { border-color: #DC4FDC; }   /* 紫色 */
.node-handle.type-control  { border-color: #DC4FDC; }   /* 紫色 */
.node-handle.type-int      { border-color: #3B82F6; }   /* 蓝色 */
.node-handle.type-float    { border-color: #14B8A6; }  /* 青色 */
.node-handle.type-boolean  { border-color: #FF4C4C; }   /* 红色 */
.node-handle.type-string   { border-color: #8B5CF6; }   /* 紫色 */
.node-handle.type-array    { border-color: #FFFF4C; }   /* 黄色 */
.node-handle.type-object   { border-color: #FFFF4C; }   /* 黄色 */
.node-handle.type-model    { border-color: #888888; }   /* 灰色 */
.node-handle.type-any      { border-color: #E0E0E0; }   /* 浅灰 */

/* 已连接端口：类型色 + 绿色边框叠加，不覆盖类型色本身 */
.node-handle.vue-flow-handle-connected {
  border-color: #22c55e !important;
  background: #1e1e2e !important;
}

.port-label {
  font-size: 12px;
  color: #aaa;
  white-space: nowrap;
}

/* 执行状态 */
.node-status {
  position: absolute;
  top: 8px;
  right: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.status-indicator.running {
  background: #5898ff;
  animation: pulse 1s infinite;
}

.status-indicator.success {
  background: #4CFF4C;
}

.status-indicator.failed {
  background: #FF4C4C;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 删除按钮 */
.node-delete-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ff4c4c;
  border: 2px solid #1e1e2e;
  color: #fff;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;

  &:hover {
    opacity: 1;
    transform: scale(1.1);
  }

  /* 节点选中或悬停时显示删除按钮 */
  .rule-node:hover &,
  .rule-node.selected & {
    opacity: 1;
    pointer-events: auto;
  }
}

</style>
