<!-- -*- coding: utf-8 -*- -->
<!--
  CogniFlow 项目整体 Review - 2026-06-19

  范围：后端规则引擎 + 前端整体架构 + 工程化/测试/构建
  方法：源码核实 + 三路并行调查交叉验证（仅保留经文件证据确认的发现）
  关联：规则引擎前端 bug/性能细节见同目录《规则引擎前端实现分析-2026-06-19.md》
-->

# CogniFlow 项目整体 Review（2026-06-19）

## 0. 核心结论

CogniFlow 是一个功能覆盖面很广（采集/特征/检测/训练/推理/规则引擎/可视化编排）的视觉感知框架，**功能完整度高，但工程化与架构分层明显滞后于功能扩张**。规则引擎是项目当前最活跃、最复杂的子系统，其前端已经做了大量精细化性能优化（LOD、v-memo、d3-drag 事件委托、Tier 2 边增量更新），但**优化越精细，周边的结构性债务反而越显眼**。

成熟度速览：

| 维度 | 评分 | 一句话 |
|------|------|--------|
| 功能完整度 | ★★★★☆ | 训练/推理/规则引擎/编排闭环已通 |
| 架构分层 | ★★★☆☆ | service 反向依赖 router 已修；前端单 store 单 api 文件未动 |
| 工程化/CI | ★★☆☆☆ | 无 CI、无 .env.example、覆盖率统计缺失 |
| 规范执行 | ★★★☆☆ | CLAUDE.md §6/§8 矛盾已修, docs/superpowers 已清; cf- 样式仍空转 |
| 测试体系 | ★★☆☆☆ | 后端 254 用例 (+8), 前端 1 store 测试, 无 e2e |
| 文档一致性 | ★★★☆☆ | §6/§8 统一为 MD, docs 混入清理 |

**2026-06-19 修复进度** (本批):

| 修复 | 状态 | Commit |
|------|------|--------|
| BE-P0-1 拆 detection 反向依赖 | ✅ | `e195cb7` |
| BE-P0-2 节点级故障隔离 | ✅ | `882f21a` |
| BE-P0-3 调度器执行互斥 | ✅ | `acb462c` |
| ENG-P0-1 修 CLAUDE.md §6/§8 矛盾 | ✅ | `4695448` |
| ENG-P0-2 清理 docs 混入 | ✅ | `3facc6f` |

**已修 5/30+ 项 (17%)**。剩余 25+ 项主要是后端 P1/P2 (图存储/注册表/类型 schema)、前端架构 (单 store 拆分 / api 拆分 / WS 统一)、工程化 (CI / .env.example / 测试合并)、性能优化 (8 PERF)。详细见各章节 "状态" 行。

**最该先动的 5 件事**（详见 §5 路线图）：

1. 拆掉 `detection_nodes.py` 对 `backend.routers.yolo_training` 的反向依赖（P0，3 处函数内延迟导入） ✅ `e195cb7`
2. 给执行器加节点级故障隔离 + 给调度器加执行互斥锁（P0，并发健壮性） ✅ `882f21a` + `acb462c`
3. 前端拆分 `ruleEngine.ts` 单体 store 与 `api/index.ts` 单文件（P1，制约后续所有重构）
4. 统一 WebSocket 连接管理（P1，4 个 view 各自 `new WebSocket`）
5. 修正 CLAUDE.md §6/§8 文档格式矛盾 + 清理 docs/ 混入的 `superpowers/`（P1，规范可信度） ✅ `4695448` + `3facc6f`

> 注：本报告所有发现均经源码核实，行号为核实当时状态。规则引擎前端的 8 bug / 8 性能问题不在此重复，见关联文档（已修 8/8 bug + 6/8 perf, 关联文档 §0 表）。

---

## 1. 后端规则引擎

### BE-P0-1 · 检测节点反向依赖路由层（分层破缺）

**位置**：`backend/services/rule_engine/nodes/detection_nodes.py:190, 366, 547`

**现象**：service 层节点在**函数内部**三次重复 `from backend.routers.yolo_training import load_yolo_model, inference_yolo`。

**根因**：正确的依赖方向应是 `router → service → engine/核心`，但检测节点为了复用 YOLO 推理函数，直接 import 了 router 模块。作者用**函数内延迟导入**绕开了模块加载期的循环 import，这恰恰是分层已破的信号——一旦有人把这两个 import 提到模块顶部，整个规则引擎模块就会 import 爆炸。

**危害**：
- service 无法脱离 router 独立测试/复用
- router 的任何重构都会波及 service
- 规则引擎节点无法被其他 entrypoint（如 CLI、调度器直调）复用

**解决方案**：
1. 在 `backend/services/` 下抽出 `inference_service.py`（或 `backend/core/` 下抽 `yolo_inference.py`），把 `load_yolo_model` / `inference_yolo` 的实现搬过去
2. `routers/yolo_training.py` 改为调用该 service（router 只做 HTTP 编解码）
3. `detection_nodes.py` 顶部 `from backend.services.inference_service import ...`，删除三处函数内导入
4. 加一条架构约束测试：`grep -r "from backend.routers" backend/services/` 必须为空（可放进 pre-commit）

### BE-P0-2 · 执行器层内并行缺节点级故障隔离

**位置**：`backend/services/rule_engine/executor.py:584`（`await asyncio.gather(*tasks, return_exceptions=True)`）

**现象**：层内并行用 `gather(return_exceptions=True)` 收集结果，异常被吞成返回值再统一标记节点状态。

**根因**：`return_exceptions=True` 的语义是"不抛、把异常当结果"，这本身没问题；问题在于**没有节点级资源清理、没有部分失败下的图级策略**。当一层 8 个节点有 1 个抛异常时：
- 该节点占用的 GPU/模型句柄是否释放？无显式 `finally`
- 下游层是否继续执行？取决于状态判定，但缺统一的"失败传播策略"（fail-fast / fail-soft / 隔离重试）
- 异常信息是否完整回传 WS？仅 mark status，堆栈可能丢

**解决方案**：
1. 每个节点执行包一层 `try/finally`，确保 `finally` 释放资源（模型句柄、临时帧缓冲）
2. 在 GraphExecutor 引入 `failure_policy: 'isolate' | 'abort'` 配置（默认 isolate），isolate 下失败节点输出置空、同层其他节点继续
3. 异常对象连同 `traceback.format_exc()` 一并写入节点 status，WS 推送完整错误
4. 加测试：一层注入 1 个 raise 节点，断言其余节点正常完成、图不整体中断

### BE-P0-3 · 调度器无执行互斥，Cron 与手动触发可并发冲撞

**位置**：`backend/services/rule_engine/scheduler.py:48`（`_execute_graph`）— grep 全文无 `Lock`/`mutex`

**现象**：Cron 触发与"立即执行"按钮都直接 `create_task(_execute_graph(...))`，无任何互斥。若某图执行耗时 30s、Cron 间隔 10s，会出现同一图三份并发执行。

**危害**：
- 重复推理浪费 GPU
- 共享节点状态（如检测节点缓存的模型）被并发改写
- WS 推送日志交错，前端无法区分哪次执行

**解决方案**：
1. 引入 `asyncio.Lock` 字典 `self._running_locks: dict[graph_id, Lock]`，`_execute_graph` 入口 `async with lock`
2. 二次触发时策略可选：`skip`（默认，已运行则跳过）/ `queue`（排队）/ `cancel_prev`
3. 锁需带超时释放兜底，防异常未释放导致永久死锁
4. WS 日志带 `execution_id`，前端按执行实例分组

### BE-P1-1 · 图数据以 JSON 字符串持久化，无版本/迁移机制

**位置**：`backend/services/rule_engine/graph_manager.py`（nodes/edges 存为 JSON 字符串）

**现象**：图结构整体序列化为 JSON 存库，无 schema version 字段。

**危害**：节点配置 schema 一旦演进（新增字段、改字段类型），历史图加载后要么静默丢字段、要么运行时 KeyError，且无法回滚。

**解决方案**：
1. 图存储增加 `schema_version` 字段
2. 实现 `migrate_graph(graph, from_version, to_version)` 注册表
3. 加载时自动迁移 + 迁移失败明确报错而非静默
4. 节点定义侧同步声明 config schema（与前端共享，见 FE-P1-2）

### BE-P1-2 · 节点注册表无依赖校验，注册即生效

**位置**：`backend/services/rule_engine/registry.py:40-53`（`register()` 直接 `_executors[node_type] = executor_class`）

**现象**：注册是纯命令式 `dict.put`，无重复注册告警、无节点间依赖拓扑校验。

**解决方案**：
1. 重复注册 `node_type` 时 raise（开发期）或 warn（生产期）
2. 启动时打印已注册节点清单，便于排查"忘了注册"
3. 可选：声明式注册（装饰器 + 自动扫描），减少手动 `register()` 漏调

### BE-P1-3 · 节点 config 为动态 dict，类型安全边界缺失

**位置**：`backend/services/rule_engine/models.py`（config: dict）+ 各节点 `execute` 内手动取值

**现象**：节点配置全靠 `config.get('threshold', 0.5)` 这种字符串键取值，前端 schema 与后端校验两套独立维护。

**解决方案**：
1. 每个节点类声明 `ConfigSchema`（Pydantic model）
2. 执行前 `ConfigSchema(**config)` 校验，失败即节点失败（带清晰字段错误）
3. 该 schema 同时作为前端 NodeConfigEditor 的类型源（生成 TS 类型，见 FE-P1-2）

### BE-P2-1 · 拓扑排序每次执行重算，无缓存

**位置**：`executor.py` Kahn 实现

**解决方案**：图结构未变时复用上次分层结果；图变更（增删边）时失效缓存。

### BE-P2-2 · 取消机制仅在 executor 级，内部 async 不可中断

**位置**：`executor.py:1109-1110`（`context.cancelled` flag）

**解决方案**：传入 `asyncio.CancelledError` 可传播的取消点；长任务（视频推理）在帧循环检查 cancelled。

---

## 2. 前端整体架构

> 规则引擎前端的 bug/性能细节见关联文档，本节只讲架构层。

### FE-P0-1 · 整个 WebUI 只有一个 Pinia store

**位置**：`webui/src/stores/` 仅含 `ruleEngine.ts`（39.7KB 单文件）+ 其测试

**现象**：项目有 9 个 view（训练/推理/图集/模型/规则引擎…），但状态管理只有规则引擎一个 store。其余 view 的状态全靠组件内 `ref`/`reactive` 局部持有，跨 view 共享数据只能靠 props 透传或重新请求。

**危害**：
- 训练列表、模型列表、图集列表等在多个 view 重复请求
- 无法做"切走再切回保持状态"
- `ruleEngine.ts` 单文件 39.7KB 已是巨型 store，继续膨胀不可维护

**解决方案**：按领域拆 store：`useTrainingStore`、`useModelStore`、`useAtlasStore`、`useRuleEngineStore`（保留并瘦身）。共享的"当前选中项目/全局配置"抽 `useAppStore`。拆分时保持现有 `shallowRef + markRaw` 性能模式。

### FE-P0-2 · API 层单文件全塞，无统一错误处理

**位置**：`webui/src/api/index.ts`（10.2KB 单文件，承载全部后端调用）

**现象**：所有 HTTP 调用挤在一个文件，错误处理、响应类型断言散落各调用点。

**解决方案**：
1. 按领域拆 `api/training.ts` / `api/model.ts` / `api/ruleEngine.ts` / `api/atlas.ts`
2. 抽 `api/client.ts`：单一 axios 实例 + 拦截器（统一错误 toast、401 跳转、loading 计数）
3. 响应类型统一从 `types/api.ts` 导入，禁止调用点就地 `as any`

### FE-P0-3 · WebSocket 连接分散在 4 个 view，无统一管理

**位置**：`RuleCanvas.vue` / `ModelList.vue` / `Home.vue` / `Training.vue` 各自 `new WebSocket(...)`；虽有 `utils/streamClient.ts` 但未统一收口

**危害**：
- 断线重连逻辑要写 4 遍（且大概率不一致）
- 组件卸载时连接泄漏风险（需逐个核 `onBeforeUnmount`）
- 无法做连接复用（同一后端多路 WS）

**解决方案**：抽 `composables/useWebSocket.ts`，封装连接/重连/心跳/自动清理；现有 `streamClient.ts` 作为其底层实现。所有 view 改用该 composable。

### FE-P1-1 · 样式体系规范空转：cf- 快捷方式近乎零落地

**位置**：`webui/src/views/` 下 `ui-*` class 用于 8 个文件，`cf-*` class 用于 **0 个文件**

**现象**：CLAUDE.md §7.5 用整张表定义了 40+ 个 `cf-` UnoCSS shortcut，但实际 view 代码**一个都没用**，仍在用 §7.3 的旧 `.ui-*` SCSS 体系。两套体系名义并存，实际只有旧的在跑。

**危害**：
- 规范文档与代码严重脱节，新人无所适从
- 之前几条 commit（"第 N 波 ui-* 迁 cf-"）声称在迁移，但 views 层零落地，迁移停留在 shortcut 定义层
- 维护两套样式心智模型

**解决方案**（二选一，需老大拍板）：
- **方案 A（推荐）**：承认 cf- 迁移未到时机，从 CLAUDE.md 删除 cf- 表，统一回归 `ui-*`，避免规范空转
- **方案 B**：真正推进迁移，按 view 批量替换 `ui-btn`→`cf-btn` 等，并删 `_common.scss` 中重复定义，设 deadline 清零

无论哪种，现状"定义了不用"是最差状态，必须消除。

### FE-P1-2 · 前后端类型手工同步，漂移风险高

**位置**：`webui/src/types/` 与 `backend/schemas.py` / `rule_engine/models.py` 各自维护

**现象**：节点 config schema、图结构、训练 job 响应等类型，前后端各写一遍，无任何生成/校验机制。

**解决方案**：
1. 后端 Pydantic model 用 `pydantic2ts` 生成 TS 类型到 `src/types/generated/`
2. 前端业务类型 `import type { TrainingJobResponse } from '@/types/generated'`
3. CI 里加"类型是否最新"检查（生成后 diff，不一致则失败）

### FE-P1-3 · 业务逻辑泄漏进 view，页面骨架重复

**位置**：各 view 的 page-header / loading / empty 结构重复手写

**现象**：CLAUDE.md §7.3 给了 `page-header` 模板，但每个 view 仍各自复制粘贴；loading/error 状态各 view 各写一套 try/catch + ref。

**解决方案**：
1. 抽 `BasePageHeader.vue` 组件统一 page-header
2. 抽 `useAsyncData(fn)` composable 统一 loading/error/data 三态
3. view 只声明数据源与布局，不写状态机样板

### FE-P2-1 · 路由无懒加载与守卫

**位置**：`webui/src/router/`

**解决方案**：`() => import(...)` 动态导入各 view；按需加路由守卫（鉴权未到时机则先留口子）。

---

## 3. 工程化、测试与构建

### ENG-P0-1 · 文档规范自相矛盾，docs 实际全用 MD

**位置**：`CLAUDE.md` §6 vs §8

**现象**：
- §6 写"2026-06-03 起 HTML 源已清空，新文档直接编辑 MD 文件"
- §8 仍大篇幅要求"README 除外所有文档一律使用 HTML，禁止使用 Markdown"
- 实际 `docs/research-md/`、`docs/guides-md/` 等全是 `.md`
- §8.2 的 HTML 文档规范、`docs/css/main.css` 体系已完全过时

**危害**：规范文档内部打架，新人不知道该听谁的。

**解决方案**：删除 §8 全部 HTML 规范内容，统一为"所有文档用 Markdown，放 `docs/*-md/`"；保留 §6 的目录约定。

### ENG-P0-2 · docs/ 目录混入非项目内容 + 未登记目录

**位置**：`docs/` 下存在 `superpowers/`（skill 目录）与 `architecture/`（未在 §6 结构树登记）

**现象**：`superpowers/` 是 oh-my-claudecode skill 插件的内容，不应进项目 docs；`architecture/` 不在 CLAUDE.md 列的 5 类文档目录里。

**解决方案**：
1. `superpowers/` 移出 docs（或加 .gitignore），它是工具产物非项目资产
2. `architecture/` 要么并入 `research-md/`，要么补进 §6 目录约定

### ENG-P1-1 · 完全无 CI/CD

**位置**：`.github/workflows/` 不存在

**现象**：无任何自动化。`PYTHONPATH=. pytest`、`pnpm build:type`、`pnpm lint`、`tsc --noEmit` 全靠人工跑。

**危害**：回归靠自觉，CLAUDE.md 记的"已知遗留失败测试"会持续累积；前端类型错误无人拦截。

**解决方案**：起一个最小 CI：PR 触发，跑 `PYTHONPATH=. pytest backend/tests/` + `cd webui && pnpm lint && pnpm build:type`。后续再加覆盖率门槛。

### ENG-P1-2 · 无 .env.example，敏感/路径配置散落

**位置**：无 `.env*` 文件

**现象**：数据库路径、模型缓存路径、数据目录等硬编码或散落各模块，新人无从知道可配置项。

**解决方案**：建 `.env.example` 列全部可配置项（DB path、model cache、data root、WS port…），代码改读 env；`.env` 进 gitignore。

### ENG-P1-3 · 后端测试分散两处，覆盖率统计缺失

**位置**：`backend/tests/` 与 `tests/test_rule_engine/` 并存

**现象**：CLAUDE.md §5 记 236 passed，但两套测试目录、无覆盖率报告、无覆盖率门槛。已知 1 个遗留失败（cv2 假设）未修。

**解决方案**：
1. 统一测试目录（建议合并到 `tests/`，按子系统分子目录）
2. pytest 加 `--cov=backend --cov=engine --cov-report=term-missing`
3. 修掉 cv2 那个遗留失败（改测试假设而非跳过）
4. CI 设核心模块覆盖率门槛

### ENG-P1-4 · 前端测试几乎空白

**位置**：`webui/src/stores/ruleEngine.test.ts`（仅 1 个 store 测试）

**现象**：有 vitest 基建但只有 1 个测试文件。composables（useCogniFlowDrag / useEdgePathUpdater）、API 层、关键组件（RuleNode / NodeConfigEditor）零覆盖。

**解决方案**：优先补 useCogniFlowDrag 的单元测试（拖拽/选中/isClick 判定是 bug 高发区），再补 store 的 undo/redo（已知有 BUG-1）。

### ENG-P2-1 · Git 提交规范执行不彻底

**位置**：最近 commit 如 `style: 第 3 波 ui-* 体系迁到 uno.config.ts shortcut`

**现象**：type 用了但 scope 命名随意（`webui` vs 无 scope 混用），且 §7.7 定义的 scope 体系未严格执行。

**解决方案**：加 commitlint + conventional-changelog，CI 校验。

### ENG-P2-2 · 数据库文件位置

**位置**：需核实 `engine.db` 是否落在 `data/database/`（CLAUDE.md §3 声明位置）

**解决方案**：统一所有 SQLite 落 `data/database/`，路径走 env 配置。

---

## 4. 规范执行度抽查

| CLAUDE.md 规范 | 实际执行 | 偏差 |
|----------------|---------|------|
| §7.5 cf- 样式体系 | views 层 0 落地 | 严重空转 |
| §7.4.1 禁用原生表单标签 | 抽查需进一步核实 | 待验 |
| §2.1 中文注释 | 抽查符合 | 良好 |
| §8 HTML 文档 | 全用 MD | 规范已废但未删 |
| §4.2 conventional commits | type 有，scope 不严 | 轻微 |
| §5 PYTHONPATH=. 跑测试 | 已记录 | 良好（但无 CI 兜底） |

---

## 5. 解决方案路线图（按优先级）

### 第一阶段（P0，1-2 周）

| # | 问题 | 改动量 | 风险 |
|---|------|--------|------|
| 1 | BE-P0-1 拆 detection_nodes 反向依赖 | 中（抽 service + 改 3 处导入） | 低 |
| 2 | BE-P0-2 执行器节点级故障隔离 | 中（包 try/finally + 策略） | 中（改执行路径） |
| 3 | BE-P0-3 调度器执行互斥锁 | 小（加 Lock 字典） | 低 |
| 4 | ENG-P0-1 修 CLAUDE.md §6/§8 矛盾 | 小（删 §8） | 无 |
| 5 | ENG-P0-2 清理 docs/superpowers + 登记 architecture | 小 | 无 |

### 第二阶段（P1，2-4 周）

| # | 问题 | 改动量 | 风险 |
|---|------|--------|------|
| 6 | FE-P0-1 拆 ruleEngine 单体 store | 大（按领域拆 + 瘦身） | 中（回归风险） |
| 7 | FE-P0-2 拆 api/index.ts + 统一拦截器 | 中 | 低 |
| 8 | FE-P0-3 统一 WebSocket composable | 中 | 中（4 view 改造） |
| 9 | FE-P1-1 样式体系二选一（建议删 cf-） | 小（改文档）或大（真迁移） | 取决方案 |
| 10 | ENG-P1-1 起最小 CI | 小 | 无 |
| 11 | ENG-P1-2 建 .env.example | 小 | 低 |
| 12 | BE-P1-1 图存储加版本 + 迁移 | 中 | 中 |

### 第三阶段（P2，持续）

- FE-P1-2 前后端类型生成（pydantic2ts）
- FE-P1-3 抽 BasePageHeader + useAsyncData
- BE-P1-3 节点 config 强类型 schema
- ENG-P1-3/4 测试统一 + 覆盖率 + 前端补测
- ENG-P2-1 commitlint

---

## 6. 文件-问题交叉索引

| 文件/目录 | 涉及问题 |
|-----------|---------|
| `backend/services/rule_engine/nodes/detection_nodes.py` | BE-P0-1 |
| `backend/services/rule_engine/executor.py` | BE-P0-2, BE-P2-1, BE-P2-2 |
| `backend/services/rule_engine/scheduler.py` | BE-P0-3 |
| `backend/services/rule_engine/graph_manager.py` | BE-P1-1 |
| `backend/services/rule_engine/registry.py` | BE-P1-2 |
| `backend/services/rule_engine/models.py` | BE-P1-3 |
| `webui/src/stores/ruleEngine.ts` | FE-P0-1（+ 关联文档 8 bug/8 perf） |
| `webui/src/api/index.ts` | FE-P0-2 |
| `webui/src/views/{RuleCanvas,ModelList,Home,Training}.vue` | FE-P0-3 |
| `webui/src/views/*` | FE-P1-1（ui- vs cf-） |
| `webui/src/types/` | FE-P1-2 |
| `webui/src/router/` | FE-P2-1 |
| `CLAUDE.md` §6/§8 | ENG-P0-1 |
| `docs/superpowers/`, `docs/architecture/` | ENG-P0-2 |
| `.github/workflows/`（缺失） | ENG-P1-1 |
| `.env.example`（缺失） | ENG-P1-2 |
| `backend/tests/`, `tests/` | ENG-P1-3 |
| `webui/src/stores/ruleEngine.test.ts` | ENG-P1-4 |

---

## 7. 验证清单（修复后逐项核）

**后端**
- [ ] `grep -r "from backend.routers" backend/services/` 为空
- [ ] 一层注入 raise 节点，其余节点正常完成
- [ ] 同图 Cron 间隔 < 执行耗时，不出现并发执行
- [ ] 历史图加载后 schema 迁移日志可见
- [ ] `PYTHONPATH=. pytest` 全绿且无遗留失败

**前端**
- [ ] `webui/src/stores/` 下按领域拆分，ruleEngine.ts 瘦身
- [ ] `webui/src/api/` 按领域拆分，单一 axios 实例
- [ ] 4 个 view 的 WebSocket 改用 `useWebSocket`
- [ ] CLAUDE.md 样式体系与现实一致（cf- 删或全迁移）
- [ ] `pnpm build:type` 通过
- [ ] useCogniFlowDrag 单测覆盖拖拽/选中/isClick

**工程化**
- [ ] CI 在 PR 上跑通 pytest + lint + tsc
- [ ] `.env.example` 存在且代码读 env
- [ ] docs/ 无 superpowers/，architecture/ 已登记或合并
- [ ] CLAUDE.md §8 HTML 规范已删
