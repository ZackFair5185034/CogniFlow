# -*- coding: utf-8 -*-
"""规则图执行器 - Kahn 拓扑排序 + 层内并行执行。
按设计文档 phase2-execution-engine.md 实现。
"""
import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.database import ExecutionHistory, NodeExecutionLog
from .exceptions import CycleError, ExecutorError, ValidationError
from .nodes.base import BaseExecutor, ExecutionContext, NodeStatus
from .port_types import PORT_COMPATIBILITY, is_port_compatible
from .registry import NodeRegistry, get_registry

# BE-P0-2 (2026-06-19): 用于 finally cleanup 失败时降级告警, 不掩盖主结果
logger = logging.getLogger(__name__)


class RuleGraphExecutor:
    """规则图执行引擎 - 负责图的解析、调度和执行。

    使用 Kahn 拓扑排序算法实现节点调度，同层节点并行执行。
    """

    # 保存所有进行中的执行上下文（用于取消操作）
    _active_executions: Dict[int, ExecutionContext] = {}

    # 端口类型兼容性矩阵 - 唯一事实源在 port_types 模块, 此处仅做向后兼容转发
    PORT_COMPATIBILITY = PORT_COMPATIBILITY

    def __init__(self, db=None, ws_manager=None):
        """初始化执行器。

        Args:
            db: 数据库会话
            ws_manager: WebSocket 管理器
        """
        self.db = db
        self.ws_manager = ws_manager

    def create_execution_record(
        self,
        graph_id: int,
        trigger_type: str = "manual",
        trigger_data: dict = None
    ) -> int:
        """创建执行记录。

        Args:
            graph_id: 规则图ID
            trigger_type: 触发类型
            trigger_data: 触发数据

        Returns:
            执行记录ID
        """
        if not self.db:
            return 0

        from backend.database import ExecutionHistory

        record = ExecutionHistory(
            graph_id=graph_id,
            status="pending",
            trigger_type=trigger_type,
            trigger_data_json=json.dumps(trigger_data or {}, default=str),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record.id

    # ============================================================
    # 图连接校验
    # ============================================================

    def _validate_graph_connections(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ):
        """校验图中所有连接的端口类型兼容性。

        Args:
            nodes: 节点列表（List[Dict]），每个节点包含 id, type 等
            edges: 边列表（List[Dict]），每条边包含 source, target, sourceHandle, targetHandle

        Raises:
            ValidationError: 如果存在不兼容的连接
        """
        if not nodes:
            return

        # 构建节点类型映射: node_id -> node_type
        node_type_map = {node["id"]: node.get("type") for node in nodes}

        # 获取节点注册表
        registry = get_registry()

        for edge in edges:
            source_id = edge.get("source")
            target_id = edge.get("target")
            source_handle = edge.get("source_handle") or edge.get("sourceHandle")
            target_handle = edge.get("target_handle") or edge.get("targetHandle")

            source_type = node_type_map.get(source_id)
            target_type = node_type_map.get(target_id)

            if not source_type or not target_type:
                continue  # 跳过无法识别的节点

            # 获取源节点输出端口类型
            source_executor_cls = registry.get(source_type)
            if not source_executor_cls:
                continue
            source_def = source_executor_cls().get_definition()
            source_port_type = None
            if source_handle and source_handle in source_def.outputs:
                source_port_type = source_def.outputs[source_handle].type
            elif source_def.outputs:
                # 如果没有指定handle，取第一个输出端口
                first_output = next(iter(source_def.outputs.values()))
                source_port_type = first_output.type

            # 获取目标节点输入端口类型
            target_executor_cls = registry.get(target_type)
            if not target_executor_cls:
                continue
            target_def = target_executor_cls().get_definition()
            target_port_type = None
            if target_handle and target_handle in target_def.inputs:
                target_port_type = target_def.inputs[target_handle].type
            elif target_def.inputs:
                # 如果没有指定handle，取第一个输入端口
                first_input = next(iter(target_def.inputs.values()))
                target_port_type = first_input.type

            # 检查兼容性 - 统一走共享矩阵, 与前端连线校验使用同一套规则
            if source_port_type and target_port_type:
                if not is_port_compatible(source_port_type, target_port_type):
                    raise ValidationError(
                        f"端口类型不兼容: {source_id}.{source_handle or 'output'} "
                        f"({source_port_type}) → {target_id}.{target_handle or 'input'} "
                        f"({target_port_type})"
                    )

    # ============================================================
    # Kahn 拓扑排序
    # ============================================================

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
            source = edge.get("source")
            target = edge.get("target")
            if not source or not target:
                continue
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

    def _find_all_cycles(
        self,
        graph: Dict[str, List[str]],
        remaining: Set[str]
    ) -> List[List[str]]:
        """从剩余节点中用迭代 DFS 检测所有环。

        Args:
            graph: 邻接表
            remaining: 还未处理的节点集合

        Returns:
            所有环的列表，每个环是节点 ID 列表
        """
        if not remaining:
            return []

        all_cycles: List[List[str]] = []
        visited: Set[str] = set()

        for start_node in remaining:
            if start_node in visited:
                continue

            # 使用显式栈模拟递归 DFS
            # 栈元素: (node, next_neighbor_index)
            stack: List[Tuple[str, int]] = []
            rec_stack: Set[str] = set()
            path: List[str] = []

            # 初始化：从起始节点开始
            visited.add(start_node)
            stack.append((start_node, 0))
            rec_stack.add(start_node)
            path.append(start_node)

            while stack:
                node, neighbor_idx = stack[-1]
                neighbors = graph.get(node, [])

                if neighbor_idx < len(neighbors):
                    # 还有邻居需要处理
                    neighbor = neighbors[neighbor_idx]
                    # 更新当前节点的邻居索引（下次从这里继续）
                    stack[-1] = (node, neighbor_idx + 1)

                    if neighbor not in visited:
                        # 未访问过，深度优先探索
                        visited.add(neighbor)
                        stack.append((neighbor, 0))
                        rec_stack.add(neighbor)
                        path.append(neighbor)
                    elif neighbor in rec_stack:
                        # 在当前递归栈中找到邻居 -> 发现环
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        all_cycles.append(cycle)
                    # else: neighbor 已访问但不在递归栈中，说明是其他分支的节点，跳过
                else:
                    # 当前节点所有邻居都已处理完毕，回溯
                    stack.pop()
                    path.pop()
                    rec_stack.remove(node)

        return all_cycles

    def _find_cycle_nodes(
        self,
        graph: Dict[str, List[str]],
        remaining: Set[str]
    ) -> List[str]:
        """从剩余节点中用 DFS 检测环。

        Args:
            graph: 邻接表
            remaining: 还未处理的节点集合

        Returns:
            环中的节点列表。如果存在多个环，返回所有环的节点。
        """
        all_cycles = self._find_all_cycles(graph, remaining)

        if not all_cycles:
            return list(remaining)

        # 返回所有环的节点（去重后）
        cycle_nodes = []
        for cycle in all_cycles:
            cycle_nodes.extend(cycle[:-1])  # 最后一个和第一个是重复的环节点

        # 去重并保持顺序
        seen = set()
        unique_cycle_nodes = []
        for node in cycle_nodes:
            if node not in seen:
                seen.add(node)
                unique_cycle_nodes.append(node)

        return unique_cycle_nodes

    # ============================================================
    # 主执行流程
    # ============================================================

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

    async def execute(
        self,
        graph_data: Dict[str, Any],
        execution_id: int,
        trigger_type: str = "manual",
        trigger_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行规则图。

        Args:
            graph_data: 规则图数据（nodes, edges, variables）
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
        raw_nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])
        variables = graph_data.get("variables", {})

        # 统一节点格式：前端保存为 list [{id, type, data}],
        # 执行器内部使用 dict {node_id: node}
        if isinstance(raw_nodes, list):
            nodes = {n["id"]: n for n in raw_nodes if "id" in n}
        elif isinstance(raw_nodes, dict):
            nodes = dict(raw_nodes)
        else:
            nodes = {}

        if not nodes:
            raise ValidationError("规则图为空")

        # 校验图连接（端口类型兼容性）
        nodes_list = list(nodes.values())
        self._validate_graph_connections(nodes_list, edges)

        # 拓扑排序
        try:
            levels = self.topological_sort_levels(nodes, edges)
        except CycleError:
            raise

        # ============ Phase 19.1: Branch 分流支持 ============
        # 预扫: 收集所有 Branch 节点的输出边, 按 sourceHandle ("true"/"false") 分组
        # 执行时根据 Branch 节点 result["branch"] 决定跳过分支
        # 不重算拓扑 (一次性 Kahn 排序保持), 只在执行层跳过
        branch_outputs: Dict[str, Dict[str, List[str]]] = {}
        for edge in edges:
            src = edge.get("source")
            src_handle = edge.get("sourceHandle") or edge.get("source_handle")
            tgt = edge.get("target")
            if not src or not tgt or not src_handle:
                continue
            node_type = (nodes.get(src, {}).get("data", {}) or {}).get("type") or nodes.get(src, {}).get("type")
            if node_type == "branch":
                branch_outputs.setdefault(src, {"true": [], "false": []})
                if src_handle in ("true", "false"):
                    branch_outputs[src][src_handle].append(tgt)
        skipped_node_ids: Set[str] = set()

        # P2-A (2026-06-19): 预扫描, 把禁用节点 (data.disabled === true) 加入 skipped
        #   这些节点及所有依赖它们的下游节点也会被跳过 (因为入度永不为 0 → 不加入层)
        #   简化处理: 仅直接跳过禁用节点自身 + 拓扑下沉标记
        disabled_ids = set()
        for node_id, node in nodes.items():
            node_data = (node.get("data") or {})
            if node_data.get("disabled") is True:
                disabled_ids.add(node_id)
        skipped_node_ids.update(disabled_ids)

        # 创建执行上下文
        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            node_results={},
            node_status={},
            variables=dict(variables),
            config={"nodes": nodes},
            cancelled=False,
            ws_manager=self.ws_manager
        )

        # 如果在调用 execute() 之前就已请求取消，需要继承取消状态
        # 注意：必须在 register_execution 之前检查旧的注册状态
        pre_cancelled = RuleGraphExecutor._active_executions.get(execution_id)
        was_cancelled = pre_cancelled and pre_cancelled.is_cancelled()

        # 注册执行上下文（会覆盖旧的）
        self.register_execution(execution_id, context)

        # 继承取消状态
        if was_cancelled:
            context.request_cancel()

        # 更新执行记录状态
        await self._update_execution_status(execution_id, "running")

        try:
            total_levels = len(levels)
            total_nodes = sum(len(level) for level in levels)

            # 执行每一层
            for level_idx, level in enumerate(levels):
                # 检查是否取消
                if context.is_cancelled():
                    await self._handle_cancellation(execution_id, context)
                    return {
                        "status": "cancelled",
                        "cancelled_at": datetime.now().isoformat(),
                        "completed_nodes": sum(len(levels[i]) for i in range(level_idx)),
                        "total_nodes": total_nodes
                    }

                # 推送进度
                await self._broadcast_progress(
                    execution_id,
                    level_idx,
                    total_levels,
                    len(level),
                    total_nodes,
                    levels
                )

                # 并行执行当前层 (传 skipped_set 让 _execute_level 分流)
                await self._execute_level(level, context, skipped_node_ids, branch_outputs)

            # 全部完成
            # 顶层状态由节点真实结果推导 —— 旧实现恒为 "completed",
            # 掩盖了「全部节点失败、零输出」的情况。
            failed_nodes = [
                node_id for node_id, st in context.node_status.items()
                if st in ("failed", "timeout")
            ]
            top_status = "failed" if failed_nodes else "completed"
            result = {
                "status": top_status,
                "completed_at": datetime.now().isoformat(),
                "node_results": context.node_results,
                "failed_nodes": failed_nodes,
                "error": (
                    f"{len(failed_nodes)} 个节点执行失败: {', '.join(failed_nodes[:10])}"
                    if failed_nodes else None
                ),
                # 落库摘要: 只含状态与指标, 不含可能带 base64 图像的原始输出
                "summary": {
                    "node_status": dict(context.node_status),
                    "node_count": len(context.node_status),
                },
            }

            await self._update_execution_status(execution_id, top_status, result)
            await self._broadcast_complete(execution_id, result)

            return result

        except Exception as e:
            await self._handle_execution_error(execution_id, context, e)
            raise
        finally:
            # 确保注销
            self.unregister_execution(execution_id)

    async def _execute_level(
        self,
        level: List[str],
        context: ExecutionContext,
        skipped_node_ids: Set[str] = None,
        branch_outputs: Dict[str, Dict[str, List[str]]] = None,
    ):
        """执行同一层的所有节点（并行）。

        Args:
            level: 当前层节点 ID 列表
            context: 执行上下文
            skipped_node_ids: 已被 Branch 分流跳过的节点 ID 集合 (Phase 19.1)
            branch_outputs: Branch 节点输出边索引 {branch_id: {"true": [...], "false": [...]}}
        """
        # Phase 19.1: 默认空集合, 兼容直接调用 (单测, 内部测试)
        if skipped_node_ids is None:
            skipped_node_ids = set()
        if branch_outputs is None:
            branch_outputs = {}

        # 跳过被 branch 跳过的节点
        executable = [nid for nid in level if nid not in skipped_node_ids]
        skipped_in_level = [nid for nid in level if nid in skipped_node_ids]

        # 先标记 skipped 节点
        for nid in skipped_in_level:
            context.set_node_status(nid, "skipped")
            # 写 NodeExecutionLog
            node = context.config.get("nodes", {}).get(nid, {})
            node_type = (node.get("data", {}) or {}).get("type") or node.get("type") or "unknown"
            await self._save_node_log(
                execution_id=context.execution_id,
                node_id=nid,
                node_type=node_type,
                status="skipped",
                duration_ms=0,
                error_message="Branch 分流未走该分支",
                metrics={},
            )

        if not executable:
            return

        tasks = [
            self._execute_node(node_id, context)
            for node_id in executable
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查是否有失败
        for node_id, result in zip(executable, results):
            if isinstance(result, Exception):
                context.set_node_status(node_id, "failed")

        # Phase 19.1: Branch 节点完成后, 标记未走分支的下游节点为 skipped
        # 在 _execute_node 完成后 (已写 context.node_results), 扫描可执行节点
        for node_id in executable:
            node = context.config.get("nodes", {}).get(node_id, {})
            node_type = (node.get("data", {}) or {}).get("type") or node.get("type")
            if node_type != "branch":
                continue
            if node_id not in branch_outputs:
                continue
            result = context.get_node_result(node_id, "branch")
            if result not in ("true", "false"):
                # branch 字段缺失或异常值, 不跳过 (保守: 都跑)
                continue
            # 未走的那条 output 边 target 加入 skipped
            not_taken = "true" if result == "false" else "false"
            for tgt in branch_outputs[node_id].get(not_taken, []):
                if tgt not in skipped_node_ids:
                    skipped_node_ids.add(tgt)

    async def _execute_node(
        self,
        node_id: str,
        context: ExecutionContext,
        timeout: int = None
    ):
        """执行单个节点。

        使用 asyncio.wait_for 提供超时保护，
        超时后标记节点为 failed 并继续执行下游。

        Args:
            node_id: 节点 ID
            context: 执行上下文
            timeout: 节点执行超时时间（秒），默认从上下文配置读取或 300s
        """
        start_time = time.monotonic()
        execution_start = datetime.now()

        # 从上下文读取超时配置（可在规则图级别覆盖）
        if timeout is None:
            timeout = context.config.get('node_timeout', 300)
        if context.is_cancelled():
            context.set_node_status(node_id, "cancelled")
            return

        # 获取节点信息
        node = context.config.get("nodes", {}).get(node_id)
        if not node:
            raise ExecutorError(f"节点 {node_id} 不存在", node_id=node_id)

        node_data = node.get("data", {})
        # 节点类型：优先读 data.type（前端格式），兼容 node.type（测试格式）
        node_type = node_data.get("type") or node.get("type")
        # 配置参数：兼容前端格式 data.config（扁平）和测试格式 data.params（嵌套）
        flat_config = node_data.get("config") or node_data.get("params", {})
        params = flat_config if isinstance(flat_config, dict) else {}
        # 输入端口连接信息
        # 新契约: data.connections = {目标端口名: {node_id, output}}
        # 旧契约: data.inputs 为 dict 时同样兼容(存量图)
        # 端口元数据(data.inputs 为数组)不含连线信息, 不能当连接配置用。
        inputs_config = node_data.get("connections")
        if not isinstance(inputs_config, dict):
            inputs_config = node_data.get("inputs")
        if not isinstance(inputs_config, dict):
            inputs_config = {}

        # 更新状态为 running
        context.set_node_status(node_id, "running")
        await self._broadcast_node_started(context.execution_id, node_id, node_type)

        status = "failed"
        error_msg = None
        outputs = None
        # BE-P0-2 (2026-06-19): executor 提前 None 化, finally cleanup 安全
        executor = None

        try:
            # 解析输入数据
            inputs = self._resolve_inputs(inputs_config, context)

            # 合并默认参数
            merged_inputs = {**inputs, **params}

            # 获取执行器实例（包装配置为 {params: ...} 格式，兼容各节点 executor 的读取方式）
            registry = get_registry()
            executor = registry.create_node(
                node_type,
                node_id=node_id,
                config={"params": params}
            )

            if not executor:
                raise ExecutorError(f"未知的节点类型: {node_type}", node_id=node_id, node_type=node_type)

            # P0-A (2026-09-11): 执行期 hard fail - 强类型校验节点配置。
            # graph_manager 保存期已 soft warn, 这里是兜底: 即使上游未校验,
            # 也确保运行时配置合法, 并用 sanitized_config 替换原 params
            # (Pydantic 会丢弃未知字段 + 应用默认值, 与后续 execute() 行为一致)。
            # 用 getattr 容错: 测试 mock 类 (test_executor_fault_isolation.OkExec) 不继承
            # BaseExecutor 时不会崩, 与下方 cleanup 容错模式一致。
            validate_config = getattr(executor, "validate_config", None)
            if validate_config is not None:
                is_valid, config_err, sanitized_config = validate_config(params)
                if not is_valid:
                    raise ExecutorError(
                        f"节点配置校验失败: {config_err}",
                        node_id=node_id,
                        node_type=node_type,
                    )
                if sanitized_config:
                    params = sanitized_config

            # 校验输入
            is_valid, error_msg = executor.validate_inputs(merged_inputs)
            if not is_valid:
                raise ExecutorError(
                    f"输入校验失败: {error_msg}",
                    node_id=node_id,
                    node_type=node_type
                )

            # 节点级超时覆盖：优先使用节点定义中的 default_timeout，
            # 然后是规则图级别的 node_timeout，最后是 300s 默认
            node_timeout = getattr(executor, "default_timeout", None) or timeout
            # 执行（带超时保护）
            outputs = await asyncio.wait_for(
                executor.execute(merged_inputs, context),
                timeout=node_timeout
            )

            # 计算执行耗时
            node_duration_ms = int((time.monotonic() - start_time) * 1000)

            # 保存结果
            context.set_node_result(node_id, outputs)
            context.set_node_status(node_id, "completed")
            status = "completed"

            # 计算输出指标（detections 数量、数据量等），用于前端轻量级展示
            node_metrics = self._compute_metrics(outputs)

            # 推送节点完成（含耗时 + 指标）
            await self._broadcast_node_executed(
                context.execution_id,
                node_id,
                "success",
                outputs,
                duration_ms=node_duration_ms,
                metrics=node_metrics,
            )

        except asyncio.TimeoutError:
            status = "failed"
            error_msg = f"执行超时（{node_timeout}s）"
            # 超时：标记为 failed，不抛异常继续执行下游（断路器模式）
            context.set_node_status(node_id, "failed")
            await self._broadcast_node_timeout(
                context.execution_id,
                node_id,
                timeout_seconds=node_timeout,
                error=error_msg
            )

        except Exception as e:
            # BE-P0-2 修复 (2026-06-19): 异常对象连同 traceback 一并写入 status
            #   WS 推送完整堆栈, 便于排查 (之前只存 str(e), 丢上下文)
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            status = "failed"
            context.set_node_status(node_id, "failed")
            await self._broadcast_node_failed(context.execution_id, node_id, error_msg)

            if isinstance(e, ExecutorError):
                raise

            raise ExecutorError(
                f"节点执行失败: {str(e)}",
                node_id=node_id,
                node_type=node_type
            ) from e

        finally:
            # BE-P0-2 修复 (2026-06-19): 节点级资源清理
            #   若 executor 实现了 async cleanup() / close() 钩子, 必调 (finally 兜底)
            #   用于释放模型句柄、临时帧缓冲、GPU 显存等
            if executor is not None:
                cleanup = getattr(executor, "cleanup", None) or getattr(executor, "close", None)
                if cleanup is not None:
                    try:
                        result = cleanup()
                        if hasattr(result, "__await__"):
                            await result
                    except Exception as cleanup_err:
                        # cleanup 失败不掩盖主结果, 只记录
                        logger.warning(
                            "节点 %s 资源清理失败: %s",
                            node_id, cleanup_err,
                            exc_info=True,
                        )
            # 计算耗时并保存执行日志
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            metrics = self._compute_metrics(outputs or {})
            await self._save_node_log(
                execution_id=context.execution_id,
                node_id=node_id,
                node_type=node_type,
                status=status,
                duration_ms=elapsed_ms,
                error_message=error_msg,
                metrics=metrics
            )

    def _resolve_inputs(
        self,
        inputs_config: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """解析节点的输入数据。

        从已完成的节点结果或默认值中获取输入。
        支持 {{variable}} 语法变量插值。

        Args:
            inputs_config: 端口连接配置。
                新契约 `data.connections`: {端口名: {node_id, output}}；
                旧契约 `data.inputs` 为 dict 时同构兼容；
                若传入 list(端口元数据数组), 视为无连接信息, 返回空字典。
            context: 执行上下文

        Returns:
            {端口名: 输入值}；未解析到的端口不出现在结果中。
        """
        inputs = {}

        # 容错: 前端历史版本把 data.inputs 存成端口元数据数组, 直接调 .items() 会崩
        # (实测导致 54 个节点全部崩溃、0 输出)
        if not isinstance(inputs_config, dict):
            return inputs

        for port_name, config in inputs_config.items():
            if not isinstance(config, dict):
                continue
            # 优先从连接的节点获取
            if config.get("node_id"):
                source_node = config["node_id"]
                source_output = config.get("output", "result")
                inputs[port_name] = context.get_node_result(source_node, source_output)
            # 其次使用默认值（支持 {{variable}} 变量插值）
            elif "value" in config:
                inputs[port_name] = self._interpolate(config["value"], context)
            # 既无连线也无默认值: 不写入该键, 让下游的输入校验尽早暴露缺失

        return inputs

    def _interpolate(self, value: Any, context: ExecutionContext, visited: Set[str] = None) -> Any:
        """解析 {{variable}} 变量插值语法。

        Args:
            value: 原始值，可能是字符串或普通类型
            context: 执行上下文，包含 variables
            visited: 已访问的变量集合，用于检测循环引用

        Returns:
            解析后的值。如果 value 不是字符串或不含 {{}}，直接返回原值。

        Raises:
            ExecutorError: 如果检测到循环引用
        """
        if not isinstance(value, str):
            return value

        # 初始化 visited 集合（用于检测循环引用）
        if visited is None:
            visited = set()

        # 匹配 {{variable_name}} 格式
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, value)

        if not matches:
            return value

        result = value
        for var_name in matches:
            # 检测循环引用：变量已在当前替换路径中
            if var_name in visited:
                raise ExecutorError(
                    f"变量插值存在循环引用: {{{{{var_name}}}}}",
                    node_id=None,
                    node_type=None
                )
            # 将当前变量加入已访问集合
            visited.add(var_name)

            var_value = context.variables.get(var_name, f'{{{{{var_name}}}}}')
            # 递归解析变量值（可能包含更多插值）
            if isinstance(var_value, str) and '{{' in var_value:
                var_value = self._interpolate(var_value, context, visited)
            # 替换所有 {{var_name}} 为变量值
            result = result.replace(f'{{{{{var_name}}}}}', str(var_value))

            # 从已访问集合中移除（允许同一变量在不同路径中出现）
            visited.discard(var_name)

        # 尝试转换类型
        return self._try_convert(result)

    def _try_convert(self, value: str) -> Any:
        """尝试将字符串转换为适当类型。"""
        # 布尔值
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False

        # 数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 返回字符串
        return value

    # ============================================================
    # 指标采集 & 日志
    # ============================================================

    def _compute_metrics(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """计算节点输出数据的统计指标。

        Args:
            outputs: 节点输出数据字典

        Returns:
            指标字典，包含各输出的数据量估计
        """
        metrics = {}
        for key, value in outputs.items():
            if isinstance(value, list):
                metrics[key] = len(value)
            elif isinstance(value, dict):
                metrics[key] = len(value)
            elif isinstance(value, str):
                metrics[key] = len(value)
            elif isinstance(value, (int, float)):
                metrics[key] = 1
            elif value is None:
                metrics[key] = 0
            else:
                metrics[key] = 1  # 其他类型记为 1
        return metrics

    async def _save_node_log(
        self,
        execution_id: int,
        node_id: str,
        node_type: str,
        status: str,
        duration_ms: int,
        error_message: str = None,
        metrics: Dict[str, Any] = None
    ):
        """保存节点执行日志到数据库。

        Args:
            execution_id: 执行记录 ID
            node_id: 节点 ID
            node_type: 节点类型
            status: 执行状态
            duration_ms: 执行耗时（毫秒）
            error_message: 错误信息
            metrics: 输出指标数据
        """
        if not self.db:
            return

        try:
            from backend.database import NodeExecutionLog

            log = NodeExecutionLog(
                execution_id=execution_id,
                node_id=node_id,
                node_type=node_type,
                status=status,
                duration_ms=duration_ms,
                start_time=datetime.now(),
                end_time=datetime.now(),
                error_message=error_message,
                metrics_json=json.dumps(metrics, default=str) if metrics else None
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            # 日志保存失败不影响主流程
            pass

    # ============================================================
    # WebSocket 广播
    # ============================================================

    async def _broadcast_node_started(
        self,
        execution_id: int,
        node_id: str,
        node_type: str
    ):
        """广播节点开始执行。"""
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_started",
                "execution_id": execution_id,
                "node_id": node_id,
                "node_type": node_type,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_node_executed(
        self,
        execution_id: int,
        node_id: str,
        status: str,
        outputs: Dict[str, Any],
        duration_ms: int = None,
        metrics: Dict[str, Any] = None,
    ):
        """广播节点执行完成。

        Args:
            metrics: 节点输出指标（detections 数量、数据量等），可选。
                前端可基于 metrics 做轻量级展示（徽章、计数等），
                无需解析完整 outputs 即可了解节点产出规模。
        """
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_executed",
                "execution_id": execution_id,
                "node_id": node_id,
                "status": status,
                "outputs": outputs,
                "duration_ms": duration_ms,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_node_failed(
        self,
        execution_id: int,
        node_id: str,
        error: str
    ):
        """广播节点执行失败。"""
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_failed",
                "execution_id": execution_id,
                "node_id": node_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_node_timeout(
        self,
        execution_id: int,
        node_id: str,
        timeout_seconds: float,
        error: str = None
    ):
        """广播节点执行超时。

        区别于通用的 node_failed：用于前端做差异化展示（黄色警告 vs 红色错误）。
        超时后下游节点仍会继续执行（断路器模式）。
        """
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_timeout",
                "execution_id": execution_id,
                "node_id": node_id,
                "timeout_seconds": timeout_seconds,
                "error": error or f"节点执行超时（{timeout_seconds}s）",
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_progress(
        self,
        execution_id: int,
        current_level: int,
        total_levels: int,
        nodes_in_level: int,
        total_nodes: int,
        levels: List[List[str]] = None
    ):
        """广播执行进度。"""
        if self.ws_manager:
            completed_nodes = 0
            if levels:
                completed_nodes = sum(len(levels[i]) for i in range(current_level))

            await self.ws_manager.broadcast({
                "type": "execution_progress",
                "execution_id": execution_id,
                "progress": int((current_level + 1) / total_levels * 100) if total_levels > 0 else 0,
                "current_level": current_level + 1,
                "total_levels": total_levels,
                "completed_nodes": completed_nodes,
                "total_nodes": total_nodes,
                "timestamp": datetime.now().isoformat()
            })

    async def _broadcast_complete(
        self,
        execution_id: int,
        result: Dict[str, Any]
    ):
        """广播执行完成。"""
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": result.get("status", "completed"),
                "result": result,
                "timestamp": datetime.now().isoformat()
            })

    # ============================================================
    # 数据库操作
    # ============================================================

    async def _update_execution_status(
        self,
        execution_id: int,
        status: str,
        result: Dict[str, Any] = None
    ):
        """更新执行记录状态。"""
        if not self.db:
            return

        record = self.db.query(ExecutionHistory).filter(
            ExecutionHistory.id == execution_id
        ).first()

        if record:
            record.status = status

            if status == "running" and not record.start_time:
                record.start_time = datetime.now()

            if status in ("completed", "failed", "cancelled"):
                record.end_time = datetime.now()
                # 安全检查：只有当 start_time 是真实 datetime 时才计算 delta
                try:
                    if record.start_time and isinstance(record.start_time, datetime):
                        delta = record.end_time - record.start_time
                except (TypeError, AttributeError):
                    pass

            if result:
                # 只落轻量摘要: node_results 可能含 base64 图像, 不能整份入库。
                # 原始负载保留在 execute() 返回值与 WS 推送里。
                summary = result.get("summary") or {
                    "status": result.get("status"),
                    "completed_at": result.get("completed_at"),
                    "failed_nodes": result.get("failed_nodes", []),
                    "error": result.get("error"),
                }
                record.result_json = json.dumps(summary, default=str)

            self.db.commit()

    async def _handle_cancellation(
        self,
        execution_id: int,
        context: ExecutionContext
    ):
        """处理执行取消。"""
        await self._update_execution_status(execution_id, "cancelled")

        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "cancelled",
                "message": "执行已被用户取消",
                "node_results": context.node_results,
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_execution_error(
        self,
        execution_id: int,
        context: ExecutionContext,
        error: Exception
    ):
        """处理执行错误。"""
        error_message = str(error)

        if self.db:
            record = self.db.query(ExecutionHistory).filter(
                ExecutionHistory.id == execution_id
            ).first()

            if record:
                record.status = "failed"
                record.end_time = datetime.now()
                record.result_json = json.dumps({
                    "error": error_message,
                    "node_results": context.node_results
                }, default=str)
                self.db.commit()

        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "failed",
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            })
