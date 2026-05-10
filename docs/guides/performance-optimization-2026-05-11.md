# CogniFlow 规则引擎性能优化方案

**调研日期**: 2026-05-11
**项目路径**: `/home/coding/CogniFlow`

---

## 一、调研概述

本次调研覆盖 CogniFlow 规则引擎的四个核心性能领域：前端 VueFlow 画布渲染、后端 Kahn 拓扑排序执行引擎、SQLAlchemy 数据库查询、WebSocket 实时推送。

---

## 二、前端 VueFlow 画布性能

### 2.1 发现的问题

#### 问题 1: `nodes` 和 `edges` 直接响应式绑定导致过度渲染

**文件**: `webui/src/views/RuleCanvas.vue` (lines 339-340)

```javascript
v-model:nodes="nodes"
v-model:edges="edges"
```

`nodes` 和 `edges` 使用 `ref<any[]>([])` 直接绑定，当节点数量较多时（>100），每次拖拽、缩放都会触发 VueFlow 内部的节点更新，进而触发完整的响应式更新链路。

**影响**: 节点数 >100 时可能出现明显卡顿。

#### 问题 2: `filteredCategories` 计算属性每次调用创建新数组

**文件**: `RuleCanvas.vue` (lines 731-750)

```javascript
const filteredCategories = computed(() => {
  const query = nodeSearchQuery.value.trim().toLowerCase()
  if (!query) {
    return nodeCategories.value  // 返回引用，无额外开销
  }
  return nodeCategories.value
    .map(cat => ({
      ...cat,
      nodes: cat.nodes.filter((n: any) => /* ... */),
      expanded: true
    }))
    .filter(cat => cat.nodes.length > 0)
})
```

当存在搜索词时，每次调用都会 `.map()` 创建新数组对象，且内部 `filter` 创建更多临时数组。

#### 问题 3: `miniMapNodeColor` 函数每次调用创建颜色映射对象

**文件**: `RuleCanvas.vue` (lines 797-807)

```javascript
function miniMapNodeColor(node: any) {
  const colors: Record<string, string> = {
    input: '#4CFF4C',
    detection: '#00f0FF',
    // ...
  }
  return colors[node.category] || '#888'
}
```

此函数在 MiniMap 渲染每个节点时调用，每次创建新的 `colors` 对象。

#### 问题 4: `handleNodesChange` 中频繁保存历史记录

**文件**: `RuleCanvas.vue` (lines 1515-1527)

```javascript
function handleNodesChange(changes: any[]) {
  const hasRemoval = changes.some(c => c.type === 'remove')
  if (hasRemoval) {
    // ...
    saveHistory()  // 每次节点删除都保存历史
  }
}
```

`saveHistory()` 会对 `nodes` 和 `edges` 进行 `JSON.parse(JSON.stringify(...))` 深拷贝，在频繁操作时开销明显。

#### 问题 5: RuleNode 子组件 computed 属性未优化

**文件**: `webui/src/components/rule-engine/RuleNode.vue`

- `configProperties` (line 299): 每次访问都 `Object.create(null)`
- `nodeConfig` (line 309): 每次访问都遍历 schema 构建 defaults
- `configSummary` (line 407): 每次访问都遍历 `summaryKeys`

这些 computed 在节点配置面板打开时会频繁访问。

### 2.2 优化建议

#### 优化 1: 使用 `shallowRef` 减少大规模响应式开销

```typescript
// 将 nodes 和 edges 改为 shallowRef
import { shallowRef } from 'vue'

const nodes = shallowRef<any[]>([])
const edges = shallowRef<any[]>([])

// 配合 VueFlow 的 :after-change 回调手动触发必要更新
function handleNodesChange(changes: any[]) {
  // 仅在最终变更后更新，避免中间状态触发渲染
  nextTick(() => {
    nodes.value = [...vueFlowRef.value.getNodes()]
  })
}
```

#### 优化 2: 缓存 `filteredCategories` 结果

```typescript
const filteredCategories = computed(() => {
  const query = nodeSearchQuery.value.trim().toLowerCase()
  if (!query) {
    return nodeCategories.value
  }
  
  // 使用 Map 缓存搜索结果
  const cacheKey = query
  if (!_filteredCache.has(cacheKey)) {
    _filteredCache.set(cacheKey, nodeCategories.value
      .map(cat => ({
        ...cat,
        nodes: cat.nodes.filter((n: any) =>
          n.label?.toLowerCase().includes(query) ||
          n.type?.toLowerCase().includes(query)
        ),
        expanded: true
      }))
      .filter(cat => cat.nodes.length > 0)
    )
  }
  return _filteredCache.get(cacheKey)!
})
```

#### 优化 3: 提取颜色映射为模块常量

```typescript
// 提取到组件外部
const NODE_CATEGORY_COLORS: Record<string, string> = {
  input: '#4CFF4C',
  detection: '#00f0FF',
  processing: '#FFFF4C',
  action: '#FF7F4C',
  logic: '#DC4FDC',
  output: '#FF4C4C'
}

function miniMapNodeColor(node: any) {
  return NODE_CATEGORY_COLORS[node.category] || '#888'
}
```

#### 优化 4: 批量保存历史记录 + 防抖

```typescript
import { debounce } from 'lodash-es'

const flushHistory = debounce(() => {
  saveHistory()
}, 500)

function handleNodesChange(changes: any[]) {
  const hasRemoval = changes.some(c => c.type === 'remove')
  if (hasRemoval) {
    flushHistory()
  }
}

// 组件卸载时取消
onBeforeUnmount(() => flushHistory.cancel())
```

#### 优化 5: RuleNode 添加 v-memo 减少不必要的重新渲染

```vue
<div
  class="rule-node"
  v-memo="[data.category, data.status, nodeConfig]"
>
```

---

## 三、后端执行引擎性能

### 3.1 发现的问题

#### 问题 1: Kahn 拓扑排序实现基本合理，但存在优化空间

**文件**: `backend/services/rule_engine/executor.py` (lines 169-260)

当前实现使用标准 Kahn 算法，复杂度 O(V+E)：
- `build_dependency_graph`: O(E) 构建邻接表
- `topological_sort_levels`: O(V+E) 处理所有节点和边

**潜在瓶颈**:
1. `_find_cycle_nodes` 使用递归 DFS，对极深图可能触发 Python 递归限制
2. 每层执行完后调用 `_broadcast_progress`，如果层数多会产生大量 WebSocket 消息

#### 问题 2: `asyncio.gather` 并发执行同层节点

**文件**: `executor.py` (lines 458-469)

```python
async def _execute_level(self, level: List[str], context: ExecutionContext):
    tasks = [
        self._execute_node(node_id, context)
        for node_id in level
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

实现正确，同层节点确实并行执行。但需注意：
- 如果单层节点数过多（如 >50），`asyncio.gather` 创建大量 Task 开销明显
- 节点执行如果涉及 CPU 密集型操作，GIL 会限制并行效果

#### 问题 3: 执行上下文缓存所有节点结果

**文件**: `base.py` (lines 63-66)

```python
@dataclass
class ExecutionContext:
    node_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
```

所有节点的输出都缓存在内存中。如果：
- 节点输出数据量很大（如图片、检测结果）
- 图非常复杂（>500 节点）

可能导致内存压力。

#### 问题 4: 进度广播过于频繁

**文件**: `executor.py` (lines 681-705)

```python
async def _broadcast_progress(
    self, execution_id, current_level, total_levels, ...
):
    # 每层执行完后都广播
```

如果图有 50 层，会产生 50 次 WebSocket 广播消息。

### 3.2 优化建议

#### 优化 1: 消除递归 DFS，改为迭代实现

```python
def _find_cycle_nodes(
    self,
    graph: Dict[str, List[str]],
    remaining: Set[str]
) -> List[str]:
    """迭代版本避免递归栈溢出"""
    if not remaining:
        return []
    
    visited: Set[str] = set()
    path: List[str] = []
    
    for start_node in remaining:
        if start_node in visited:
            continue
        
        stack = [(start_node, iter(graph.get(start_node, [])))]
        path_stack = [start_node]
        
        while stack:
            node, neighbors = stack[-1]
            try:
                neighbor = next(neighbors)
                if neighbor not in visited:
                    if neighbor in path_stack:
                        cycle_start = path_stack.index(neighbor)
                        return path_stack[cycle_start:] + [neighbor]
                    visited.add(neighbor)
                    stack.append((neighbor, iter(graph.get(neighbor, []))))
                    path_stack.append(neighbor)
                else:
                    continue
            except StopIteration:
                stack.pop()
                path_stack.pop()
    
    return list(remaining)
```

#### 优化 2: 限制单层最大并发数

```python
MAX_CONCURRENCY = 20  # 限制同层最大并发

async def _execute_level(self, level: List[str], context: ExecutionContext):
    # 分批处理避免创建过多 Task
    for i in range(0, len(level), MAX_CONCURRENCY):
        batch = level[i:i + MAX_CONCURRENCY]
        tasks = [self._execute_node(node_id, context) for node_id in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
```

#### 优化 3: 大图场景下流式处理节点结果

```python
# 节点结果超过阈值时清理旧结果
MAX_CACHED_RESULTS = 100

if len(context.node_results) > MAX_CACHED_RESULTS:
    # 保留最近使用的，清理最旧的
    oldest_keys = list(context.node_results.keys())[:-MAX_CACHED_RESULTS]
    for k in oldest_keys:
        del context.node_results[k]
```

#### 优化 4: 进度广播降频

```python
# 仅在关键节点完成或每 N% 进度时广播
LAST_PROGRESS_STEP = 10  # 每 10% 广播一次

async def _broadcast_progress(self, ...):
    progress_pct = int((current_level + 1) / total_levels * 100) if total_levels > 0 else 0
    if progress_pct - self._last_broadcast_progress >= LAST_PROGRESS_STEP:
        await self.ws_manager.broadcast(...)
        self._last_broadcast_progress = progress_pct
```

---

## 四、数据库查询优化

### 4.1 发现的问题

#### 问题 1: 缺少关键索引

**文件**: `backend/database.py`

```python
class ExecutionHistory(Base):
    __tablename__ = "execution_history"
    # 无 index=True 的列

class NodeExecutionLog(Base):
    __tablename__ = "node_execution_log"
    # 缺少 execution_id 索引
```

当前索引情况：
- `RuleGraph.id`: 主键（已有）
- `ExecutionHistory.id`: 主键（已有）
- `ExecutionHistory.graph_id`: 无索引 ❌
- `ExecutionHistory.status`: 无索引 ❌
- `NodeExecutionLog.execution_id`: 无索引 ❌
- `NodeExecutionLog.node_id`: 无索引 ❌

#### 问题 2: 规则图查询未分页

**文件**: `backend/services/rule_engine/graph_manager.py` (lines 75-81)

```python
def get_all_graphs(self) -> list[RuleGraph]:
    return self.db.query(RuleGraph).order_by(RuleGraph.updated_at.desc()).all()
```

返回所有规则图，无分页。

#### 问题 3: JSON 列全量解析

```python
nodes = json.loads(graph.nodes_json)  # 每次都解析完整 JSON
```

规则图的 `nodes_json` 和 `edges_json` 存储为 Text 类型，每次查询都完整解析。

### 4.2 优化建议

#### 优化 1: 添加必要索引

```python
class ExecutionHistory(Base):
    __tablename__ = "execution_history"
    __table_args__ = (
        Index('ix_execution_history_graph_id', 'graph_id'),
        Index('ix_execution_history_status', 'status'),
        Index('ix_execution_history_trigger_type', 'trigger_type'),
    )

class NodeExecutionLog(Base):
    __tablename__ = "node_execution_log"
    __table_args__ = (
        Index('ix_node_execution_log_execution_id', 'execution_id'),
        Index('ix_node_execution_log_node_id', 'node_id'),
    )
```

#### 优化 2: 分页查询支持

```python
def get_all_graphs(
    self,
    page: int = 1,
    page_size: int = 20
) -> tuple[list[RuleGraph], int]:
    """分页获取规则图"""
    total = self.db.query(RuleGraph).count()
    graphs = (
        self.db.query(RuleGraph)
        .order_by(RuleGraph.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return graphs, total
```

#### 优化 3: 使用 JOIN 而非 N+1 查询

```python
# 获取规则图及其最近执行记录
def get_graph_with_recent_executions(self, graph_id: int, limit: int = 5):
    return (
        self.db.query(RuleGraph)
        .outerjoin(
            ExecutionHistory,
            RuleGraph.id == ExecutionHistory.graph_id
        )
        .filter(RuleGraph.id == graph_id)
        .options(joinedload(ExecutionHistory))
        .first()
    )
```

---

## 五、WebSocket 性能

### 5.1 发现的问题

#### 问题 1: 消息广播无批处理

**文件**: `backend/services/rule_engine/websocket_manager.py` (lines 72-97)

```python
async def broadcast(self, message: dict):
    # ...
    text = json.dumps(message, ensure_ascii=False)
    
    async def send_to(ws: WebSocket):
        try:
            await ws.send_text(text)
        except Exception:
            pass
    
    await asyncio.gather(*[send_to(ws) for ws in subscribers], return_exceptions=True)
```

每条消息独立发送，无批处理。如果短时间有多条消息，会产生多次网络往返。

#### 问题 2: 消息未压缩

大型消息（如包含节点完整输出）未压缩传输。

#### 问题 3: 前端 WebSocket 重连逻辑

**文件**: `webui/src/views/RuleCanvas.vue` (lines 853-861)

```javascript
ws.onerror = () => {
  wsConnected.value = false
  if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
  wsReconnectTimer = setTimeout(() => {
    if (executionStatus.value === 'running' && executionId.value) {
      connectWebSocket(executionId.value)
    }
  }, 3000)
}
```

重连间隔固定 3 秒，未使用指数退避。

#### 问题 4: 进度更新过于频繁

执行进度每层都更新，但用户界面刷新频率有限（通常 60fps = 16.6ms）。

### 5.2 优化建议

#### 优化 1: 消息批处理

```python
class RuleExecutionConnectionManager:
    def __init__(self):
        # ...
        self._pending_messages: Dict[int, List[dict]] = {}
        self._flush_task: Optional[asyncio.Task] = None
    
    async def broadcast(self, message: dict):
        # 延迟 16ms 收集同一时间窗口的消息
        execution_id = message.get("execution_id")
        if execution_id not in self._pending_messages:
            self._pending_messages[execution_id] = []
        
        self._pending_messages[execution_id].append(message)
        
        if not self._flush_task or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_messages())
    
    async def _flush_messages(self):
        await asyncio.sleep(0.016)  # ~60fps
        async with self._lock:
            for exec_id, messages in self._pending_messages.items():
                if messages:
                    # 合并消息
                    batch = {"type": "batch", "messages": messages}
                    await self._send_batch(exec_id, batch)
            self._pending_messages.clear()
```

#### 优化 2: 消息压缩

```python
import zlib

async def broadcast(self, message: dict):
    # ...
    text = json.dumps(message, ensure_ascii=False)
    compressed = zlib.compress(text.encode('utf-8'))
    
    # 标记消息已压缩，客户端自动解压
    await asyncio.gather(*[
        ws.send_bytes(compressed)
        for ws in subscribers
    ], return_exceptions=True)
```

#### 优化 3: 指数退避重连

```typescript
function connectWebSocket(execId: number) {
  let retryCount = 0
  const maxDelay = 30000
  
  function attempt() {
    ws = new WebSocket(getWsUrl())
    
    ws.onerror = () => {
      const delay = Math.min(1000 * Math.pow(2, retryCount), maxDelay)
      retryCount++
      wsReconnectTimer = setTimeout(attempt, delay)
    }
    // ...
  }
  
  attempt()
}
```

#### 优化 4: 前端节流进度更新

```typescript
import { throttle } from 'lodash-es'

const handleWsMessage = throttle((msg: any) => {
  switch (msg.type) {
    case 'execution_progress':
      executionProgress.value = msg.progress
      break
    // ...
  }
}, 100)  // 最多每 100ms 更新一次
```

---

## 六、总结

### 优先级排序

| 优先级 | 优化项 | 预期效果 |
|--------|--------|----------|
| P0 | 添加数据库索引 | 查询响应提升 10-50x |
| P0 | 进度广播降频 | 减少 WebSocket 消息量 80% |
| P1 | 前端 shallowRef 改造 | 节点数 >100 时渲染性能提升 |
| P1 | 批量历史保存 + 防抖 | 减少 50% 深拷贝开销 |
| P2 | WebSocket 消息批处理 | 减少网络往返次数 |
| P2 | 拓扑排序迭代实现 | 避免深图递归溢出 |
| P3 | 节点结果流式清理 | 降低大图内存压力 |
| P3 | 前端进度节流 | 减少无效渲染 |

### 关键指标目标

- **画布渲染**: 100 节点以内保持 60fps
- **执行引擎**: 500 节点图拓扑排序 < 10ms
- **数据库查询**: 分页查询 < 50ms
- **WebSocket**: 消息延迟 < 100ms

---

*本文档由 Hermes Agent 调研生成*
