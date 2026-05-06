# Phase 5 技术实现文档：实时通信（WebSocket）

> ⚠️ **实现前审核状态：** 待老大评审
> 文档版本：v1.0
> 基于调研：canvas-editor-research-2026-05-06.md
> 阶段：Phase 5
> 创建时间：2026-05-06

---

## 1. 阶段目标

**目标：** 实现 WebSocket 实时推送机制，让前端实时显示规则执行进度。

**验收标准：**
- [ ] WebSocket 连接在打开规则图时自动建立
- [ ] 执行开始后，前端实时显示节点执行状态（pending → running → completed/failed）
- [ ] 每层执行完成后，进度条更新
- [ ] 执行完成后，弹出结果摘要
- [ ] 执行失败时，显示错误详情和失败的节点
- [ ] 连接断开时自动重连

---

## 2. WebSocket 协议

### 2.1 消息类型（参考调研 4.5）

```typescript
// webui/src/types/websocket.ts

// ========== 客户端 → 服务端 ==========

interface SubscribeMessage {
  type: 'subscribe'
  execution_id: number
}

interface UnsubscribeMessage {
  type: 'unsubscribe'
  execution_id: number
}

interface CancelExecutionMessage {
  type: 'cancel'
  execution_id: number
}

// ========== 服务端 → 客户端 ==========

interface NodeStartedMessage {
  type: 'node_started'
  execution_id: number
  node_id: string
  node_type: string
  timestamp: string
}

interface NodeExecutedMessage {
  type: 'node_executed'
  execution_id: number
  node_id: string
  status: 'success'
  outputs: Record<string, any>
  timestamp: string
}

interface NodeFailedMessage {
  type: 'node_failed'
  execution_id: number
  node_id: string
  error: string
  timestamp: string
}

interface ExecutionProgressMessage {
  type: 'execution_progress'
  execution_id: number
  progress: number
  current_level: number
  total_levels: number
  completed_nodes: number
  total_nodes: number
  timestamp: string
}

interface ExecutionCompleteMessage {
  type: 'execution_complete'
  execution_id: number
  status: 'completed' | 'failed' | 'cancelled'
  result?: { node_results: Record<string, any> }
  error?: string
  timestamp: string
}

type ServerMessage =
  | NodeStartedMessage
  | NodeExecutedMessage
  | NodeFailedMessage
  | ExecutionProgressMessage
  | ExecutionCompleteMessage
```

---

## 3. 后端 WebSocket 管理器

### 3.1 ConnectionManager

```python
# backend/services/rule_engine/websocket_manager.py

import asyncio
import json
from typing import Dict, Set, List, Optional
from fastapi import WebSocket
from datetime import datetime


class ConnectionManager:
    """WebSocket 连接管理器。

    负责：
    1. 管理所有活跃的 WebSocket 连接
    2. 按 execution_id 订阅/取消订阅
    3. 向订阅的连接推送消息
    """

    def __init__(self):
        # 所有活跃连接: websocket -> set of execution_ids
        self._connections: Dict[WebSocket, Set[int]] = {}

        # execution_id -> set of subscribed websockets
        self._subscriptions: Dict[int, Set[WebSocket]] = {}

        # 锁，保证线程安全
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, execution_ids: List[int] = None):
        """客户端连接。"""
        await websocket.accept()

        async with self._lock:
            self._connections[websocket] = set(execution_ids or [])

            for eid in execution_ids or []:
                if eid not in self._subscriptions:
                    self._subscriptions[eid] = set()
                self._subscriptions[eid].add(websocket)

    async def disconnect(self, websocket: WebSocket):
        """客户端断开连接。"""
        async with self._lock:
            execution_ids = self._connections.pop(websocket, set())

            for eid in execution_ids:
                if eid in self._subscriptions:
                    self._subscriptions[eid].discard(websocket)

    async def subscribe(self, websocket: WebSocket, execution_id: int):
        """订阅执行更新。"""
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket].add(execution_id)

            if execution_id not in self._subscriptions:
                self._subscriptions[execution_id] = set()
            self._subscriptions[execution_id].add(websocket)

    async def unsubscribe(self, websocket: WebSocket, execution_id: int):
        """取消订阅。"""
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket].discard(execution_id)

            if execution_id in self._subscriptions:
                self._subscriptions[execution_id].discard(websocket)

    async def broadcast(
        self,
        message: dict,
        execution_id: Optional[int] = None
    ):
        """向订阅的客户端广播消息。"""
        message_str = json.dumps(message, ensure_ascii=False)

        async with self._lock:
            if execution_id is not None:
                websockets = self._subscriptions.get(execution_id, set())
            else:
                websockets = set(self._connections.keys())

            disconnected = set()

            for websocket in websockets:
                try:
                    await websocket.send_text(message_str)
                except Exception:
                    disconnected.add(websocket)

            for websocket in disconnected:
                await self.disconnect(websocket)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """发送消息给单个客户端。"""
        try:
            await websocket.send_json(message)
        except Exception:
            await self.disconnect(websocket)


# 全局连接管理器实例
connection_manager = ConnectionManager()
```

### 3.2 集成到执行引擎

```python
# backend/services/rule_engine/executor.py

class RuleGraphExecutor:
    """规则图执行引擎。"""

    def __init__(self, db=None, ws_manager=None):
        self.db = db
        self.ws_manager = ws_manager or connection_manager

    async def _broadcast_node_started(
        self,
        execution_id: int,
        node_id: str,
        node_type: str
    ):
        """广播节点开始执行。"""
        await self.ws_manager.broadcast(
            {
                "type": "node_started",
                "execution_id": execution_id,
                "node_id": node_id,
                "node_type": node_type,
                "timestamp": datetime.now().isoformat()
            },
            execution_id=execution_id
        )

    async def _broadcast_progress(
        self,
        execution_id: int,
        current_level: int,
        total_levels: int,
        nodes_in_level: int,
        total_nodes: int
    ):
        """广播执行进度。"""
        completed_nodes = sum(
            len(level) for i, level in enumerate([])
            if i < current_level
        ) + nodes_in_level

        await self.ws_manager.broadcast(
            {
                "type": "execution_progress",
                "execution_id": execution_id,
                "progress": int((current_level + 1) / total_levels * 100),
                "current_level": current_level + 1,
                "total_levels": total_levels,
                "completed_nodes": completed_nodes,
                "total_nodes": total_nodes,
                "timestamp": datetime.now().isoformat()
            },
            execution_id=execution_id
        )

    async def _broadcast_complete(
        self,
        execution_id: int,
        status: str,
        result: dict = None,
        error: str = None
    ):
        """广播执行完成。"""
        message = {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }

        if result:
            message["result"] = result

        if error:
            message["error"] = error

        await self.ws_manager.broadcast(message, execution_id=execution_id)
```

---

## 4. FastAPI WebSocket 路由

### 4.1 WebSocket 端点

```python
# backend/routers/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

from backend.services.rule_engine.websocket_manager import connection_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/rule-execution")
async def rule_execution_websocket(websocket: WebSocket):
    """规则执行 WebSocket 连接。

    客户端连接时订阅指定的执行 ID，
    之后会收到该执行的所有进度更新。

    消息格式：
    - 客户端发送: {"type": "subscribe", "execution_id": 123}
    - 客户端发送: {"type": "unsubscribe", "execution_id": 123}
    - 客户端发送: {"type": "cancel", "execution_id": 123}
    """
    await connection_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            msg_type = data.get("type")

            if msg_type == "subscribe":
                execution_id = data.get("execution_id")
                if execution_id:
                    await connection_manager.subscribe(websocket, execution_id)

            elif msg_type == "unsubscribe":
                execution_id = data.get("execution_id")
                if execution_id:
                    await connection_manager.unsubscribe(websocket, execution_id)

            elif msg_type == "cancel":
                execution_id = data.get("execution_id")
                if execution_id:
                    from backend.services.rule_engine.executor import RuleGraphExecutor
                    RuleGraphExecutor.cancel_execution(execution_id)

    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception:
        await connection_manager.disconnect(websocket)
```

---

## 5. 前端 WebSocket 服务

### 5.1 WebSocketService

```typescript
// webui/src/services/websocket.ts

type MessageHandler = (data: any) => void

export class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private handlers: Map<string, Set<MessageHandler>> = new Map()
  private subscriptionIds: Set<number> = new Set()

  public connected = ref(false)
  public error = ref<string | null>(null)

  constructor(url: string) {
    this.url = url
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.connected.value = true
        this.error.value = null
        this.reconnectAttempts = 0

        for (const id of this.subscriptionIds) {
          this.send({ type: 'subscribe', execution_id: id })
        }
      }

      this.ws.onclose = () => {
        this.connected.value = false
        this.ws = null

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts)
        }
      }

      this.ws.onerror = (event) => {
        this.error.value = 'WebSocket 连接错误'
        console.error('WebSocket error:', event)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

    } catch (e) {
      this.error.value = 'WebSocket 连接失败'
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected.value = false
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  subscribe(executionId: number) {
    this.subscriptionIds.add(executionId)
    this.send({ type: 'subscribe', execution_id: executionId })
  }

  unsubscribe(executionId: number) {
    this.subscriptionIds.delete(executionId)
    this.send({ type: 'unsubscribe', execution_id: executionId })
  }

  cancel(executionId: number) {
    this.send({ type: 'cancel', execution_id: executionId })
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)
  }

  off(type: string, handler: MessageHandler) {
    this.handlers.get(type)?.delete(handler)
  }

  private handleMessage(data: any) {
    const handlers = this.handlers.get(data.type)
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(data)
        } catch (e) {
          console.error(`Handler error for ${data.type}:`, e)
        }
      }
    }
  }
}

let wsService: WebSocketService | null = null

export function getWebSocketService(): WebSocketService {
  if (!wsService) {
    const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/rule-execution`
    wsService = new WebSocketService(wsUrl)
  }
  return wsService
}
```

---

## 6. 前端执行状态管理

### 6.1 executionStore

```typescript
// webui/src/stores/execution.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getWebSocketService } from '@/services/websocket'

export interface NodeExecutionStatus {
  node_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  outputs?: Record<string, any>
  error?: string
}

export const useExecutionStore = defineStore('execution', () => {
  const currentExecutionId = ref<number | null>(null)
  const nodeStatuses = ref<Map<string, NodeExecutionStatus>>(new Map())
  const progress = ref(0)
  const currentLevel = ref(0)
  const totalLevels = ref(0)
  const totalNodes = ref(0)
  const completedNodes = ref(0)
  const executionStatus = ref<'idle' | 'running' | 'completed' | 'failed' | 'cancelled'>('idle')
  const errorMessage = ref<string | null>(null)

  const wsService = getWebSocketService()

  function initWebSocket() {
    wsService.on('node_started', (data) => {
      if (data.execution_id !== currentExecutionId.value) return

      nodeStatuses.value.set(data.node_id, {
        node_id: data.node_id,
        status: 'running'
      })
    })

    wsService.on('node_executed', (data) => {
      if (data.execution_id !== currentExecutionId.value) return

      nodeStatuses.value.set(data.node_id, {
        node_id: data.node_id,
        status: 'completed',
        outputs: data.outputs
      })
    })

    wsService.on('node_failed', (data) => {
      if (data.execution_id !== currentExecutionId.value) return

      nodeStatuses.value.set(data.node_id, {
        node_id: data.node_id,
        status: 'failed',
        error: data.error
      })

      errorMessage.value = data.error
    })

    wsService.on('execution_progress', (data) => {
      if (data.execution_id !== currentExecutionId.value) return

      progress.value = data.progress
      currentLevel.value = data.current_level
      totalLevels.value = data.total_levels
      totalNodes.value = data.total_nodes
      completedNodes.value = data.completed_nodes
    })

    wsService.on('execution_complete', (data) => {
      if (data.execution_id !== currentExecutionId.value) return

      executionStatus.value = data.status

      if (data.status === 'failed') {
        errorMessage.value = data.error
      }

      progress.value = 100
    })

    wsService.connect()
  }

  function startExecution(executionId: number) {
    currentExecutionId.value = executionId
    executionStatus.value = 'running'
    progress.value = 0
    nodeStatuses.value.clear()
    errorMessage.value = null

    wsService.subscribe(executionId)
  }

  function cancelExecution() {
    if (currentExecutionId.value !== null) {
      wsService.cancel(currentExecutionId.value)
    }
  }

  function endExecution() {
    if (currentExecutionId.value !== null) {
      wsService.unsubscribe(currentExecutionId.value)
      currentExecutionId.value = null
    }
  }

  function getNodeStatus(nodeId: string): NodeExecutionStatus | undefined {
    return nodeStatuses.value.get(nodeId)
  }

  return {
    currentExecutionId,
    nodeStatuses,
    progress,
    currentLevel,
    totalLevels,
    totalNodes,
    completedNodes,
    executionStatus,
    errorMessage,
    initWebSocket,
    startExecution,
    cancelExecution,
    endExecution,
    getNodeStatus
  }
})
```

---

## 7. 前端执行进度组件

### 7.1 ExecutionProgress 组件

```vue
<!-- webui/src/components/rule-canvas/ExecutionProgress.vue -->

<template>
  <div class="execution-progress" v-if="visible">
    <div class="progress-overlay">
      <div class="progress-card">
        <h3>规则执行中</h3>

        <div class="progress-info">
          <span>进度: {{ progress }}%</span>
          <span>层: {{ currentLevel }}/{{ totalLevels }}</span>
          <span>节点: {{ completedNodes }}/{{ totalNodes }}</span>
        </div>

        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>

        <div class="running-nodes" v-if="runningNodes.length > 0">
          <span class="label">正在执行:</span>
          <span v-for="node in runningNodes" :key="node.node_id" class="node-badge">
            {{ getNodeLabel(node.node_id) }}
          </span>
        </div>

        <div class="failed-info" v-if="failedNodes.length > 0">
          <span class="label error">失败:</span>
          <span v-for="node in failedNodes" :key="node.node_id" class="node-badge error">
            {{ getNodeLabel(node.node_id) }} - {{ node.error }}
          </span>
        </div>

        <div class="progress-actions">
          <button class="btn cancel" @click="onCancel">取消执行</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useExecutionStore } from '@/stores/execution'
import { useRuleCanvasStore } from '@/stores/ruleCanvas'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const executionStore = useExecutionStore()
const canvasStore = useRuleCanvasStore()

const progress = computed(() => executionStore.progress)
const currentLevel = computed(() => executionStore.currentLevel)
const totalLevels = computed(() => executionStore.totalLevels)
const completedNodes = computed(() => executionStore.completedNodes)
const totalNodes = computed(() => executionStore.totalNodes)

const runningNodes = computed(() => {
  return Array.from(canvasStore.nodes.values())
    .filter(n => executionStore.getNodeStatus(n.id)?.status === 'running')
})

const failedNodes = computed(() => {
  return Array.from(canvasStore.nodes.values())
    .filter(n => executionStore.getNodeStatus(n.id)?.status === 'failed')
    .map(n => ({
      node_id: n.id,
      error: executionStore.getNodeStatus(n.id)?.error
    }))
})

function getNodeLabel(nodeId: string): string {
  const node = canvasStore.nodes.get(nodeId)
  return node?.data?.label || nodeId
}

function onCancel() {
  executionStore.cancelExecution()
}
</script>

<style scoped>
.execution-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

.progress-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-card {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 24px;
  min-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.progress-card h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: var(--text-primary);
}

.progress-info {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.progress-bar {
  height: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
  transition: width 0.3s ease;
}

.running-nodes,
.failed-info {
  margin-bottom: 12px;
}

.label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-right: 8px;
}

.label.error {
  color: var(--accent-red);
}

.node-badge {
  display: inline-block;
  font-size: 12px;
  background: var(--bg-card);
  padding: 4px 8px;
  border-radius: 4px;
  margin-right: 4px;
  color: var(--accent-cyan);
}

.node-badge.error {
  color: var(--accent-red);
}

.progress-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.btn.cancel {
  background: transparent;
  border: 1px solid var(--accent-red);
  color: var(--accent-red);
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
}

.btn.cancel:hover {
  background: rgba(255, 76, 76, 0.1);
}
</style>
```

---

## 8. 节点状态可视化

### 8.1 自定义节点组件状态

```vue
<!-- webui/src/components/rule-canvas/nodes/ExecutionStatusBadge.vue -->

<template>
  <div class="status-badge" :class="status">
    <span class="dot"></span>
    <span class="label">{{ statusText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
}>()

const statusText = computed(() => {
  const texts = {
    pending: '等待',
    running: '执行中',
    completed: '完成',
    failed: '失败',
    cancelled: '取消'
  }
  return texts[props.status]
})
</script>

<style scoped>
.status-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  z-index: 10;
}

.status-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-badge.pending {
  background: var(--bg-card);
  color: var(--text-muted);
}

.status-badge.pending .dot {
  background: var(--text-muted);
}

.status-badge.running {
  background: rgba(0, 240, 255, 0.2);
  color: var(--accent-cyan);
}

.status-badge.running .dot {
  background: var(--accent-cyan);
  animation: pulse 1s infinite;
}

.status-badge.completed {
  background: rgba(76, 255, 76, 0.2);
  color: #4CFF4C;
}

.status-badge.completed .dot {
  background: #4CFF4C;
}

.status-badge.failed {
  background: rgba(255, 76, 76, 0.2);
  color: var(--accent-red);
}

.status-badge.failed .dot {
  background: var(--accent-red);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
```

### 8.2 节点集成

```vue
<!-- webui/src/components/rule-canvas/nodes/DetectionNode.vue -->

<template>
  <div class="vue-flow-node detection-node" :class="nodeClass">
    <NodeHeader :color="nodeColor" :icon="icon">
      {{ data.label }}
    </NodeHeader>

    <div class="node-body">
      <div class="input-handles">
        <Handle
          v-for="(port, key) in inputPorts"
          :key="key"
          type="target"
          :position="Position.Left"
          :id="key as string"
          :style="{ top: getHandleTop(key as string) + 'px' }"
        />
      </div>

      <div class="node-content">
        <div class="param-preview" v-if="modelName">
          模型: {{ modelName }}
        </div>
      </div>

      <div class="output-handles">
        <Handle
          v-for="(port, key) in outputPorts"
          :key="key"
          type="source"
          :position="Position.Right"
          :id="key as string"
          :style="{ top: getHandleTop(key as string) + 'px', background: portColors[key as string] }"
        />
      </div>
    </div>

    <!-- 状态徽章 -->
    <ExecutionStatusBadge :status="executionStatus" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import NodeHeader from './NodeHeader.vue'
import ExecutionStatusBadge from './ExecutionStatusBadge.vue'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps<{
  id: string
  data: any
}>()

const executionStore = useExecutionStore()

const executionStatus = computed(() =>
  executionStore.getNodeStatus(props.id)?.status || 'pending'
)

const nodeClass = computed(() => ({
  'is-running': executionStatus.value === 'running',
  'is-completed': executionStatus.value === 'completed',
  'is-failed': executionStatus.value === 'failed'
}))
</script>
```

---

## 9. 验收检查清单

### 9.1 WebSocket 连接
- [ ] 连接在打开规则图时自动建立
- [ ] 连接断开后自动重连（最多 5 次）
- [ ] 重连后自动恢复订阅

### 9.2 状态更新
- [ ] 节点开始执行时状态变为 running
- [ ] 节点执行成功时状态变为 completed
- [ ] 节点执行失败时状态变为 failed，显示错误
- [ ] 执行被取消时状态变为 cancelled

### 9.3 进度显示
- [ ] 进度条实时更新（0-100%）
- [ ] 显示当前层/总层数
- [ ] 显示已完成节点/总节点数

### 9.4 结果展示
- [ ] 执行完成后弹出结果摘要
- [ ] 失败时显示错误详情和失败节点
- [ ] 可关闭结果面板

### 9.5 取消功能
- [ ] 取消按钮能终止执行
- [ ] 取消后画布状态正确更新
