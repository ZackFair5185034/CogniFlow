# 规则引擎 API 设计文档
节点定义、规则图 CRUD、执行管理、WebSocket 实时通信

---

## 一、概述
本文档定义 CogniFlow 规则引擎画布编辑器的 API 设计，涵盖节点定义、规则图 CRUD、执行管理、WebSocket 实时通信四大模块。

### 设计原则

 
- RESTful API 为主，WebSocket 处理实时通信 
- 参考 ComfyUI API 风格（Prompt 序列化、队列管理） 
- 前后端数据格式与 Vue Flow 组件模型对齐 

## 二、基础信息
       
| 项目 | 内容 |
| --- | --- |
| Base URL | /api/rule-engine |
| 内容类型 | application/json |
| 认证方式 | （当前未设计认证，未来扩展） |

## 三、节点定义 API

### 3.1 获取所有节点定义
获取前端渲染节点面板所需的完整节点类型信息。

```text
GET /api/rule-engine/nodes/definitions
```

**数据类型对照表：**

             
| 类型标识 | 说明 | 兼容输出类型 |
| --- | --- | --- |
| IMAGE | 图片数据 | IMAGE, MASK |
| BBOX | 检测框坐标列表 | BBOX |
| MASK | 掩码数据 | MASK |
| SCORES | 置信度浮点数列表 | SCORES |
| CLASS_IDS | 类别 ID 整数列表 | CLASS_IDS |
| TRIGGER | 触发信号 | 任意 |
| CONTROL | 控制信号 | CONTROL |
| MODEL | 模型引用 | MODEL |
| ANY | 任意类型 | 任意 |

## 四、规则图 CRUD API

### 4.1 创建规则图

```text
POST /api/rule-engine/graphs
```

### 4.2 列出所有规则图

```text
GET /api/rule-engine/graphs
```

### 4.3 获取规则图详情

```text
GET /api/rule-engine/graphs/{graph_id}
```

### 4.4 获取规则图详情（含解析后数据）

```text
GET /api/rule-engine/graphs/{graph_id}/detail
```

**数据结构说明：**

       
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| nodes | Dict[str, Node] | 节点字典，key 为节点 ID |
| edges | List[Edge] | 边列表 |
| variables | Dict[str, Variable] | 规则变量 |

### 4.5 更新规则图

```text
PUT /api/rule-engine/graphs/{graph_id}
```

### 4.6 删除规则图

```text
DELETE /api/rule-engine/graphs/{graph_id}
```

### 4.7 更新规则图缩略图

```text
PATCH /api/rule-engine/graphs/{graph_id}/thumbnail
```

## 五、规则图校验与激活

### 5.1 校验规则图

```text
POST /api/rule-engine/graphs/{graph_id}/validate
```

**校验项目：**

 
- 节点 ID 无重复 
- 所有输入端口已连接或有默认值 
- 连接的输出端口存在 
- 无环回依赖（拓扑排序检测） 
- 节点类型有效 

### 5.2 激活规则图

```text
POST /api/rule-engine/graphs/{graph_id}/activate
```

**前置条件：**规则图必须通过校验。

### 5.3 停用规则图

```text
POST /api/rule-engine/graphs/{graph_id}/deactivate
```

## 六、执行管理 API

### 6.1 手动触发执行

```text
POST /api/rule-engine/execute
```

**trigger_type 可选值：**

       
| 值 | 说明 |
| --- | --- |
| manual | 手动触发（用户点击执行按钮） |
| timer | 定时触发（由 APScheduler 内部调用） |
| webhook | Webhook 触发（由 webhook 接口内部调用） |

### 6.2 获取执行历史

```text
GET /api/rule-engine/executions?graph_id=1&limit=50
```

### 6.3 获取执行详情

```text
GET /api/rule-engine/executions/{execution_id}
```

### 6.4 获取执行日志

```text
GET /api/rule-engine/executions/{execution_id}/logs
```

## 七、Webhook 触发 API

### 7.1 Webhook 触发端点

```text
POST /api/rule-engine/webhook/{graph_id}
```

**请求头：**

     
| 头信息 | 说明 |
| --- | --- |
| X-Secret | Webhook 密钥，用于验证请求来源 |

## 八、WebSocket 实时通信

### 8.1 连接

```text
WebSocket /api/ws/rule-engine
```

### 8.2 客户端 → 服务端消息
       
| 消息类型 | 说明 |
| --- | --- |
| subscribe | 订阅特定执行 ID 的进度推送 |
| unsubscribe | 取消订阅 |
| cancel | 请求取消正在执行的规则图 |

### 8.3 服务端 → 客户端消息
          
| 消息类型 | 触发时机 | 说明 |
| --- | --- | --- |
| connected | 连接成功时 | 返回 session_id |
| node_started | 节点开始执行 | 标识某个节点开始工作 |
| node_executed | 节点执行完成 | 包含节点输出或错误 |
| execution_progress | 每层执行完成 | 进度百分比 + 当前层级 |
| execution_complete | 执行全部完成 | 最终状态和结果汇总 |
| execution_log | 任意时刻 | 日志信息（调试用） |

### 8.4 WebSocket 消息流程示例

```text
客户端                      服务端
  |                           |
  | ---- subscribe ---------> |  {type: "subscribe", execution_id: 123}
  |                           |
  | <--- connected ----------- |  {type: "connected", session_id: "xxx"}
  |                           |
  | <--- node_started -------- |  {type: "node_started", ...}
  | <--- node_executed ------- |  {type: "node_executed", ...}
  |                           |
  | <--- execution_progress -- |  {type: "execution_progress", ...}
  |                           |
  | <--- execution_complete -- |  {type: "execution_complete", ...}
  |                           |
```

## 九、错误处理

### 9.1 错误响应格式

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
| --- | --- |
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败（Webhook 密钥错误） |
| 404 | 资源不存在 |
| 422 | 校验失败 |
| 500 | 服务器内部错误 |

## 十、API 设计决策说明

### 10.1 为什么不使用嵌套的 nodes 数组？
参考 ComfyUI 的设计，我们使用 Dict[str, Node] 而非数组：

 
- **查询优势：**O(1) 节点查找（数组需要遍历） 
- **去重保证：**key 即 ID，无需额外校验 
- **边管理清晰：**edges 独立数组，通过 source/target 引用节点 

### 10.2 为什么 inputs 使用 node_id + output 引用？

 
- 引用关系明确，避免嵌套数据拷贝 
- 支持序列化传输（JSON 字符串化后直接可用） 
- 拓扑排序时容易构建依赖图 

### 10.3 WebSocket 为什么不用 REST 轮询？

 
- **低延迟：**节点执行完成立即推送，无需轮询间隔 
- **双向通信：**支持客户端取消执行 
- **状态同步：**断开重连后可从上次状态继续
