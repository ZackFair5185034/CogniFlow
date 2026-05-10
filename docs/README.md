# CogniFlow 文档体系

## 文档分类方案

| 目录 | 类型 | 说明 |
|------|------|------|
| `guides/` | 活跃文档 | 教程、项目分析等持续维护的指南 |
| `plans/` | 进行中的计划 | 未完成的开发计划、TODO 清单 |
| `archives/` | 已完成归档 | 已实现的设计方案、已完成的任务计划 |
| `research/` | 技术研究 | 仍在迭代中的调研、设计文档 |

**管理规则：**
- 计划实施完成后，从 `plans/` 移入 `archives/`
- 设计方案对应的功能上线后，移入 `archives/`
- `research/` 保留正在演进中的设计文档，阶段性完结后归档
- 每次重大更新后，同步更新 `guides/` 中的教程和分析文档

---

## guides/ 指南

| 文件 | 说明 | 状态 |
|------|------|------|
| [TUTORIAL.md](guides/TUTORIAL.md) | 快速开始教程，包含项目概述、快速启动、API 参考 | 活跃 |
| [project-analysis-2026.md](guides/project-analysis-2026.md) | 项目分析报告，包含现状分析、迭代计划 | 活跃 |

---

## plans/ 进行中的计划

| 文件 | 说明 |
|------|------|
| [2026-05-07-rule-engine-ui-revision-plan.md](plans/2026-05-07-rule-engine-ui-revision-plan.md) | 规则引擎前端 UI 修订计划 |
| [rule-engine-todo.md](plans/rule-engine-todo.md) | 规则引擎开发待办清单 |

---

## archives/ 已完成归档

| 文件 | 说明 | 完成日期 |
|------|------|----------|
| [2026-04-11-webui-upgrade-design.md](archives/2026-04-11-webui-upgrade-design.md) | WebUI 升级设计方案 | 2026-04-11 |
| [2026-05-01-cogniflow-logo-implementation.md](archives/2026-05-01-cogniflow-logo-implementation.md) | Logo 实施方案 | 2026-05-01 |
| [2026-05-01-cogniflow-logo-design.md](archives/2026-05-01-cogniflow-logo-design.md) | Logo 设计方案 | 2026-05-01 |
| [2026-05-04-cogniflow-system-tray-design.md](archives/2026-05-04-cogniflow-system-tray-design.md) | 系统托盘功能设计 | 2026-05-04 |
| [rule-engine-port-connection-design.md](archives/rule-engine-port-connection-design.md) | 规则引擎端口连接设计 | 2026-05 |
| [video-detection-optimization.md](archives/video-detection-optimization.md) | 视频检测优化（流水线已实现） | 2026-05 |
| [video-stream-inference-design.md](archives/video-stream-inference-design.md) | 视频流推理设计（WS推送已实现） | 2026-05 |

---

## research/ 技术研究

### 画布/编辑器研究

| 文件 | 说明 |
|------|------|
| [canvas-editor-research-2026-05-06.md](research/canvas-editor-research-2026-05-06.md) | 画布编辑器调研 |
| [canvas-editor-research-2026-05-07.md](research/canvas-editor-research-2026-05-07.md) | 画布编辑器调研 |
| [infinite-canvas-optimization.md](research/infinite-canvas-optimization.md) | 无限画布缩放/平移性能优化 |
| [node-graph-data-structure-design.md](research/node-graph-data-structure-design.md) | 节点图数据结构设计 |
| [node-red-editor-architecture.md](research/node-red-editor-architecture.md) | Node-RED 编辑器架构研究 |

### 规则引擎研究

| 文件 | 说明 |
|------|------|
| [rule-engine-index.md](research/rule-engine-index.md) | 规则引擎索引/目录 |
| [rule-engine-redesign-v2.md](research/rule-engine-redesign-v2.md) | 规则引擎重新设计 v2 |
| [rule-engine-api-design.md](research/rule-engine-api-design.md) | API 设计 |
| [rule-engine-data-models.md](research/rule-engine-data-models.md) | 数据模型设计 |
| [rule-engine-dev-guide.md](research/rule-engine-dev-guide.md) | 开发指南 |
| [rule-engine-development-plan.md](research/rule-engine-development-plan.md) | 开发计划 |
| [rule-engine-phase1-node-registry.md](research/rule-engine-phase1-node-registry.md) | Phase 1: 节点注册表 |
| [rule-engine-phase2-execution-engine.md](research/rule-engine-phase2-execution-engine.md) | Phase 2: 执行引擎 |
| [rule-engine-phase3-canvas-frontend.md](research/rule-engine-phase3-canvas-frontend.md) | Phase 3: 画布前端 |
| [rule-engine-phase4-property-panel.md](research/rule-engine-phase4-property-panel.md) | Phase 4: 属性面板 |
| [rule-engine-phase5-websocket.md](research/rule-engine-phase5-websocket.md) | Phase 5: WebSocket |
| [rule-engine-phase6-trigger.md](research/rule-engine-phase6-trigger.md) | Phase 6: 触发器 |
| [rule-engine-ui-ux-spec.md](research/rule-engine-ui-ux-spec.md) | UI/UX 规格 |

---

## 文档更新日志

| 日期 | 说明 |
|------|------|
| 2026-05-10 | 全面梳理项目实现情况，更新 TUTORIAL.md、project-analysis-2026.md、README.md |
| 2026-05-05 | 项目分析报告初版 |
| 2026-05-01 | Logo 设计/实施方案归档 |
| 2026-04-11 | WebUI 升级设计方案归档 |
