# -*- coding: utf-8 -*-
"""规则图执行器 - 执行规则图的核心引擎。"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Optional, Dict, List, Any

from backend.database import ExecutionHistory, NodeExecutionLog
from .nodes.base import BaseNode, ExecutionContext, NodeStatus, NodeResult
from .registry import NodeRegistry, init_builtin_executors


class ExecutionError(Exception):
    """执行异常。"""
    pass


class RuleGraphExecutor:
    """规则图执行器 - 负责执行规则图。

    使用异步遍历执行图节点，支持条件分支和并行执行。
    """

    def __init__(self, db_session=None):
        """初始化执行器。

        Args:
            db_session: 数据库会话（可选）
        """
        self.db = db_session
        self.registry: NodeRegistry = init_builtin_executors()

    async def execute(
        self,
        graph_data: dict,
        execution_id: Optional[int] = None,
        trigger_type: str = "manual",
        trigger_data: dict = None,
    ) -> dict:
        """执行规则图。

        Args:
            graph_data: 图数据，包含 nodes, edges, variables
            execution_id: 执行记录ID（用于数据库记录）
            trigger_type: 触发类型 (yolo/timer/manual/http)
            trigger_data: 触发数据（如 YOLO 检测结果）

        Returns:
            执行结果字典
        """
        context = ExecutionContext(
            execution_id=execution_id,
            trigger_data=trigger_data or {},
        )

        # 加载变量
        variables = graph_data.get("variables", {})
        for key, value in variables.items():
            context.set_var(key, value)

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            return {
                "status": "failed",
                "error": "规则图为空",
            }

        # 构建节点实例映射
        node_instances: Dict[str, BaseNode] = {}
        for node_data in nodes:
            node_type = node_data.get("type")
            node_id = node_data.get("id")
            node_config = node_data.get("data", {})

            node_instance = self.registry.create_node(node_type, node_id, node_config)
            if node_instance is None:
                raise ExecutionError(f"未知节点类型: {node_type}")

            node_instances[node_id] = node_instance

        # 构建边映射: source_id -> [(target_id, target_handle)]
        edge_map: Dict[str, list] = defaultdict(list)
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            source_handle = edge.get("source_handle")
            target_handle = edge.get("target_handle")
            edge_map[source].append({
                "target": target,
                "source_handle": source_handle,
                "target_handle": target_handle,
            })

        # 查找触发器节点（起始节点）
        trigger_nodes = [
            node_id for node_id, node in node_instances.items()
            if node.category.value == "trigger"
        ]

        if not trigger_nodes:
            raise ExecutionError("规则图没有触发器节点")

        # 执行图遍历
        try:
            result = await self._execute_from_nodes(
                trigger_nodes,
                node_instances,
                edge_map,
                context,
            )

            # 更新执行记录
            if execution_id and self.db:
                self._update_execution(
                    execution_id,
                    status="completed",
                    result=result,
                    logs=context.logs,
                )

            return {
                "status": "completed",
                "result": result,
                "logs": context.logs,
            }

        except Exception as e:
            # 更新执行记录
            if execution_id and self.db:
                self._update_execution(
                    execution_id,
                    status="failed",
                    result={"error": str(e)},
                    logs=context.logs,
                )

            return {
                "status": "failed",
                "error": str(e),
                "logs": context.logs,
            }

    async def _execute_from_nodes(
        self,
        node_ids: List[str],
        node_instances: Dict[str, BaseNode],
        edge_map: Dict[str, list],
        context: ExecutionContext,
        input_data: dict = None,
    ) -> dict:
        """从指定节点开始执行。

        Args:
            node_ids: 起始节点ID列表
            node_instances: 节点实例映射
            edge_map: 边映射
            context: 执行上下文
            input_data: 传递给起始节点的输入数据

        Returns:
            执行结果
        """
        results = {}

        for node_id in node_ids:
            node_result = await self._execute_node_recursive(
                node_id,
                node_instances,
                edge_map,
                context,
                input_data or {},
            )
            results[node_id] = node_result

        return results

    async def _execute_node_recursive(
        self,
        node_id: str,
        node_instances: Dict[str, BaseNode],
        edge_map: Dict[str, list],
        context: ExecutionContext,
        input_data: dict,
    ) -> dict:
        """递归执行节点及其下游节点。

        Args:
            node_id: 当前节点ID
            node_instances: 节点实例映射
            edge_map: 边映射
            context: 执行上下文
            input_data: 输入数据

        Returns:
            节点执行结果
        """
        node = node_instances.get(node_id)
        if node is None:
            return {"status": "failed", "error": f"节点不存在: {node_id}"}

        # 记录节点执行日志
        node_log_id = None
        if self.db and context.execution_id:
            node_log_id = self._create_node_log(
                context.execution_id,
                node_id,
                node.node_type,
                "running",
                input_data,
            )

        # 执行节点
        node_result = await node.execute(context, input_data)

        # 更新节点执行日志
        if self.db and node_log_id:
            self._update_node_log(
                node_log_id,
                status=node_result.status.value,
                output_data=node_result.output_data,
                error_message=node_result.error_message,
            )

        # 根据节点类型决定下游执行
        if node_result.status == NodeStatus.FAILED:
            return {
                "status": "failed",
                "error": node_result.error_message,
                "output": node_result.output_data,
            }

        # 获取下游节点
        downstream = edge_map.get(node_id, [])
        if not downstream:
            return {
                "status": "completed",
                "output": node_result.output_data,
            }

        # 处理下游节点
        # 根据节点类型决定执行策略
        if node.category.value == "condition":
            # 条件节点：根据输出数据选择分支
            condition_result = node_result.output_data.get("result", False)
            branch = "true" if condition_result else "false"

            # 找到对应分支的边
            for edge in downstream:
                if edge.get("target_handle") == branch or edge.get("source_handle") == branch:
                    return await self._execute_node_recursive(
                        edge["target"],
                        node_instances,
                        edge_map,
                        context,
                        node_result.output_data,
                    )
        else:
            # 其他节点：执行所有下游
            all_results = {}
            for edge in downstream:
                result = await self._execute_node_recursive(
                    edge["target"],
                    node_instances,
                    edge_map,
                    context,
                    node_result.output_data,
                )
                all_results[edge["target"]] = result

            return {
                "status": "completed",
                "output": node_result.output_data,
                "downstream": all_results,
            }

        return {
            "status": "completed",
            "output": node_result.output_data,
        }

    def _create_node_log(
        self,
        execution_id: int,
        node_id: str,
        node_type: str,
        status: str,
        input_data: dict,
    ) -> Optional[int]:
        """创建节点执行日志记录。"""
        try:
            log = NodeExecutionLog(
                execution_id=execution_id,
                node_id=node_id,
                node_type=node_type,
                status=status,
                input_data_json=json.dumps(input_data),
            )
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)
            return log.id
        except Exception:
            return None

    def _update_node_log(
        self,
        log_id: int,
        status: str,
        output_data: dict = None,
        error_message: str = None,
    ) -> None:
        """更新节点执行日志。"""
        try:
            log = self.db.query(NodeExecutionLog).filter(NodeExecutionLog.id == log_id).first()
            if log:
                log.status = status
                log.end_time = datetime.utcnow()
                if output_data:
                    log.output_data_json = json.dumps(output_data)
                if error_message:
                    log.error_message = error_message
                self.db.commit()
        except Exception:
            pass

    def _update_execution(
        self,
        execution_id: int,
        status: str,
        result: dict,
        logs: list,
    ) -> None:
        """更新执行记录。"""
        try:
            execution = self.db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
            if execution:
                execution.status = status
                execution.end_time = datetime.utcnow()
                execution.result_json = json.dumps(result)
                execution.logs_json = json.dumps(logs)
                self.db.commit()
        except Exception:
            pass

    def create_execution_record(
        self,
        graph_id: int,
        trigger_type: str,
        trigger_data: dict = None,
    ) -> Optional[int]:
        """创建执行记录。

        Args:
            graph_id: 规则图ID
            trigger_type: 触发类型
            trigger_data: 触发数据

        Returns:
            执行记录ID
        """
        if not self.db:
            return None

        try:
            execution = ExecutionHistory(
                graph_id=graph_id,
                status="running",
                trigger_type=trigger_type,
                trigger_data_json=json.dumps(trigger_data) if trigger_data else None,
            )
            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)
            return execution.id
        except Exception:
            return None
