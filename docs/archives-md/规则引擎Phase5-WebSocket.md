# Phase 5 技术实现文档：实时通信（WebSocket）
实现 WebSocket 实时推送机制，让前端实时显示规则执行进度

---

## 一、阶段目标
**目标：**实现 WebSocket 实时推送机制，让前端实时显示规则执行进度。

**验收标准：**

 
- WebSocket 连接在打开规则图时自动建立 
- 执行开始后，前端实时显示节点执行状态（pending → running → completed/failed） 
- 每层执行完成后，进度条更新 
- 执行完成后，弹出结果摘要 
- 执行失败时，显示错误详情和失败的节点 
- 连接断开时自动重连 

## 二、WebSocket 协议

### 2.1 消息类型
            
| 方向 | 类型 | 字段 |
| --- | --- | --- |
| 客户端 → 服务端 | `subscribe` | execution_id |
| 客户端 → 服务端 | `unsubscribe` | execution_id |
| 客户端 → 服务端 | `cancel` | execution_id |
| 服务端 → 客户端 | `node_started` | execution_id, node_id, node_type, timestamp |
| 服务端 → 客户端 | `node_executed` | execution_id, node_id, status, outputs, timestamp |
| 服务端 → 客户端 | `node_failed` | execution_id, node_id, error, timestamp |
| 服务端 → 客户端 | `execution_progress` | execution_id, progress, current_level, total_levels, completed_nodes, total_nodes |
| 服务端 → 客户端 | `execution_complete` | execution_id, status, result?, error? |

## 三、后端 WebSocket 管理器

### 3.1 ConnectionManager
连接管理器负责管理所有活跃的 WebSocket 连接，按 execution_id 订阅/取消订阅：

 
- `_connections` — websocket → set of execution_ids 
- `_subscriptions` — execution_id → set of websockets 
- `connect()` — 客户端连接，自动订阅 
- `broadcast()` — 向订阅者广播消息 
- `subscribe()` / `unsubscribe()` — 动态订阅/取消 

### 3.2 集成到执行引擎

```python
class RuleGraphExecutor:
    def __init__(self, db=None, ws_manager=None):
        self.db = db
        self.ws_manager = ws_manager or connection_manager

    async def _broadcast_node_started(self, execution_id, node_id, node_type):
        await self.ws_manager.broadcast({
            "type": "node_started",
            "execution_id": execution_id,
            "node_id": node_id,
            "node_type": node_type,
            "timestamp": datetime.now().isoformat()
        }, execution_id=execution_id)

    async def _broadcast_progress(self, execution_id, current_level, total_levels, ...):
        await self.ws_manager.broadcast({
            "type": "execution_progress",
            "progress": int((current_level + 1) / total_levels * 100),
            ...
        }, execution_id=execution_id)
```

### 3.3 FastAPI WebSocket 端点

```python
@router.websocket("/ws/rule-execution")
async def rule_execution_websocket(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "subscribe":
                await connection_manager.subscribe(websocket, data.get("execution_id"))
            elif msg_type == "unsubscribe":
                await connection_manager.unsubscribe(websocket, data.get("execution_id"))
            elif msg_type == "cancel":
                RuleGraphExecutor.cancel_execution(data.get("execution_id"))
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
```

## 四、前端 WebSocket 服务

### 4.1 WebSocketService
前端 WebSocket 服务封装了连接管理、自动重连和消息分发：

 
- `connect()` — 建立连接，重连时自动恢复订阅 
- `subscribe(executionId)` — 订阅执行进度 
- `cancel(executionId)` — 取消执行 
- `on(type, handler)` — 注册消息处理器 
- `off(type, handler)` — 取消消息处理器 
*自动重连：最多 5 次，延迟 1s/2s/4s/8s/16s 指数退避*

### 4.2 executionStore
Pinia Store 管理执行状态：

 
- `nodeStatuses` — Map<nodeId, NodeExecutionStatus> 
- `progress` / `currentLevel` / `totalLevels` 
- `executionStatus` — idle/running/completed/failed/cancelled 
- `startExecution()` / `cancelExecution()` / `endExecution()` 

## 五、前端执行进度组件

### 5.1 ExecutionProgress 组件
执行进度覆盖层（Overlay），包含：

 
- 进度百分比和层信息 
- 进度条（CSS 渐变动画） 
- 正在执行的节点徽章列表 
- 失败的节点及其错误信息 
- 取消执行按钮 

### 5.2 ExecutionStatusBadge 组件
节点状态徽章，跟随节点显示在右上角：

         
| 状态 | 样式 |
| --- | --- |
| `pending` | 灰色 |
| `running` | 青色 + 脉冲动画 |
| `completed` | 绿色 |
| `failed` | 红色 |
| `cancelled` | 红色 |

## 六、验收检查清单
                   
| 类别 | 验收项 |
| --- | --- |
| WebSocket 连接 | 连接在打开规则图时自动建立 |
| 连接断开后自动重连（最多 5 次） |  |
| 重连后自动恢复订阅 |  |
| 状态更新 | 节点开始执行时状态变为 running |
| 节点执行成功时状态变为 completed |  |
| 节点执行失败时状态变为 failed，显示错误 |  |
| 执行被取消时状态变为 cancelled |  |
| 进度显示 | 进度条实时更新（0-100%） |
| 显示当前层/总层数 |  |
| 显示已完成节点/总节点数 |  |
| 结果展示 | 执行完成后弹出结果摘要 |
| 失败时显示错误详情和失败节点 |  |
| 可关闭结果面板 |  |
| 取消功能 | 取消按钮能终止执行 |
| 取消后画布状态正确更新 |  |
