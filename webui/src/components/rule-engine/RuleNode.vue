<template>
  <div class="rule-node" :class="[`category-${data.category}`, { selected }]">
    <!-- 顶部3px色条 -->
    <div class="node-color-bar"></div>

    <!-- 标题栏 -->
    <div class="node-header">
      <div class="node-icon" :class="data.category">
        <!-- Input: 箭头 -->
        <svg v-if="data.category === 'input'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
        <!-- Detection: 靶心 -->
        <svg v-else-if="data.category === 'detection'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <circle cx="12" cy="12" r="6"/>
          <circle cx="12" cy="12" r="2"/>
        </svg>
        <!-- Processing: 齿轮 -->
        <svg v-else-if="data.category === 'processing'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
        </svg>
        <!-- Action: 闪电 -->
        <svg v-else-if="data.category === 'action'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        <!-- Logic: 分支 -->
        <svg v-else-if="data.category === 'logic'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 4v16M18 4v16"/>
          <circle cx="6" cy="12" r="2"/>
          <circle cx="18" cy="12" r="2"/>
        </svg>
        <!-- Output: 下载 -->
        <svg v-else-if="data.category === 'output'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <!-- Fallback -->
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
        </svg>
      </div>
      <div class="node-title">
        <span class="node-label">{{ data.label || data.type }}</span>
        <span class="node-type">{{ data.type }}</span>
      </div>
    </div>

    <!-- 配置控件区域 -->
    <div class="node-body" v-if="hasConfig">
      <div
        v-for="(schema, key) in configProperties"
        :key="key"
        class="node-field"
      >
        <label class="field-label">{{ schema.title || key }}</label>
        <div class="field-control">
          <!-- Slider -->
          <template v-if="schema.widget === 'slider'">
            <input
              type="range"
              :min="schema.minimum"
              :max="schema.maximum"
              :step="schema.step"
              :value="nodeConfig[key]"
              @input="updateConfig(key, ($event.target as HTMLInputElement).value)"
              class="slider-input"
            />
            <span class="slider-value">{{ nodeConfig[key] }}</span>
          </template>

          <!-- Number -->
          <template v-else-if="schema.widget === 'number'">
            <input
              type="number"
              :min="schema.minimum"
              :max="schema.maximum"
              :step="schema.step"
              :value="nodeConfig[key]"
              @input="updateConfig(key, Number(($event.target as HTMLInputElement).value))"
              class="number-input"
            />
          </template>

          <!-- Dropdown -->
          <template v-else-if="schema.widget === 'dropdown'">
            <select
              :value="nodeConfig[key]"
              @change="updateConfig(key, ($event.target as HTMLSelectElement).value)"
              class="select-input"
            >
              <option
                v-for="opt in schema.enum"
                :key="opt"
                :value="opt"
              >{{ opt }}</option>
            </select>
          </template>

          <!-- Model Select -->
          <template v-else-if="schema.widget === 'model-select'">
            <select
              :value="nodeConfig[key]"
              @change="updateConfig(key, ($event.target as HTMLSelectElement).value)"
              class="select-input model-select"
            >
              <option value="">选择模型...</option>
              <option
                v-for="model in availableModels"
                :key="model.id"
                :value="model.id"
              >{{ model.name }}</option>
            </select>
          </template>

          <!-- Text / Default -->
          <template v-else>
            <input
              type="text"
              :value="nodeConfig[key]"
              @input="updateConfig(key, ($event.target as HTMLInputElement).value)"
              class="text-input"
              :placeholder="schema.description || ''"
            />
          </template>
        </div>
      </div>
    </div>

    <!-- 端口区域 - 左进右出 -->
    <div class="node-ports">
      <!-- 左侧输入端口 -->
      <div class="ports-side inputs" v-if="data.inputs?.length">
        <div
          v-for="input in data.inputs"
          :key="input.name"
          class="port-item"
        >
          <div class="port-dot input-port" :class="input.type?.toLowerCase()"></div>
          <span class="port-label">{{ input.label || input.name }}</span>
        </div>
      </div>

      <!-- 右侧输出端口 -->
      <div class="ports-side outputs" v-if="data.outputs?.length">
        <div
          v-for="output in data.outputs"
          :key="output.name"
          class="port-item"
        >
          <span class="port-label">{{ output.label || output.name }}</span>
          <div class="port-dot output-port" :class="output.type?.toLowerCase()"></div>
        </div>
      </div>
    </div>

    <!-- 执行状态指示 -->
    <div class="node-status" v-if="data.status">
      <div class="status-indicator" :class="data.status"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import {
  InputIcon,
  DetectionIcon,
  ProcessingIcon,
  ActionIcon,
  LogicIcon,
  OutputIcon
} from './icons'

interface ConfigSchemaProperty {
  type: string
  title?: string
  description?: string
  default?: any
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
  configSchema?: {
    properties?: Record<string, ConfigSchemaProperty>
  }
  config?: Record<string, any>
  status?: string
}

const props = defineProps<{
  data: NodeData
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:config', key: string, value: any): void
}>()

// 分类图标映射
function getCategoryIcon(category: string) {
  const icons: Record<string, any> = {
    input: InputIcon,
    detection: DetectionIcon,
    processing: ProcessingIcon,
    action: ActionIcon,
    logic: LogicIcon,
    output: OutputIcon
  }
  return icons[category] || icons.action
}

// 配置属性 - 后端返回扁平格式 {key: ConfigSchemaProperty}
const configProperties = computed(() => {
  return props.data.configSchema || {}
})

// 是否有配置
const hasConfig = computed(() => {
  return Object.keys(configProperties.value).length > 0
})

// 节点配置（合并默认值）
const nodeConfig = computed(() => {
  const defaults: Record<string, any> = {}
  const schema = props.data.configSchema || {}
  for (const [key, prop] of Object.entries(schema)) {
    if ((prop as any).default !== undefined) {
      defaults[key] = (prop as any).default
    }
  }
  return { ...defaults, ...props.data.config }
})

// 可用模型（model-select用）
const availableModels = inject<Array<{ id: number; name: string }>>('availableModels', [])

// 更新配置
function updateConfig(key: string, value: any) {
  emit('update:config', key, value)
}
</script>

<style scoped>
.rule-node {
  background: #1e1e2e;
  border: 1px solid #3a3a4a;
  border-radius: 8px;
  min-width: 200px;
  max-width: 280px;
  font-size: 12px;
  color: #e0e0e0;
  position: relative;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.rule-node:hover {
  border-color: #5a5a6a;
}

.rule-node.selected {
  border-color: #00f0ff;
  box-shadow: 0 0 0 2px rgba(0, 240, 255, 0.3);
}

/* 顶部3px色条 */
.node-color-bar {
  height: 3px;
  border-radius: 8px 8px 0 0;
}

.category-input .node-color-bar { background: #4CFF4C; }
.category-detection .node-color-bar { background: #00f0FF; }
.category-processing .node-color-bar { background: #FFFF4C; }
.category-action .node-color-bar { background: #FF7F4C; }
.category-logic .node-color-bar { background: #DC4FDC; }
.category-output .node-color-bar { background: #FF4C4C; }

/* 标题栏 */
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #2a2a3a;
}

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

.category-input .node-icon { background: rgba(76, 255, 76, 0.2); color: #4CFF4C; }
.category-detection .node-icon { background: rgba(0, 240, 255, 0.2); color: #00f0FF; }
.category-processing .node-icon { background: rgba(255, 255, 76, 0.2); color: #FFFF4C; }
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
  border-bottom: 1px solid #2a2a3a;
}

.node-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 11px;
  color: #999;
  font-weight: 500;
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
  background: #2a2a3a;
  border: 1px solid #3a3a4a;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #e0e0e0;
  min-width: 0;
}

.text-input:focus,
.number-input:focus,
.select-input:focus {
  outline: none;
  border-color: #00f0ff;
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
  background: #00f0ff;
  border-radius: 50%;
  cursor: pointer;
}

.slider-value {
  font-size: 11px;
  color: #00f0ff;
  min-width: 32px;
  text-align: right;
  font-family: monospace;
}

.select-input {
  cursor: pointer;
}

/* 端口区域 */
.node-ports {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  min-height: 24px;
}

.ports-side {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ports-side.inputs {
  align-items: flex-start;
}

.ports-side.outputs {
  align-items: flex-end;
}

.port-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
}

.port-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #5a5a6a;
  background: #1e1e2e;
  flex-shrink: 0;
}

.port-dot.input-port {
  margin-left: -5px;
}

.port-dot.output-port {
  margin-right: -5px;
}

/* 端口类型颜色 */
.port-dot.image { border-color: #4CFF4C; }
.port-dot.bbox { border-color: #00f0FF; }
.port-dot.mask { border-color: #FFFF4C; }
.port-dot.scores { border-color: #FF7F4C; }
.port-dot.trigger { border-color: #DC4FDC; }
.port-dot.control { border-color: #DC4FDC; }
.port-dot.boolean { border-color: #FF4C4C; }
.port-dot.array { border-color: #4CFF4C; }
.port-dot.any { border-color: #888; }

.port-label {
  font-size: 11px;
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
  background: #00f0ff;
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
</style>
