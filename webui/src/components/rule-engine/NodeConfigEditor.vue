<template>
  <div class="node-config-editor">
    <!-- 节点头部: 标题 + 分类 -->
    <header class="nce-header">
      <div
        class="nce-icon"
        :class="nodeData?.category"
      >
        <SvgIcon :name="nodeData?.category" />
      </div>
      <div class="nce-titles">
        <h3 class="nce-label">
          {{ nodeData?.label || nodeData?.type || '' }}
        </h3>
        <span class="nce-type">{{ nodeData?.type }}</span>
      </div>
    </header>

    <!-- 配置控件区域 -->
    <div class="nce-body">
      <div
        v-for="(schema, key) in configProperties"
        :key="key"
        v-memo="[getNodeValue(key)]"
        class="nce-field"
      >
        <label class="nce-field-label">
          {{ schema.title || key }}
          <span
            v-if="schema.description"
            class="nce-field-hint"
            :title="schema.description"
          >?</span>
        </label>
        <div class="nce-field-control">
          <!-- Slider -->
          <template v-if="schema.widget === 'slider'">
            <div
              class="slider-wrapper"
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
              class="nce-input nce-number-input"
              @update:model-value="(v: number | undefined) => updateConfig(key, v ?? null)"
            />
          </template>

          <!-- Dropdown -->
          <template v-else-if="schema.widget === 'dropdown'">
            <el-select
              :model-value="getNodeValue(key)"
              class="nce-input nce-select-input"
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
              class="nce-input nce-select-input"
              :placeholder="schema.allow_create ? '可输入或选择...' : '请选择...'"
              @update:model-value="updateConfig(key, $event)"
            >
              <el-option
                v-for="opt in dynamicEnumFor(key, schema)"
                :key="String(opt)"
                :value="String(opt)"
                :label="String(opt)"
              />
            </el-select>
            <el-tooltip
              v-if="key === 'class_names' && hasModelIdField()"
              content="从所选模型加载类别（覆盖当前输入）"
              placement="top"
            >
              <button
                class="nce-aux-btn"
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
              class="nce-input nce-select-input"
              :placeholder="availableModels.length === 0 ? '暂无可用模型（请先训练模型）' : '选择模型...'"
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
                class="nce-input file-picker-input"
                @update:model-value="updateConfig(key, $event)"
              />
              <button
                class="nce-aux-btn"
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
              class="nce-input nce-textarea-input"
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
              class="nce-input nce-code-input"
              @update:model-value="updateConfig(key, $event)"
            />
          </template>

          <!-- Toggle -->
          <template v-else-if="schema.widget === 'toggle'">
            <el-switch
              :model-value="!!getNodeValue(key)"
              active-text="开启"
              inactive-text="关闭"
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
              class="nce-input nce-text-input"
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
              class="nce-aux-btn"
              title="绑定变量 — 引用上游节点的输出"
              @click.stop="toggleVarMenu(key)"
            >
              <SvgIcon name="tag" />
            </button>
          </el-tooltip>

          <!-- 变量下拉菜单 -->
          <div
            v-if="activeVarMenu === key && variables.length > 0"
            class="nce-var-dropdown"
          >
            <div
              v-for="v in variables"
              :key="v.name"
              class="nce-var-option"
              @click="bindVariable(key, v.name)"
            >
              {{ formatVarRef(v.name) }}
            </div>
          </div>
        </div>
      </div>

      <!-- 无配置项时提示 -->
      <div
        v-if="!hasConfig"
        class="nce-empty"
      >
        <p>该节点无需配置</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * NodeConfigEditor - 节点配置面板
 *
 * Phase A 改造: 从 RuleNode.vue 拆出，配置全权编辑放到右侧属性面板。
 * - 接收 nodeId + data props
 * - 渲染当前选中节点的 configSchema 全部配置控件
 * - 调用 store.updateNodeConfig() 写回
 * - 完整保留: 10 种 widget + 变量绑定 + 模型选择 + 文件选择
 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRuleEngineStore } from '@/stores/ruleEngine'
import type { RuleNodeData, ConfigSchemaProperty } from '@/types/api'
import type { Variable } from '@/stores/ruleEngine'
import { modelApi } from '@/api'

// ============ 类型定义 ============

type NodeConfigValue = string | number | boolean | (string | number)[] | null

// ============ Props ============

const props = defineProps<{
  nodeId: string
}>()

const store = useRuleEngineStore()

// ============ 从 store 读取该节点数据 ============

const nodeData = computed((): RuleNodeData | null => {
  const node = store.nodeById.get(props.nodeId)
  return (node?.data as RuleNodeData) ?? null
})

// ============ 计算属性 ============

/** 节点配置 schema */
const configProperties = computed((): Record<string, ConfigSchemaProperty> => {
  return nodeData.value?.configSchema ?? (Object.create(null) as Record<string, ConfigSchemaProperty>)
})

/** 是否有配置项 */
const hasConfig = computed(() => {
  return Object.keys(configProperties.value).length > 0
})

/** 节点配置值（合并默认值） */
const nodeConfig = computed((): Record<string, NodeConfigValue> => {
  const nd = nodeData.value
  if (!nd) return {}
  const defaults: Record<string, NodeConfigValue> = {}
  const schema = nd.configSchema ?? {}
  for (const [key, prop] of Object.entries(schema)) {
    if ((prop as ConfigSchemaProperty).default !== undefined) {
      defaults[key] = (prop as ConfigSchemaProperty).default as NodeConfigValue
    }
  }
  return { ...defaults, ...(nd.config as Record<string, NodeConfigValue>) }
})

/** 拿到节点配置值（辅助方法） */
function getNodeValue(key: string): NodeConfigValue {
  return (nodeConfig.value as Record<string, NodeConfigValue>)[key] ?? null
}

/** 可用模型（model-select 用） */
const availableModels = computed(() => store.availableModels)

/** 可用变量（从 Pinia store 读取） */
const variables = computed<Variable[]>(() => store.variables)

// ============ 模型类别管理 (Phase 14.2 + 16.3 增强) ============

const loadingCategories = ref<Set<string>>(new Set())
const dynamicCategoryEnum = ref<string[]>([])

/** 检查当前节点 configSchema 是否包含 model_id 字段 */
function hasModelIdField(): boolean {
  return !!nodeData.value?.configSchema?.model_id
}

/** 拿到所选 model_id 字段的值 */
function getModelIdValue(): number | null {
  const modelId = nodeData.value?.config?.model_id
  if (modelId === undefined || modelId === null || modelId === '') return null
  const n = Number(modelId)
  return Number.isFinite(n) && n > 0 ? n : null
}

/** 动态 enum 源：class_names 字段如果有缓存的模型类别，优先使用 */
function dynamicEnumFor(key: string, schema: ConfigSchemaProperty): unknown[] {
  if (key === 'class_names' && dynamicCategoryEnum.value.length > 0) {
    return dynamicCategoryEnum.value
  }
  return schema.enum ?? []
}

/** 从所选模型加载训练类别 */
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
    const current = getNodeValue(fieldKey) as unknown
    const isEmpty = !Array.isArray(current) || (current as unknown[]).length === 0
    if (isEmpty) {
      // updateNodeConfig 单值签名不支持 array，绕过它直接调 store
      store.updateNodeConfig(props.nodeId, fieldKey, cats as unknown as NodeConfigValue)
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
watch(
  () => nodeData.value?.config?.model_id,
  (_newVal, oldVal) => {
    if (oldVal === undefined || oldVal === null || oldVal === '' || oldVal === 0) {
      dynamicCategoryEnum.value = []
      return
    }
    dynamicCategoryEnum.value = []
    const classNamesKey = 'class_names'
    if (hasModelIdField() && configProperties.value[classNamesKey]) {
      const current = getNodeValue(classNamesKey) as unknown
      if (Array.isArray(current) && (current as unknown[]).length > 0) {
        store.updateNodeConfig(
          props.nodeId,
          classNamesKey,
          [] as unknown as NodeConfigValue
        )
        ElMessage.warning('模型已切换，原目标类别已清空，请重新加载或手动输入')
      }
    }
  }
)

// ============ 文件选择器 ============

const fileInputRefs = ref<Record<string, HTMLInputElement>>({})

function setFileInputRef(key: string, el: any) {  // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!el) {
    delete fileInputRefs.value[key]
    return
  }
  if (el.tagName === 'INPUT' && el.type === 'file') {
    fileInputRefs.value[key] = el as HTMLInputElement
  }
}

function openFilePicker(key: string) {
  const input = fileInputRefs.value[key]
  if (input) {
    input.value = ''
    input.click()
  }
}

function handleFileSelected(key: string, event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    updateConfig(key, file.name)
  }
}

// ============ 变量绑定 ============

const activeVarMenu = ref<string | null>(null)
const inputRefs = ref<Record<string, HTMLInputElement | HTMLTextAreaElement>>({})

function setInputRef(key: string, el: any) {  // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!el) {
    delete inputRefs.value[key]
    return
  }
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
  const currentValue = String(nodeConfig.value[key] || '')
  const varRef = `{{${varName}}}`

  if (currentValue.includes(varRef)) {
    activeVarMenu.value = null
    return
  }

  const inputEl = inputRefs.value[key]
  let newValue: string

  if (inputEl && (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT')) {
    const start = inputEl.selectionStart ?? currentValue.length
    const end = inputEl.selectionEnd ?? currentValue.length
    newValue = currentValue.slice(0, start) + varRef + currentValue.slice(end)
    updateConfig(key, newValue)
    setTimeout(() => {
      if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
        const newPos = start + varRef.length
        inputEl.setSelectionRange(newPos, newPos)
        inputEl.focus()
      }
    }, 0)
  } else {
    newValue = currentValue ? currentValue + varRef : varRef
    updateConfig(key, newValue)
  }

  activeVarMenu.value = null
}

function formatVarRef(name: string) {
  return `{{${name}}}`
}

// ============ 更新配置 ============

function updateConfig(key: string, value: string | number | boolean | null) {
  store.updateNodeConfig(props.nodeId, key, value)
}
</script>

<style scoped lang="scss">
.node-config-editor {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  color: var(--text-primary);
}

.nce-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.nce-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--accent-blue-muted);
  color: var(--accent-blue);
}

.nce-titles {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nce-label {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nce-type {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nce-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.nce-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nce-field-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.nce-field-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--bg-hover);
  color: var(--text-muted);
  font-size: 10px;
  cursor: help;
}

.nce-field-control {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.nce-input {
  flex: 1;
  min-width: 0;
}

.nce-text-input,
.nce-number-input,
.nce-select-input,
.nce-textarea-input,
.nce-code-input,
.file-picker-input {
  width: 100%;
}

// 统一 Element Plus 输入控件高度
:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  box-sizing: border-box !important;
  min-height: 32px !important;
  max-height: 32px !important;
  padding: 0 8px !important;
  display: flex;
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

.slider-wrapper {
  flex: 1;
  min-width: 0;
}

.slider-value {
  min-width: 36px;
  text-align: right;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);
}

.nce-aux-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.nce-aux-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--accent-blue);
  border-color: var(--accent-blue);
}

.nce-aux-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.nce-aux-btn svg {
  width: 14px;
  height: 14px;
}

.file-picker-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.file-input-hidden {
  display: none;
}

.nce-var-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  min-width: 180px;
  max-height: 200px;
  overflow-y: auto;
  background: var(--bg-overlay, #1a1a24);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.nce-var-option {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.1s;
  font-family: 'JetBrains Mono', monospace;
}

.nce-var-option:hover {
  background: var(--bg-hover);
  color: var(--accent-blue);
}

.nce-empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
