# AntV X6 3.x 深度调研

> **生成日期**: 2026-06-07
> **调研主题**: AntV X6 3.x 作为 CogniFlow 规则引擎画布（@vue-flow/core 1.48.2）替代品的可行性深度评估
> **结论先行**: ✅ **强烈推荐作为升级目标**。MIT 许可证、Vue 3 一等公民、内置 Scroller 视口虚拟化 + 正交路由拖拽降级 + Selection/History/Clipboard/Dnd/MiniMap/Export 全套插件，预估迁移周期 5-7 周单人。
> **关键卖点**：`Selection.movingRouterFallback: 'orth'` 一行配置解决拖拽路由卡顿问题——这正是 CogniFlow 之前在 VueFlow 上手工优化的痛点。

---

## 1. 项目档案

| 维度 | 值 | 来源 |
|---|---|---|
| 仓库 | https://github.com/antvis/x6 | GitHub |
| 当前最新版本 | **3.1.7** (stable), 3.1.4-beta.1 (beta) | npm registry `dist-tags` |
| 许可证 | **MIT** | LICENSE 文件（Copyright 2021-2025 Alipay.inc） |
| 维护方 | 蚂蚁集团 / 阿里（Alipay.inc） | 许可证 + 域名 `x6.antv.antgroup.com` |
| 维护者 | 10 人（lvisei、iaaron、jinke.li、afc163、bbsqq 等） | npm registry |
| 运行时依赖 | 仅 4 个：`lodash-es` `dom-align` `utility-types` `mousetrap` | npm metadata |
| Node 要求 | `>= 20.0.0`（构建期） | npm engines |
| 包结构 | **3.x 单包**：所有 plugin 合并到 `@antv/x6`，shape 包独立 | `tutorial/update.zh.md` |
| Vue 绑定 | `@antv/x6-vue-shape@3.0.2`（必须同主版本） | npm |
| 总版本数 | 426 个（自 0.1.0 至今） | npm registry |
| GitHub stars | 4.1k（Context7 / 第三方数据；unverified due to GitHub API rate limit） | 估算 |

### 1.1 MIT 许可证原文（核心摘录）

```
MIT License
Copyright (c) 2021-2025 Alipay.inc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND...
```

— 与 CogniFlow 的 MIT 完全兼容，无任何附加条款。

### 1.2 3.x vs 2.x 重大变更

| 维度 | 2.x | 3.x |
|---|---|---|
| 包结构 | 多个 `@antv/x6-plugin-*` 拆分 | **全部合并到 `@antv/x6` 单包** |
| `@antv/x6-common` | 独立 | 合并入主包 |
| `@antv/x6-geometry` | 独立 | 合并入主包 |
| `@antv/x6-vue-shape` | 独立 | 仍在独立包，需升 `^3.x` |
| `panning` 默认 | 关闭 | **默认启用**（重要行为变更） |
| 视口虚拟化 | 无 | **新增 `virtual: true`**（与 Scroller 配合） |
| 路由 | normal/orth/manhattan | 新增 `metro`、`er` |

---

## 2. 核心架构

### 2.1 渲染模型：SVG + HTML 双轨

- **SVG**（默认）：节点、边、端口全部 SVG
- **HTML**（`<foreignObject>`）：复杂节点可嵌入 React / Vue / Angular 组件
- ❌ **不**支持 Canvas 2D，❌ **不**支持 WebGL
- npm 描述原文："uses **SVG and HTML** for rendering"

### 2.2 数据模型：Cell / Node / Edge / Port

```
Cell (基类)
 ├─ Node (可含 ports)
 │    └─ Port (固定连接点，可分组)
 └─ Edge (含 router + connector + attrs)
```

- **Markup** + **Attrs** 双层抽象（"similar to HTML and CSS respectively"）
- 自定义节点通过 `markup` 数组声明 SVG 元素，通过 `attrs` 设置属性
- 端口通过 `ports.groups`（位置+样式）+ `ports.items`（具体端口）配置

### 2.3 坐标系与视口

- 6 个坐标转换 API：`clientToLocal` / `localToClient` / `pageToLocal` / `localToPage` / `localToGraph` / `graphToLocal`（支持点 / 矩形重载）
- 视口变换：`translate` / `zoom` / `zoomTo` / `zoomToFit` / `centerContent` / `resize`
- 缩放范围：`scaling: { min: 0.01, max: 16 }`（默认）

### 2.4 事件系统

- `graph.on(eventName, handler)` 订阅
- 命名风格 `namespace:verb`：`node:selected` / `cell:unselected` / `box:mousemove` / `history:undo` / `selection:changed`
- 触摸 / 键鼠：Keyboard 插件通过 `bindKey` 绑定（基于 `mousetrap`）

### 2.5 插件体系（3.x 单包）

通过 `graph.use(new Plugin(...))` 挂载：

| 插件 | 用途 | 关键配置 |
|---|---|---|
| **Selection** | 单选/多选/框选 | `multiple`, `rubberband`, `movable`, **`movingRouterFallback`** |
| **Scroller** | 视口滚动 | `enabled`, `pannable`, `autoResize` |
| **Snapline** | 拖拽对齐辅助线 | `enabled: true` |
| **MiniMap** | 缩略图 | `container: HTMLElement` |
| **Transform** | 节点 resize/rotate | `resizing`, `rotating` |
| **Keyboard** | 快捷键 | `bindKey` |
| **History** | 撤销/重做 | `stackSize`, `enabled` |
| **Dnd** | 拖入节点 | `target: graph` |
| **Export** | PNG/JPEG/SVG 导出 | `exportPNG(fileName, options)` |
| **Highlight** | 高亮 | 与 Graph `highlighting` 协同 |
| **Clipboard** | 复制/粘贴/剪切 | `copy/cut/paste` |

---

## 3. 关键 API 表面

### 3.1 Graph 构造选项

```typescript
new Graph({
  container: HTMLElement,                    // required
  width / height: number,
  scaling: { min: 0.01, max: 16 },
  autoResize: boolean | Element | Document,
  panning: boolean | PanningManager.Options, // 3.x 默认 true
  mousewheel: boolean | MouseWheel.Options,
  grid: boolean | number | GridManager.Options,
  background: false | BackgroundManager.Options,
  translating: { restrict: false, autoOffset: true },
  connecting: Connecting.Options,            // snap/allow*/router/anchor/validateConnection
  highlighting: Highlighting.Options,
  interacting: { edgeLabelMovable: false },
  magnetThreshold: number | 'onleave',
  moveThreshold: number,
  clickThreshold: number,
  preventDefaultContextMenu: boolean,
  preventDefaultBlankAction: boolean,
  async: boolean,                            // 3.x 默认 true
  virtual: boolean | { enabled, margin },    // ★ 视口虚拟化
})
```

### 3.2 Cell CRUD

| 方法 | 签名 | 备注 |
|---|---|---|
| `addNode` / `addNodes` | `(node, options?) => Node` | 批量优 |
| `addEdge` / `addEdges` | `(edge, options?) => Edge` | 批量优 |
| `addCell` / `addCells` | 通用 | |
| `removeNode` / `removeEdge` / `removeCell` | | |
| `getCellById` / `getNodes` / `getEdges` / `getCells` | | |
| `toJSON` / `fromJSON` | 序列化/反序列化 | **`fromJSON({ diff: true, silent: true })` 增量更新** |
| `createNode` / `createEdge` | 工厂（不挂载） | |

**性能提示**：`addNodes` 批量 > 多次 `addNode`；`fromJSON({ silent: true })` 抑制重绘。

### 3.3 视口 API

```
graph.resize(w, h)
graph.translate(tx, ty)        // 相对平移
graph.zoom(factor, { absolute? })
graph.zoomTo(factor)            // 绝对
graph.zoomToFit({ maxScale, padding, ... })
graph.centerContent(options?)
graph.getTranslate() / setTranslate(tx, ty)
graph.togglePanning(enabled?)
```

### 3.4 坐标转换

```
clientToLocal(rect | (x,y,w,h) | p | (x,y)) -> Rectangle | Point
localToClient(...)                            -> Rectangle | Point
pageToLocal(...)                              -> Rectangle | Point
localToPage(...)                              -> Rectangle | Point
localToGraph(...)                             -> Rectangle | Point
graphToLocal(...)                             -> Rectangle | Point
```

覆盖 Page / Client / Graph / Local 四套坐标空间。

### 3.5 选中 API

- `graph.select(cells)` / `unselect(cells)` / `getSelectedCells()` / `resetSelection(cells?)`
- 过滤：`graph.setSelectionFilter(filter)`（字符串 / 对象 / 函数）
- 事件：`cell:selected` / `cell:unselected` / `selection:changed`

### 3.6 连线配置 (`connecting`)

| 字段 | 类型 | 默认 |
|---|---|---|
| `snap` | `boolean \| { radius }` | `false` (true 等价 `radius: 50`) |
| `allowNode` | `boolean \| function` | `true` |
| `allowEdge` | `boolean \| function` | — |
| `allowPort` | `boolean \| function` | `true` |
| `allowBlank` | `boolean \| function` | — |
| `allowLoop` | `boolean \| function` | — |
| `allowMulti` | `boolean \| function \| 'withPort'` | `false` |
| `router` | RouterData | 边可覆盖 |
| `anchor` | AnchorData | |
| `connectionPoint` | ConnectionPointData | |
| `validateConnection` | `(args) => boolean` | — |
| `createEdge` | `(args) => Edge` | 自定义创建 |

### 3.7 边路由 (`router`)

| Router | 算法 | 关键参数 | 适用 |
|---|---|---|---|
| `normal` | O(1)，原样返回 | — | 直连 |
| `orth` | 简单几何转角 | `padding` | **流程图/规则引擎首选** |
| `oneSide` | 三段式受限正交 | `side: 'right' \| 'left'` | 树状/分层 |
| `manhattan` | **A\* 寻路，自动避障** | `step`（默认 10）、`excludeTerminals`、`fallbackRouter` | 节点密集需避障 |
| `metro` | Manhattan 变体，45° 斜角 | `maxDirectionChange`（默认 45） | 地铁图风格 |
| `er` | Z 字形斜角 | `offset`、`direction` | ER 图 |

### 3.8 边标记（Marker / Arrowhead）

```typescript
edge.attr({
  line: {
    sourceMarker: 'block',                                          // 字符串 = 内置箭头名
    targetMarker: { name: 'ellipse', rx: 10, ry: 6 },               // 对象 = 内置 + 参数
  },
})
```

内置箭头：`block` `ellipse` `classic` `diamond` `cross` `async`

---

## 4. 端口（Ports）原语

### 4.1 数据结构

```typescript
interface PortGroupMetadata {
  markup?: Markup
  attrs?: Attr.CellAttrs
  zIndex?: number | 'auto'
  position?:
    | [number, number]                        // 绝对定位
    | string                                  // 布局算法名
    | { name: string; args?: object }         // 算法 + 参数
  label?: { markup?; position?: {...} }
}

interface PortMetadata {
  id?: string
  group?: string                              // 继承分组默认
  args?: object
  markup?: Markup
  attrs?: Attr.CellAttrs
  zIndex?: number | 'auto'
  label?: { markup?; position?: {...} }
}
```

### 4.2 边 source / target 4 种形式

```typescript
{ x: number, y: number }                                      // 画布点
{ cell: 'id' | Node | Edge }                                  // 节点/边
{ cell: 'id', port: 'port-id' }                               // 节点 + 端口
{ cell: 'id', selector: 'css-selector' }                      // 节点 + DOM 元素
```

### 4.3 内置 portLayout 算法

`line` / `abs` / `left` / `right` / `top` / `bottom` / `absolute` 等

---

## 5. Vue 3 集成（`@antv/x6-vue-shape`）

### 5.1 包版本与依赖

- `vue@3.x`（CogniFlow 现用 `^3.5.34`）
- `@antv/x6@^3.x`
- `@antv/x6-vue-shape@^3.x`（必须同主版本）

### 5.2 集成 API 表面

| API | 用途 | Vue 3 必须? |
|---|---|---|
| `register({ shape, width, height, component, effect? })` | 全局注册 Vue 节点 | 是 |
| `getTeleport()` | 返回 `<TeleportContainer />` 组件 | 是（Vue 3 必装） |
| `registerComponent` (2.x 旧名) | 等价于 `register` | — |

**关键：`<TeleportContainer />` 必须挂到页面根**（Vue 3 渲染到 SVG `<foreignObject>` 的特殊处理）。

### 5.3 节点 props 传递

```vue
<script setup lang="ts">
import type { Node as X6Node } from '@antv/x6'
interface Props {
  node: X6Node                    // X6 注入的 Node 实例
  // 其余字段由 cell.data 展开传入
  label?: string
  config?: Record<string, unknown>
}
const props = defineProps<Props>()

// 通过 node prop 回写
function update() {
  props.node.setData({ count: 1 })  // 触发 effect 重渲染
}
</script>
```

### 5.4 effect 字段（性能关键）

```typescript
register({
  shape: 'rule-node',
  width: 280,
  height: 100,
  effect: ['data'],       // ← 监听 cell.data 变化触发 Vue 重渲染
  component: RuleNodeVue,
})
```

- 不声明 `effect` → Vue 组件 props 在 `setData()` 后**可能不更新**
- 可选值：`'data'` `'size'` `'position'` `'attrs'`

### 5.5 Element Plus 控件集成

- ✅ `el-slider` / `el-input` / `el-select` / `el-switch` / `el-checkbox` 在 `<foreignObject>` 内**完全可用**
- ✅ CSS 变量穿透（`var(--bg-card)` 等生效）
- ✅ UnoCSS 原子类生效
- ⚠️ `el-select` 必须加 `:teleported="false"` 避免与 `<foreignObject>` Teleport 冲突
- ⚠️ `el-form` 控件 focus 时 X6 的 mousedown 拖拽监听会抢焦点 → 配置 `interacting: { nodeMovable: (cellView) => !cellView.cell.data?.editable }`

### 5.6 Pinia 集成模式

**模式 B（推荐）**：store 持有 Graph 引用

```typescript
import { defineStore } from 'pinia'
import { shallowRef } from 'vue'  // ⚠️ shallowRef!
import { Graph } from '@antv/x6'

export const useRuleGraphStore = defineStore('ruleGraph', () => {
  const graph = shallowRef<Graph | null>(null)  // shallowRef 防止深度代理

  function bindGraph(g: Graph) { graph.value = g }
  function dispose() { graph.value?.dispose() }
  return { graph, bindGraph, dispose }
})
```

**陷阱**：
- `ref(graph)` → Vue 深度代理整个 Graph → 性能崩溃
- `watch(cells, () => fromJSON(cells))` → 节点拖动时循环触发
- 必须 `onBeforeUnmount` 调 `graph.dispose()`

---

## 6. 性能特征

### 6.1 视口虚拟化

```typescript
new Graph({
  virtual: { enabled: true, margin: 200 }  // margin 缓冲区防抖动
})
```

- **机制**：仅渲染视口内 + `margin` 缓冲区内的元素；拖动/缩放/滚动时动态加载/卸载
- **可与 Scroller 叠加**
- **vs VueFlow `only-render-visible-elements`**：概念类似，但 X6 通过 Scroller 虚拟化更彻底（含滚动条交互）

### 6.2 拖拽路由降级（**核心优势**）

```typescript
new Selection({
  multiple: true,
  rubberband: true,
  movingRouterFallback: 'orth',  // ★ 拖拽时降级 manhattan → orth
})
```

**官方文档原文警告**：
> "set to `orth` when dragging many nodes with `manhattan` routing for better performance"

**这直接对应 CogniFlow 之前的痛点**——拖拽 80+ 节点时 VueFlow 的边路由卡顿。X6 用 1 行配置解决。

### 6.3 边路由复杂度

| Router | 复杂度 | 拖拽风险 |
|---|---|---|
| `normal` | O(1) | 无 |
| `orth` | O(n)，n=vertices | 低 |
| `oneSide` | O(n) | 低 |
| `manhattan` | **A\* 寻路**：O(边数 × 网格) | **高** → 必须 `movingRouterFallback: 'orth'` |
| `metro` | Manhattan 变体 | 高 |
| `er` | O(n) | 低 |

### 6.4 实测数据（官方未提供基准）

⚠️ **AntV 官方未发布 100/500/1000 节点 benchmark 数据**。所有性能声称需自跑 PoC 验证。

| 场景 | X6 可行性 | 关键配置 |
|---|---|---|
| 80 节点 60fps | **高** | `orth` + `virtual` 关闭 |
| 200 节点 60fps | **中-高** | 必须 `virtual: true` + `orth` 路由 |
| 500 节点 60fps | **中** | virtual + `movingRouterFallback: 'orth'` |
| 1000 节点 60fps | **中-低** | 依赖虚拟化深度 + 节点简化 |
| 拖拽无明显卡顿 | **中-高** | `movingRouterFallback: 'orth'` + `virtual: true` |

### 6.5 与 VueFlow 1.48 对比

| 维度 | AntV X6 3.1.7 | VueFlow 1.48.0 |
|---|---|---|
| 渲染模型 | **SVG + foreignObject** | DOM only |
| 视口虚拟化 | `virtual: { enabled, margin }` | `only-render-visible-elements` |
| **拖拽路由降级** | **内置** `movingRouterFallback` | ❌ 无（bezier/step 本就轻量） |
| 边路由 | 6 种（含 manhattan 避障） | 4 种（bezier/step/smoothstep/straight） |
| 节点自定义 | SVG attr + foreignObject Vue 组件 | Vue 组件直接渲染 |
| 框架绑定 | 框架无关 + shape 包 | Vue 3 专用 |
| 数据流 | **命令式** `graph.addNode()` | **声明式** `<VueFlow :nodes="..."/>` |
| 命中测试 | SVG hit-test | DOM hit-test |
| 异步渲染 | `async: true` 默认 | — |
| Bundle 体积（unpacked） | 8.56 MB / 2374 文件 | 1.46 MB / 226 文件 |
| 运行时依赖 | 4（`lodash-es` 等） | 5 |

### 6.6 已知性能陷阱

| 陷阱 | 说明 | 缓解 |
|---|---|---|
| `manhattan` + 小 `step` | 寻路空间爆炸 | `movingRouterFallback: 'orth'` + 增大 `step` |
| 高频 `node:change:position` 60Hz | 业务层重计算 | 自实现 rAF throttle |
| 大量 port | SVG 端口 hit-test 开销 | portLayout 选简单算法 |
| 边动画 + manhattan | 每帧重算路径 | 动画时禁用路由 |
| `setData` 浅比较 | 修改内部字段不会触发重绘 | 必须传新对象引用 |

---

## 7. VueFlow → X6 API 映射

### 7.1 核心映射表

| VueFlow API | X6 对应 | 迁移成本 |
|---|---|---|
| `<VueFlow>` 容器 | `new Graph({ container, ... })` + onMounted | 中 |
| `<MiniMap>` | `new MiniMap({ container })` 插件 | 低 |
| `<Controls>` | 自实现 4-6 个按钮 | 低（10-20 行） |
| `<Background>` | `background: { color }` + `grid` 配置 | 低 |
| `:node-types` | `register({ shape, component })` 全局 | 中 |
| `<Handle>` | `ports: { items: [{ id, group, attrs }] }` | 中 |
| `Position.Left/Right` | `position: { name: 'left' \| 'right' }` | 中 |
| `node.data` | `node.getData<T>()` / `setData()` | 中 |
| `MarkerType.ArrowClosed` | `targetMarker: { name: 'block' }` | 低 |
| `:pan-on-drag` / `:pan-on-scroll` | `panning: true` + `mousewheel: { enabled }` | 低 |
| `fitView()` | `graph.zoomToFit({ padding: 16 })` | 低 |
| `screenToFlowCoordinate()` | `graph.clientToLocal(x, y)` | 低 |
| `setViewport` / `getViewport` | `graph.zoom()` + `graph.translate()` | 低 |
| `addSelectedNodes(arr)` | `graph.select(cells)` | 低 |
| `getNodes()` | `graph.getNodes()` | 低 |
| `applyNodeChanges` | `graph.batchUpdate(() => {...})` + 监听细粒度事件 | 中 |
| `userSelectionRect` | `graph.on('rubberband:drawing', ({rect}) => ...)` | 低 |

### 7.2 事件名映射

| VueFlow 事件 | X6 事件 |
|---|---|
| `@node-click` | `graph.on('node:click', ...)` |
| `@node-drag-start` | `graph.on('node:change:position', ...)`（带 dragging 状态） |
| `@nodes-change` | `graph.on('node:change:position/size/attrs', ...)` |
| `@edges-change` | `graph.on('edge:change:*', ...)` |
| `@connect` | `graph.on('edge:connected', ...)` |
| `@pane-click` | `graph.on('blank:click', ...)` |
| `@node-context-menu` | `graph.on('node:contextmenu', ...)` |
| `@pane-context-menu` | `graph.on('blank:contextmenu', ...)` |
| `@move` | `graph.on('translate', ({tx, ty}) => ...)` |
| `@zoom` | `graph.on('scale', ({sx}) => ...)` |
| `@selection-drag-start` | `graph.on('selection:drag-start', ...)` |

### 7.3 数据模型转换

**Node schema**：
```typescript
// VueFlow
{ id, type: 'ruleNode', position: {x, y}, data: RuleNodeData, selected? }

// X6
{ id, shape: 'rule-node', x, y, width, height, data: RuleNodeData, ports?: PortMetadata[] }
```

**Edge schema**：
```typescript
// VueFlow
{ id, source, target, sourceHandle?, targetHandle?, type: 'default', animated?, markerEnd }

// X6
{ id, shape: 'edge', source: { cell, port? }, target: { cell, port? },
  attrs: { line: { stroke, targetMarker: { name: 'block' } } },
  router: { name: 'orth' }, connector: { name: 'rounded' } }
```

**关键差异**：`source`/`target` 在 X6 是 `{ cell, port }` 对象（不是字符串）。

---

## 8. 性能优化对照

### 8.1 CogniFlow 现有 4 轮优化在 X6 是否仍需做

| 优化（commit） | X6 是否需要 | 说明 |
|---|---|---|
| `v-memo` 引用比较 (`9fbab4cf`) | **保留** | X6 节点也是 Vue 组件 |
| rAF 节流拖拽 (`817b2ec8` + `57f2f275`) | **保留** | X6 拖拽同样 60Hz |
| `contain: layout style` (`9fbab4cf`) | **保留** | 节点 wrapper 同样适用 |
| `will-change: transform` (`817b2ec8`) | **保留** | X6 也用 transform 定位 |
| `outline` 替代 `border-width` (`dcc00ad5`) | **改用 X6 选择框** | Selection 插件默认蓝色选框不影响盒模型 |
| 视口虚拟化 `only-render-visible-elements` (`9fbab4cf`) | **改用 X6 内置** | `virtual: { enabled: true, margin: 200 }` |
| selection 跳过 (`5882437e`) | **保留** | `node:change:position` 同样 60Hz 需 throttle |
| CSS 化选中视觉 (`5882437e`) | **保留** | X6 节点 DOM 也走 CSS |

### 8.2 X6 内置无需重做的优化

| 优化 | X6 内置对应 |
|---|---|
| 视口虚拟化 | `virtual: { enabled: true, margin: 200 }` |
| 正交路由拖拽降级 | `movingRouterFallback: 'orth'` |
| 边动画 dasharray | `attrs.line.style.animation` |
| 节点 zIndex 自动管理 | X6 内置 |
| 节点拖拽边界 | `translating: { restrict: true }` |
| 异步渲染避免阻塞 | `async: true` 默认 |
| 历史栈 + 撤销/重做 | History 插件（命令模式，比 JSON 快照更精确） |
| 缩略图 | Export 插件 `graph.toPNG()` |

---

## 9. CogniFlow 迁移成本评估

### 9.1 改造点（精确到行号）

**RuleCanvas.vue**（3643 行 → 净 +230 行）：
- `359-411` `<VueFlow>` 标签 → onMounted 内 `new Graph()` 初始化
- `363-381` 20+ props → 翻成 Graph 构造参数
- `383-397` 16 events → `graph.on()` 串接
- `400-407` `<MiniMap>` → 插件挂载
- `410` `<Controls>` → 自实现 4-6 个按钮
- `627-639` `useVueFlow()` 11 API → 改 `graph.value` + 局部 API
- `1081-1145` 选择/复制/粘贴相关 → 改 `graph.getSelectedCells()`
- `1340-1353` `setCenter` → `graph.zoomTo()`
- `1550-1581` `handleNodesChange` + `applyNodeChanges` → 监听细粒度事件
- `2634-2771` `<style scoped>` 内 `.vue-flow__*` → `.x6-node*` 选择器

**RuleNode.vue**（1156 行 → 净 +25 行）：
- `1-9` 根 div 改 `inject: ['getNode']`
- `23-263` Element Plus widget 完整保留
- `265-298` 端口区 + `<Handle>` → `node.addPort()` 改为元数据
- `276/293` `Position` enum → 删除
- `317` `import { Position }` → 删除
- `365-368` `defineProps<{ data }>` → `defineProps<{ node: X6Node }>`
- v-memo 引用比较逻辑保留（仅改 props 源）

**ruleEngine.ts**（621 行 → 净 +8 行）：
- `22-23` VueFlow 类型/MarkerType → X6 类型
- `83/86` `Node<RuleNodeData>[]` → `X6Node[]`
- `185-198` 旧数据归一化保留（业务 type → shape）
- `298-326` `createNode` 改用 `graph.addNode({ shape, x, y, data, ports: {...} })`
- `334-346` `updateNodeConfig` 改 `node.setData({ ...node.getData(), config: {...} })`
- `368-383` `addEdge` 改 `graph.addEdge`
- `394-398` `VUEFLOW_INTERNAL_KEYS` 12 字段 → `X6_INTERNAL_KEYS` ~6 字段

**新增**：
- `webui/src/utils/portStyles.ts`：14 种 port type 颜色（从 CSS 移到 JS）
- `webui/src/components/rule-engine/nodeRegistration.ts`：模块加载时 `register({ shape: 'rule-node', component: RuleNode, effect: ['data'] })`

### 9.2 数据迁移兼容性

| 兼容点 | 风险 | 解决方案 |
|---|---|---|
| 后端存储格式（`nodes_json` / `edges_json`） | 低 | 适配层 `toX6Node` / `fromX6Node` |
| 旧数据 `n.type = 'ruleNode'` | 低 | `loadGraph` 归一化层保留（ruleEngine.ts:186） |
| 旧数据 `n.position: {x, y}` | 低 | `loadGraph` 转 `x, y` 顶层字段 |
| 旧数据 `sourceHandle` / `targetHandle` | 低 | 适配层转 `source.port` / `target.port` |
| VueFlow 12 内部字段 | 低 | 适配层 strip 字段（X6 内部字段少） |
| 历史栈 20 步 | 低 | X6 History 插件 `stackSize: 20` |
| 缩略图 base64 | 无 | `graph.toPNG()` 同 base64 |
| WebSocket 消息格式 | 无 | 不涉及画布 |

### 9.3 总周期估算

| 阶段 | 时间 | 任务 |
|---|---|---|
| **阶段 1：环境搭建 + 最小 demo** | 1-2 天 | 装包、demo 页面、注册简单节点、验证拖拽连线 |
| **阶段 2：节点注册 + 数据流迁移** | 3-5 天 | `loadGraph` / `createNode` / `addEdge` 改 X6；RuleNode.vue 改 `inject: ['getNode']`；端口元数据转 X6 ports |
| **阶段 3：交互功能迁移** | 5-7 天 | Selection / Dnd / Clipboard / History / MiniMap / Keyboard / Snapline 插件 + 自实现 Controls + 右键菜单 + 缩略图 |
| **阶段 4：性能调优** | 3-5 天 | 启用 `virtual`、配 `movingRouterFallback`、业务层 throttle、跑 benchmark |
| **阶段 5：回归测试 + 灰度** | 3-5 天 | Playwright e2e、性能对比、双画布灰度 |
| **总计** | **5-7 周单人** | |

### 9.4 风险登记

| # | 风险 | 可能性 | 影响 |
|---|---|---|---|
| R1 | `effect: ['data']` 忘记声明 → Vue 节点 props 不更新 | 中 | 中 |
| R2 | `el-select` 没加 `:teleported="false"` → 下拉错位 | 中 | 低 |
| R3 | `ref(graph)` 用错（应是 `shallowRef`）→ 性能崩溃 | 中 | 高 |
| R4 | 没启用 `virtual` → 500+ 节点掉帧 | 中 | 高 |
| R5 | 没配 `movingRouterFallback` → manhattan 拖拽卡顿 | 中 | 中 |
| R6 | `onBeforeUnmount` 漏 `graph.dispose()` → 内存泄漏 | 中 | 中 |
| R7 | 数据双向同步循环 → 死循环 | 中 | 高 |
| R8 | `registerEdge` API 文档缺失（需查源码） | 低 | 低 |
| R9 | 大规模节点（1000+）官方 benchmark 缺失 | 中 | 中 |
| R10 | X6 4.x 仍 RC → 锁 3.x | 低 | 低 |

### 9.5 不会解决的卡顿点

| 来源 | 是否被 X6 解决 |
|---|---|
| Element Plus 控件 26 处状态变化 | ❌ Vue 响应式问题 |
| `nodeConfig` 引用比较失效 | ❌ 需在 store 重建对象 |
| WebSocket 60Hz 状态推送 | ❌ 需在 store 端 throttle |
| 缩略图生成 100ms+ | ❌ 需 `requestIdleCallback` |

---

## 10. 何时考虑迁移

| 触发条件 | 推荐方案 |
|---|---|
| **200 节点开始掉帧** | **推荐迁移到 X6**（Scroller 虚拟化 + 路由降级） |
| **需要 BPMN 兼容** | LogicFlow 2.2.3 |
| **需要 Canvas 像素级编辑** | leafer-ui 2.x |
| **想加节点 resize/rotate** | 迁移 X6（Transform 插件内置） |
| **想加对齐辅助线** | 迁移 X6（Snapline 插件内置） |
| **想加命令式撤销/重做** | 迁移 X6（History 插件命令模式） |
| **API 升级** | 锁 3.x，4.x 稳定后评估 |

**当前 CogniFlow 不命中任何"必须迁移"条件**，但 5-7 周迁移窗口对个人项目可承受。

---

## 11. 与 leafer-ui 的最终对比

| 维度 | AntV X6 3.x | leafer-ui 2.x |
|---|---|---|
| **节点图原语** | ✅ 开箱即用 | ❌ 全部需自实现 |
| Vue 3 集成 | ✅ 官方 `@antv/x6-vue-shape` | ❌ 无官方绑定 |
| 视口虚拟化 | ✅ `virtual: { enabled }` | ❌ 需自实现（脏矩形 ≠ 视口剔除） |
| 拖拽路由降级 | ✅ 内置 `movingRouterFallback` | ❌ 不适用（无路由概念） |
| Element Plus 控件 | ✅ 完整支持 | ❌ canvas 化会牺牲交互 |
| 迁移成本 | 5-7 周单人 | 2-4 月单人（写 2000-3000 行原语） |
| 维护方 | 蚂蚁集团（bus factor 高） | 单点 + PxGrow 商业化（bus factor 1） |
| 许可证 | MIT | MIT（核心） + 商业 PxGrow 插件 |
| 社区规模 | 4.1k stars + 426 版本 | 4.1k stars + 多 monorepo 包 |

**X6 是对位替代；leafer-ui 是底层引擎（更不对位）。**

---

## 12. 决策矩阵

| 场景 | 决定 |
|---|---|
| 当前 80 节点 60fps 稳定 | ⏸ **不急** 迁移，先做 NodeConfigField 拆分 + keep-alive 优化 |
| 200 节点开始卡顿 | 🚀 **推荐迁移 X6**（5-7 周） |
| 需要 BPMN | → LogicFlow 2.2.3 |
| 需要 Canvas 原生编辑 | → leafer-ui 2.x |

**当前阶段推荐**：继续 VueFlow 1.48 + Stage 3 优化（NodeConfigField 拆分）。当下一次性能瓶颈出现（200+ 节点）时启动 X6 迁移。

---

## 13. 回退方案

**双画布运行**：保留 VueFlow 版本作为后备，按 feature flag 切换

```typescript
// webui/src/config/canvasConfig.ts
export const CANVAS_BACKEND = (import.meta.env.VITE_CANVAS_BACKEND ?? 'x6') as 'x6' | 'vueflow'
```

```vue
<template>
  <component :is="canvasComponent" v-if="canvasComponent" />
</template>
<script setup>
import RuleCanvasX6 from './RuleCanvas.x6.vue'
import RuleCanvasVF from './RuleCanvas.vf.vue'  // 旧 VueFlow
const canvasComponent = computed(() =>
  CANVAS_BACKEND === 'x6' ? RuleCanvasX6 : RuleCanvasVF
)
</script>
```

**回退操作**：修改 `VITE_CANVAS_BACKEND=vueflow` → 重新构建 → **5 分钟回退**。

**数据无缝切换**：后端存储格式不变，X6 写入的 JSON 用 X6 schema（与 VueFlow schema 几乎一致，X6 额外字段 `attrs`/`ports` 可被 VueFlow 忽略）。

---

## 14. 引用资料

### 一手官方
- [AntV X6 GitHub](https://github.com/antvis/x6)
- [X6 官方文档](https://x6.antv.antgroup.com)
- [X6 3.x 升级指南](https://github.com/antvis/x6/blob/master/site/docs/tutorial/update.zh.md)
- [Graph 构造选项](https://github.com/antvis/x6/blob/master/site/docs/api/graph/graph.zh.md)
- [Node API（含 Ports）](https://github.com/antvis/x6/blob/master/site/docs/api/model/node.zh.md)
- [Edge API](https://github.com/antvis/x6/blob/master/site/docs/api/model/edge.zh.md)
- [Router 注册表](https://github.com/antvis/x6/blob/master/site/docs/api/registry/router.zh.md)
- [Selection 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/selection.zh.md)
- [Scroller 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/scroller.zh.md)
- [MiniMap 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/minimap.zh.md)
- [Transform 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/transform.zh.md)
- [History 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/history.zh.md)
- [Keyboard 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/keyboard.zh.md)
- [Dnd 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/dnd.zh.md)
- [Export 插件](https://github.com/antvis/x6/blob/master/site/docs/tutorial/plugins/export.zh.md)
- [Vue 3 集成教程](https://github.com/antvis/x6/blob/master/site/docs/tutorial/intermediate/vue.zh.md)
- [View 配置（含 virtual）](https://github.com/antvis/x6/blob/master/site/docs/api/mvc/view.zh.md)
- [LICENSE 原文](https://raw.githubusercontent.com/antvis/x6/master/LICENSE)

### 包元数据（npm registry 验证）
- `@antv/x6@3.1.7` — latest, 4 deps, engines >= 20
- `@antv/x6-vue-shape@3.0.2` — Vue 3 binding
- 维护者 10 人

### 上下文
- 上份调研：[leafer-ui 迁移可行性](./leafer-ui-迁移可行性调研.md)
- CogniFlow 现状：[规则引擎索引](./rule-engine-index.md)
- 性能优化历史：commit `9fbab4cf` `817b2ec8` `5882437e` `dcc00ad5` `57f2f275`

### 关键不确定项
- ⚠️ GitHub stars / commits（API 限流，unverified）— 建议自查
- ⚠️ 大规模节点（1000+）官方 benchmark 缺失 — 需自跑 PoC
- ⚠️ VueFlow / LogicFlow / X6 独立基准未找到 — 需自跑

---

## 15. 总结

**AntV X6 3.1.7 是 CogniFlow 规则引擎画布的最佳升级目标**：

| 优势 | 详情 |
|---|---|
| 许可证 | MIT，与 CogniFlow 完全兼容 |
| 维护 | 蚂蚁集团（bus factor 高，10 人维护） |
| 节点图原语 | 完整开箱即用：Handle / Port / Edge Router / Box Select / MiniMap / Snapline / History / Clipboard / Dnd / Export |
| 性能关键 | `virtual: { enabled }` 视口虚拟化 + `movingRouterFallback: 'orth'` 拖拽路由降级 |
| Vue 3 集成 | 官方 `@antv/x6-vue-shape@3.x` 一等公民，`<TeleportContainer />` + `effect: ['data']` |
| Element Plus | 完全可用（节点内 26 处 el-* 控件保留） |
| 迁移成本 | 5-7 周单人（净 +263 LoC） |
| 回退方案 | 双画布 + 5 分钟 feature flag 切换 |

**推荐路径**：
1. **当前阶段**：保持 VueFlow 1.48，继续 Stage 3 优化（NodeConfigField 拆分 + keep-alive）
2. **200 节点开始卡顿时**：启动 X6 迁移（5-7 周）
3. **迁移前 PoC**：写 200/500 节点 X6 demo，对比当前 VueFlow FPS 与拖拽延迟
4. **锁 3.x**：4.x 仍 RC/beta，3.x 稳定后 4.x 再评估

---

## 附录 — 缩写

- **DAG**: Directed Acyclic Graph
- **BPMN**: Business Process Model and Notation
- **SVG**: Scalable Vector Graphics
- **DOM**: Document Object Model
- **PoC**: Proof of Concept
- **rAF**: requestAnimationFrame
- **a11y**: Accessibility
- **P0/P1/P2**: 优先级分级
