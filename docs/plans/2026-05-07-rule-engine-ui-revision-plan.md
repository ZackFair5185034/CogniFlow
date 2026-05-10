# Rule Engine UI 整改方案

> **目标：** 对规则引擎前端画布的 11 个遗留问题进行系统性分析，给出明确的技术方案和执行优先级，确保所有问题一次修复到位。

---

## 问题清单与根因分析

### P0 — 必须修复（功能阻塞）

#### 1. 左侧节点列表不能展开收纳

**根因：** `nodeCategories` 是 `computed` 属性（`RuleCanvas.vue:467`），每次依赖变化都会重建数组对象。`expanded` 状态附着在这些临时对象上，展开/折叠后 computed 重新计算，状态丢失。

```typescript
// 当前代码 — 每次访问都新建对象
const nodeCategories = computed(() => [
  { name: 'input', label: '输入', expanded: true, nodes: [] },
  // expanded: true 只在初始化有效，无法持久化
])
```

**方案：** 将分类状态提取为独立的 `reactive` 对象，与 computed 分离。使用 `Map<categoryName, boolean>` 存储展开状态：

```typescript
const categoryExpanded = reactive<Record<string, boolean>>({
  input: true, detection: true, processing: true,
  action: true, logic: true, output: true
})

const nodeCategories = computed(() => CATEGORIES.map(cat => ({
  ...cat,
  expanded: categoryExpanded[cat.name],
  nodes: nodeDefinitions.value.filter(d => d.category === cat.name)
})))
```

`handleSearchInput` 中直接修改 `categoryExpanded[key] = true` 而非修改 computed 对象。

---

#### 2. 框选功能未实现

**根因：** VueFlow v1.48 中 `:select-nodes-on-drag="true"` 默认在点击空白处拖拽时进入框选模式，但因为 `@mousedown` / `@mousemove` / `@mouseup` 在 `flow-container` 上拦截了事件，导致 VueFlow 的框选逻辑无法正常触发。此外 `:selection-key-code="true"` 需要搭配 SelectionMode 使用。

**方案：** 
- 保留 `:select-nodes-on-drag="true"` 
- 移除 `flow-container` 上的 `@mousedown` / `@mousemove` / `@mouseup`（或改为只在点击节点时生效）
- 使用 `:selection-mode="SelectionMode.Partial"` 替代 `selection-key-code`
- 使用 VueFlow 的 `onSelectionChange` 回调监听选区变化

---

#### 3. 右键菜单在节点上未实现

**根因：** `RuleNode.vue:2` 的 `@contextmenu.prevent` 阻止了所有右键事件冒泡，VueFlow 的 `@node-context-menu` 收不到事件。

**方案：** 移除 `@contextmenu.prevent`，改为在 `RuleNode.vue` 内部通过 `@contextmenu` 手动 `emit` 给父组件。但更简洁的方案是利用 VueFlow 的 `@node-context-menu` 事件（已在 `RuleCanvas.vue:216` 注册），只需去掉 RuleNode 的 `prevent` 即可。

```vue
<!-- RuleNode.vue — 移除 prevent，让事件冒泡到 VueFlow -->
<div class="rule-node" :class="[`category-${data.category}`, { selected }]">
```

额外需要处理：因为 `@contextmenu.prevent` 被移除，需要在节点内部处理浏览器默认菜单。可在 `handleContextMenu` 中统一 `preventDefault`。

---

#### 4. 节点背景色溢出

**根因：** `RuleNode.vue:341-354` 的 `.rule-node` 有 `border-radius: 6px`，但内部儿童（如 `node-header` 的背景渐变）没有裁剪到圆角范围内。

**方案：** 在 `.rule-node` 上添加 `overflow: hidden;`：

```css
.rule-node {
  overflow: hidden;  /* 确保圆角裁剪生效 */
}
```

注意：Handle 是绝对定位可能超出节点边界，`overflow: hidden` 会裁剪 Handle。需要确保 Handle 的 `position: absolute` 不会被父容器裁剪，或使用 `overflow: clip` 替代。

---

#### 5. Handle 位置不对

**根因：** VueFlow 的 `Handle` 组件默认使用 `top` 定位，虽然设置了 `:position="Position.Left"`，但需要同时指定 `offset` 或使用 CSS 调整位置使其对齐到节点边框。

**方案：** Handle 使用绝对定位相对于节点，需要设置正确的 `offset` 属性，或通过 CSS 调整。检查 VueFlow 文档，Handle 的 `position` 属性控制其在节点上的方位（Top/Bottom/Left/Right），但默认偏移是 50%。对于输入端口（target），Position.Left 应该让 Handle 位于节点左侧中间。

如果 Handle 显示位置不对，可能是缺少 `:offset` 或样式覆盖问题。需要在 `RuleNode.vue` 中设置：

```vue
<Handle type="target" :position="Position.Left" :id="input.name" :offset="0" />
```

并确保父容器没有 `overflow: hidden` 导致 Handle 被裁剪。

---

### P1 — 重要改进

#### 6. 连接功能不正常

**根因：** `handleConnect` 函数（`RuleCanvas.vue:1208`）调用 `validateConnection` 后调用 `addEdges`，但 `addEdges` 来自 `useVueFlow()`。需要确认 `addEdges` 是否正确工作。可能的问题：
- `addEdges` 的参数格式与 VueFlow 期望的不一致
- 连接时 Handle id 不正确导致找不到端口

**方案：** 
- 在 `handleConnect` 中添加日志输出，确认 `params` 结构
- 确保 edges 的 `sourceHandle` / `targetHandle` 正确设置
- 验证 `validateConnection` 中的 `getNodePortType` 逻辑 — 当前 `ports[handleId]` 假设 ports 是对象以 handleId 为 key，但 `data.inputs/outputs` 是数组，需要用 `find` 查找

```typescript
function getNodePortType(nodeId: string, handleId: string | null, isSource: boolean): string | null {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node?.data) return null
  const ports = isSource ? node.data.outputs : node.data.inputs
  if (!ports?.length) return null
  // data.inputs/outputs 是数组，需要用 find 匹配 handleId
  const port = ports.find((p: any) => p.name === handleId || p.label === handleId)
  return port?.type || 'ANY'
}
```

---

#### 7. 连接颜色设计（Blender 风格）

**描述：** 当前 Handle 的端口类型颜色定义在 `RuleNode.vue:680-688` 中，每种类型有独立颜色。Blender 风格的连接设计是同类型可连接的端口使用相同颜色，让用户直观识别哪些端口可以连接。

**方案：** 当前端口类型颜色已经定义（`.node-handle.type-image`、`.type-bbox` 等），问题是这些类名是否正确地应用到了 Handle 上。需要确保 Handle 根据端口类型获得正确的 CSS 类：

```vue
<Handle :class="['node-handle', `type-${port.type.toLowerCase()}`]" ... />
```

同时确保 `isPortCompatible` 的规则与视觉对应——同色端口可连接。目前只有 TRIGGER/CONTROL 有特殊规则，其他类型要求完全相同。这是合理的。

---

#### 8. 工具栏重新规划

**根因：** 当前工具栏有 6 组功能（导航、撤销/重做、缩放、视图切换、网格、操作按钮），按钮过于密集。

**方案：** 重新规划工具栏分组：

| 分组 | 按钮 | 保留 |
|------|------|------|
| 导航 | 返回 | ✅ |
| 编辑 | 撤销、重做 | ✅ |
| 视图 | 缩放百分比、放大、缩小、适应画布 | ✅ |
| 网格 | 显示网格、网格吸附 | 合并为单一"吸附"切换 |
| 小地图 | 小地图切换 | ✅ |
| 操作 | 校验、保存、执行 | ✅ |

精简项：
- 移除 `showGrid` 切换（点阵背景默认显示）
- 将 `snapGrid` 合并到齿轮菜单或保留
- 整体布局保持 `header-left / center / right` 三栏

---

#### 9. 折叠按钮位置不对

**根因：** `collapse-btn` 在 `palette-header` 的右侧，用户期望在面板边缘（左上或左下）找到折叠按钮。

**方案：** 将折叠按钮放在 `palette-header` 左侧或面板左上角。具体位置：
- 折叠按钮放在 `palette-header` 的最左侧
- 或者放在面板底部，类似 VS Code 的侧栏折叠

```vue
<div class="palette-header">
  <button class="collapse-btn" @click="showPalette = !showPalette">
    <SvgIcon name="chevron-left" :class="{ rotated: !showPalette }" />
  </button>
  <h3 v-if="showPalette">节点库</h3>
</div>
```

---

### P2 — 体验优化

#### 10. 控制台不可调整高度

**根因：** `execution-panel` 使用固定定位（`position: fixed; bottom: 0`），无拖拽调整大小的功能。

**方案：** 添加拖拽调整高度功能：

1. 在 `execution-header` 上方添加一个 4px 高的拖拽条（drag handle）
2. 拖拽条的 `@mousedown` 开始监听鼠标移动
3. `@mousemove` 时计算新高度，限制最小/最大范围（如 100px ~ 400px）
4. `@mouseup` 时结束拖拽

```typescript
const panelHeight = ref(200)
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startY = e.clientY
  const startHeight = panelHeight.value
  
  const onMove = (ev: MouseEvent) => {
    const newHeight = startHeight + (startY - ev.clientY)
    panelHeight.value = Math.max(100, Math.min(400, newHeight))
  }
  const onUp = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}
```

---

#### 11. 收纳宽度适配

**根因：** `.node-palette.collapsed` 设置 `width: 48px`，但内部 `.palette-content` 只是 `display: none`，`execution-panel` 的 `left` 值仍使用 `$palette-width`（280px），没有响应式适配。

**方案：** 

```typescript
const paletteWidth = computed(() => showPalette.value ? 280 : 48)
```

```scss
.execution-panel {
  left: v-bind('paletteWidth + "px"');
}
```

同时需要在折叠状态下显示简化的图标工具栏（垂直排列的节点分类图标），让用户即使面板折叠也能拖拽节点。

---

## 执行计划

### Phase 1: P0 修复（优先级最高）

| # | 任务 | 涉及文件 | 预估复杂度 |
|---|------|---------|-----------|
| 1 | 节点分类展开状态持久化 | `RuleCanvas.vue` | 简单 |
| 2 | 框选功能修复 | `RuleCanvas.vue` | 中等 |
| 3 | 右键菜单冒泡修复 | `RuleNode.vue` | 简单 |
| 4 | 节点圆角溢出修复 | `RuleNode.vue` | 简单 |
| 5 | Handle 位置修正 | `RuleNode.vue` | 简单 |

### Phase 2: P1 改进

| # | 任务 | 涉及文件 | 预估复杂度 |
|---|------|---------|-----------|
| 6 | 连接功能修正 | `RuleCanvas.vue` | 中等 |
| 7 | Blender 端口颜色 | `RuleNode.vue` | 简单 |
| 8 | 工具栏重新规划 | `RuleCanvas.vue` | 中等 |
| 9 | 折叠按钮位置 | `RuleCanvas.vue` | 简单 |

### Phase 3: P2 体验优化

| # | 任务 | 涉及文件 | 预估复杂度 |
|---|------|---------|-----------|
| 10 | 控制台拖拽调整高度 | `RuleCanvas.vue` | 中等 |
| 11 | 侧栏收纳宽度适配 | `RuleCanvas.vue` | 中等 |

---

## 验证标准

每次修复完成后，通过以下 checklist 验证：

- [ ] 左侧节点列表可以展开/折叠，刷新页面后状态保持当前画布级别
- [ ] 框选：在画布空白处拖拽出现选择框，松开后选中框内节点
- [ ] 右键菜单：在节点上右键弹出复制/剪切/删除菜单，在空白处右键弹出粘贴/全选菜单
- [ ] 节点圆角不溢出，子元素被正确裁剪
- [ ] Handle 显示在节点左右边框中间位置，鼠标悬浮放大按中心缩放
- [ ] 相同类型端口之间可以连接，不同类型端口拒绝连接并给出 Toast 提示
- [ ] Handle 颜色与其端口类型匹配
- [ ] 工具栏简洁无冗余，功能按钮分组合理
- [ ] 折叠按钮在面板左上方，折叠后面板宽度适配为 48px
- [ ] 控制台面板可拖拽调整高度，有最小/最大限制
- [ ] 面板折叠后，执行日志面板的 left 值随之更新
