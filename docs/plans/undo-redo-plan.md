# CogniFlow 规则引擎画布撤销/重做功能实现计划

## 一、当前实现状态

### 1.1 已有的实现

**RuleCanvas.vue (画布页面)**：
- ✅ UI 工具栏有撤销/重做按钮（第 33-48 行）
- ✅ 键盘快捷键绑定：Ctrl+Z（撤销）、Ctrl+Y/Ctrl+Shift+Z（重做）（第 957-969 行）
- ✅ `historyStack` 和 `historyIndex` 管理历史记录（第 704-707 行）
- ✅ `saveHistory()` 函数在节点增删改时保存快照（第 913-924 行）
- ✅ `handleUndo()` 和 `handleRedo()` 函数实现（第 1181-1198 行）
- ✅ 历史栈限制 50 步

**ruleEngine.ts (Pinia Store)**：
- ✅ 也有独立的 undo/redo 实现（第 110-125 行）
- ✅ `saveToHistory()`、`undo()`、`redo()` 函数（第 293-333 行）
- ✅ 历史栈限制 20 步

### 1.2 存在的问题

| 问题 | 描述 |
|------|------|
| **未使用 VueFlow 官方 API** | 项目使用 @vue-flow/core v1.48.2，但没有使用 VueFlow 官方提供的 `useHistory` composable |
| **历史限制不统一** | RuleCanvas.vue 限制 50 步，store 限制 20 步 |
| **拖拽过程产生过多快照** | 节点拖拽时可能产生大量中间状态快照，消耗内存 |
| **边操作未触发保存** | 检查发现边的增删操作可能未统一调用 `saveHistory()` |
| **缺少 @vue-flow/history 包** | 未安装官方 history 扩展包 |

---

## 二、技术方案

### 2.1 VueFlow useHistory API

VueFlow 官方提供 `useHistory` composable（来自 `@vue-flow/history` 包），功能包括：

```typescript
import { useHistory } from '@vue-flow/history'

const { history, historyIndex, setHistory, undo, redo, canUndo, canRedo, pause, unpause } = useHistory()
```

**特点**：
- 提供 `pause()`/`unpause()` 控制是否记录历史（用于拖拽场景）
- 自动管理历史栈
- 与 VueFlow 内部状态集成

### 2.2 数据结构设计

```typescript
// 历史记录快照结构
interface HistorySnapshot {
  nodes: Node[]
  edges: Edge[]
}

// 历史栈
interface HistoryState {
  stack: HistorySnapshot[]
  index: number
  maxSize: number  // 建议 50 步
}
```

### 2.3 需要修改的文件

| 文件 | 修改内容 |
|------|----------|
| `webui/package.json` | 添加 `@vue-flow/history` 依赖 |
| `webui/src/views/RuleCanvas.vue` | 集成 useHistory，移除手动实现的 historyStack |
| `webui/src/stores/ruleEngine.ts` | 保持现有实现或考虑复用 useHistory |

---

## 三、推荐实现方案

### 方案 A：集成 VueFlow 官方 useHistory（推荐）

**优点**：
- 与 VueFlow 深度集成
- 提供 pause/unpause API，避免拖拽时产生过多快照
- 官方维护，减少 bug

**步骤**：

1. **安装依赖**
   ```bash
   cd webui
   npm install @vue-flow/history
   ```

2. **修改 RuleCanvas.vue**
   ```typescript
   import { useHistory } from '@vue-flow/history'
   import { useVueFlow } from '@vue-flow/core'
   
   // 在 setup 中
   const { history, historyIndex, setHistory, undo, redo, canUndo, canRedo, pause, unpause } = useHistory()

   // 在节点拖拽开始时暂停记录
   function onNodeDragStart() {
     pause()
   }
   
   // 在节点拖拽结束时恢复记录并保存
   function onNodeDragStop() {
     unpause()
     setHistory()
   }
   ```

### 方案 B：优化现有手动实现

如果不想引入新依赖，可以优化现有实现：

1. **统一历史限制**：将 store 和组件的历史限制统一为 50 步
2. **添加 pause 机制**：手动实现暂停/恢复功能
3. **优化保存时机**：只在操作结束时保存，而非拖拽过程中

---

## 四、键盘快捷键

现有实现已支持：

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Z | 撤销 |
| Ctrl+Y | 重做 |
| Ctrl+Shift+Z | 重做 |

**建议**：
- 考虑添加 Ctrl+S 保存后自动清空 redo 栈（现有实现已自动清空）
- 添加快捷键提示 tooltip

---

## 五、实施计划

### Phase 1: 调研和方案确认
- [x] 查看 RuleCanvas.vue 现有实现
- [x] 查看 VueFlow useHistory API
- [x] 检查项目依赖
- [x] 制定实现方案

### Phase 2: 集成 VueFlow useHistory（推荐方案）
- [ ] 安装 `@vue-flow/history` 包
- [ ] 修改 RuleCanvas.vue，集成 useHistory
- [ ] 实现拖拽时的 pause/unpause
- [ ] 测试撤销/重做功能
- [ ] 测试键盘快捷键

### Phase 3: 优化和调优
- [ ] 统一历史栈大小（建议 50 步）
- [ ] 确保所有操作（节点增删改、边增删改）正确触发保存
- [ ] 边界情况测试（空画布、单个节点等）

---

## 六、实际实施情况

### 6.1 @vue-flow/history 包状态

**调查结论**：`@vue-flow/history` 包在 npm 上不存在（404 错误）。

- 使用 `pnpm add @vue-flow/history` 测试：返回 `ERR_PNPM_FETCH_404`
- 使用 `npm install @vue-flow/history` 测试：返回 `Cannot read properties of null`
- 检查 `@vue-flow/core` v1.48.2：内置 composables 列表中无 `useHistory`
- `@vue-flow/core` 的 composables 目录：`useConnection`, `useDrag`, `useEdge`, `useNode`, `useVueFlow` 等，不包含 history

### 6.2 替代实现方案

采用**手动 pause/unpause 机制**实现与 `useHistory` 类似的拖拽优化功能：

```typescript
// 暂停历史记录（拖拽开始时调用）
function pauseHistory() {
  isHistoryPaused.value = true
}

// 恢复历史记录并保存快照（拖拽结束时调用）
function unpauseHistory() {
  isHistoryPaused.value = false
  saveHistory()
}
```

**效果**：节点拖拽过程中不会产生大量中间快照，只在拖拽结束时保存一次。

---

## 七、结论

**当前状态**：撤销/重做功能已基本实现，采用了手动 pause/unpause 机制优化拖拽过程中的历史记录管理。

**调查结论**：`@vue-flow/history` 包在 npm 上不存在（404 错误），无法安装。`@vue-flow/core` v1.48.2 也没有内置 `useHistory` composable。

**实现效果**：
- 节点拖拽开始时暂停历史记录（`pauseHistory`）
- 节点拖拽结束时恢复记录并统一保存快照（`unpauseHistory`）
- 边的增删操作也能正确触发历史保存
- 避免拖拽过程中产生大量中间状态快照

---

## 八、参考文档

- [VueFlow History Documentation](https://vueflow.dev/guide/components/history.html)
- [VueFlow GitHub - useHistory](https://github.com/xyflow/xyflow/blob/main/packages/svelte/src/lib/components/History.svelte)

**工作量预估**：2-4 小时（包含测试）
