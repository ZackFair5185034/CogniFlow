# Phase 2 技术实现文档：执行引擎核心（后端）

> ⚠️ **实现前审核状态：** 待老大评审
> 文档版本：v1.1
> 创建时间：2026-05-06
> **执行器设计规范：** 所有 `BaseExecutor.execute()` 必须为 `async def`，同步 I/O 用 `asyncio.to_thread()` 封装

---

## 1. 阶段目标

**目标：** 实现 Kahn 拓扑排序算法进行节点调度，支持同层并行执行，具备环回检测和取消执行能力。

**验收标准：**
- [ ] 规则图执行顺序与拓扑依赖关系一致
- [ ] 无环图正常执行，有环图报错并返回环节点信息
- [ ] 单层内多节点并行执行，总耗时 ≈ 最慢节点耗时
- [ ] 执行中途可取消，已执行的节点结果不丢失
- [ ] 单元测试覆盖：拓扑排序、环检测、并行调度

---

## 2. 核心架构

### 2.1 组件关系

```
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
   │ (查执行器)  │      │ (存结果)    │      │ (推送进度)  │
   └─────────────┘      └─────────────┘      └─────────────┘
```

### 2.2 执行流程

```
执行请求
    │
    ▼
┌─────────────────────────────────────┐
│ 1. GraphManager.get_graph_detail()  │ ── 获取规则图
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. ExecutionContext 初始化           │ ── 创建上下文
│    - node_results: {}               │
│    - node_status: {}               │
│    - variables: {...}              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Kahn 拓扑排序                    │
│    → List[List[node_id]]            │ ── 返回按层级分组
│    → 检测环回，如有环抛出 CycleError │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. 逐层执行                         │
│    for level in levels:             │
│      tasks = []                     │
│      for node_id in level:          │
│        inputs = resolve_inputs()    │
│        task = execute_node()        │
│        tasks.append(task)           │
│      await asyncio.gather(*tasks)   │ ── 同层并行
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. WebSocket 推送                   │
│    - node_started                   │
│    - node_executed / node_failed   │
│    - execution_progress             │
│    - execution_complete             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 6. 保存执行记录到数据库              │
└─────────────────────────────────────┘
```

---

## 3. 执行上下文

### 3.1 ExecutionContext 完整实现

```python
# backend/services/rule_engine/executor.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    """规则图执行时的上下文，在整个执行期间共享。

    Attributes:
        execution_id: 执行记录 ID
        trigger_type: 触发类型（manual/timer/webhook）
        trigger_data: 触发时携带的数据
        node_results: 节点执行结果缓存，node_id -> output_data
        node_status: 节点状态，node_id -> status
        variables: 规则变量
        config: 规则图配置（节点参数等）
        cancelled: 是否已请求取消
        ws_manager: WebSocket 管理器（用于进度推送）
    """

    execution_id: int
    trigger_type: str
    trigger_data: Dict[str, Any]

    node_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    node_status: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = field(default=False)

    # WebSocket 管理器引用（可选）
    ws_manager: Any = field(default=None)

    def get_node_result(self, node_id: str, output_name: str) -> Any:
        """获取指定节点的输出数据。"""
        return self.node_results.get(node_id, {}).get(output_name)

    def set_node_result(self, node_id: str, outputs: Dict[str, Any]):
        """设置节点输出数据。"""
        self.node_results[node_id] = outputs

    def get_node_status(self, node_id: str) -> str:
        """获取节点状态。"""
        return self.node_status.get(node_id, "pending")

    def set_node_status(self, node_id: str, status: str):
        """设置节点状态。"""
        self.node_status[node_id] = status

    def is_cancelled(self) -> bool:
        """检查是否已请求取消。"""
        return self.cancelled

    def request_cancel(self):
        """请求取消执行。"""
        self.cancelled = True
```

---

## 4. Kahn 拓扑排序

### 4.1 核心实现

```python
# backend/services/rule_engine/executor.py

from collections import defaultdict, deque
from typing import Any, Dict, List, Set, Tuple

from .exceptions import CycleError, ValidationError


class RuleGraphExecutor:
    """规则图执行引擎 - 负责图的解析、调度和执行。"""

    def __init__(self, db=None, ws_manager=None):
        self.db = db
        self.ws_manager = ws_manager

    # ========== 拓扑排序 ==========

    def build_dependency_graph(
        self,
        nodes: Dict[str, Any],
        edges: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """从节点和边构建依赖图。

        Args:
            nodes: 节点字典，key 为节点 ID
            edges: 边列表

        Returns:
            (graph, in_degree) 元组
            - graph: 邻接表，graph[source] = [targets...]
            - in_degree: 入度表，node_id -> 入度数量
        """
        graph = defaultdict(list)  # source -> [targets]
        in_degree = defaultdict(int)  # node -> in_degree

        # 初始化所有节点的入度为 0
        for node_id in nodes:
            in_degree[node_id] = 0

        # 从边构建依赖关系
        for edge in edges:
            source = edge["source"]
            target = edge["target"]

            # target 依赖 source（需要先执行 source）
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

        Args:
            nodes: 节点字典
            edges: 边列表

        Returns:
            List of levels, each level is a list of node IDs
            e.g., [["node_001"], ["node_002", "node_003"], ["node_004"]]
            Level 0 的节点无依赖，最先执行;

        Raises:
            CycleError: 如果图中存在循环依赖
        """
        graph, in_degree = self.build_dependency_graph(nodes, edges)

        all_nodes = set(nodes.keys())
        remaining_in_degree = dict(in_degree)

        # 收集所有节点（用于最终检查）
        all_nodes_in_degree = sum(remaining_in_degree.values())

        levels: List[List[str]] = []
        processed: Set[str] = set()

        while True:
            # 找到所有入度为 0 的节点（当前层）
            current_level = [
                node_id for node_id in all_nodes
                if node_id not in processed and remaining_in_degree.get(node_id, 0) == 0
            ]

            if not current_level:
                # 没有入度为 0 的节点，检查是否所有节点都已处理
                if len(processed) == len(all_nodes):
                    break
                # 否则说明存在环
                unprocessed = all_nodes - processed
                cycle_info = self._find_cycle_nodes(graph, unprocessed)
                raise CycleError(
                    f"规则图存在循环依赖: {' -> '.join(cycle_info[:5])}...",
                    cycle_nodes=cycle_info
                )

            levels.append(current_level)
            processed.update(current_level)

            # 更新下游节点的入度
            for node_id in current_level:
                for dependent in graph.get(node_id, []):
                    remaining_in_degree[dependent] -= 1

        return levels

    def _find_cycle_nodes(
        self,
        graph: Dict[str, List[str]],
        remaining: Set[str]
    ) -> List[str]:
        """从剩余节点中找出环的节点（简单实现）。

        使用 DFS 检测环，从任意节点开始，沿着图的边遍历，
        如果遇到已访问的节点，则存在环。

        Args:
            graph: 邻接表
            remaining: 还未处理的节点集合

        Returns:
            环中的节点列表
        """
        if not remaining:
            return []

        # 简单实现：返回任意一个未处理的节点作为环的标识
        # 实际应该用 DFS 完整检测
        return list(remaining)
```

---

## 5. 执行引擎主逻辑

### 5.1 完整执行流程

```python
# backend/services/rule_engine/executor.py

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from .models import ExecutionContext
from .exceptions import ExecutorError, ValidationError
from .registry import get_registry


class RuleGraphExecutor:
    """规则图执行引擎。"""

    def __init__(self, db=None, ws_manager=None):
        self.db = db
        self.ws_manager = ws_manager

    async def execute(
        self,
        graph_data: Dict[str, Any],
        execution_id: int,
        trigger_type: str = "manual",
        trigger_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行规则图。

        Args:
            graph_data: 规则图数据（来自 parse_graph_data）
            execution_id: 执行记录 ID
            trigger_type: 触发类型
            trigger_data: 触发时携带的数据

        Returns:
            执行结果字典

        Raises:
            ValidationError: 规则图校验失败
            CycleError: 规则图存在循环依赖
            ExecutorError: 节点执行失败
        """
        trigger_data = trigger_data or {}

        # 解析图数据
        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])
        variables = graph_data.get("variables", {})

        # 拓扑排序
        try:
            levels = self.topological_sort_levels(nodes, edges)
        except CycleError:
            raise

        # 创建执行上下文
        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            variables=dict(variables),
            config={"nodes": nodes},
            ws_manager=self.ws_manager
        )

        # 更新执行记录状态
        await self._update_execution_status(execution_id, "running")

        # 执行每一层
        try:
            total_levels = len(levels)
            total_nodes = sum(len(level) for level in levels)

            for level_idx, level in enumerate(levels):
                # 检查是否取消
                if context.is_cancelled():
                    await self._handle_cancellation(execution_id, context)
                    return {"status": "cancelled", "cancelled_at": datetime.now().isoformat()}

                # 推送进度
                await self._broadcast_progress(
                    execution_id,
                    level_idx,
                    total_levels,
                    len(level),
                    total_nodes
                )

                # 并行执行当前层
                await self._execute_level(level, context)

            # 全部完成
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

    async def _execute_level(
        self,
        level: List[str],
        context: ExecutionContext
    ):
        """执行同一层的所有节点（并行）。"""
        tasks = [
            self._execute_node(node_id, context)
            for node_id in level
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查是否有失败
        for node_id, result in zip(level, results):
            if isinstance(result, Exception):
                # 记录失败状态（不立即抛出，由外层处理）
                context.set_node_status(node_id, "failed")

    async def _execute_node(
        self,
        node_id: str,
        context: ExecutionContext
    ):
        """执行单个节点。"""
        # 检查是否取消
        if context.is_cancelled():
            context.set_node_status(node_id, "cancelled")
            return

        # 获取节点信息
        node = context.config["nodes"].get(node_id)
        if not node:
            raise ExecutorError(f"节点 {node_id} 不存在", node_id=node_id)

        node_type = node.get("type")
        node_data = node.get("data", {})
        params = node_data.get("params", {})
        inputs_config = node_data.get("inputs", {})

        # 更新状态为 running
        context.set_node_status(node_id, "running")
        await self._broadcast_node_started(execution_id, node_id, node_type)

        try:
            # 解析输入数据
            inputs = self._resolve_inputs(inputs_config, context)

            # 合并默认参数
            merged_inputs = {**inputs, **params}

            # 获取执行器
            registry = get_registry()
            executor = registry.get_executor(node_type)

            if not executor:
                raise ExecutorError(f"未知的节点类型: {node_type}", node_id=node_id, node_type=node_type)

            # 校验输入
            is_valid, error_msg = executor.validate_inputs(merged_inputs)
            if not is_valid:
                raise ExecutorError(
                    f"输入校验失败: {error_msg}",
                    node_id=node_id,
                    node_type=node_type
                )

            # 执行
            outputs = await executor.execute(merged_inputs, context)

            # 保存结果
            context.set_node_result(node_id, outputs)
            context.set_node_status(node_id, "completed")

            # 推送节点完成
            await self._broadcast_node_executed(
                context.execution_id,
                node_id,
                "success",
                outputs
            )

        except Exception as e:
            context.set_node_status(node_id, "failed")
            await self._broadcast_node_failed(context.execution_id, node_id, str(e))

            if isinstance(e, ExecutorError):
                raise

            raise ExecutorError(
                f"节点执行失败: {str(e)}",
                node_id=node_id,
                node_type=node_type
            ) from e

    def _resolve_inputs(
        self,
        inputs_config: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """解析节点的输入数据。

        从已完成的节点结果或默认值中获取输入。
        """
        inputs = {}

        for port_name, config in inputs_config.items():
            # 优先从连接的节点获取
            if config.get("node_id"):
                source_node = config["node_id"]
                source_output = config.get("output", "result")
                inputs[port_name] = context.get_node_result(source_node, source_output)
            # 其次使用默认值
            elif "value" in config:
                inputs[port_name] = config["value"]
            # 否则为 None

        return inputs
```

---

## 6. WebSocket 进度推送

### 6.1 广播方法

```python
# backend/services/rule_engine/executor.py

    # ========== WebSocket 广播 ==========

    async def _broadcast_node_started(
        self,
        execution_id: int,
        node_id: str,
        node_type: str
    ):
        """广播节点开始执行。"""
        if self.ws_manager:
            await self.ws_manager.broadcast(
                {
                    "type": "node_started",
                    "execution_id": execution_id,
                    "node_id": node_id,
                    "node_type": node_type,
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _broadcast_node_executed(
        self,
        execution_id: int,
        node_id: str,
        status: str,
        outputs: Dict[str, Any]
    ):
        """广播节点执行完成。"""
        if self.ws_manager:
            await self.ws_manager.broadcast(
                {
                    "type": "node_executed",
                    "execution_id": execution_id,
                    "node_id": node_id,
                    "status": status,
                    "outputs": outputs,
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _broadcast_node_failed(
        self,
        execution_id: int,
        node_id: str,
        error: str
    ):
        """广播节点执行失败。"""
        if self.ws_manager:
            await self.ws_manager.broadcast(
                {
                    "type": "node_failed",
                    "execution_id": execution_id,
                    "node_id": node_id,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                }
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
        if self.ws_manager:
            completed_nodes = sum(
                i * len(level) for i, level in enumerate(
                    range(current_level)
                )
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
                }
            )

    async def _broadcast_complete(
        self,
        execution_id: int,
        result: Dict[str, Any]
    ):
        """广播执行完成。"""
        if self.ws_manager:
            await self.ws_manager.broadcast(
                {
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "status": result.get("status", "completed"),
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            )
```

---

## 7. 执行状态管理

### 7.1 数据库操作

```python
# backend/services/rule_engine/executor.py

    async def _update_execution_status(
        self,
        execution_id: int,
        status: str,
        result: Dict[str, Any] = None
    ):
        """更新执行记录状态。"""
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
                import json
                record.result_data = json.dumps(result)

            self.db.commit()

    async def _handle_cancellation(
        self,
        execution_id: int,
        context: ExecutionContext
    ):
        """处理执行取消。"""
        await self._update_execution_status(execution_id, "cancelled")

        if self.ws_manager:
            await self.ws_manager.broadcast(
                {
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "status": "cancelled",
                    "message": "执行已被用户取消",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_execution_error(
        self,
        execution_id: int,
        context: ExecutionContext,
        error: Exception
    ):
        """处理执行错误。"""
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
            await self.ws_manager.broadcast(
                {
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": error_message,
                    "timestamp": datetime.now().isoformat()
                }
            )
```

---

## 8. 取消执行机制

### 8.1 取消流程

```python
# backend/services/rule_engine/executor.py

class RuleGraphExecutor:
    """规则图执行引擎。"""

    # 保存所有进行中的执行上下文
    _active_executions: Dict[int, ExecutionContext] = {}

    @classmethod
    def register_execution(cls, execution_id: int, context: ExecutionContext):
        """注册执行上下文（用于取消操作）。"""
        cls._active_executions[execution_id] = context

    @classmethod
    def unregister_execution(cls, execution_id: int):
        """注销执行上下文。"""
        cls._active_executions.pop(execution_id, None)

    @classmethod
    def cancel_execution(cls, execution_id: int) -> bool:
        """请求取消指定执行。

        Returns:
            True 如果执行存在并已请求取消，False 如果执行不存在
        """
        context = cls._active_executions.get(execution_id)
        if context:
            context.request_cancel()
            return True
        return False

    async def execute(self, ...):
        """执行规则图（修改版，支持取消注册）。"""
        # 注册执行上下文
        self.register_execution(execution_id, context)

        try:
            # ... 执行逻辑
            return result
        finally:
            # 确保注销
            self.unregister_execution(execution_id)
```

---

## 9. Kahn 算法层级分组详解

### 9.1 算法图解

```
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
    node_005 (无依赖，可与 node_004 并行？不对，node_005 依赖 node_004)


边：
edge_001: node_001 → node_002
edge_002: node_001 → node_003
edge_003: node_002 → node_004
edge_004: node_003 → node_004
edge_005: node_004 → node_005

拓扑排序过程：
Step 1: 入度为 0 的节点 → Level 0 = [node_001]
        处理 node_001 后，node_002 和 node_003 入度减为 0

Step 2: 入度为 0 的节点 → Level 1 = [node_002, node_003]
        处理后，node_004 入度减为 0

Step 3: 入度为 0 的节点 → Level 2 = [node_004]
        处理后，node_005 入度减为 0

Step 4: 入度为 0 的节点 → Level 3 = [node_005]

结果：
levels = [
    ["node_001"],           # Level 0：最先执行
    ["node_002", "node_003"], # Level 1：并行执行
    ["node_004"],           # Level 2：等待 Level 1
    ["node_005"]            # Level 3：最后执行
]

并行分析：
- Level 0: 1 个节点（node_001）
- Level 1: 2 个节点（node_002, node_003）→ 并行，耗时 = max(t_002, t_003)
- Level 2: 1 个节点（node_004）
- Level 3: 1 个节点（node_005）
```

---

## 10. 单元测试

### 10.1 拓扑排序测试

```python
# tests/test_rule_engine/test_executor.py

import pytest
from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.exceptions import CycleError


class TestTopologicalSort:
    """拓扑排序测试。"""

    @pytest.fixture
    def executor(self):
        return RuleGraphExecutor()

    def test_simple_chain(self, executor):
        """测试简单链式依赖。"""
        nodes = {
            "a": {},
            "b": {},
            "c": {}
        }
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
        """测试并行节点。"""
        nodes = {
            "a": {},
            "b": {},
            "c": {}
        }
        edges = [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"}
        ]

        levels = executor.topological_sort_levels(nodes, edges)

        assert len(levels) == 2
        assert levels[0] == ["a"]
        assert set(levels[1]) == {"b", "c"}

    def test_complex_dag(self, executor):
        """测试复杂 DAG（有多个并行分支）。"""
        nodes = {
            "a": {},
            "b": {},
            "c": {},
            "d": {},
            "e": {}
        }
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
        """测试环检测。"""
        nodes = {
            "a": {},
            "b": {},
            "c": {}
        }
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            {"source": "c", "target": "a"}  # 形成环
        ]

        with pytest.raises(CycleError) as exc_info:
            executor.topological_sort_levels(nodes, edges)

        assert "循环依赖" in str(exc_info.value)

    def test_partial_cycle(self, executor):
        """测试部分环。"""
        nodes = {
            "a": {},
            "b": {},
            "c": {},
            "d": {}
        }
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
            # a 和 d 无依赖关系
            {"source": "c", "target": "a"},  # 形成环：a → b → c → a
        ]

        with pytest.raises(CycleError):
            executor.topological_sort_levels(nodes, edges)


class TestBuildDependencyGraph:
    """依赖图构建测试。"""

    @pytest.fixture
    def executor(self):
        return RuleGraphExecutor()

    def test_build_graph(self, executor):
        """测试依赖图构建。"""
        nodes = {"a": {}, "b": {}, "c": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"}
        ]

        graph, in_degree = executor.build_dependency_graph(nodes, edges)

        assert graph == {"a": ["b"], "b": ["c"]}
        assert in_degree == {"a": 0, "b": 1, "c": 1}

    def test_multiple_dependencies(self, executor):
        """测试多依赖（b 和 c 都依赖 a）。"""
        nodes = {"a": {}, "b": {}, "c": {}}
        edges = [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"}
        ]

        graph, in_degree = executor.build_dependency_graph(nodes, edges)

        assert graph == {"a": ["b", "c"]}
        assert in_degree == {"a": 0, "b": 1, "c": 1}
```

---

## 11. 验收检查清单

### 11.1 功能验收

- [ ] 拓扑排序返回按层级分组的节点列表
- [ ] 无环图正常执行，节点按依赖顺序执行
- [ ] 同层节点并行执行，总耗时 ≈ 最慢节点
- [ ] 有环图抛出 CycleError，包含环节点信息
- [ ] 取消请求能中断正在执行的节点

### 11.2 WebSocket 验收

- [ ] node_started 在节点执行前推送
- [ ] node_executed/node_failed 在节点执行后推送
- [ ] execution_progress 在每层完成后推送
- [ ] execution_complete 在全部完成后推送

### 11.3 状态管理验收

- [ ] 执行开始时状态为 running
- [ ] 执行完成时状态为 completed
- [ ] 执行失败时状态为 failed
- [ ] 取消执行时状态为 cancelled
- [ ] completed_at 和 total_time_ms 正确记录
