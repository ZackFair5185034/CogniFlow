<template>
  <div
    class="rule-node"
    :class="[`category-${data.category}`, { selected }]"
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

    <!-- 配置控件区域 -->
    <div
      v-if="hasConfig"
      class="node-body"
    >
      <div
        v-for="(schema, key) in configProperties"
        v-memo="[getNodeValue(key)]"
        :key="key"
        class="node-field"
      >
        <label class="field-label">{{ schema.title || key }}</label>
        <div class="field-control">
          <!-- Slider -->
          <template v-if="schema.widget === 'slider'">
            <div
              style="flex:1; min-width:0;"
              @mousedown.stop
            >
              <el-slider
                :model-value="getNodeValue(key) as number"
                :min="schema.minimum"
                :max="schema.maximum"
                :step="schema.step"
                @update:model-value="(v: number | number[]) => updateConfig(key, Array.isArray(v) ? v[0] : v)"
              />
            </div>
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
              @mousedown.stop
              @update:model-value="(v: number | undefined) => updateConfig(key, v ?? null)"
            />
          </template>

          <!-- Dropdown -->
          <template v-else-if="schema.widget === 'dropdown'">
            <el-select
              :model-value="getNodeValue(key)"
              class="select-input"
              @mousedown.stop
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

          <!-- MultiSelect -->
          <template v-else-if="schema.widget === 'multiselect'">
            <el-select
              :model-value="getNodeValue(key) as (string | number)[] || []"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :filterable="!!schema.allow_create"
              :allow-create="!!schema.allow_create"
              :default-first-option="!!schema.allow_create"
              class="select-input"
              :placeholder="schema.allow_create ? '可输入或选择...' : '请选择...'"
              @mousedown.stop
              @update:model-value="updateConfig(key, $event)"
            >
              <el-option
                v-for="opt in schema.enum"
                :key="opt"
                :value="opt"
                :label="String(opt)"
              />
            </el-select>
          </template>

          <!-- Model Select -->
          <template v-else-if="schema.widget === 'model-select'">
            <el-select
              :key="'ms-' + availableModels.length"
              :model-value="getNodeValue(key)"
              class="select-input model-select"
              :placeholder="availableModels.length === 0 ? '暂无可用模型（请先训练模型）' : '选择模型...'"
              @mousedown.stop
              @update:model-value="updateConfig(key, $event)"
            >
              <el-option
                v-if="availableModels.length === 0"
                :value="''"
                label="暂无可用模型"
                disabled
              />
              <el-option
                v-for="model in availableModels"
                :key="model.id"
                :value="model.id"
                :label="model.name"
              />
            </el-select>
          </template>

          <!-- File Picker -->
          <template v-else-if="schema.widget === 'file-picker'">
            <div class="file-picker-wrapper">
              <el-input
                :model-value="String(getNodeValue(key) ?? '')"
                :placeholder="schema.description || '选择或输入文件路径'"
                class="file-picker-input"
                @update:model-value="updateConfig(key, $event)"
              />
              <button
                class="file-picker-btn"
                title="本地上传"
                @click.stop="openFilePicker(key)"
              >
                <SvgIcon name="file" />
              </button>
              <button
                class="file-picker-btn file-picker-btn-atlas"
                title="从图集选择"
                @click.stop="openAtlasPicker(key)"
              >
                <SvgIcon name="folder" />
              </button>
            </div>
            <input
              :ref="el => setFileInputRef(key, el)"
              type="file"
              accept="image/*,video/*"
              class="file-input-hidden"
              @change="handleFileSelected(key, $event)"
            >
          </template>

          <!-- Textarea -->
          <template v-else-if="schema.widget === 'textarea'">
            <el-input
              :ref="el => setInputRef(key, el)"
              :model-value="(getNodeValue(key) as string | number | null) ?? ''"
              type="textarea"
              :placeholder="schema.description || ''"
              :rows="2"
              class="textarea-input"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- Code -->
          <template v-else-if="schema.widget === 'code'">
            <el-input
              :ref="el => setInputRef(key, el)"
              :model-value="(getNodeValue(key) as string | number | null) ?? ''"
              type="textarea"
              :placeholder="schema.description || ''"
              :rows="2"
              class="code-input"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- Toggle -->
          <template v-else-if="schema.widget === 'toggle'">
            <el-switch
              :model-value="!!getNodeValue(key)"
              active-text="开启"
              inactive-text="关闭"
              @mousedown.stop
              @update:model-value="(v: unknown) => updateConfig(key, !!v)"
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
              :ref="el => setInputRef(key, el)"
              :model-value="String(getNodeValue(key) ?? '')"
              :placeholder="schema.description || ''"
              class="text-input"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- 变量绑定按钮：引用上游节点的输出值作为当前字段的变量 -->
          <el-tooltip
            v-if="schema.widget !== 'checkbox' && schema.widget !== 'toggle' && schema.widget !== 'multiselect'"
            content="绑定变量 — 引用上游节点输出的值作为动态输入（格式：{{变量名}}）"
            placement="top"
            :show-after="300"
          >
            <button
              class="var-bind-btn"
              title="绑定变量 — 引用上游节点的输出"
              @click.stop="toggleVarMenu(key)"
            >
              <SvgIcon name="tag" />
            </button>
          </el-tooltip>

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
      v-if="data.status && data.status !== 'idle'"
      class="node-status"
    >
      <div
        class="status-indicator"
        :class="data.status"
        :title="statusTitle"
      />
    </div>

    <!-- 删除按钮已移除：保留右键菜单删除 + Delete/Backspace 快捷键删除 -->
  </div>

  <!-- Atlas 图集选择对话框 -->
  <el-dialog
    v-model="atlasDialog.visible"
    title="从图集选择"
    width="600px"
    :close-on-click-modal="false"
    @close="closeAtlasDialog"
  >
    <div v-if="atlasDialog.errorMessage" class="atlas-error">
      {{ atlasDialog.errorMessage }}
    </div>
    <div v-if="atlasDialog.atlases.length > 0" class="atlas-section">
      <label class="atlas-label">选择图集：</label>
      <el-select
        :model-value="atlasDialog.selectedAtlasId"
        placeholder="选择图集"
        :loading="atlasDialog.loading"
        @update:model-value="(v: number | null) => v && selectAtlas(v)"
      >
        <el-option
          v-for="a in atlasDialog.atlases"
          :key="a.id"
          :value="a.id"
          :label="a.name"
        />
      </el-select>
    </div>
    <div v-else-if="!atlasDialog.loading" class="atlas-empty">
      暂无图集
    </div>
    <div v-if="atlasDialog.images.length > 0" class="atlas-image-grid">
      <div
        v-for="img in atlasDialog.images"
        :key="img.id"
        class="atlas-image-item"
        :title="img.filename"
        @click="selectAtlasImage(img)"
      >
        <img :src="img.url" :alt="img.filename">
        <span class="atlas-image-name">{{ img.filename }}</span>
      </div>
    </div>
    <template #footer>
      <button class="ui-btn ui-btn-small" @click="closeAtlasDialog">关闭</button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { Position } from '@vue-flow/core'
import { useRuleEngineStore } from '@/stores/ruleEngine'
import type { Variable } from '@/stores/ruleEngine'
import { atlasApi } from '@/api'

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
}>()

const store = useRuleEngineStore()

function handleContextMenu(event: MouseEvent) {
  event.preventDefault()
  emit('contextmenu', event)
}

// 状态指示器 tooltip 文案
const statusTitle = computed(() => {
  switch (props.data.status) {
    case 'running': return '正在执行...'
    case 'success': return '执行成功'
    case 'failed': return '执行失败'
    case 'timeout': return '执行超时'
    default: return ''
  }
})

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
function getNodeValue(key: string): NodeConfigValue {
  return (nodeConfig.value as Record<string, NodeConfigValue>)[key] ?? null
}

// 可用模型（model-select用，从 Pinia store 读取）
const availableModels = computed(() => store.availableModels)

// 可用变量列表（从 Pinia store 读取，单源模式）
const variables = computed<Variable[]>(() => store.variables)

// 变量绑定菜单状态
const activeVarMenu = ref<string | null>(null)

// 输入框引用字典（用于获取光标位置）
const inputRefs = ref<Record<string, HTMLInputElement | HTMLTextAreaElement>>({})

// 文件输入引用字典（file-picker widget 使用）
const fileInputRefs = ref<Record<string, HTMLInputElement>>({})

// Atlas 图集选择对话框状态
const atlasDialog = reactive<{
  visible: boolean
  targetKey: string | null
  atlases: Array<{ id: number; name: string }>
  selectedAtlasId: number | null
  images: Array<{ id: number; filename: string; url: string }>
  loading: boolean
  errorMessage: string
}>({
  visible: false,
  targetKey: null,
  atlases: [],
  selectedAtlasId: null,
  images: [],
  loading: false,
  errorMessage: '',
})

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

// 设置文件输入引用（file-picker widget 使用）
function setFileInputRef(key: string, el: any) {
  if (!el) {
    delete fileInputRefs.value[key]
    return
  }
  if (el.tagName === 'INPUT' && el.type === 'file') {
    fileInputRefs.value[key] = el as HTMLInputElement
  }
}

// 打开文件选择器
function openFilePicker(key: string) {
  const input = fileInputRefs.value[key]
  if (input) {
    input.value = ''  // 重置以便重复选择同一文件
    input.click()
  }
}

// 处理文件选择
function handleFileSelected(key: string, event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    updateConfig(key, file.name)
  }
}

// 打开 Atlas 图集选择对话框
async function openAtlasPicker(key: string) {
  atlasDialog.targetKey = key
  atlasDialog.visible = true
  atlasDialog.errorMessage = ''
  atlasDialog.images = []
  atlasDialog.selectedAtlasId = null
  await loadAtlasList()
}

// 加载图集列表
async function loadAtlasList() {
  atlasDialog.loading = true
  try {
    const res = await atlasApi.list()
    const list = (res.data as Array<{ id: number; name: string }>) || []
    atlasDialog.atlases = list.map((a: { id: number; name: string }) => ({ id: a.id, name: a.name }))
    // 默认选中第一个
    if (atlasDialog.atlases.length > 0 && atlasDialog.selectedAtlasId === null) {
      await selectAtlas(atlasDialog.atlases[0].id)
    }
  } catch (err: any) {
    atlasDialog.errorMessage = `加载图集失败: ${err?.message || String(err)}`
  } finally {
    atlasDialog.loading = false
  }
}

// 选中某个图集 → 加载图片列表
async function selectAtlas(atlasId: number) {
  atlasDialog.selectedAtlasId = atlasId
  atlasDialog.loading = true
  atlasDialog.errorMessage = ''
  try {
    const res = await atlasApi.getImages(atlasId, undefined, 1, 200)
    const items = (res.data as any)?.items || res.data || []
    atlasDialog.images = items.map((img: any) => ({
      id: img.id,
      filename: img.filename || img.name || `image_${img.id}`,
      url: img.url || `/api/image/${img.id}/file`,
    }))
  } catch (err: any) {
    atlasDialog.errorMessage = `加载图片失败: ${err?.message || String(err)}`
    atlasDialog.images = []
  } finally {
    atlasDialog.loading = false
  }
}

// 选中某张图片 → 写入配置
function selectAtlasImage(img: { id: number; filename: string; url: string }) {
  if (atlasDialog.targetKey === null) return
  // 优先写文件名（与 file-picker 一致），保留 url 作为前缀路径
  updateConfig(atlasDialog.targetKey, img.filename)
  atlasDialog.visible = false
}

// 关闭对话框
function closeAtlasDialog() {
  atlasDialog.visible = false
  atlasDialog.targetKey = null
  atlasDialog.images = []
  atlasDialog.errorMessage = ''
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

// 更新配置 - 直连 Pinia Store（绕过事件转发）
function updateConfig(key: string, value: string | number | boolean | null) {
  store.updateNodeConfig(props.data.id, key, value)
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
  width: 280px;
  font-size: 12px;
  color: #e0e0e0;
  position: relative;
  transition: all 0.2s ease;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 2px 8px rgba(0,0,0,0.3);
  /* 连接点需要溢出显示，但不能影响布局 */
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

/* Phase 14 节点状态可视高亮：边框颜色按执行状态区分，
   一眼看出哪个节点 running / success / failed / timeout */
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

/* 标题栏 - 使用背景色区分类型 */
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
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
  display: none; /* 隐藏英文节点类型，只保留中文 label */
}

/* 配置区域 - contain 隔离重绘避免影响整图 */
.node-body {
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(0,0,0,0.15);
  border-bottom: 1px solid rgba(255,255,255,0.03);
  contain: layout style paint;
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

/* ============================================
 * 输入控件样式
 * 原则：所有视觉样式（背景/边框/颜色/padding）由全局 _element-plus.scss 统一控制
 * 本处只负责：1) 布局（flex / min-width） 2) :deep() 缩小字号到 12px（适配 280px 节点）
 * 3) 强制统一高度 32px + box-sizing，避免 model-select/dropdown/multiselect/number
 * 各自 Element Plus 默认 padding 不一致导致"一个大一个小"
 * ============================================ */
.text-input,
.number-input,
.select-input,
.textarea-input,
.code-input {
  flex: 1;
  min-width: 0;
  width: 100%;
}

.select-input {
  cursor: pointer;
}

/* 统一输入控件高度与盒模型 —— 消除"一个大一个小" */
:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  box-sizing: border-box !important;
  min-height: 32px !important;
  max-height: 32px !important;
  padding: 0 8px !important;
  display: flex !important;
  align-items: center !important;
}

:deep(.el-input__wrapper .el-input__inner) {
  height: 30px !important;
  line-height: 30px !important;
  font-size: 12px !important;
}

:deep(.el-textarea__inner) {
  font-size: 12px !important;
  padding: 6px 8px !important;
  box-sizing: border-box !important;
}

/* textarea / code 区别：等宽字体 + 最小高度 */
:deep(.el-textarea__inner) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  min-height: 40px;
  resize: vertical;
}

/* code 风格：更深背景作为视觉区分（差异化基于内层 textarea） */
.code-input :deep(.el-textarea__inner) {
  background: #0a0a12;
  min-height: 36px;
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
  padding: 3px 4px;
  border-radius: 3px;
  color: #777;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.var-bind-btn svg {
  width: 14px;
  height: 14px;
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
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #666;
  box-shadow: 0 0 6px currentColor;
}

.status-indicator.running {
  background: #5898ff;
  color: #5898ff;
  animation: pulse 1s infinite;
}

.status-indicator.success {
  background: #4CFF4C;
  color: #4CFF4C;
}

.status-indicator.failed {
  background: #FF4C4C;
  color: #FF4C4C;
}

.status-indicator.timeout {
  background: #FFA500;
  color: #FFA500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 删除按钮已移除：删除操作通过右键菜单 + Delete/Backspace 快捷键 */

/* File Picker 控件 */
.file-picker-wrapper {
  display: flex;
  flex: 1;
  gap: 4px;
}

.file-picker-input {
  flex: 1;
  min-width: 0;
}

.file-picker-btn {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  background: #3a3a4a;
  border: 1px solid #5a5a6a;
  border-radius: 4px;
  color: #aaa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-picker-btn:hover {
  background: #4a4a5a;
  color: #5898ff;
}

.file-input-hidden {
  display: none;
}

/* Atlas 图集按钮（与 file-picker 按钮紧邻，提示从图集选择） */
.file-picker-btn-atlas {
  color: var(--accent-cyan, #00f0ff);
}

/* Atlas 对话框 */
.atlas-error {
  color: #ff4c4c;
  margin-bottom: 12px;
  font-size: 13px;
}

.atlas-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.atlas-label {
  font-size: 13px;
  color: var(--text-secondary, #8888aa);
  white-space: nowrap;
}

.atlas-empty {
  color: var(--text-muted, #555566);
  text-align: center;
  padding: 24px 0;
  font-size: 13px;
}

.atlas-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  max-height: 360px;
  overflow-y: auto;
}

.atlas-image-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px;
  border: 1px solid var(--border-color, #2a2a3a);
  border-radius: 6px;
  cursor: pointer;
  background: var(--bg-primary, #0a0a0f);
  transition: border-color 0.2s, background 0.2s;
}

.atlas-image-item:hover {
  border-color: var(--accent-cyan, #00f0ff);
  background: rgba(0, 240, 255, 0.08);
}

.atlas-image-item img {
  width: 100%;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  background: #1a1a24;
}

.atlas-image-name {
  font-size: 11px;
  color: var(--text-secondary, #8888aa);
  margin-top: 4px;
  text-align: center;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

</style>
