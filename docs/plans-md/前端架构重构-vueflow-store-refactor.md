# 前端架构重构 — Pinia Store 作为唯一数据源
规则引擎画布从"双源管理"改造为"单源模式" · 2026-05

---

## 背景
规则引擎画布（`RuleCanvas.vue`）原先采用"本地状态 + Pinia Store 双源"管理模式： 节点/边数据同时存在于画布的本地 `shallowRef` 和 Store 的 `currentGraph` 中， 导致数据同步困难、配置更新事件链路断裂、状态不一致。

核心问题链：节点配置更新时，`RuleNode.vue` 通过 `@update:config` 事件 向父组件派发，但 VueFlow 不转发自定义节点事件（需 `node:` 前缀）， 导致配置变更无法到达 Store，最终表现为"YOLO 检测节点配置项不可编辑"。

## 变更统计
8 文件变更 +596 行 −781 行 净减 185 行

            
| 文件 | 变更 | 说明 |
| --- | --- | --- |
| `webui/src/stores/ruleEngine.ts` | +330 / −162 | Store 重写为单源，新增节点/边/执行/模型状态和方法 |
| `webui/src/views/RuleCanvas.vue` | +198 / −530 | 移除全部本地状态，使用 `storeToRefs` 绑定 Store |
| `webui/src/components/rule-engine/RuleNode.vue` | +54 / −85 | 直连 Store，移除事件转发和 configSummary |
| `backend/services/rule_engine/nodes/detection_nodes.py` | +4 / −4 | 修复 YOLO 节点 `model_path` → `file_path` 字段名 |
| `webui/src/views/AtlasList.vue` | +2 / −2 | `rows="3"` → `:rows="3"` 绑定修复 |
| `webui/src/views/RuleList.vue` | +1 / −1 | 同上绑定修复 |
| `webui/src/components.d.ts` | +1 / −0 | 添加 `ElTooltip` 类型声明 |
| `.gitignore` | +3 / −2 | 添加 `.codegraph/` 忽略项 |

---

## 架构对比

#### ❌ 改造前：双源模式

```text

┌─────────────────────┐
│    RuleCanvas.vue    │
│  ┌────────────────┐ │
│  │ shallowRef     │ │  ← 本地节点/边
│  │ historyStack   │ │  ← 本地撤销栈
│  │ executionLogs  │ │  ← 本地执行状态
│  │ nodeStates     │ │  ← 本地节点状态
│  │ variables      │ │  ← 本地变量
│  │ availableModels│ │  ← 本地模型列表
│  └──────┬─────────┘ │
│         │ @update:  │  ← 事件链路（已断裂）
│         ▼           │
│  ┌────────────────┐ │
│  │   RuleNode     │ │  → emit('update:config')
│  └────────────────┘ │
└──────────┬──────────┘
           │
           ▼ (有时同步，有时不同步)
┌─────────────────────┐
│  Pinia Store        │
│  currentGraph       │  ← 另一份节点/边副本
└─────────────────────┘
          
```

**问题：**两处数据源容易不同步；VueFlow 不转发自定义事件， 导致 `@update:config` 永远无法到达 Store。

#### ✅ 改造后：单源模式

```text

┌──────────────────────────┐
│    Pinia Store (唯一源)   │
│  ┌────────────────────┐  │
│  │ nodes / edges      │  │  ← VueFlow v-model 直接绑定
│  │ graphMeta          │  │  ← 图元数据
│  │ selectedNodeId     │  │
│  │ executionState     │  │  ← 统一执行状态
│  │ variables          │  │
│  │ availableModels    │  │
│  │ historyStack       │  │  ← 撤销栈（50 步）
│  └──────┬─────────────┘  │
│         │ storeToRefs()   │
│         ▼                 │
│  ┌────────────────────┐  │
│  │  RuleCanvas.vue    │  │  ← 纯模板，无本地状态
│  └────────────────────┘  │
│         │ store.update-  │
│         ▼   NodeConfig() │
│  ┌────────────────────┐  │
│  │  RuleNode.vue      │  │  ← 直连 Store
│  └────────────────────┘  │
└──────────────────────────┘
          
```

**优势：**唯一数据源，所有组件直连 Store； 无需事件转发，配置变更即刻写入 Store。

## 关键改动

### 1. 修复事件链路断裂（根因）
VueFlow 的自定义节点事件不会自动转发到父组件 —— `@update:config` 在 `<VueFlow>` 上永远收不到。解决方案： 让 RuleNode 直接调用 `store.updateNodeConfig(nodeId, key, value)`，完全绕过事件机制。

### 2. Pinia Store 能力扩展

 
- 新增 `nodes` / `edges` ref，类型为 `Ref<Node<RuleNodeData>[]>`，直接绑定 VueFlow v-model 
- 新增 `graphMeta` 接口替代 `currentGraph`，分离元数据和节点数据 
- 新增 `executionState` 统一管理执行状态/日志/进度/节点状态 
- 新增 `availableModels` + `fetchModels()` 为 model-select widget 提供数据 
- 新增 `createNode` / `updateNodeConfig` / `removeNode` / `addEdge` / `removeEdge` / `selectNode` 
- 新增 `addVariable` / `removeVariable` / `updateVariable` / `getVariable` 
- 新增 `setExecutionStatus` / `addExecutionLog` / `setExecutionProgress` / `clearExecution` 等 
- 历史栈容量从 20 提升到 50，新增 `pauseHistory` / `unpauseHistory` 
- `fetchNodeDefinitions` 增加 try-catch 确保失败不阻塞调用链 
- `loadGraph` 增加节点 type 标准化逻辑（兼容旧数据格式） 
- `saveGraph` 只序列化业务字段，不保存 VueFlow 内部状态 

### 3. RuleCanvas.vue 瘦身 (-530 行)

 
- 移除全部本地状态声明：`shallowRef nodes/edges`、`historyStack/Index`、`executionLogs/Status/Progress/Id`、`nodeStates`、`variables`、`availableModels` 
- 使用 `storeToRefs(store)` 绑定 Store 数据到模板 
- 撤销/重做 → `store.undo()` / `store.redo()` 
- 变量操作 → 委托到 Store 方法 
- 执行事件 → `store.setExecutionState()` / `store.addExecutionLog()` 
- 移除 `provide('availableModels')` / `provide('variables')` 

### 4. RuleNode.vue 精简 (-31 行)

 
- 移除 `emit('update:config')` 和 `emit('delete')` → 直接调 `store.updateNodeConfig()` / `store.removeNode()` 
- 移除 `configSummary` computed 属性和对应的 `.node-footer` 模板/CSS（节点底部不再显示配置摘要） 
- 移除 `onDelete` 类型定义（JSON 序列化后丢失，改为 Store 方法） 
- 可用模型改为 `computed(() => store.availableModels)`（从 inject 改为 store） 
- 所有配置 widget 添加 `@mousedown.stop` 防止 VueFlow 拖拽干扰 
- model-select 空列表时显示 "暂无可用模型" 反馈 
- 变量绑定按钮增加 el-tooltip 说明 + SvgIcon 

### 5. YOLO 后端修复

 
- `detection_nodes.py` 中 `Model.model_path` → `Model.file_path`（数据库字段名不匹配） 

### 6. 模板绑定修复

 
- `AtlasList.vue`、`RuleList.vue` 中 `rows="3"` → `:rows="3"`（v-bind 缺失） 

---

## 验收标准
            
| # | 验收项 | 状态 |
| --- | --- | --- |
| 1 | TypeScript 编译零错误（相关文件） | ✅ 通过 |
| 2 | YOLO 节点配置项可编辑（slider/number/dropdown） | ✅ 修复 |
| 3 | YOLO 节点模型下拉展示已训练模型列表 | ✅ 修复 |
| 4 | 配置修改即时保存到 Store，画布可同步 | ✅ 修复 |
| 5 | 撤销/重做功能正常 | ✅ 保留 |
| 6 | 执行日志面板正常显示 | ✅ 保留 |
| 7 | 去除节点底部冗余配置摘要 | ✅ 完成 |
| 8 | API 调用失败不级联阻塞（独立 try-catch） | ✅ 修复 |

TS 检查命令：`rtk npx vue-tsc --noEmit 2>&1 | grep -E "^src/(stores/ruleEngine|views/RuleCanvas|components/rule-engine)"`

---

## 关联文档

 
- 规则引擎迭代计划 v2.0 — Phase 10.1 model-select 对接任务 
- 规则引擎节点参考 — 节点系统完整分析 
- 逐节点前端验证计划 — 节点编辑功能验证清单 

---

CogniFlow · 前端架构重构 — Pinia Store 单源改造 · 2026-05-28
