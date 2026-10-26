# Phase 2 技术实现文档：执行引擎核心（后端）
Kahn 拓扑排序算法进行节点调度，支持同层并行执行，具备环回检测和取消执行能力

---

## 一、阶段目标
**目标：**实现 Kahn 拓扑排序算法进行节点调度，支持同层并行执行，具备环回检测和取消执行能力。

### 验收标准

 
- 规则图执行顺序与拓扑依赖关系一致 
- 无环图正常执行，有环图报错并返回环节点信息 
- 单层内多节点并行执行，总耗时 ≈ 最慢节点耗时 
- 执行中途可取消，已执行的节点结果不丢失 
- 单元测试覆盖：拓扑排序、环检测、并行调度 

## 二、核心架构

### 2.1 组件关系

```text
┌─────────────────────────────────────────────────────────────────┐
│                     RuleGraphExecutor                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. parse_graph_data()    - 解析规则图为内部格式            │  │
│  │ 2. topological_sort()    - Kahn 算法，返回按层级分组的节点  │  │
│  │ 3. execute()             - 逐层调度，层内并行执行           │  │
│  │ 4. broadcast_progress()  - WebSocket 推送进度              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │ NodeRegistry│      │ExecutionCtx │      │WebSocketMgr │
  └─────────────┘      └─────────────┘      └─────────────┘
```

### 2.2 执行流程

```text
执行请求
    │
    ▼
┌─────────────────────────────────────┐
│ 1. GraphManager.get_graph_detail()  │ ── 获取规则图
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 2. ExecutionContext 初始化           │ ── 创建上下文
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 3. Kahn 拓扑排序                    │
│    → List[List[node_id]]            │ ── 返回按层级分组
│    → 检测环回，如有环抛出 CycleError │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 4. 逐层执行                         │
│    for level in levels:             │
│      tasks = []                     │
│      await asyncio.gather(*tasks)   │ ── 同层并行
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 5. WebSocket 推送                   │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 6. 保存执行记录到数据库              │
└─────────────────────────────────────┘
```

## 三、执行上下文

### 3.1 ExecutionContext 完整实现

```python
# backend/services/rule_engine/executor.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ExecutionContext:
    """规则图执行时的上下文，在整个执行期间共享。"""

    execution_id: int
    trigger_type: str
    trigger_data: Dict[str, Any]
    node_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    node_status: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = field(default=False)
    ws_manager: Any = field(default=None)

    def get_node_result(self, node_id: str, output_name: str) -> Any:
        return self.node_results.get(node_id, {}).get(output_name)

    def set_node_result(self, node_id: str, outputs: Dict[str, Any]):
        self.node_results[node_id] = outputs

    def get_node_status(self, node_id: str) -> str:
        return self.node_status.get(node_id, "pending")

    def set_node_status(self, node_id: str, status: str):
        self.node_status[node_id] = status

    def is_cancelled(self) -> bool:
        return self.cancelled

    def request_cancel(self):
        self.cancelled = True
```

## 四、Kahn 拓扑排序

### 4.1 核心实现

```python
class RuleGraphExecutor:
    """规则图执行引擎 - 负责图的解析、调度和执行。"""

    def __init__(self, db=None, ws_manager=None):
        self.db = db
        self.ws_manager = ws_manager

    def build_dependency_graph(
        self,
        nodes: Dict[str, Any],
        edges: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """从节点和边构建依赖图。"""
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        for node_id in nodes:
            in_degree[node_id] = 0
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            graph[source].append(target)
            in_degree[target] += 1
        return dict(graph), dict(in_degree)

    def topological_sort_levels(
        self,
        nodes: Dict[str, Any],
        edges: List[Dict[str, Any]]
    ) -> List[List[str]]:
        """Kahn 算法拓扑排序，返回按层级分组的节点列表。

        同一层内的节点没有依赖关系，可以并行执行。

        Raises:
            CycleError: 如果图中存在循环依赖
        """
        graph, in_degree = self.build_dependency_graph(nodes, edges)
        all_nodes = set(nodes.keys())
        remaining_in_degree = dict(in_degree)
        levels: List[List[str]] = []
        processed: Set[str] = set()

        while True:
            current_level = [
                node_id for node_id in all_nodes
                if node_id not in processed and remaining_in_degree.get(node_id, 0) == 0
            ]
            if not current_level:
                if len(processed) == len(all_nodes):
                    break
                unprocessed = all_nodes - processed
                cycle_info = self._find_cycle_nodes(graph, unprocessed)
                raise CycleError(
                    f"规则图存在循环依赖: {' -> '.join(cycle_info[:5])}...",
                    cycle_nodes=cycle_info
                )
            levels.append(current_level)
            processed.update(current_level)
            for node_id in current_level:
                for dependent in graph.get(node_id, []):
                    remaining_in_degree[dependent] -= 1
        return levels
```

## 五、执行引擎主逻辑

### 5.1 完整执行流程

```python
class RuleGraphExecutor:

    async def execute(
        self,
        graph_data: Dict[str, Any],
        execution_id: int,
        trigger_type: str = "manual",
        trigger_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行规则图。"""
        trigger_data = trigger_data or {}
        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])
        variables = graph_data.get("variables", {})

        try:
            levels = self.topological_sort_levels(nodes, edges)
        except CycleError:
            raise

        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            variables=dict(variables),
            config={"nodes": nodes},
            ws_manager=self.ws_manager
        )

        await self._update_execution_status(execution_id, "running")

        try:
            total_levels = len(levels)
            total_nodes = sum(len(level) for level in levels)

            for level_idx, level in enumerate(levels):
                if context.is_cancelled():
                    await self._handle_cancellation(execution_id, context)
                    return {"status": "cancelled", "cancelled_at": datetime.now().isoformat()}
                await self._broadcast_progress(execution_id, level_idx, total_levels, len(level), total_nodes)
                await self._execute_level(level, context)

            result = {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "node_results": context.node_results
            }
            await self._update_execution_status(execution_id, "completed", result)
            await self._broadcast_complete(execution_id, result)
            return result

        except Exception as e:
            await self._handle_execution_error(execution_id, context, e)
            raise

    async def _execute_level(self, level: List[str], context: ExecutionContext):
        """执行同一层的所有节点（并行）。"""
        tasks = [self._execute_node(node_id, context) for node_id in level]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for node_id, result in zip(level, results):
            if isinstance(result, Exception):
                context.set_node_status(node_id, "failed")

    async def _execute_node(self, node_id: str, context: ExecutionContext):
        """执行单个节点。"""
        if context.is_cancelled():
            context.set_node_status(node_id, "cancelled")
            return
        node = context.config["nodes"].get(node_id)
        if not node:
            raise ExecutorError(f"节点 {node_id} 不存在", node_id=node_id)
        node_type = node.get("type")
        node_data = node.get("data", {})
        params = node_data.get("params", {})
        inputs_config = node_data.get("inputs", {})
        context.set_node_status(node_id, "running")
        await self._broadcast_node_started(context.execution_id, node_id, node_type)

        try:
            inputs = self._resolve_inputs(inputs_config, context)
            merged_inputs = {**inputs, **params}
            registry = get_registry()
            executor = registry.get_executor(node_type)
            if not executor:
                raise ExecutorError(f"未知的节点类型: {node_type}", node_id=node_id, node_type=node_type)
            is_valid, error_msg = executor.validate_inputs(merged_inputs)
            if not is_valid:
                raise ExecutorError(f"输入校验失败: {error_msg}", node_id=node_id, node_type=node_type)
            outputs = await executor.execute(merged_inputs, context)
            context.set_node_result(node_id, outputs)
            context.set_node_status(node_id, "completed")
            await self._broadcast_node_executed(context.execution_id, node_id, "success", outputs)
        except Exception as e:
            context.set_node_status(node_id, "failed")
            await self._broadcast_node_failed(context.execution_id, node_id, str(e))
            if isinstance(e, ExecutorError):
                raise
            raise ExecutorError(f"节点执行失败: {str(e)}", node_id=node_id, node_type=node_type) from e

    def _resolve_inputs(self, inputs_config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """解析节点的输入数据。"""
        inputs = {}
        for port_name, config in inputs_config.items():
            if config.get("node_id"):
                source_node = config["node_id"]
                source_output = config.get("output", "result")
                inputs[port_name] = context.get_node_result(source_node, source_output)
            elif "value" in config:
                inputs[port_name] = config["value"]
        return inputs
```

## 六、WebSocket 进度推送

### 6.1 广播方法

```python
    async def _broadcast_node_started(self, execution_id, node_id, node_type):
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_started",
                "execution_id": execution_id,
                "node_id": node_id,
                "node_type": node_type,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_node_executed(self, execution_id, node_id, status, outputs):
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_executed",
                "execution_id": execution_id,
                "node_id": node_id,
                "status": status,
                "outputs": outputs,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_node_failed(self, execution_id, node_id, error):
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_failed",
                "execution_id": execution_id,
                "node_id": node_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_progress(self, execution_id, current_level, total_levels, nodes_in_level, total_nodes):
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_progress",
                "execution_id": execution_id,
                "progress": int((current_level + 1) / total_levels * 100),
                "current_level": current_level + 1,
                "total_levels": total_levels,
                "completed_nodes": sum(len(level) for level in range(current_level)) + nodes_in_level,
                "total_nodes": total_nodes,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_complete(self, execution_id, result):
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": result.get("status", "completed"),
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
```

## 七、执行状态管理

### 7.1 数据库操作

```python
    async def _update_execution_status(self, execution_id, status, result=None):
        if not self.db:
            return
        from backend.database import ExecutionHistory
        record = self.db.query(ExecutionHistory).filter(
            ExecutionHistory.id == execution_id
        ).first()
        if record:
            record.status = status
            if status == "running":
                record.started_at = datetime.now()
            if status in ("completed", "failed", "cancelled"):
                record.completed_at = datetime.now()
                if record.started_at:
                    delta = record.completed_at - record.started_at
                    record.total_time_ms = int(delta.total_seconds() * 1000)
            if result:
                record.result_data = json.dumps(result)
            self.db.commit()

    async def _handle_cancellation(self, execution_id, context):
        await self._update_execution_status(execution_id, "cancelled")
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "cancelled",
                "message": "执行已被用户取消",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_execution_error(self, execution_id, context, error):
        error_message = str(error)
        if self.db:
            from backend.database import ExecutionHistory
            record = self.db.query(ExecutionHistory).filter(
                ExecutionHistory.id == execution_id
            ).first()
            if record:
                record.status = "failed"
                record.error_message = error_message
                record.completed_at = datetime.now()
                if record.started_at:
                    delta = record.completed_at - record.started_at
                    record.total_time_ms = int(delta.total_seconds() * 1000)
                self.db.commit()
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "failed",
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            })
```

## 八、取消执行机制

### 8.1 取消流程

```python
class RuleGraphExecutor:
    """规则图执行引擎。"""

    # 保存所有进行中的执行上下文
    _active_executions: Dict[int, ExecutionContext] = {}

    @classmethod
    def register_execution(cls, execution_id: int, context: ExecutionContext):
        cls._active_executions[execution_id] = context

    @classmethod
    def unregister_execution(cls, execution_id: int):
        cls._active_executions.pop(execution_id, None)

    @classmethod
    def cancel_execution(cls, execution_id: int) -> bool:
        """请求取消指定执行。"""
        context = cls._active_executions.get(execution_id)
        if context:
            context.request_cancel()
            return True
        return False

    async def execute(self, ...):
        # 注册执行上下文
        self.register_execution(execution_id, context)
        try:
            # ... 执行逻辑
            return result
        finally:
            self.unregister_execution(execution_id)
```

## 九、Kahn 算法层级分组详解

### 9.1 算法图解

```text
规则图示例：
    node_001 (无输入依赖)
        │
        ▼
    node_002, node_003 (都依赖 node_001)
        │
        ▼
    node_004 (依赖 node_002 和 node_003)
        │
        ▼
    node_005 (依赖 node_004)

拓扑排序过程：
Step 1: 入度为 0 的节点 → Level 0 = [node_001]
Step 2: 入度为 0 的节点 → Level 1 = [node_002, node_003]  → 并行
Step 3: 入度为 0 的节点 → Level 2 = [node_004]
Step 4: 入度为 0 的节点 → Level 3 = [node_005]

结果：
levels = [
    ["node_001"],              # Level 0：最先执行
    ["node_002", "node_003"], # Level 1：并行执行
    ["node_004"],              # Level 2：等待 Level 1
    ["node_005"]              # Level 3：最后执行
]
```

## 十、单元测试

### 10.1 拓扑排序测试

```python
# tests/test_rule_engine/test_executor.py

import pytest
from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.exceptions import CycleError

class TestTopologicalSort:

    @pytest.fixture
    def executor(self):
        return RuleGraphExecutor()

    def test_simple_chain(self, executor):
        nodes = {"a": {}, "b": {}, "c": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"}
        ]
        levels = executor.topological_sort_levels(nodes, edges)
        assert len(levels) == 3
        assert levels[0] == ["a"]
        assert levels[1] == ["b"]
        assert levels[2] == ["c"]

    def test_parallel_nodes(self, executor):
        nodes = {"a": {}, "b": {}, "c": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"}
        ]
        levels = executor.topological_sort_levels(nodes, edges)
        assert len(levels) == 2
        assert levels[0] == ["a"]
        assert set(levels[1]) == {"b", "c"}

    def test_complex_dag(self, executor):
        nodes = {"a": {}, "b": {}, "c": {}, "d": {}, "e": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"},
            {"source": "b", "target": "d"},
            {"source": "c", "target": "d"},
            {"source": "d", "target": "e"}
        ]
        levels = executor.topological_sort_levels(nodes, edges)
        assert len(levels) == 4
        assert levels[0] == ["a"]
        assert set(levels[1]) == {"b", "c"}
        assert levels[2] == ["d"]
        assert levels[3] == ["e"]

    def test_cycle_detection(self, executor):
        nodes = {"a": {}, "b": {}, "c": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "a"}
        ]
        with pytest.raises(CycleError) as exc_info:
            executor.topological_sort_levels(nodes, edges)
        assert "循环依赖" in str(exc_info.value)

class TestBuildDependencyGraph:

    @pytest.fixture
    def executor(self):
        return RuleGraphExecutor()

    def test_build_graph(self, executor):
        nodes = {"a": {}, "b": {}, "c": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"}
        ]
        graph, in_degree = executor.build_dependency_graph(nodes, edges)
        assert graph == {"a": ["b"], "b": ["c"]}
        assert in_degree == {"a": 0, "b": 1, "c": 1}
```

## 十一、验收检查清单

### 11.1 功能验收

 
- 拓扑排序返回按层级分组的节点列表 
- 无环图正常执行，节点按依赖顺序执行 
- 同层节点并行执行，总耗时 ≈ 最慢节点 
- 有环图抛出 CycleError，包含环节点信息 
- 取消请求能中断正在执行的节点 

### 11.2 WebSocket 验收

 
- node_started 在节点执行前推送 
- node_executed / node_failed 在节点执行后推送 
- execution_progress 在每层完成后推送 
- execution_complete 在全部完成后推送 

### 11.3 状态管理验收

 
- 执行开始时状态为 running 
- 执行完成时状态为 completed 
- 执行失败时状态为 failed 
- 取消执行时状态为 cancelled 
- completed_at 和 total_time_ms 正确记录
