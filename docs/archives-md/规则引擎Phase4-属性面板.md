# Phase 4 技术实现文档：节点配置面板（前端）
选中节点后，右侧面板显示该节点的参数编辑表单，支持变量绑定

---

## 一、阶段目标
**目标：**选中节点后，右侧面板显示该节点的参数编辑表单，支持变量绑定。

**验收标准：**

 
- 选中节点后，右侧面板正确显示节点类型、ID、名称 
- 输入参数表单根据节点类型动态生成 
- 支持 STRING/INT/FLOAT/BOOL/ENUM 类型参数编辑 
- 参数修改后节点数据实时更新 
- 变量下拉菜单能插入 `{{variable_name}}` 到输入框 
- "断连"按钮能断开指定输入连接 

## 二、面板布局

```text
┌────────────────────────────────────────────────────────┐
│  选中节点: YOLOModel                        [关闭 X]  │
├────────────────────────────────────────────────────────┤
│  节点类型        YOLO 检测模型                         │
│  节点 ID         node_002                             │
│  节点名称        [________________]                   │
├────────────────────────────────────────────────────────┤
│  ▼ 输入配置                                           │
│  ├─ 图片输入    [已连接: node_001 → image      ] [断] │
│  ├─ 置信度阈值  [0.5_____________________] 📎         │
│  └─ 模型选择    [选择模型___________▼] 📎             │
├────────────────────────────────────────────────────────┤
│  ▼ 输出配置                                           │
│  ├─ 检测框(BBOX)   → node_003                        │
│  └─ 置信度(SCORES) → [未连接]                        │
├────────────────────────────────────────────────────────┤
│  ▼ 节点操作                                           │
│  [删除节点]                              [查看输入源] │
└────────────────────────────────────────────────────────┘
```

### 组件结构

 
- `PropertyPanel.vue` — 主面板容器，含折叠切换 
- `NodeBasicInfo.vue` — 基本信息（类型/ID/名称） 
- `InputConfigSection.vue` — 输入配置（连接+参数） 
- `OutputConfigSection.vue` — 输出配置（连接状态） 
- `NodeActions.vue` — 节点操作（删除/查看源） 

## 三、动态表单生成

### 3.1 输入配置分类

 
- **已连接的输入** — 显示来源节点名称，提供"断"按钮 
- **可编辑的输入参数** — 根据类型渲染不同控件 

### 3.2 控件类型映射
          
| 端口类型 | 渲染控件 |
| --- | --- |
| `STRING` | `StringInput.vue` — 文本输入框 |
| `FLOAT` | `NumberInput.vue` — 数字输入框 |
| `INT` | `NumberInput.vue` — 整数输入框 |
| `BOOL` | `BoolInput.vue` — 开关 toggle |
| `ENUM` | `SelectInput.vue` — 下拉选择 |
| `MODEL` | `ModelSelect.vue` — 模型选择下拉框 |

## 四、变量绑定

### 4.1 变量引用语法
变量引用使用双花括号语法：

```text
置信度阈值: {{CONF_THRESHOLD}}
目标类别: {{TARGET_CLASS}}
路径前缀: /data/{{USER_ID}}/images
```

### 4.2 后端变量解析器
使用正则 `\{\{(\w+)\}\}` 提取变量名，从 variables 字典中查找替换：

 
- `resolve(value)` — 解析单个值 
- `resolve_dict(data)` — 递归解析字典中所有字符串 
- `has_variable(value)` — 检查是否包含变量引用 

### 4.3 变量菜单组件
点击 📎 按钮弹出变量选择菜单，选择后追加 `{{variable_name}}` 到输入框：

```javascript
function onVariableSelect(variable: Variable) {
  const currentValue = getParamValue(targetPort) || ''
  const newValue = currentValue + '{{' + variable.name + '}}'
  onParamUpdate(targetPort, newValue)
}
```

## 五、输出配置显示
输出端口显示连接状态：

 
- **已连接** — 显示目标节点名称（如 `→ node_003`） 
- **未连接** — 显示 *未连接* 提示 
端口颜色遵循类型矩阵：`IMAGE`=绿、`BBOX`=青、`MASK`=紫、`SCORES`=黄

## 六、集成到 RuleCanvas

```text
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
```

属性面板通过 `v-if="!!canvasStore.selectedNodeIds.length"` 控制显示/隐藏，无选中节点时显示空状态提示。

## 七、验收检查清单
                      
| 类别 | 验收项 |
| --- | --- |
| 面板显示 | 选中节点后右侧面板显示 |
| 面板显示节点类型、ID、名称 |  |
| 无选中节点时显示空状态提示 |  |
| 表单生成 | STRING 类型渲染文本输入框 |
| INT/FLOAT 类型渲染数字输入框 |  |
| BOOL 类型渲染开关 |  |
| ENUM 类型渲染下拉选择 |  |
| MODEL 类型渲染模型选择下拉框 |  |
| 连接显示 | 已连接的输入显示来源节点名称 |
| "断"按钮能断开指定连接 |  |
| 未连接的输入显示可编辑 |  |
| 输出端口显示连接状态 |  |
| 变量绑定 | 变量菜单能选择变量 |
| 选择后插入 `{{variable_name}}` |  |
| 支持多个变量混合 |  |
| 数据更新 | 修改参数后节点数据实时更新 |
| 修改名称后画布节点标签更新 |  |
| 所有更改标记脏状态 |  |
