# VueFlow Fork 改源码工作流

**最后更新**: 2026-06-13
**适用范围**: CogniFlow 规则画布 + 所有用 `@vue-flow/core` 业务项目
**核心原则**: 业务需求 → 优先用 VueFlow 官方 API / 自研应用层 / 自研插件解决，**最后才改 VueFlow 上游源码**

---

## 1. 仓库位置

| 仓库 | URL | 路径 |
|---|---|---|
| **VueFlow fork** | `git@github.com:ZackFair5185034/vue-flow.git` | `/home/wanglei/vue-flow/` |
| **CogniFlow 业务** | `git@github.com:ZackFair5185034/CogniFlow.git` | `/home/coding/PRIVATE_WORKSPACE/CogniFlow/` |

**重要**: `webui/package.json` 里 `@vue-flow/core` 是 `file:/home/wanglei/vue-flow/packages/core` —— 引用本地副本，**改完 fork 必须重新 `pnpm install` 让 pnpm 重新 link dist**。

---

## 2. 当前 fork 状态

| 项 | 值 |
|---|---|
| 上游基础版本 | `@vue-flow/core@1.48` (`52a03012 chore: bump versions`) |
| 自定义 commit 数 | **5** 个 perf/fix（master 分支） |
| 改的源码文件 | 仅 2 个:<br>① `packages/core/src/composables/useDrag.ts`<br>② `packages/core/src/container/Pane/Pane.vue` |
| 累积的 dist commit | 2 个（`c543f622` `307784ea`）—— **每个 src 改动都配 build commit 同步 dist** |

### 5 个自定义 commit 全清单

| Commit | 类型 | 改了啥 | 业务原因 |
|---|---|---|---|
| `7ef52400` | perf | `useDrag.ts` 拖拽过程跳过 nodesChange 触发 | **拖动期 0 响应式写入**（50 节点 60fps 红线） |
| `381d832b` | perf | `Pane.vue` 框选过程跳过 O(N) getNodesInside | **框选期 0 响应式写入** |
| `b359907a` | fix | `Pane.vue` 框选结束不再重复计算 | 修 381d832b 引入的框选结束双跑命中 |
| `421cd33c` | fix | 恢复 7ef52400 + useDrag.ts 第 4 参数 | 上游某次变动回退了我们的优化 |
| `9e7a718f` | fix | Pane.vue 末尾逗号 | type-check |

---

## 3. 何时改 fork 源码 (决策树)

```
有业务需求 X
  │
  ├─ 1. VueFlow 官方 API 能解决? ──── 是 → 用官方 API (committed in 业务仓库)
  │                                    │
  │                                    否 ↓
  │
  ├─ 2. 业务侧自研 (应用层) 能解决? ── 是 → 业务仓库 (committed in 业务仓库)
  │       (composables / 自研组件)     │
  │                                    否 ↓
  │
  ├─ 3. VueFlow 插件机制能解决? ────── 是 → 业务仓库 (vue-flow plugin)
  │       (useVueFlow 提供扩展点)      │
  │                                    否 ↓
  │
  └─ 4. 只能改 VueFlow 上游源码 ────── 是 → 走 fork 工作流 (本文档 §4)
         (内部数据结构 / 不可扩展点)
```

**原则**: 90% 的需求在前 3 步解决。**只有 5% 不到的"内部行为优化"才改 fork**。

### 决策判断标准

| 改动类型 | 走哪条路 | 例子 |
|---|---|---|
| 新增/调整 selected 行为 | 业务侧（应用层） | ✅ 已用 `addSelectedNodes/removeSelectedNodes` |
| 自定义拖动逻辑 | 业务侧（d3-drag + 自研 composable） | ✅ 已用 `useCogniFlowDrag` |
| 自定义框选 | 业务侧（自研 `customSelectionRect`） | ✅ 已用 `RuleCanvas.vue handleSelectionEnd` |
| LOD / 节点分级 | 业务侧（自研） | ✅ 已用 `store.lodLevelMap` |
| **拖动期跳过响应式写入** | **fork 源码** | ✅ `7ef52400 useDrag.ts` |
| **框选期跳过 O(N) 计算** | **fork 源码** | ✅ `381d832b Pane.vue` |
| 新增 props / events | 提 PR 给 VueFlow 上游（不通过 fork） | - |

---

## 4. 改 fork 源码的标准流程

### 4.1 前置检查

```bash
# 1. 确认上游无更新
cd /home/wanglei/vue-flow
git fetch upstream  # 如果配了 upstream（见 §5）
git log HEAD..upstream/master --oneline

# 2. 确认本地无未提交改动
git status
```

### 4.2 创建工作分支

```bash
cd /home/wanglei/vue-flow

# 基于 master 创建 fix/feat 分支
git checkout -b fix/cogniflow-<简短描述>
# 例: fix/cogniflow-pane-selection-on-drag-fix
```

### 4.3 改源码 + 自测

**只改 src/**:
- `packages/core/src/composables/useDrag.ts`
- `packages/core/src/container/Pane/Pane.vue`
- 或其他必要时

**改完跑 lint + type-check**:
```bash
cd /home/wanglei/vue-flow
pnpm install  # 第一次或依赖变时
pnpm --filter @vue-flow/core typecheck
pnpm --filter @vue-flow/core lint
```

### 4.4 改业务侧适配

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui

# 业务侧可能需要适配新行为 (例: 新增 props / 改事件签名)
# 改完跑三件套
pnpm vue-tsc --noEmit
pnpm build
pnpm vitest run

# 跑后端测试 (如果改了影响 BFS 拓扑)
cd ..
python -m pytest backend/tests/test_rule_engine/
```

### 4.5 浏览器实测 (50 节点 60fps 红线)

```bash
# 启动 webui
cd webui && pnpm dev

# 浏览器打开 50 节点示例图
# 实测:
# 1. 拖动流畅度 (Chrome DevTools Performance 面板录制)
# 2. 框选响应
# 3. 选中交互
# 4. 所有原有功能未破坏
```

### 4.6 构建 + 提交 dist (★ 关键)

**VueFlow 是 monorepo + 提供 dist 产物给业务**:
```bash
cd /home/wanglei/vue-flow
pnpm --filter @vue-flow/core build
```

**build 后 dist 变化**:
- `packages/core/dist/vue-flow-core.js`
- `packages/core/dist/vue-flow-core.mjs`
- `packages/core/dist/vue-flow-core.iife.js`
- (其他 .d.ts 不会变)

**提交两步走 (分两个 commit)**:
```bash
# 1. 源码 commit
git add packages/core/src/
git commit -m "perf|fix(scope): 业务需求描述

根因:
- 旧版 X 行为导致 Y 问题

修复:
- 改 Z 文件 W 行

业务侧:
- 触发场景: [业务需求链接/描述]
- 性能影响: [50 节点拖动 fps / 框选响应时间]
- 回归测试: 业务仓库三件套 + 浏览器实测 50 节点 60fps"

# 2. dist commit (紧跟源码)
git add packages/core/dist/
git commit -m "build(core): 重新构建 dist 反映 [上一 commit 简述]"
```

### 4.7 业务侧 link 新 fork

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui

# file: 引用会跟随本地路径变化, 重装即可
pnpm install

# 验证 dist 已更新
ls -la node_modules/@vue-flow/core/dist/vue-flow-core.js
md5sum /home/wanglei/vue-flow/packages/core/dist/vue-flow-core.js \
       node_modules/@vue-flow/core/dist/vue-flow-core.js
# 两个 hash 必须一致

# 跑三件套
pnpm vue-tsc --noEmit
pnpm build
pnpm vitest run
```

### 4.8 推送 + 提 PR (可选)

```bash
cd /home/wanglei/vue-flow
git push origin fix/cogniflow-<简短描述>

# 提 PR 到 master
gh pr create --base master --title "fix/cogniflow-..." --body "..."
```

**或者直接 merge 到 master** (小改动走 fast-forward):
```bash
git checkout master
git merge --ff-only fix/cogniflow-<简短描述>
git push origin master
```

---

## 5. 升 VueFlow 上游 (同步新版本)

### 5.1 配置 upstream 远程 (一次性)

```bash
cd /home/wanglei/vue-flow
git remote add upstream https://github.com/xyflow/xyflow-vue.git
# (VueFlow 上游 vue 版本仓库地址, 实际请以官方为准)
git fetch upstream
```

### 5.2 rebase 自定义 commit

```bash
git checkout master
git fetch upstream

# 看上游新版本
git log HEAD..upstream/master --oneline | head -20

# 假设 upstream 到 v1.50, 我们 5 个自定义 commit 要 rebase
git rebase upstream/master
# 解决冲突 (通常 useDrag.ts / Pane.vue 会有冲突)

# 跑 §4.3 - §4.7 流程回归
```

### 5.3 如果上游已修了我们的 bug

**对照检查 5 个自定义 commit**:
| Commit | 我们的改动 | 上游是否已修? |
|---|---|---|
| `7ef52400` | 拖动期跳过 nodesChange | 检查 upstream useDrag.ts 是否还有同样问题 |
| `381d832b` | 框选期跳过 getNodesInside | 同上 |
| `b359907a` | 框选结束不再重复计算 | 同上 |
| `421cd33c` | 恢复 + 第 4 参数 | 第 4 参数是否被上游 API 化? |
| `9e7a718f` | 末尾逗号 | 不适用 (type-check) |

**如果上游已修** → 丢弃对应自定义 commit，省维护负担。

---

## 6. 关键陷阱 (Pitfalls)

### 6.1 不要用绝对路径在文档/脚本里写 fork 路径
❌ 错误: `cd /home/wanglei/vue-flow/packages/core`
✅ 正确: 用 git remote / package.json file: 引用追溯

### 6.2 dist 必须跟 src 同步提交
改 src 不 build = 业务仓库 link 不到改动
build 不提交 dist = 其他开发机 clone 后用旧 dist

### 6.3 pnpm install 不会自动 link 新 dist
**改完 fork 必须 `pnpm install`** 重 link, 哪怕只是改 dist:
```bash
cd webui
pnpm install  # 触发 file: 重新 link
md5sum /home/wanglei/vue-flow/packages/core/dist/vue-flow-core.js \
       node_modules/@vue-flow/core/dist/vue-flow-core.js
# 必须一致, 否则浏览器拿到的是旧 dist
```

### 6.4 monorepo 根 build ≠ 单包 build
```bash
# ❌ 错: 在 monorepo 根 build 不会生成 packages/core/dist
pnpm build

# ✅ 对: 单独 build core 包
pnpm --filter @vue-flow/core build
```

### 6.5 改 fork 不写测试 = 老大背锅
**改 fork 必加测试**:
- `packages/core/` 自己如果有 vitest 配置 → 加单测
- 业务侧 `webui/src/composables/useCogniFlowDrag.test.ts` 加场景测试
- 浏览器实测必跑 50 节点 60fps

### 6.6 file: 引用限制
- CI/CD 流水线**不能直接复用本地 path** —— 需要把 fork 也同步到 CI 可访问的位置
- 团队新成员**clone 业务仓库后要手动 clone fork 到 `/home/wanglei/vue-flow`**
- **未来如果换机器或上 CI 容器, fork 路径要重新配置**

**未来改进方向** (不立即做, 等老大拍):
1. 把 `file:/home/wanglei/...` 改成 `git+ssh://git@github.com:ZackFair5185034/vue-flow.git#master`
2. 这样所有开发机/CI 都能直接 `pnpm install` 拉到 fork

---

## 7. 关键联系人 / 决策

| 角色 | 决定什么 |
|---|---|
| **老大** | 业务需求 → 是否走 fork 改源码 (决策树第 4 步) |
| **CogniFlow 维护者** | 业务侧适配 (composable / 组件 / 状态) |
| **VueFlow 上游** | 提 issue / PR 把我们的优化反哺给社区 (理想状态) |

---

## 8. 相关文档

- [vue-flow-usage.md](./vue-flow-usage.md) —— "我们用 VueFlow 什么、不用什么、为什么"
- [performance-budget.md](./performance-budget.md) —— 50 节点 60fps 红线 (待写)
- `.hermes/skills/cogniflow/architecture.md` —— 项目整体架构 (待写)

---

## 9. 改 fork 时的 commit message 模板

```
perf|fix(scope): 一句话描述

根因:
- 业务侧 X 行为触发 Y 问题 (链接 issue/反馈)
- 上游 Z 模块未提供 W 扩展点

修复:
- 改 src/path/to/file.ts: 描述
- 配套 build commit: 同步 dist

业务侧:
- 触发场景: [用例描述]
- 性能数据: [50 节点拖动 X fps / 框选响应 Y ms]
- 回归测试: 三件套 + 浏览器实测 50 节点 60fps 通过
- 是否可反哺上游: 是/否 (理由)
```

---

**TL;DR**: 改 fork 是 5% 不到的事，**90% 需求走业务侧 + VueFlow API**。改 fork 必走"src 改 → build → dist 提交 → 业务侧 link → 三件套 → 浏览器实测 50 节点"完整链路。**改完不写文档 = 下一个维护者踩坑**。
