<template>
  <!-- 懒挂载预览态 (PERF 2026-09-11): lazy 模式且未激活时渲染纯文本, 不挂载任何 Element Plus 控件 -->
  <div
    v-if="!isActive"
    class="node-config-editor nce-preview-mode"
    :class="{ 'nce-inline': mode === 'inline' }"
    @pointerdown.capture="activate"
  >
    <div class="nce-body">
      <div
        v-for="(schema, key) in configProperties"
        :key="key"
        class="nce-field nce-field-preview"
      >
        <label class="nce-field-label">{{ schema.title || key }}</label>
        <span class="nce-field-value">{{ previewValue(key) }}</span>
      </div>
      <div
        v-if="!hasConfig"
        class="nce-empty"
      >
        <p>该节点无需配置</p>
      </div>
    </div>
  </div>

  <!-- 完整编辑态 -->
  <div
    v-else
    class="node-config-editor"
    :class="{ 'nce-inline': mode === 'inline' }"
  >
    <!-- 节点头部: 标题 + 分类 (inline 模式隐藏，节点壳已有) -->
    <header
      v-if="mode !== 'inline'"
      class="nce-header"
    >
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
            v-if="activeVarMenu === key"
            class="nce-var-dropdown"
          >
            <!-- 有变量时正常列出选项 -->
            <template v-if="variables.length > 0">
              <div
                v-for="v in variables"
                :key="v.name"
                class="nce-var-option"
                @click="bindVariable(key, v.name)"
              >
                {{ formatVarRef(v.name) }}
              </div>
            </template>
            <!-- 2026-06-21: 空状态提示 — 之前 v-if="variables.length > 0" 导致无变量时静默不渲染,
                 用户点击 tag 按钮没反应以为坏了. 现在给明确指引.
                 注: 变量管理 UI 内联在 RuleCanvas.vue 左侧调色板底部 (📌 变量 区),
                 VariablePanel.vue 是孤儿组件, 不要引用. -->
            <div
              v-else
              class="nce-var-empty"
            >
              <div class="nce-var-empty-title">
                暂无变量
              </div>
              <div class="nce-var-empty-desc">
                请先在左侧调色板底部「📌 变量」区域点击「+ 添加变量」后再来绑定
              </div>
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

const props = withDefaults(defineProps<{
  nodeId: string
  /**
   * 渲染模式:
   * - 'panel' (默认): 右侧属性面板风格 (有头部标题栏)
   * - 'inline': 节点内嵌模式 (隐藏头部, 紧凑 padding, 适合 LOD 2 节点壳)
   */
  mode?: 'panel' | 'inline'
  /**
   * 懒挂载 (PERF 2026-09-11)。
   *
   * 为 true 时: 未交互前只渲染纯文本预览 (label + 值), **不挂载任何 Element Plus 控件**;
   * 首次 pointerdown 后才实例化完整控件。
   *
   * 背景: 每个 el-select 会连带产生 1 个 el-tooltip 触发器 + 1 个 el-popper 下拉
   * + 1 个 el-scrollbar。80 节点图实测 49 个可见节点 → 49 el-select / 98 el-popper
   * / 49 el-scrollbar, 挂载与布局重算造成单个 3323ms 长任务 (加载) 与 4×320ms
   * 长任务 (缩放)。改为懒挂载后加载长任务总计 3822ms → 711ms。
   *
   * 注意: 仅节点内嵌 (mode='inline') 场景开启; 右侧属性面板不开启。
   */
  lazy?: boolean
}>(), {
  mode: 'panel',
  lazy: false
})

// ============ 懒挂载状态 ============

/** 是否已激活 (lazy 模式下首次交互后置 true)。 */
const activated = ref(false)

/** 当前是否渲染完整控件 (非 lazy 模式恒为 true)。 */
const isActive = computed(() => !props.lazy || activated.value)

/** 首次交互时激活完整控件。 */
function activate() {
  if (props.lazy && !activated.value) {
    activated.value = true
  }
}

const store = useRuleEngineStore()

// ============ 从 store 读取该节点数据 ============

// FIX (BUG-4 2026-06-19): 节点配置变更响应式信号
// Task 14 (2026-10-24): 改为**按节点粒度** —— 读本节点的版本号,
//   改 A 节点不会让 B/C/D... 的 Editor computed 全部失效。
//   旧实现读全局计数器 store.configVersion, 80 节点图上每敲一个键 = 80 次重算。
const nodeData = computed((): RuleNodeData | null => {
  // 显式读取本节点的配置版本号建立响应式依赖
  void store.configVersionOf(props.nodeId)
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

/**
 * 预览态的值文本 (懒挂载占位用)。
 *
 * 只做纯字符串格式化 — 不引入任何 Element Plus 控件, 故预览态组件开销为零。
 * 未设置的值显示 '—', 让"默认全展开"的观感保持完整。
 */
function previewValue(key: string): string {
  const v = getNodeValue(key)
  if (v === null || v === undefined || v === '') return '—'
  if (Array.isArray(v)) return v.length > 0 ? v.join(', ') : '—'
  if (typeof v === 'boolean') return v ? '是' : '否'
  return String(v)
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

/* ========== inline 模式 (节点内嵌 LOD 2) 紧凑样式 ==========
   隐藏 panel 头部, padding 减半, 字号略小, 跟节点壳融为一体 */
.node-config-editor.nce-inline {
  background: transparent;
  padding: 0;
  font-size: 11px;

  .nce-body {
    padding: 0;
    gap: 6px;
  }

  .nce-field {
    gap: 2px;
  }

  .nce-field-label {
    font-size: 10px;
    font-weight: 500;
    color: var(--text-muted);
    margin-bottom: 1px;
  }

  .nce-field-control {
    gap: 4px;
  }

  // 紧凑 element-plus 控件 (覆盖 :deep 样式)
  :deep(.el-input__wrapper) {
    padding: 1px 6px;
    min-height: 22px;
    background: rgba(255, 255, 255, 0.04);
    box-shadow: none;
  }
  :deep(.el-input__inner) {
    font-size: 11px;
    line-height: 18px;
  }
  :deep(.el-textarea__inner) {
    font-size: 11px;
    padding: 4px 6px;
    background: rgba(255, 255, 255, 0.04);
  }
  :deep(.el-select__wrapper) {
    padding: 1px 6px;
    min-height: 22px;
    background: rgba(255, 255, 255, 0.04);
    box-shadow: none;
  }
  :deep(.el-input-number .el-input__wrapper) {
    padding: 1px 6px;
  }
  :deep(.el-slider) {
    margin: 4px 0;
  }
  :deep(.el-slider__runway) {
    height: 3px;
  }
  :deep(.el-slider__bar) {
    height: 3px;
  }
  :deep(.el-slider__button) {
    width: 10px;
    height: 10px;
  }
  :deep(.el-switch) {
    --el-switch-on-color: var(--accent-blue);
    --el-switch-off-color: rgba(255, 255, 255, 0.1);
  }
  :deep(.el-checkbox__label) {
    font-size: 11px;
  }
  .nci-aux-btn,
  .nce-aux-btn {
    width: 18px;
    height: 18px;
  }
  .slider-value {
    font-size: 10px;
    min-width: 28px;
  }
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

/* 懒挂载预览态 (PERF 2026-09-11)
   纯文本占位, 目的是"看起来配置区还在", 但不挂载任何 Element Plus 控件。
   首次 pointerdown / 点击后切换为完整编辑态。cursor 提示此处可交互。 */
.nce-preview-mode {
  cursor: pointer;
}

.nce-field-preview {
  gap: 2px;
}

.nce-field-value {
  font-size: 12px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

/* 2026-06-21: 空状态 — 提示用户去 VariablePanel 添加变量 */
.nce-var-empty {
  padding: 12px;
  min-width: 200px;
}

.nce-var-empty-title {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-bottom: 4px;
}

.nce-var-empty-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
}

.nce-empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 12px;
}
</style>
