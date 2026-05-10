# Phase 4 技术实现文档：节点配置面板（前端）

> ⚠️ **实现前审核状态：** 待老大评审
> 文档版本：v1.0
> 基于调研：canvas-editor-research-2026-05-06.md
> 阶段：Phase 4
> 创建时间：2026-05-06

---

## 1. 阶段目标

**目标：** 选中节点后，右侧面板显示该节点的参数编辑表单，支持变量绑定。

**验收标准：**
- [ ] 选中节点后，右侧面板正确显示节点类型、ID、名称
- [ ] 输入参数表单根据节点类型动态生成
- [ ] 支持 STRING/INT/FLOAT/BOOL/ENUM 类型参数编辑
- [ ] 参数修改后节点数据实时更新
- [ ] 变量下拉菜单能插入 `{{variable_name}}` 到输入框
- [ ] "断连"按钮能断开指定输入连接

---

## 2. 面板布局

### 2.1 整体结构

```
┌────────────────────────────────────────────────────────┐
│  选中节点: YOLOModel                        [关闭 X]  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  节点类型        YOLO 检测模型                         │
│  节点 ID         node_002                             │
│  节点名称        [________________]                   │
│                                                        │
├────────────────────────────────────────────────────────┤
│  ▼ 输入配置                                           │
│  ├─ 图片输入    [已连接: node_001 → image      ] [断] │
│  ├─ 置信度阈值  [0.5_____________________] 📎         │
│  └─ 模型选择    [选择模型___________▼] 📎             │
│                                                        │
├────────────────────────────────────────────────────────┤
│  ▼ 输出配置                                           │
│  ├─ 检测框(BBOX)   → node_003                        │
│  └─ 置信度(SCORES) → [未连接]                        │
│                                                        │
├────────────────────────────────────────────────────────┤
│  ▼ 节点操作                                           │
│  [删除节点]                              [查看输入源] │
└────────────────────────────────────────────────────────┘
```

### 2.2 组件结构

```vue
<!-- webui/src/components/rule-canvas/PropertyPanel.vue -->

<template>
  <aside class="property-panel" :class="{ collapsed: !visible }">
    <div class="panel-header">
      <h3>属性配置</h3>
      <button class="close-btn" @click="onClose">
        <SvgIcon name="close" />
      </button>
    </div>

    <div class="panel-content" v-if="selectedNode">
      <!-- 节点基本信息 -->
      <NodeBasicInfo :node="selectedNode" @update="onBasicInfoUpdate" />

      <!-- 输入配置 -->
      <InputConfigSection
        :node="selectedNode"
        :definitions="nodeDefinitions"
        :variables="variables"
        @update="onInputUpdate"
        @disconnect="onDisconnect"
      />

      <!-- 输出配置 -->
      <OutputConfigSection
        :node="selectedNode"
        :definitions="nodeDefinitions"
        :edges="edges"
      />

      <!-- 节点操作 -->
      <NodeActions
        :node-id="selectedNode.id"
        @delete="onDelete"
        @view-source="onViewSource"
      />
    </div>

    <div class="panel-empty" v-else>
      <SvgIcon name="info" />
      <p>选择节点以编辑属性</p>
    </div>
  </aside>
</template>
```

---

## 3. 节点基本信息

### 3.1 NodeBasicInfo 组件

```vue
<!-- webui/src/components/rule-canvas/NodeBasicInfo.vue -->

<template>
  <section class="config-section">
    <div class="section-header">
      <span>基本信息</span>
    </div>

    <div class="section-body">
      <div class="info-row">
        <label>节点类型</label>
        <span class="node-type-badge" :style="{ color: nodeColor }">
          {{ nodeTypeName }}
        </span>
      </div>

      <div class="info-row">
        <label>节点 ID</label>
        <code class="node-id">{{ node.id }}</code>
      </div>

      <div class="info-row">
        <label>节点名称</label>
        <input
          type="text"
          class="form-input"
          :value="node.data.label"
          @input="onLabelChange"
          placeholder="输入节点名称"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  node: CanvasNode
}>()

const emit = defineEmits<{
  (e: 'update', updates: Partial<CanvasNode>): void
}>()

// 获取节点类型显示名称
const nodeTypeName = computed(() => {
  // 从节点定义获取 display_name
  return props.node.type
})

// 获取节点颜色
const nodeColor = computed(() => {
  const colors: Record<string, string> = {
    input: '#4CFF4C',
    detection: '#00f0FF',
    processing: '#FFFF4C',
    action: '#FF7F4C',
    logic: '#DC4FDC',
    output: '#FF4C4C'
  }
  // 从定义获取类别颜色
  return colors['detection'] || '#7D7D7D'
})

function onLabelChange(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update', {
    data: {
      ...props.node.data,
      label: target.value
    }
  })
}
</script>

<style scoped>
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.info-row label {
  font-size: 13px;
  color: var(--text-secondary);
}

.node-type-badge {
  font-size: 13px;
  font-weight: 500;
}

.node-id {
  font-size: 12px;
  font-family: monospace;
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--text-muted);
}

.form-input {
  width: 160px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-cyan);
}
</style>
```

---

## 4. 动态表单生成

### 4.1 InputConfigSection 组件

```vue
<!-- webui/src/components/rule-canvas/InputConfigSection.vue -->

<template>
  <section class="config-section">
    <div class="section-header collapsible" @click="expanded = !expanded">
      <span>输入配置</span>
      <SvgIcon :name="expanded ? 'chevron-down' : 'chevron-right'" />
    </div>

    <div class="section-body" v-show="expanded">
      <!-- 已连接的输入 -->
      <div
        v-for="(port, key) in connectedInputs"
        :key="'conn-' + key"
        class="input-row connected"
      >
        <label>{{ port.name }}</label>
        <div class="input-value">
          <span class="connection-badge">
            <SvgIcon name="link" />
            {{ getConnectedNodeName(key as string) }}
          </span>
          <button class="disconnect-btn" @click="onDisconnect(key as string)">
            断
          </button>
        </div>
      </div>

      <!-- 可编辑的输入参数 -->
      <div
        v-for="(port, key) in editableInputs"
        :key="'edit-' + key"
        class="input-row"
      >
        <label>
          {{ port.name }}
          <span v-if="port.required" class="required">*</span>
        </label>
        <div class="input-control">
          <!-- 根据类型渲染不同控件 -->
          <StringInput
            v-if="port.type === 'STRING'"
            :value="getParamValue(key as string)"
            @update="onParamUpdate(key as string, $event)"
          />
          <NumberInput
            v-else-if="port.type === 'FLOAT' || port.type === 'INT'"
            :value="getParamValue(key as string)"
            :step="port.type === 'INT' ? 1 : 0.1"
            @update="onParamUpdate(key as string, $event)"
          />
          <BoolInput
            v-else-if="port.type === 'BOOL'"
            :value="getParamValue(key as string)"
            @update="onParamUpdate(key as string, $event)"
          />
          <SelectInput
            v-else-if="port.type === 'ENUM'"
            :value="getParamValue(key as string)"
            :options="port.options || []"
            @update="onParamUpdate(key as string, $event)"
          />
          <ModelSelect
            v-else-if="port.type === 'MODEL'"
            :value="getParamValue(key as string)"
            @update="onParamUpdate(key as string, $event)"
          />
          <span v-else class="unsupported-type">{{ port.type }}</span>

          <!-- 变量绑定按钮 -->
          <button
            class="var-btn"
            @click="showVariableMenu(key as string)"
            title="插入变量"
          >
            📎
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import StringInput from './formcontrols/StringInput.vue'
import NumberInput from './formcontrols/NumberInput.vue'
import BoolInput from './formcontrols/BoolInput.vue'
import SelectInput from './formcontrols/SelectInput.vue'
import ModelSelect from './formcontrols/ModelSelect.vue'

const props = defineProps<{
  node: CanvasNode
  definitions: NodeDefinition[]
  variables: Variable[]
}>()

const emit = defineEmits<{
  (e: 'update', key: string, value: any): void
  (e: 'disconnect', portName: string): void
}>()

const expanded = ref(true)

// 获取节点定义
const nodeDefinition = computed(() =>
  props.definitions.find(d => d.type === props.node.type)
)

// 已连接的输入（配置了 node_id）
const connectedInputs = computed(() => {
  const def = nodeDefinition.value
  if (!def) return {}

  const connected: Record<string, any> = {}
  for (const [key, input] of Object.entries(props.node.data.inputs)) {
    if (input?.node_id) {
      connected[key] = def.inputs[key]
    }
  }
  return connected
})

// 可编辑的输入参数
const editableInputs = computed(() => {
  const def = nodeDefinition.value
  if (!def) return {}

  // 只返回参数类输入（不是数据连接）
  const params: Record<string, any> = {}
  for (const [key, port] of Object.entries(def.inputs)) {
    if (props.node.data.inputs[key]?.node_id) continue // 跳过已连接的
    params[key] = port
  }
  return params
})

// 获取参数值
function getParamValue(key: string): any {
  return props.node.data.params?.[key] ?? null
}

// 更新参数
function onParamUpdate(key: string, value: any) {
  emit('update', key, value)
}

// 断开连接
function onDisconnect(portName: string) {
  emit('disconnect', portName)
}

// 获取已连接的节点名称
function getConnectedNodeName(portName: string): string {
  const input = props.node.data.inputs?.[portName]
  if (!input?.node_id) return ''

  // 简单实现：应该从 store 获取节点名称
  return input.node_id
}

// 显示变量菜单
const variableMenuTarget = ref<string | null>(null)

function showVariableMenu(portName: string) {
  variableMenuTarget.value = portName
  // TODO: 显示变量选择菜单
}
</script>

<style scoped>
.input-row {
  margin-bottom: 12px;
}

.input-row label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.required {
  color: var(--accent-red);
}

.input-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.connection-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--accent-cyan);
  background: rgba(0, 240, 255, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
}

.disconnect-btn {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--accent-red);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.disconnect-btn:hover {
  background: #ff6666;
}

.input-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.var-btn {
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
}

.var-btn:hover {
  background: var(--bg-hover);
}

.unsupported-type {
  font-size: 11px;
  color: var(--text-muted);
  font-style: italic;
}
</style>
```

---

## 5. 表单控件组件

### 5.1 StringInput

```vue
<!-- webui/src/components/rule-canvas/formcontrols/StringInput.vue -->

<template>
  <input
    type="text"
    class="form-input string-input"
    :value="value"
    @input="onInput"
    placeholder="输入字符串"
  />
</template>

<script setup lang="ts">
const props = defineProps<{
  value: string | null
}>()

const emit = defineEmits<{
  (e: 'update', value: string): void
}>()

function onInput(event: Event) {
  emit('update', (event.target as HTMLInputElement).value)
}
</script>
```

### 5.2 NumberInput

```vue
<!-- webui/src/components/rule-canvas/formcontrols/NumberInput.vue -->

<template>
  <div class="number-input">
    <input
      type="number"
      class="form-input"
      :value="value"
      :step="step"
      @input="onInput"
    />
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  value: number | null
  step?: number
}>()

const emit = defineEmits<{
  (e: 'update', value: number): void
}>()

function onInput(event: Event) {
  const val = parseFloat((event.target as HTMLInputElement).value)
  if (!isNaN(val)) {
    emit('update', val)
  }
}
</script>
```

### 5.3 BoolInput

```vue
<!-- webui/src/components/rule-canvas/formcontrols/BoolInput.vue -->

<template>
  <label class="bool-input">
    <input
      type="checkbox"
      :checked="value"
      @change="onChange"
    />
    <span class="switch"></span>
  </label>
</template>

<script setup lang="ts">
const props = defineProps<{
  value: boolean | null
}>()

const emit = defineEmits<{
  (e: 'update', value: boolean): void
}>()

function onChange(event: Event) {
  emit('update', (event.target as HTMLInputElement).checked)
}
</script>

<style scoped>
.bool-input {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.bool-input input {
  display: none;
}

.switch {
  width: 36px;
  height: 20px;
  background: var(--bg-primary);
  border-radius: 10px;
  position: relative;
  transition: background 0.2s;
}

.switch::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  background: white;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
}

.bool-input input:checked + .switch {
  background: var(--accent-cyan);
}

.bool-input input:checked + .switch::after {
  transform: translateX(16px);
}
</style>
```

### 5.4 ModelSelect

```vue
<!-- webui/src/components/rule-canvas/formcontrols/ModelSelect.vue -->

<template>
  <select class="form-select" :value="value" @change="onChange">
    <option value="">选择模型</option>
    <option v-for="m in models" :key="m.id" :value="m.id">
      {{ m.name }}
    </option>
  </select>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  value: number | null
}>()

const emit = defineEmits<{
  (e: 'update', value: number | null): void
}>()

const models = ref<Array<{ id: number; name: string }>>([])

onMounted(async () => {
  // 加载模型列表
  // const response = await fetch('/api/models')
  // models.value = await response.json()
})

function onChange(event: Event) {
  const val = (event.target as HTMLSelectElement).value
  emit('update', val ? parseInt(val) : null)
}
</script>
```

---

## 6. 变量绑定

### 6.1 变量引用语法

变量引用使用双花括号语法：`{{variable_name}}`

**示例：**
```
置信度阈值: {{CONF_THRESHOLD}}
目标类别: {{TARGET_CLASS}}
路径前缀: /data/{{USER_ID}}/images
```

### 6.2 变量解析器（后端）

```python
# backend/services/rule_engine/variable_resolver.py

import re
from typing import Any, Dict, Optional


class VariableResolver:
    """变量解析器 - 负责解析运行时变量引用。

    支持的语法：
    - 简单变量: {{variable_name}}
    - 属性访问: {{variable.property}}（暂不支持）
    - 索引访问: {{variable[0]}}（暂不支持）
    """

    VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    def __init__(self, variables: Dict[str, Any]):
        """初始化解析器。

        Args:
            variables: 规则变量字典，key 为变量名，value 为变量值
        """
        self.variables = variables

    def resolve(self, value: Any) -> Any:
        """解析值中的变量引用。

        Args:
            value: 可能是字符串（包含变量引用）或其他类型值

        Returns:
            解析后的值。如果 value 不是字符串，直接返回。

        Examples:
            resolver = VariableResolver({"THRESHOLD": 0.5, "NAME": "test"})
            resolver.resolve("{{THRESHOLD}}")  # -> 0.5
            resolver.resolve("path/{{NAME}}/file")  # -> "path/test/file"
            resolver.resolve(0.5)  # -> 0.5（直接返回）
        """
        if not isinstance(value, str):
            return value

        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.variables:
                return str(self.variables[var_name])
            # 变量不存在，保留原引用
            return match.group(0)

        return self.VARIABLE_PATTERN.sub(replace_var, value)

    def resolve_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归解析字典中的所有字符串值。

        Args:
            data: 待解析的字典

        Returns:
            解析后的新字典（原字典不变）
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.resolve(item) for item in value
                ]
            else:
                result[key] = self.resolve(value)
        return result

    def has_variable(self, value: str) -> bool:
        """检查字符串是否包含变量引用。"""
        if not isinstance(value, str):
            return False
        return bool(self.VARIABLE_PATTERN.search(value))


# 使用示例
variables = {
    "CONF_THRESHOLD": 0.5,
    "TARGET_CLASS": "person",
    "MAX_COUNT": 10
}

resolver = VariableResolver(variables)

# 解析简单变量
resolver.resolve("{{CONF_THRESHOLD}}")  # -> "0.5"

# 解析混合字符串
resolver.resolve("/data/{{TARGET_CLASS}}/img")  # -> "/data/person/img"

# 检查是否包含变量
resolver.has_variable("{{CONF_THRESHOLD}}")  # -> True
resolver.has_variable("plain text")  # -> False
```

### 6.3 变量菜单组件

```vue
<!-- webui/src/components/rule-canvas/VariableMenu.vue -->

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="variable-menu"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
    >
      <div class="menu-header">插入变量</div>
      <div class="menu-list">
        <div
          v-for="v in variables"
          :key="v.name"
          class="menu-item"
          @click="onSelect(v)"
        >
          <span class="var-name">{{ '{{' + v.name + '}}' }}</span>
          <span class="var-type">{{ v.type }}</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{
  visible: boolean
  position: { x: number; y: number }
  variables: Variable[]
}>()

const emit = defineEmits<{
  (e: 'select', variable: Variable): void
  (e: 'close'): void
}>()

function onSelect(variable: Variable) {
  emit('select', variable)
  emit('close')
}
</script>

<style scoped>
.variable-menu {
  position: fixed;
  z-index: 9999;
  min-width: 200px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.menu-header {
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
}

.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}

.menu-item:hover {
  background: var(--bg-hover);
}

.var-name {
  font-family: monospace;
  color: var(--accent-cyan);
}

.var-type {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
```

### 6.2 变量插入逻辑

```typescript
// PropertyPanel.vue 中的变量插入处理

import VariableMenu from './VariableMenu.vue'

const variableMenu = ref({
  visible: false,
  position: { x: 0, y: 0 },
  targetPort: ''
})

function showVariableMenu(portName: string, event: MouseEvent) {
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  variableMenu.value = {
    visible: true,
    position: { x: rect.right + 5, y: rect.top },
    targetPort: portName
  }
}

function onVariableSelect(variable: Variable) {
  // 在当前值后面追加变量引用
  const currentValue = getParamValue(variableMenu.value.targetPort) || ''
  const newValue = currentValue + '{{' + variable.name + '}}'
  onParamUpdate(variableMenu.value.targetPort, newValue)
  variableMenu.value.visible = false
}
```

---

## 7. 输出配置显示

### 7.1 OutputConfigSection 组件

```vue
<!-- webui/src/components/rule-canvas/OutputConfigSection.vue -->

<template>
  <section class="config-section">
    <div class="section-header collapsible" @click="expanded = !expanded">
      <span>输出配置</span>
      <SvgIcon :name="expanded ? 'chevron-down' : 'chevron-right'" />
    </div>

    <div class="section-body" v-show="expanded">
      <div
        v-for="(port, key) in outputs"
        :key="key"
        class="output-row"
      >
        <div class="output-port">
          <Handle
            type="source"
            :position="Position.Right"
            :id="key as string"
            :style="{ background: portColor(port.type) }"
          />
          <span class="port-name">{{ port.name }}</span>
          <span class="port-type">({{ port.type }})</span>
        </div>

        <div class="output-target">
          <template v-if="getConnectedEdge(key as string)">
            <span class="target-badge">
              → {{ getTargetNodeName(key as string) }}
            </span>
          </template>
          <template v-else>
            <span class="no-connection">未连接</span>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  node: CanvasNode
  definitions: NodeDefinition[]
  edges: CanvasEdge[]
}>()

const expanded = ref(true)

// 节点定义
const nodeDefinition = computed(() =>
  props.definitions.find(d => d.type === props.node.type)
)

// 输出端口列表
const outputs = computed(() =>
  nodeDefinition.value?.outputs || {}
)

// 端口颜色
function portColor(type: string): string {
  const colors: Record<string, string> = {
    IMAGE: '#4CFF4C',
    BBOX: '#00f0FF',
    MASK: '#DC4FDC',
    SCORES: '#FFFF4C',
    CLASS_IDS: '#FF7F4C',
    TRIGGER: '#FF4C4C',
    CONTROL: '#4CFFFF'
  }
  return colors[type] || '#7D7D7D'
}

// 获取连接的边
function getConnectedEdge(portName: string): CanvasEdge | undefined {
  return props.edges.find(
    e => e.source === props.node.id && e.sourceHandle === portName
  )
}

// 获取目标节点名称
function getTargetNodeName(portName: string): string {
  const edge = getConnectedEdge(portName)
  if (!edge) return ''
  // 应该从 store 获取节点标签
  return edge.target
}
</script>

<style scoped>
.output-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.output-row:last-child {
  border-bottom: none;
}

.output-port {
  display: flex;
  align-items: center;
  gap: 8px;
}

.port-name {
  font-size: 13px;
}

.port-type {
  font-size: 11px;
  color: var(--text-muted);
}

.target-badge {
  font-size: 12px;
  color: var(--accent-cyan);
}

.no-connection {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}
</style>
```

---

## 8. 节点操作

### 8.1 NodeActions 组件

```vue
<!-- webui/src/components/rule-canvas/NodeActions.vue -->

<template>
  <section class="config-section">
    <div class="section-header">
      <span>节点操作</span>
    </div>

    <div class="section-body">
      <div class="action-row">
        <button class="action-btn danger" @click="onDelete">
          <SvgIcon name="delete" />
          删除节点
        </button>

        <button class="action-btn" @click="onViewSource" v-if="hasSource">
          <SvgIcon name="link" />
          查看输入源
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  nodeId: string
}>()

const emit = defineEmits<{
  (e: 'delete'): void
  (e: 'view-source'): void
}>()

// 是否有输入源（被其他节点连接）
const hasSource = computed(() => {
  // 从 store 获取边信息判断
  return false
})

function onDelete() {
  emit('delete')
}

function onViewSource() {
  emit('view-source')
}
</script>

<style scoped>
.action-row {
  display: flex;
  gap: 12px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--bg-hover);
}

.action-btn.danger {
  color: var(--accent-red);
  border-color: var(--accent-red);
}

.action-btn.danger:hover {
  background: rgba(255, 76, 76, 0.1);
}
</style>
```

---

## 9. 集成到 RuleCanvas

### 9.1 主组件集成

```vue
<!-- webui/src/views/RuleCanvas.vue -->

<template>
  <div class="rule-canvas-fullscreen">
    <!-- 顶部工具栏 -->
    <header class="canvas-header">...</header>

    <!-- 主体区域 -->
    <div class="canvas-body">
      <!-- 左侧节点面板 -->
      <NodePalette
        :categories="categories"
        :nodes="nodeDefinitions"
        @drag-start="onNodeDragStart"
      />

      <!-- 中间画布 -->
      <CanvasRenderer
        v-model:nodes="canvasStore.nodes"
        v-model:edges="canvasStore.edges"
        :selected-node-ids="canvasStore.selectedNodeIds"
        @node-select="onNodeSelect"
        @node-update="onNodeUpdate"
      />

      <!-- 右侧属性面板 -->
      <PropertyPanel
        :visible="!!canvasStore.selectedNodeIds.length"
        :selected-node="selectedNode"
        :node-definitions="nodeDefinitions"
        :variables="variables"
        :edges="canvasStore.edges"
        @close="onPanelClose"
        @update="onNodeDataUpdate"
        @delete="onDeleteSelected"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRuleCanvasStore } from '@/stores/ruleCanvas'

const canvasStore = useRuleCanvasStore()

// 选中的节点
const selectedNode = computed(() => {
  if (canvasStore.selectedNodeIds.length !== 1) return null
  return canvasStore.nodes.find(n => n.id === canvasStore.selectedNodeIds[0])
})

// 节点选择事件
function onNodeSelect(nodeId: string) {
  canvasStore.selectedNodeIds = [nodeId]
}

// 属性面板关闭
function onPanelClose() {
  canvasStore.selectedNodeIds = []
}

// 节点数据更新
function onNodeDataUpdate(key: string, value: any) {
  if (!selectedNode.value) return

  if (key === 'label') {
    canvasStore.updateNode(selectedNode.value.id, {
      data: { ...selectedNode.value.data, label: value }
    })
  } else {
    // 更新参数
    canvasStore.updateNode(selectedNode.value.id, {
      data: {
        ...selectedNode.value.data,
        params: { ...selectedNode.value.data.params, [key]: value }
      }
    })
  }
}

// 断开连接
function onDisconnect(portName: string) {
  // 找到连接的边并删除
  const nodeId = selectedNode.value!.id
  const edge = canvasStore.edges.find(
    e => e.target === nodeId && e.targetHandle === portName
  )

  if (edge) {
    // 更新节点数据
    const newInputs = { ...selectedNode.value!.data.inputs }
    delete newInputs[portName]

    canvasStore.updateNode(nodeId, {
      data: { ...selectedNode.value!.data, inputs: newInputs }
    })

    // 删除边
    canvasStore.removeEdge(edge.id)
  }
}
</script>
```

---

## 10. 验收检查清单

### 10.1 面板显示
- [ ] 选中节点后右侧面板显示
- [ ] 面板显示节点类型、ID、名称
- [ ] 无选中节点时显示空状态提示

### 10.2 表单生成
- [ ] STRING 类型渲染文本输入框
- [ ] INT/FLOAT 类型渲染数字输入框
- [ ] BOOL 类型渲染开关
- [ ] ENUM 类型渲染下拉选择
- [ ] MODEL 类型渲染模型选择下拉框

### 10.3 连接显示
- [ ] 已连接的输入显示来源节点名称
- [ ] "断"按钮能断开指定连接
- [ ] 未连接的输入显示可编辑
- [ ] 输出端口显示连接状态

### 10.4 变量绑定
- [ ] 变量菜单能选择变量
- [ ] 选择后插入 `{{variable_name}}`
- [ ] 支持多个变量混合

### 10.5 数据更新
- [ ] 修改参数后节点数据实时更新
- [ ] 修改名称后画布节点标签更新
- [ ] 所有更改标记脏状态
