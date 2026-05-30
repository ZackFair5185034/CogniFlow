# -*- coding: utf-8 -*-
"""规则图执行器 - Kahn 拓扑排序 + 层内并行执行。
按设计文档 phase2-execution-engine.md 实现。
"""
import asyncio
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.database import ExecutionHistory, NodeExecutionLog
from .exceptions import CycleError, ExecutorError, ValidationError
from .nodes.base import BaseExecutor, ExecutionContext, NodeStatus
from .registry import NodeRegistry, get_registry


class RuleGraphExecutor:
    """规则图执行引擎 - 负责图的解析、调度和执行。

    使用 Kahn 拓扑排序算法实现节点调度，同层节点并行执行。
    """

    # 保存所有进行中的执行上下文（用于取消操作）
    _active_executions: Dict[int, ExecutionContext] = {}

    # 端口类型兼容性矩阵
    PORT_COMPATIBILITY = {
        # 源类型: [兼容的目标类型]
        # ANY 可连接到所有类型
        "ANY": ["ANY", "IMAGE", "BBOX", "MASK", "SCORES", "TRIGGER", "CONTROL", "MODEL",
                "INT", "FLOAT", "BOOLEAN", "STRING", "ARRAY", "OBJECT"],
        "IMAGE": ["ANY", "IMAGE"],
        "BBOX": ["ANY", "BBOX"],
        "MASK": ["ANY", "MASK"],
        "SCORES": ["ANY", "SCORES"],
        "TRIGGER": ["ANY", "TRIGGER", "CONTROL"],
        "CONTROL": ["ANY", "CONTROL"],
        "MODEL": ["ANY", "MODEL"],
        "INT": ["ANY", "INT"],
        "FLOAT": ["ANY", "FLOAT"],
        "BOOLEAN": ["ANY", "BOOLEAN"],
        "STRING": ["ANY", "STRING"],
        "ARRAY": ["ANY", "ARRAY"],
        "OBJECT": ["ANY", "OBJECT"],
    }

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
            source_executor = registry.get(source_type)
            if not source_executor:
                continue
            source_def = source_executor.get_definition()
            source_port_type = None
            if source_handle and source_handle in source_def.outputs:
                source_port_type = source_def.outputs[source_handle].type
            elif source_def.outputs:
                # 如果没有指定handle，取第一个输出端口
                first_output = next(iter(source_def.outputs.values()))
                source_port_type = first_output.type

            # 获取目标节点输入端口类型
            target_executor = registry.get(target_type)
            if not target_executor:
                continue
            target_def = target_executor.get_definition()
            target_port_type = None
            if target_handle and target_handle in target_def.inputs:
                target_port_type = target_def.inputs[target_handle].type
            elif target_def.inputs:
                # 如果没有指定handle，取第一个输入端口
                first_input = next(iter(target_def.inputs.values()))
                target_port_type = first_input.type

            # 检查兼容性
            if source_port_type and target_port_type:
                compatible_types = self.PORT_COMPATIBILITY.get(source_port_type, [])
                if target_port_type not in compatible_types:
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
        nodes = graph_data.get("nodes", {})
        edges = graph_data.get("edges", [])
        variables = graph_data.get("variables", {})

        if not nodes:
            raise ValidationError("规则图为空")

        # 校验图连接（端口类型兼容性）
        # _validate_graph_connections 期望 List[Dict]，但 nodes 是 Dict[str, Dict] 结构
        nodes_list = [node for node in nodes.values()] if isinstance(nodes, dict) else nodes
        self._validate_graph_connections(nodes_list, edges)

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
        finally:
            # 确保注销
            self.unregister_execution(execution_id)

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
                context.set_node_status(node_id, "failed")

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

        node_type = node.get("type")
        node_data = node.get("data", {})
        params = node_data.get("params", {})
        inputs_config = node_data.get("inputs", {})

        # 更新状态为 running
        context.set_node_status(node_id, "running")
        await self._broadcast_node_started(context.execution_id, node_id, node_type)

        status = "failed"
        error_msg = None
        outputs = None

        try:
            # 解析输入数据
            inputs = self._resolve_inputs(inputs_config, context)

            # 合并默认参数
            merged_inputs = {**inputs, **params}

            # 获取执行器实例
            registry = get_registry()
            executor = registry.create_node(node_type, node_id=node_id, config=node_data)

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

            # 执行（带超时保护）
            outputs = await asyncio.wait_for(
                executor.execute(merged_inputs, context),
                timeout=timeout
            )

            # 计算执行耗时
            node_duration_ms = int((time.monotonic() - start_time) * 1000)

            # 保存结果
            context.set_node_result(node_id, outputs)
            context.set_node_status(node_id, "completed")
            status = "completed"

            # 推送节点完成（含耗时）
            await self._broadcast_node_executed(
                context.execution_id,
                node_id,
                "success",
                outputs,
                duration_ms=node_duration_ms
            )

        except asyncio.TimeoutError:
            status = "failed"
            error_msg = f"执行超时（{timeout}s）"
            # 超时：标记为 failed，不抛异常继续执行下游
            context.set_node_status(node_id, "failed")
            await self._broadcast_node_failed(
                context.execution_id,
                node_id,
                error_msg
            )

        except Exception as e:
            error_msg = str(e)
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
        """
        inputs = {}

        for port_name, config in inputs_config.items():
            if not isinstance(config, dict):
                config = {}
            # 优先从连接的节点获取
            if config.get("node_id"):
                source_node = config["node_id"]
                source_output = config.get("output", "result")
                inputs[port_name] = context.get_node_result(source_node, source_output)
            # 其次使用默认值（支持 {{variable}} 变量插值）
            elif "value" in config:
                inputs[port_name] = self._interpolate(config["value"], context)
            # 否则为 None

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
        duration_ms: int = None
    ):
        """广播节点执行完成。"""
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "node_executed",
                "execution_id": execution_id,
                "node_id": node_id,
                "status": status,
                "outputs": outputs,
                "duration_ms": duration_ms,
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
                record.result_json = json.dumps(result, default=str)

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
