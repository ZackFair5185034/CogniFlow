# VueFlow 使用边界 (CogniFlow 规则画布)

**最后更新**: 2026-06-13
**目的**: 新人 onboarding / 决策依据 —— "我们要改 VueFlow X 能力, 是改 fork 还是业务侧?"

---

## 1. 一句话总结

> **VueFlow 做数据壳 + 渲染容器** (~5%)
> **业务侧自研交互/性能层** (~95%)
> **改 fork** 仅限 2 个文件 (`useDrag.ts` + `Pane.vue`), 仅限 "拖动/框选期 0 响应式写入" 类性能需求

---

## 2. VueFlow 官方能力矩阵 (CogniFlow 实装)

| 能力 | VueFlow 默认 | CogniFlow 实装 | 自研度 | 备注 |
|---|---|---|---|---|
| **数据模型** Node / Edge | ✅ 官方 | ✅ 直接用 | 0% | 类型从 `@vue-flow/core` 导入 |
| **主容器** `<VueFlow>` | ✅ 官方 | ✅ 直接用 | 0% | background/controls/minimap 走子包 |
| **背景** Background | ✅ 官方 | ✅ 用 npm 包 | 0% | `@vue-flow/background` |
| **控件** Controls | ✅ 官方 | ✅ 用 npm 包 | 0% | `@vue-flow/controls` |
| **缩略图** Minimap | ✅ 官方 | ✅ 用 npm 包 | 0% | `@vue-flow/minimap` |
| **节点 wrapper** NodeWrapper | ✅ 官方 | ✅ 用 + 自定义壳 | 30% | `RuleNode.vue` 是节点壳 |
| **端口 Handle** | ✅ 官方 | ✅ 直接用 | 0% | `:handle-id` / `:is-connectable` |
| **边渲染** EdgeWrapper | ✅ 官方 | ✅ 直接用 | 0% | 默认贝塞尔边 |
| **边路径计算** getEdges | ✅ 官方 | ⚠️ **拖动期被自研接管** | **70%** | 详见 §4 |
| **节点拖动** useDrag | ✅ 官方 | ❌ **关掉, 自研** | **100%** | `nodes-draggable="false"` + `useCogniFlowDrag` |
| **框选** Pane UserSelection | ✅ 官方 | ❌ **自研覆盖** | **100%** | `customSelectionRect` + `handleSelectionEnd` |
| **选中状态** reactive nodes | ✅ 官方 | ✅ **用官方 API** | 50% | `addSelectedNodes/removeSelectedNodes` (Phase 19.7+) |
| **键盘事件** useKeyPress | ✅ 官方 | ✅ 用 + 业务侧 ref 同步 | 30% | 抄一份 `multiSelectKeyPressed` 不用 @vueuse |
| **缩放/平移** useZoom / usePan | ✅ 官方 | ✅ 直接用 | 0% | 通过 `getViewport()` |
| **坐标转换** screenToFlowCoordinate | ✅ 官方 | ✅ 直接用 | 0% | `getSelectedNodes().map` + 屏幕坐标 |
| **A11y** A11yDescriptions | ✅ 官方 | ❌ **关掉** | 100% | 性能 + 规则图不需要 |
| **CSS theme** | ✅ 官方 | ✅ 引用默认 | 0% | `@vue-flow/core/dist/theme-default.css` |

---

## 3. 我们用 VueFlow 的"原因" (即不要改这些的理由)

| 能力 | 不用自研的原因 |
|---|---|
| 数据模型 | VueFlow Node/Edge 类型已对齐, 自研要重写类型 + 序列化 |
| 主容器 | 缩放/平移/坐标系 + CSS transform + 性能优化是 VueFlow 核心, 重写易出 bug |
| 端口 Handle | 拖拽连线 + 命中检测 + 视觉反馈全包, 自研要 200+ LOC |
| 边渲染 | SVG path + 贝塞尔算法 + 边文字 + 端点位置, 自研要 300+ LOC |
| 缩略图 | minimap 坐标系跟主画布同步 + 当前视口框 + 节点 hitbox, 自研要 400+ LOC |
| 缩放/平移 | 滚轮缩放/拖拽平移/边界限制/动画, VueFlow useZoom 写得很好, 自研反而糙 |

---

## 4. 我们"自研"或"改 fork"的原因 (即改这些的理由)

### 4.1 自研 (业务侧 composables)

| 自研点 | 原因 | 文件 |
|---|---|---|
| 节点拖动 | VueFlow useDrag 走 useVModel 响应式, 触发整图 vdom diff, 50 节点掉帧 | `useCogniFlowDrag.ts` (359 LOC) |
| 拖动期边路径 | VueFlow getEdges 整图 O(E) 重算, 80 边时拖动卡顿 | `useEdgePathUpdater.ts` (207 LOC) |
| 框选 | VueFlow Pane onPointerMove 60Hz 跑 getNodesInside O(N) | `RuleCanvas.vue customSelectionRect` (200 LOC) |
| 选中状态 | VueFlow reactive selected 走 shallowRef 死路, 自研走 addSelectedNodes API | Phase 19.7+ 全部 |
| LOD (节点分级) | VueFlow 根本无此概念 | `store.ruleEngine.lodLevelMap` (100 LOC) |
| 节点内嵌配置 | VueFlow 默认节点只显示, 无内嵌表单能力 | `NodeConfigEditor.vue` (848 LOC) |
| 节点折叠 | VueFlow 无折叠概念 | `RuleNode.vue node-collapse-btn` |
| 右键菜单 | VueFlow 无右键菜单 | `RuleCanvas.vue contextMenu` |
| 复制/粘贴 | VueFlow 无剪贴板 | `RuleCanvas.vue clipboard` |

### 4.2 改 fork 源码 (上游 vue-flow 包内)

| fork 改动 | commit | 文件 | 业务原因 |
|---|---|---|---|
| 拖动期跳过 nodesChange | `7ef52400` | `useDrag.ts` | 拖动期 0 响应式写入 (50 节点 60fps 红线) |
| 框选期跳过 getNodesInside | `381d832b` | `Pane.vue` | 框选期 0 响应式写入 |
| 框选结束不再重复计算 | `b359907a` | `Pane.vue` | 修 381d832b 引入的框选结束双跑命中 |

**核心判断标准**: **"在 60fps 拖动期间能不能避免响应式写入"** —— VueFlow 默认做不到, 必须改 fork。

---

## 5. 决策树: 新需求落到哪里?

```
业务需求 X
  │
  ├─ A. "用 VueFlow API 就能做" ──── → 业务侧直接用, 0 fork 改动
  │     例子: addSelectedNodes, screenToFlowCoordinate
  │
  ├─ B. "业务侧自研能解决" ──────── → 业务侧 composable, 0 fork 改动
  │     例子: 自研拖动, 自研框选, 自研 LOD
  │
  ├─ C. "需要 VueFlow 内部行为改" ── → **走 fork 改源码流程**
  │     例子: 拖动期跳过 nodesChange, 框选期跳过 getNodesInside
  │
  └─ D. "VueFlow 根本不支持" ─────── → 评估: 提 PR 给上游 / 业务侧完全自研
        例子: 3D 节点, 新边类型 (VueFlow 当前只支持 bezier/straight/smoothstep)
```

**90% 需求在 A/B 解决, ~8% 在 C, ~2% 在 D**。

---

## 6. 改 fork vs 业务侧的边界 (具体判断)

| 场景 | 改 fork | 业务侧 | 理由 |
|---|---|---|---|
| 拖动期 0 响应式写入 | ✅ | ❌ | VueFlow useDrag 内部 useVModel 链路, 应用层拦不住 |
| 框选期 0 响应式写入 | ✅ | ❌ | Pane.vue 内部 onPointerMove 60Hz, 必须改源码 |
| 拖动期增量更新边路径 | ❌ | ✅ | VueFlow 暴露的 `flowNode.position` reactive 可以在业务侧劫持, 不需要改上游 |
| 选中状态管理 | ❌ | ✅ | VueFlow 提供 addSelectedNodes/removeSelectedNodes, 业务侧调用即可 |
| 节点 LOD | ❌ | ✅ | VueFlow 无此概念, 完全业务侧自研 |
| 节点内嵌表单 | ❌ | ✅ | 业务侧组件, 跟 VueFlow 数据模型解耦 |

---

## 7. 反哺上游策略 (理想状态)

每次改 fork 源码, 在 commit message 里加 "**是否可反哺上游**":

| 我们的改动 | 反哺价值 | 上游是否接受 |
|---|---|---|
| 拖动期跳过 nodesChange (useDrag.ts 第 4 参数) | **高** —— 所有用 VueFlow 的项目都受益 | 需提 PR, 上游可能有不同意见 (破坏响应式契约) |
| 框选期跳过 getNodesInside (Pane.vue) | **高** | 同上, 需要默认行为 + 可选 opt-out |

**反哺好处**:
- 减少 fork 维护负担
- 上游 review 帮我们发现边界 bug
- 社区贡献提升项目声誉

**反哺难处**:
- VueFlow 维护节奏我们不可控
- 上游接受周期可能很长 (数月)
- 短期内我们要一直维护 fork 同步

**当前策略**: **不主动反哺**, 等 fork 累积到 10+ commit 时统一评估。

---

## 8. 关键文件 (新人必读)

| 文件 | LOC | 看点 |
|---|---|---|
| `webui/src/composables/useCogniFlowDrag.ts` | 359 | **d3-drag 拖动**实现 + 事件委托 + rAF 节流 |
| `webui/src/composables/useEdgePathUpdater.ts` | 207 | 拖动期边路径 O(incident_edges) 增量更新 |
| `webui/src/views/RuleCanvas.vue` | 4246 | 主画布 (含自研框选 + 选中 + 菜单) |
| `webui/src/stores/ruleEngine.ts` | 1148 | Pinia store (含 lodLevelMap + 多选 + 历史) |
| `webui/src/components/rule-engine/RuleNode.vue` | 601 | 节点壳 (LOD + 折叠 + 端口) |
| `webui/src/components/rule-engine/NodeConfigEditor.vue` | 848 | 节点内嵌配置 (老大期望方向: 替代右栏) |
| `/home/wanglei/vue-flow/packages/core/src/composables/useDrag.ts` | ~150 | **fork 改动 1**: 拖动期跳过 nodesChange |
| `/home/wanglei/vue-flow/packages/core/src/container/Pane/Pane.vue` | ~400 | **fork 改动 2**: 框选期跳过 getNodesInside |

---

## 9. 性能红线 (commit 钉死)

**commit `817b2ec8` + `c190997e` 钉死的硬指标**:
- 50 节点拖动 **60fps** (Chrome DevTools Performance 实测)
- 拖动期 0 次响应式写入
- 不允许 `transition: all` / 节点壳 width transition
- 50 节点全图 vdom diff ≤ 16ms

**任何新功能都先回答**: "50 节点场景下, 这个功能是否破坏 60fps?"

---

## 10. 未来演进 (不立即做, 等老大拍)

| 选项 | 工作量 | 价值 | 建议 |
|---|---|---|---|
| 把 `file:/home/wanglei/...` 改成 `git+ssh://github.com:ZackFair5185034/vue-flow.git#master` | 1 天 | 高 (团队 onboarding + CI 友好) | ⭐ 建议做 |
| 反哺 fork 改动给 VueFlow 上游 (PR) | 5+ 天 | 中 (长期减负) | 等 fork 累积 10+ commit 再评估 |
| 升级 VueFlow 到 1.50+ (rebase fork 自定义 commit) | 3-5 天 | 中 (上游 bug fix) | 季度评估 |
| 完全去掉 VueFlow + d3-drag | 6-8 周 | **不划算** | ❌ 不建议 |
