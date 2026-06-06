<template>
  <div
    v-bind="$attrs"
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
                v-for="opt in dynamicEnumFor(key, schema)"
                :key="String(opt)"
                :value="opt as string | number"
                :label="String(opt)"
              />
            </el-select>
            <el-tooltip
              v-if="key === 'class_names' && hasModelIdField()"
              content="从所选模型加载训练类别（覆盖当前输入）"
              placement="top"
            >
              <button
                class="var-bind-btn"
                title="从所选模型加载类别"
                :disabled="loadingCategories.has(key)"
                @click.stop="loadModelCategories(key)"
              >
                <SvgIcon :name="loadingCategories.has(key) ? 'loading' : 'refresh'" />
              </button>
            </el-tooltip>
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

    <!-- 删除按钮已移除：保留右键菜单删除 + Delete/Backspace 快捷键删除 -->
  </div>
</template>

<script setup lang="ts">
import { Position } from '@vue-flow/core'
import { useRuleEngineStore } from '@/stores/ruleEngine'
import type { Variable } from '@/stores/ruleEngine'
import { modelApi } from '@/api'

/**
 * 关闭自动属性透传：模板根是 fragment（节点 div + el-dialog），
 * Vue Flow 注入的 props (id/type/position/dimensions/dragging 等)
 * 会触发"fragment 根无法继承"警告。关闭后手动用 v-bind="$attrs" 绑到节点 div。
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
   * Vue Flow 透传的节点内部更新事件(节点大小/端口变化时通知父组件刷新 Handles)
   * 声明在 emits 中,避免 fragment 根触发"non-emits event listener"警告
   */
  (e: 'updateNodeInternals'): void
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

// Phase 14 增强：class_names multiselect 可从所选 model_id 动态拉取类别
const loadingCategories = ref<Set<string>>(new Set())

/** 拿到所选 model_id 字段的值（如果存在且非空） */
function getModelIdValue(): number | null {
  const modelId = props.data.config?.model_id
  if (modelId === undefined || modelId === null || modelId === '') return null
  const n = Number(modelId)
  return Number.isFinite(n) && n > 0 ? n : null
}

/** 检查当前节点的 configSchema 是否包含 model_id 字段（决定是否显示加载按钮） */
function hasModelIdField(): boolean {
  return !!props.data.configSchema?.model_id
}

/** 动态 enum 源：class_names 字段如果有缓存的模型类别，优先使用 */
function dynamicEnumFor(key: string, schema: ConfigSchemaProperty): unknown[] {
  if (key === 'class_names' && dynamicCategoryEnum.value.length > 0) {
    return dynamicCategoryEnum.value
  }
  return schema.enum ?? []
}

const dynamicCategoryEnum = ref<string[]>([])

/** 从所选模型加载训练类别名列表，覆盖到 enum（同时写入 multiselect 的实际值） */
async function loadModelCategories(fieldKey: string) {
  const modelId = getModelIdValue()
  if (!modelId) {
    ElMessage.warning('请先在模型字段选择模型')
    return
  }
  loadingCategories.value.add(fieldKey)
  try {
    const res = await modelApi.getCategories(modelId)
    const cats = (res.data || []) as string[]
    if (cats.length === 0) {
      ElMessage.info('该模型未提供训练类别，请手动输入')
      return
    }
    dynamicCategoryEnum.value = cats
    // 覆盖当前字段值为模型类别（仅在字段为空时自动填）
    const current = getNodeValue(fieldKey) as unknown
    const isEmpty = !Array.isArray(current) || (current as unknown[]).length === 0
    if (isEmpty) {
      // updateConfig 单值签名不支持 array，绕过它直接调 store
      store.updateNodeConfig(props.data.id, fieldKey, cats as unknown as NodeConfigValue)
    }
    ElMessage.success(`已加载 ${cats.length} 个训练类别${isEmpty ? '并填入' : '（已有输入，未覆盖）'}`)
  } catch (err) {
    console.error('加载模型类别失败:', err)
    ElMessage.error('加载模型类别失败')
  } finally {
    loadingCategories.value.delete(fieldKey)
  }
}

// 当 model_id 改变时清除缓存的 enum 并清空已选 class_names
// 避免不同模型的类别混淆（下游 YOLO 节点按 class_name 匹配，
// 保留旧模型的 class_names 会导致静默 0 检测）
watch(
  () => props.data.config?.model_id,
  (_newVal, oldVal) => {
    // 首次设置（oldVal 为空）不做清空操作
    if (oldVal === undefined || oldVal === null || oldVal === '' || oldVal === 0) {
      dynamicCategoryEnum.value = []
      return
    }
    // 切换模型：清空 dynamicCategoryEnum + 已选 class_names
    dynamicCategoryEnum.value = []
    const classNamesKey = 'class_names'
    if (hasModelIdField() && configProperties.value[classNamesKey]) {
      const current = getNodeValue(classNamesKey) as unknown
      if (Array.isArray(current) && (current as unknown[]).length > 0) {
        store.updateNodeConfig(
          props.data.id,
          classNamesKey,
          [] as unknown as NodeConfigValue
        )
        ElMessage.warning('模型已切换，原目标类别已清空，请重新加载或手动输入')
      }
    }
  }
)

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

// 已连接 handle id 集合（vue-flow 1.48 不会自动给 handle 加 connected class，
// 我们自己从 store.edges 算 — 用于 CSS 区分未连/已连 handle）
const connectedHandleIds = computed<Set<string>>(() => {
  const ids = new Set<string>()
  for (const e of store.edges) {
    if (e.source === props.data.id && e.sourceHandle) ids.add(e.sourceHandle)
    if (e.target === props.data.id && e.targetHandle) ids.add(e.targetHandle)
  }
  return ids
})

// 判断 handle 是否已连接 (模板辅助)
function isHandleConnected(handleId: string): boolean {
  return connectedHandleIds.value.has(handleId)
}

// 变量绑定菜单状态
const activeVarMenu = ref<string | null>(null)

// 输入框引用字典（用于获取光标位置）
const inputRefs = ref<Record<string, HTMLInputElement | HTMLTextAreaElement>>({})

// 文件输入引用字典（file-picker widget 使用）
const fileInputRefs = ref<Record<string, HTMLInputElement>>({})

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

/* 节点选中边框：按 category 色 (决策 4) — 2px 实色 */
.rule-node.selected {
  border-width: 2px;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 16px rgba(0,0,0,0.4);
}
.rule-node.selected.category-input     { border-color: #4CFF4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(76,255,76,0.3),   0 4px 16px rgba(0,0,0,0.4); }
.rule-node.selected.category-detection { border-color: #00f0FF; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,240,255,0.3),   0 4px 16px rgba(0,0,0,0.4); }
.rule-node.selected.category-processing{ border-color: #FFFF4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,255,76,0.3),  0 4px 16px rgba(0,0,0,0.4); }
.rule-node.selected.category-action   { border-color: #FF7F4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,127,76,0.3),  0 4px 16px rgba(0,0,0,0.4); }
.rule-node.selected.category-logic     { border-color: #DC4FDC; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(220,79,220,0.3),  0 4px 16px rgba(0,0,0,0.4); }
.rule-node.selected.category-output    { border-color: #FF4C4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,76,76,0.3),   0 4px 16px rgba(0,0,0,0.4); }

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

/* VueFlow Handle 样式
   始终按 port type 颜色填充 (Blender 风格 — 一眼看出可连接的兼容性:
   同色 = 兼容可连, 不同色 = 类型不匹配) */
.node-handle {
  width: 16px !important;
  height: 16px !important;
  border: 2px solid rgba(0, 0, 0, 0.4) !important;
  border-radius: 50% !important;
  cursor: crosshair !important;
  transition: all 0.15s ease !important;
  flex-shrink: 0;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4);
}

/* 强制 Handle 定位到节点边框，垂直居中对齐 port-item */
:deep(.vue-flow__handle-left) {
  left: -8px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
}

:deep(.vue-flow__handle-right) {
  right: -8px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
}

/* 确保 handle 容器不裁剪 */
:deep(.vue-flow__handle) {
  position: absolute !important;
}

.node-handle:hover {
  width: 18px !important;
  height: 18px !important;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 12px rgba(0, 240, 255, 0.6) !important;
}

/* 14 种 port type 颜色 (Blender 风格 — 同色 = 兼容可连)
   背景 = type 色 (始终显示, 便于识别兼容性)
   边框 = 暗一档 type 色 (与节点背景区分的层次) */
/* 视觉型 (图像/几何) */
.node-handle.type-image    { background: #4CFF4C; border-color: #2eb92e; }
.node-handle.type-bbox     { background: #00f0FF; border-color: #00b8d4; }
.node-handle.type-mask     { background: #00f0FF; border-color: #00b8d4; }
/* 评分/分数 */
.node-handle.type-scores   { background: #FF7F4C; border-color: #d9642e; }
/* 控制流 */
.node-handle.type-trigger  { background: #DC4FDC; border-color: #b02db0; }
.node-handle.type-control  { background: #DC4FDC; border-color: #b02db0; }
/* 数值 */
.node-handle.type-int      { background: #3B82F6; border-color: #2563c4; }
.node-handle.type-float    { background: #14B8A6; border-color: #0e8a7c; }
/* 逻辑 */
.node-handle.type-boolean  { background: #FF4C4C; border-color: #d62828; }
/* 文本/集合 */
.node-handle.type-string   { background: #8B5CF6; border-color: #6d3dd4; }
.node-handle.type-array    { background: #FFFF4C; border-color: #c4c41e; }
.node-handle.type-object   { background: #FFFF4C; border-color: #c4c41e; }
/* 元数据 */
.node-handle.type-model    { background: #888888; border-color: #5e5e5e; }
.node-handle.type-any      { background: #E0E0E0; border-color: #a8a8a8; }

/* 已连仅加同色发光 (fill 仍按 type 色 — 不区分已连/未连填色状态) */
.node-handle.is-connected.type-image    { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(76,255,76,0.7); }
.node-handle.is-connected.type-bbox     { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(0,240,255,0.7); }
.node-handle.is-connected.type-mask     { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(0,240,255,0.7); }
.node-handle.is-connected.type-scores   { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(255,127,76,0.7); }
.node-handle.is-connected.type-trigger  { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(220,79,220,0.7); }
.node-handle.is-connected.type-control  { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(220,79,220,0.7); }
.node-handle.is-connected.type-int      { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(59,130,246,0.7); }
.node-handle.is-connected.type-float    { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(20,184,166,0.7); }
.node-handle.is-connected.type-boolean  { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(255,76,76,0.7); }
.node-handle.is-connected.type-string   { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(139,92,246,0.7); }
.node-handle.is-connected.type-array    { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(255,255,76,0.7); }
.node-handle.is-connected.type-object   { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(255,255,76,0.7); }
.node-handle.is-connected.type-model    { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(136,136,136,0.7); }
.node-handle.is-connected.type-any      { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 0 8px rgba(224,224,224,0.7); }

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

</style>
