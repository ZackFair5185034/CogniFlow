# 规则引擎 API 设计文档

> 文档版本：v1.0  
> 基于调研：canvas-editor-research-2026-05-06.md  
> 创建时间：2026-05-06

---

## 1. 概述

本文档定义 CogniFlow 规则引擎画布编辑器的 API 设计，涵盖节点定义、规则图 CRUD、执行管理、WebSocket 实时通信四大模块。

**设计原则：**
- RESTful API 为主，WebSocket 处理实时通信
- 参考 ComfyUI API 风格（Prompt 序列化、队列管理）
- 前后端数据格式与 Vue Flow 组件模型对齐

---

## 2. 基础信息

**Base URL：** `/api/rule-engine`

**内容类型：** `application/json`

**认证方式：** （当前未设计认证，未来扩展）

---

## 3. 节点定义 API

### 3.1 获取所有节点定义

获取前端渲染节点面板所需的完整节点类型信息。

```
GET /api/rule-engine/nodes/definitions
```

**响应：**

```json
{
  "nodes": [
    {
      "type": "YOLOModel",
      "category": "detection",
      "display_name": "YOLO 检测模型",
      "description": "使用 YOLO 模型进行目标检测，支持多目标追踪",
      "icon": "radar",
      "color": "#00f0FF",
      "inputs": {
        "image": {
          "name": "图片输入",
          "type": "IMAGE",
          "required": true,
          "default": null,
          "description": "待检测的图片"
        },
        "confidence": {
          "name": "置信度阈值",
          "type": "FLOAT",
          "required": false,
          "default": 0.5,
          "description": "检测置信度下限"
        },
        "model_id": {
          "name": "模型选择",
          "type": "MODEL",
          "required": true,
          "default": null,
          "description": "已注册的 YOLO 模型"
        }
      },
      "outputs": {
        "bboxes": {
          "name": "检测框",
          "type": "BBOX",
          "description": "检测到的目标框列表"
        },
        "scores": {
          "name": "置信度",
          "type": "SCORES",
          "description": "各检测框对应的置信度"
        },
        "class_ids": {
          "name": "类别ID",
          "type": "CLASS_IDS",
          "description": "各检测框对应的类别 ID"
        }
      }
    }
  ],
  "categories": [
    {"name": "input", "display_name": "输入", "color": "#4CFF4C", "icon": "upload"},
    {"name": "detection", "display_name": "检测", "color": "#00f0FF", "icon": "radar"},
    {"name": "processing", "display_name": "处理", "color": "#FFFF4C", "icon": "process"},
    {"name": "action", "display_name": "动作", "color": "#FF7F4C", "icon": "cursor"},
    {"name": "logic", "display_name": "逻辑", "color": "#DC4FDC", "icon": "branch"},
    {"name": "output", "display_name": "输出", "color": "#FF4C4C", "icon": "download"}
  ]
}
```

**数据类型对照表（参考调研报告 3.5）：**

| 类型标识 | 说明 | 兼容输出类型 |
|---------|------|------------|
| IMAGE | 图片数据 | IMAGE, MASK |
| BBOX | 检测框坐标列表 | BBOX |
| MASK | 掩码数据 | MASK |
| SCORES | 置信度浮点数列表 | SCORES |
| CLASS_IDS | 类别 ID 整数列表 | CLASS_IDS |
| TRIGGER | 触发信号 | 任意 |
| CONTROL | 控制信号 | CONTROL |
| MODEL | 模型引用 | MODEL |
| ANY | 任意类型 | 任意 |

---

## 4. 规则图 CRUD API

### 4.1 创建规则图

```
POST /api/rule-engine/graphs
```

**请求体：**

```json
{
  "name": "目标跟踪规则",
  "description": "检测并跟踪画面中的目标对象",
  "nodes_json": "{...}",
  "edges_json": "[...]",
  "variables_json": "{...}",
  "version": 1
}
```

**说明：** `nodes_json`、`edges_json`、`variables_json` 为字符串化的 JSON，与调研报告 3.3 的 ComfyUI 格式对齐。

**响应：** `RuleGraphResponse`（见 4.4）

---

### 4.2 列出所有规则图

```
GET /api/rule-engine/graphs
```

**响应：**

```json
[
  {
    "id": 1,
    "name": "目标跟踪规则",
    "description": "检测并跟踪画面中的目标对象",
    "is_active": false,
    "thumbnail": null,
    "created_at": "2026-05-06T10:00:00Z",
    "updated_at": "2026-05-06T10:00:00Z",
    "version": 1
  }
]
```

---

### 4.3 获取规则图详情

```
GET /api/rule-engine/graphs/{graph_id}
```

**响应：** `RuleGraphResponse`（见 4.4）

---

### 4.4 获取规则图详情（含解析后数据）

```
GET /api/rule-engine/graphs/{graph_id}/detail
```

**响应：**

```json
{
  "id": 1,
  "name": "目标跟踪规则",
  "description": "检测并跟踪画面中的目标对象",
  "is_active": false,
  "nodes": {
    "node_001": {
      "id": "node_001",
      "type": "ImageCapture",
      "position": {"x": 100, "y": 200},
      "data": {
        "label": "摄像头",
        "params": {
          "source": "video0",
          "fps": 30
        }
      },
      "inputs": {},
      "outputs": {
        "image": {"type": "IMAGE"}
      }
    },
    "node_002": {
      "id": "node_002",
      "type": "YOLOModel",
      "position": {"x": 350, "y": 200},
      "data": {
        "label": "YOLO 检测",
        "params": {
          "confidence": 0.5,
          "model_id": 1
        }
      },
      "inputs": {
        "image": {"node_id": "node_001", "output": "image"},
        "confidence": {"value": 0.5}
      },
      "outputs": {
        "bboxes": {"type": "BBOX"},
        "scores": {"type": "SCORES"}
      }
    }
  },
  "edges": [
    {
      "id": "edge_001",
      "source": "node_001",
      "source_handle": "image",
      "target": "node_002",
      "target_handle": "image",
      "type": "IMAGE"
    }
  ],
  "variables": {
    "CONF_THRESHOLD": {"type": "float", "default": 0.5},
    "TARGET_CLASS": {"type": "string", "default": "person"}
  }
}
```

**数据结构说明（参考调研报告 3.3 ComfyUI 格式）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| nodes | Dict[str, Node] | 节点字典，key 为节点 ID |
| edges | List[Edge] | 边列表 |
| variables | Dict[str, Variable] | 规则变量 |

**节点数据结构（参考调研报告 3.1）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 节点唯一标识 |
| type | string | 节点类型（对应 NodeDefinition.type） |
| position | {x, y} | 画布坐标 |
| data.label | string | 节点显示名称 |
| data.params | dict | 用户配置的参数值 |
| inputs | dict | 输入端口配置，key 为端口名 |
| inputs[key].node_id | string | 连接的源节点 ID |
| inputs[key].output | string | 连接的源端口名 |
| inputs[key].value | any | 未连接时的默认值 |
| outputs | dict | 输出端口配置，key 为端口名 |

**边数据结构（参考调研报告 3.2）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 边唯一标识 |
| source | string | 源节点 ID |
| source_handle | string | 源端口名 |
| target | string | 目标节点 ID |
| target_handle | string | 目标端口名 |
| type | string | 连接数据类型 |

---

### 4.5 更新规则图

```
PUT /api/rule-engine/graphs/{graph_id}
```

**请求体：**

```json
{
  "name": "目标跟踪规则（优化版）",
  "description": "更新描述",
  "nodes_json": "{...}",
  "edges_json": "[...]",
  "variables_json": "{...}",
  "is_active": false,
  "thumbnail": "data:image/png;base64,..."
}
```

**说明：** 所有字段可选，只更新提供的字段。

---

### 4.6 删除规则图

```
DELETE /api/rule-engine/graphs/{graph_id}
```

**响应：**

```json
{
  "message": "规则图已删除"
}
```

---

### 4.7 更新规则图缩略图

```
PATCH /api/rule-engine/graphs/{graph_id}/thumbnail
```

**请求体：**

```json
{
  "thumbnail": "data:image/png;base64,..."
}
```

---

## 5. 规则图校验与激活

### 5.1 校验规则图

验证规则图的完整性和正确性。

```
POST /api/rule-engine/graphs/{graph_id}/validate
```

**校验项目：**
1. 节点 ID 无重复
2. 所有输入端口已连接或有默认值
3. 连接的输出端口存在
4. 无环回依赖（拓扑排序检测）
5. 节点类型有效

**响应：**

```json
{
  "valid": true,
  "errors": []
}
```

或

```json
{
  "valid": false,
  "errors": [
    {"node_id": "node_003", "message": "输入端口 'confidence' 未连接且无默认值"},
    {"node_id": "node_005", "message": "规则图存在循环依赖: node_001 → node_003 → node_005 → node_001"}
  ]
}
```

---

### 5.2 激活规则图

```
POST /api/rule-engine/graphs/{graph_id}/activate
```

**前置条件：** 规则图必须通过校验。

**响应：**

```json
{
  "id": 1,
  "name": "目标跟踪规则",
  "is_active": true,
  "message": "规则图已激活"
}
```

**错误响应（规则图校验失败）：**

```json
{
  "detail": "规则图验证失败: 输入端口 'image' 未连接"
}
```

---

### 5.3 停用规则图

```
POST /api/rule-engine/graphs/{graph_id}/deactivate
```

**响应：**

```json
{
  "id": 1,
  "name": "目标跟踪规则",
  "is_active": false,
  "message": "规则图已停用"
}
```

---

## 6. 执行管理 API

### 6.1 手动触发执行

```
POST /api/rule-engine/execute
```

**请求体：**

```json
{
  "graph_id": 1,
  "trigger_type": "manual",
  "trigger_data": {}
}
```

**trigger_type 可选值：**

| 值 | 说明 |
|----|------|
| manual | 手动触发（用户点击执行按钮） |
| timer | 定时触发（由 APScheduler 内部调用） |
| webhook | Webhook 触发（由 webhook 接口内部调用） |

**响应：**

```json
{
  "execution_id": 123,
  "status": "running",
  "result": {
    "started_at": "2026-05-06T10:30:00Z"
  }
}
```

**执行完成后（同步返回示例）：**

```json
{
  "execution_id": 123,
  "status": "completed",
  "result": {
    "started_at": "2026-05-06T10:30:00Z",
    "completed_at": "2026-05-06T10:30:05Z",
    "total_time_ms": 5000,
    "node_results": {
      "node_001": {"status": "completed", "outputs": {"image": "..."}},
      "node_002": {"status": "completed", "outputs": {"bboxes": [...], "scores": [...]}}
    }
  }
}
```

---

### 6.2 获取执行历史

```
GET /api/rule-engine/executions?graph_id=1&limit=50
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| graph_id | int | 可选，按规则图 ID 过滤 |
| limit | int | 可选，返回记录数，默认 50 |

**响应：**

```json
[
  {
    "id": 123,
    "graph_id": 1,
    "trigger_type": "manual",
    "trigger_data": {},
    "status": "completed",
    "started_at": "2026-05-06T10:30:00Z",
    "completed_at": "2026-05-06T10:30:05Z",
    "total_time_ms": 5000,
    "error_message": null
  }
]
```

---

### 6.3 获取执行详情

```
GET /api/rule-engine/executions/{execution_id}
```

**响应：**

```json
{
  "id": 123,
  "graph_id": 1,
  "trigger_type": "manual",
  "trigger_data": {},
  "status": "completed",
  "started_at": "2026-05-06T10:30:00Z",
  "completed_at": "2026-05-06T10:30:05Z",
  "total_time_ms": 5000,
  "node_executions": [
    {
      "node_id": "node_001",
      "node_type": "ImageCapture",
      "status": "completed",
      "started_at": "2026-05-06T10:30:00Z",
      "completed_at": "2026-05-06T10:30:00.5Z",
      "execution_time_ms": 500,
      "input_data": {},
      "output_data": {"image": "..."}
    },
    {
      "node_id": "node_002",
      "node_type": "YOLOModel",
      "status": "completed",
      "started_at": "2026-05-06T10:30:00.5Z",
      "completed_at": "2026-05-06T10:30:05Z",
      "execution_time_ms": 4500,
      "input_data": {"image": "..."},
      "output_data": {"bboxes": [...], "scores": [...]}
    }
  ],
  "error_message": null
}
```

---

### 6.4 获取执行日志

```
GET /api/rule-engine/executions/{execution_id}/logs
```

**响应：**

```json
{
  "execution": {
    "id": 123,
    "status": "completed"
  },
  "node_logs": [
    {
      "node_id": "node_001",
      "node_type": "ImageCapture",
      "status": "completed",
      "input_data": {},
      "output_data": {"image": "..."},
      "error_message": null,
      "start_time": "2026-05-06T10:30:00Z",
      "end_time": "2026-05-06T10:30:00.5Z"
    }
  ]
}
```

---

## 7. Webhook 触发 API

### 7.1 Webhook 触发端点

```
POST /api/rule-engine/webhook/{graph_id}
```

**请求头：**

| 头信息 | 说明 |
|--------|------|
| X-Secret | Webhook 密钥，用于验证请求来源 |

**请求体：**（任意 JSON，由规则图定义如何使用）

```json
{
  "event": "motion_detected",
  "timestamp": "2026-05-06T10:30:00Z",
  "data": {
    "sensor_id": "camera_01",
    "region": "entrance"
  }
}
```

**响应：**

```json
{
  "execution_id": 124,
  "status": "running",
  "message": "规则图已触发执行"
}
```

**错误响应（密钥验证失败）：**

```json
{
  "detail": "Webhook 密钥验证失败"
}
```

---

## 8. WebSocket 实时通信

### 8.1 连接

```
WebSocket /api/ws/rule-engine
```

**连接参数：**

| 参数 | 说明 |
|------|------|
| execution_id | 可选，订阅特定执行的进度 |

**示例：** `ws://host/api/ws/rule-engine?execution_id=123`

---

### 8.2 客户端 → 服务端消息

```typescript
type ClientMessage =
  | { type: 'subscribe'; execution_id: number }
  | { type: 'unsubscribe'; execution_id: number }
  | { type: 'cancel'; execution_id: number };
```

**subscribe：** 订阅特定执行 ID 的进度推送

**unsubscribe：** 取消订阅

**cancel：** 请求取消正在执行的规则图

---

### 8.3 服务端 → 客户端消息

```typescript
type ServerMessage =
  | { type: 'connected'; session_id: string }
  | { type: 'node_started'; execution_id: number; node_id: string; node_type: string; timestamp: string }
  | { type: 'node_executed'; execution_id: number; node_id: string; status: 'success' | 'failed'; outputs: any; timestamp: string }
  | { type: 'execution_progress'; execution_id: number; progress: number; total_nodes: number; current_level: number; total_levels: number }
  | { type: 'execution_complete'; execution_id: number; status: 'success' | 'failed' | 'cancelled'; result: any; timestamp: string }
  | { type: 'execution_log'; execution_id: number; node_id: string; level: 'info' | 'warn' | 'error'; message: string; timestamp: string };
```

**消息说明（参考调研报告 12.2 ComfyUI WebSocket 协议）：**

| 消息类型 | 触发时机 | 说明 |
|---------|---------|------|
| connected | 连接成功时 | 返回 session_id |
| node_started | 节点开始执行 | 标识某个节点开始工作 |
| node_executed | 节点执行完成 | 包含节点输出或错误 |
| execution_progress | 每层执行完成 | 进度百分比 + 当前层级 |
| execution_complete | 执行全部完成 | 最终状态和结果汇总 |
| execution_log | 任意时刻 | 日志信息（调试用） |

---

### 8.4 WebSocket 消息流程示例

```
客户端                      服务端
  |                           |
  | ---- subscribe ---------> |  {type: "subscribe", execution_id: 123}
  |                           |
  | <--- connected ----------- |  {type: "connected", session_id: "xxx"}
  |                           |
  | <--- node_started -------- |  {type: "node_started", execution_id: 123, node_id: "node_001", ...}
  | <--- node_executed ------- |  {type: "node_executed", execution_id: 123, node_id: "node_001", status: "success", ...}
  |                           |
  | <--- node_started -------- |  {type: "node_started", execution_id: 123, node_id: "node_002", ...}
  | <--- node_executed ------- |  {type: "node_executed", execution_id: 123, node_id: "node_002", ...}
  |                           |
  | <--- execution_progress -- |  {type: "execution_progress", execution_id: 123, progress: 50, current_level: 1, total_levels: 2}
  |                           |
  | <--- execution_complete -- |  {type: "execution_complete", execution_id: 123, status: "success", ...}
  |                           |
```

---

## 9. 错误处理

### 9.1 错误响应格式

所有 API 错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

或

```json
{
  "detail": "错误描述信息",
  "errors": [
    {"field": "nodes_json", "message": "无效的 JSON 格式"}
  ]
}
```

### 9.2 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败（Webhook 密钥错误） |
| 404 | 资源不存在 |
| 422 | 校验失败 |
| 500 | 服务器内部错误 |

---

## 10. API 设计决策说明

### 10.1 为什么不使用嵌套的 nodes 数组？

参考调研报告 3.3 ComfyUI 的设计，我们使用 `Dict[str, Node]` 而非数组：
- **查询优势**：O(1) 节点查找（数组需要遍历）
- **去重保证**：key 即 ID，无需额外校验
- **边管理清晰**：`edges` 独立数组，通过 source/target 引用节点

### 10.2 为什么 inputs 使用 node_id + output 引用？

参考调研报告 8.3 ComfyUI Prompt 格式：
- 引用关系明确，避免嵌套数据拷贝
- 支持序列化传输（JSON 字符串化后直接可用）
- 拓扑排序时容易构建依赖图

### 10.3 WebSocket 为什么不用 REST 轮询？

调研报告 12.2 明确指出 ComfyUI 使用 WebSocket 实现实时进度推送，原因：
- **低延迟**：节点执行完成立即推送，无需轮询间隔
- **双向通信**：支持客户端取消执行
- **状态同步**：断开重连后可从上次状态继续
