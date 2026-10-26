# -*- coding: utf-8 -*-
"""图管理器 - 管理规则图的创建、更新、验证。"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.database import RuleGraph
from backend.services.rule_engine.registry import get_registry
from backend.services.rule_engine.migrations import (
    CURRENT_SCHEMA_VERSION,
    migrate_graph_data,
)

logger = logging.getLogger(__name__)


class GraphValidationError(Exception):
    """图验证异常。"""
    pass


class GraphManager:
    """规则图管理器。

    负责规则图的创建、读取、更新、删除和验证。
    """

    def __init__(self, db: Session):
        """初始化图管理器。

        Args:
            db: 数据库会话
        """
        self.db = db

    def _validate_nodes_config(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """P0-A (2026-09-11): 校验所有节点的配置, 收集警告信息。

        遍历 nodes 列表, 对每个节点:
        1. 解析 node_type (兼容 data.type 与顶层 type 两种字段位置)
        2. 通过 registry 获取 executor 类
        3. 调用 executor.validate_config(params) 收集警告

        注意: 这是 soft warn, 不抛异常, 仅返回警告列表 (供前端展示)。

        Args:
            nodes: 节点 dict 列表 (前端 VueFlow 或后端直存格式)

        Returns:
            警告字符串列表 (每条形如 "node {id} ({type}): {err}")
        """
        warnings: List[str] = []
        registry = get_registry()

        for node in nodes:
            node_id = node.get("id", "<unknown>")
            # 兼容两种字段位置: data.type vs 顶层 type
            data_type = (node.get("data") or {}).get("type") or ""
            node_type = data_type or node.get("type") or ""
            if not node_type:
                continue  # 无类型节点跳过 (VueFlow 占位等)

            executor_class = registry.get(node_type)
            if executor_class is None:
                warnings.append(f"node {node_id}: 未知节点类型 '{node_type}'")
                continue

            # 提取配置: data.params 是权威, 顶层 params 兜底
            params = (node.get("data") or {}).get("params") or node.get("params") or {}
            executor = executor_class()
            is_valid, err_msg, _ = executor.validate_config(params)
            if not is_valid:
                warnings.append(
                    f"node {node_id} ({node_type}): {err_msg}"
                )
        return warnings

    def create_graph(
        self,
        name: str,
        nodes_json: str = "[]",
        edges_json: str = "[]",
        variables_json: Optional[str] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
    ) -> RuleGraph:
        """创建新规则图。

        Args:
            name: 规则图名称
            nodes_json: 节点JSON字符串
            edges_json: 边JSON字符串
            variables_json: 变量JSON字符串
            description: 规则图描述
            version: 版本号

        Returns:
            创建的规则图对象
        """
        graph = RuleGraph(
            name=name,
            description=description,
            nodes_json=nodes_json,
            edges_json=edges_json,
            variables_json=variables_json or "{}",
            version=version,
        )
        self.db.add(graph)
        self.db.commit()
        self.db.refresh(graph)
        return graph

    def get_graph(self, graph_id: int) -> Optional[RuleGraph]:
        """获取规则图。

        P0-B (2026-09-11): 返回前调用 _migrate_if_needed, 旧版本图自动升级并落库。

        Args:
            graph_id: 规则图ID

        Returns:
            规则图对象，未找到返回 None
        """
        graph = self.db.query(RuleGraph).filter(RuleGraph.id == graph_id).first()
        if graph is not None:
            self._migrate_if_needed(graph)
        return graph

    def get_all_graphs(self) -> list[RuleGraph]:
        """获取所有规则图。

        P0-B: 对每个图尝试迁移升级, 但失败 soft warn (保留原数据)。

        Returns:
            规则图列表
        """
        graphs = self.db.query(RuleGraph).order_by(RuleGraph.updated_at.desc()).all()
        for g in graphs:
            self._migrate_if_needed(g)
        return graphs

    def get_active_graphs(self) -> list[RuleGraph]:
        """获取所有激活的规则图。

        P0-B: 对每个图尝试迁移升级。

        Returns:
            激活的规则图列表
        """
        graphs = self.db.query(RuleGraph).filter(RuleGraph.is_active == True).all()
        for g in graphs:
            self._migrate_if_needed(g)
        return graphs

    def _migrate_if_needed(self, graph: RuleGraph) -> None:
        """P0-B: 如果图 schema_version 低于当前版本, 自动迁移并落库。

        失败策略: soft warn, logger.warning + 返回原数据 + 不升级 schema_version。
        这样保证历史图不会被破坏, 运维有信号但不会阻塞业务。
        """
        current_v = graph.schema_version or 1
        if current_v >= CURRENT_SCHEMA_VERSION:
            return

        try:
            nodes = json.loads(graph.nodes_json or "[]")
            edges = json.loads(graph.edges_json or "[]")
            variables = json.loads(graph.variables_json or "{}")
        except json.JSONDecodeError:
            logger.warning(
                "规则图 %d JSON 解析失败, 跳过迁移", graph.id
            )
            return

        try:
            new_nodes, new_edges, new_variables, new_v = migrate_graph_data(
                nodes, edges, variables, current_v
            )
        except Exception as e:
            logger.warning(
                "规则图 %d schema_version %d 迁移失败: %s, 保留原数据",
                graph.id, current_v, e,
            )
            return

        if new_v > current_v:
            graph.nodes_json = json.dumps(new_nodes, ensure_ascii=False)
            graph.edges_json = json.dumps(new_edges, ensure_ascii=False)
            graph.variables_json = json.dumps(new_variables, ensure_ascii=False)
            graph.schema_version = new_v
            self.db.commit()
            logger.info(
                "规则图 %d 已从 schema_version %d 升级到 %d",
                graph.id, current_v, new_v,
            )

    def update_graph(
        self,
        graph_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes_json: Optional[str] = None,
        edges_json: Optional[str] = None,
        variables_json: Optional[str] = None,
        is_active: Optional[bool] = None,
        cron_expression: Optional[str] = None,
        thumbnail: Optional[str] = None,
    ) -> Tuple[Optional[RuleGraph], List[str]]:
        """更新规则图。

        P0-A (2026-09-11): 返回值扩展为 (graph, warnings)。
        保存期调用 _validate_nodes_config 做 soft warn, 不阻断保存。

        Args:
            graph_id: 规则图ID
            name: 规则图名称
            description: 规则图描述
            nodes_json: 节点JSON字符串
            edges_json: 边JSON字符串
            variables_json: 变量JSON字符串
            is_active: 是否激活
            cron_expression: 定时触发 Cron 表达式
            thumbnail: 缩略图 Base64

        Returns:
            (更新后的规则图对象 [或 None], 配置校验警告列表)
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            return None, []

        warnings: List[str] = []
        if name is not None:
            graph.name = name
        if description is not None:
            graph.description = description
        if nodes_json is not None:
            graph.nodes_json = nodes_json
            # P0-A: 保存期 soft warn, 校验所有节点配置
            try:
                nodes = json.loads(nodes_json)
                if isinstance(nodes, list):
                    warnings.extend(self._validate_nodes_config(nodes))
            except json.JSONDecodeError:
                warnings.append("nodes_json 解析失败, 跳过配置校验")
        if edges_json is not None:
            graph.edges_json = edges_json
        if variables_json is not None:
            graph.variables_json = variables_json
        if is_active is not None:
            graph.is_active = is_active
        if cron_expression is not None:
            graph.cron_expression = cron_expression
        if thumbnail is not None:
            graph.thumbnail = thumbnail

        if warnings:
            logger.warning(
                "规则图 %d 保存时发现配置问题: %s",
                graph_id,
                "; ".join(warnings[:5]) + ("..." if len(warnings) > 5 else ""),
            )

        self.db.commit()
        self.db.refresh(graph)
        return graph, warnings

    def delete_graph(self, graph_id: int) -> bool:
        """删除规则图。

        Args:
            graph_id: 规则图ID

        Returns:
            是否成功删除
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            return False

        self.db.delete(graph)
        self.db.commit()
        return True

    def validate_graph(self, graph_id: int) -> tuple[bool, Optional[str]]:
        """验证规则图的完整性。

        检查:
        - 图是否有孤立节点（没有被任何边连接）
        - 图是否有循环引用（对于 DAG 执行模型）
        - 起始节点是否存在

        Args:
            graph_id: 规则图ID

        Returns:
            (是否有效, 错误信息)
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            return False, "规则图不存在"

        try:
            nodes = json.loads(graph.nodes_json)
            edges = json.loads(graph.edges_json)
        except json.JSONDecodeError as e:
            return False, f"JSON 解析错误: {str(e)}"

        # 构建节点和边的映射
        node_ids = {node["id"] for node in nodes}
        edge_sources = {edge["source"] for edge in edges}
        edge_targets = {edge["target"] for edge in edges}

        # P0-1 (2026-06-19): 拒绝自循环边 (source == target)
        # 历史: 之前没拒绝, 自循环边会让 Kahn 拓扑 in_degree 永不为 0, 触发误导性 "循环依赖" 错误
        self_loops = [
            edge["id"] for edge in edges
            if edge.get("source") and edge["source"] == edge.get("target")
        ]
        if self_loops:
            return False, f"存在自循环边（source == target）: {', '.join(self_loops)}"

        # P0-1 (2026-06-19): 拒绝重复边 (同 source+target+source_handle+target_handle)
        # 重复边会让下游节点被多次触发, 且端口 is-connected 状态不能区分多条
        seen_edges: set = set()
        duplicate_edges = []
        for edge in edges:
            key = (
                edge.get("source"),
                edge.get("target"),
                edge.get("source_handle") or edge.get("sourceHandle"),
                edge.get("target_handle") or edge.get("targetHandle"),
            )
            if key in seen_edges:
                duplicate_edges.append(edge.get("id", str(key)))
            else:
                seen_edges.add(key)
        if duplicate_edges:
            return False, f"存在重复边（同 source+target+handles）: {', '.join(duplicate_edges)}"

        # 兼容两种节点 type 字段位置：
        # - 后端测试/直存格式：node.type 在顶层（值为具体节点类型）
        # - VueFlow 前端格式：node.type="ruleNode"（节点种类），实际类型在 node.data.type
        # 原则：data.type 是权威业务类型（前端 VueFlow 总是设置，后端直存也常设置），
        # 顶层 type 可能是 VueFlow 占位（"ruleNode"/"custom"/"group" 等），
        # 仅当 data.type 缺失时才回退到顶层 type。
        def get_node_type(node: dict) -> str:
            data_type = (node.get("data") or {}).get("type") or ""
            if data_type:
                return data_type
            return node.get("type") or ""

        # 检查孤立节点（排除没有输入边的节点，因为触发器节点通常没有输入）
        isolated_nodes = []
        for node in nodes:
            node_id = node["id"]
            # 检查是否有输出边
            if node_id not in edge_sources and node_id not in edge_targets:
                # 如果既没有输入边也没有输出边，则为孤立节点
                # 排除触发器类型的节点
                node_type = get_node_type(node)
                if node_type not in ("yolo_trigger", "timer_trigger", "manual_trigger"):
                    isolated_nodes.append(node_id)
        if isolated_nodes:
            return False, f"存在孤立节点（无输入输出边）: {', '.join(isolated_nodes)}"

        # 检查目标节点是否存在
        for target in edge_targets:
            if target not in node_ids:
                return False, f"边指向不存在的节点: {target}"

        # 检查源节点是否存在
        for source in edge_sources:
            if source not in node_ids:
                return False, f"边源自不存在的节点: {source}"

        # 检查是否有起始节点（没有输入边的节点，且类型为触发器）
        trigger_nodes = {
            node["id"] for node in nodes
            if get_node_type(node) in ("yolo_trigger", "timer_trigger", "manual_trigger")
        }
        nodes_without_inputs = node_ids - edge_targets

        # 如果所有没有输入边的节点都不是触发器，则图无效
        if nodes_without_inputs and not trigger_nodes.intersection(nodes_without_inputs):
            return False, "规则图没有起始触发器节点"

        # P1-1 (2026-06-19): 检查必填输入端口是否都已连接
        # 构建 (node_id, target_handle) → 边存在 索引
        target_handle_pairs = set()
        for edge in edges:
            target_handle_pairs.add((edge.get("target"), edge.get("target_handle") or edge.get("targetHandle")))

        missing_required = []
        for node in nodes:
            node_id = node["id"]
            # 兼容两种字段位置: front-end data.inputs vs backend defn.inputs
            input_ports = (node.get("data") or {}).get("inputs") or node.get("inputs") or {}
            # 前端是 list[dict], 后端是 dict[name, PortDefinition], 统一为可迭代
            if isinstance(input_ports, dict):
                items = [(k, v) for k, v in input_ports.items()]
            else:
                items = [(p.get("name"), p) for p in input_ports]
            # 节点显式声明的连线端口也算「已连接」
            declared = (node.get("data") or {}).get("connections") or {}
            if isinstance(declared, dict):
                known = {name for name, _ in items}
                for port_name in declared:
                    if port_name not in known:
                        items.append((port_name, {"required": True}))
            for port_name, port in items:
                required = (port or {}).get("required", False)
                if required and (node_id, port_name) not in target_handle_pairs:
                    missing_required.append(f"{node_id}.{port_name}")

        if missing_required:
            return False, f"必填输入端口未连接: {', '.join(missing_required[:10])}" + (
                f" 等 {len(missing_required)} 个" if len(missing_required) > 10 else ""
            )

        return True, None

    def parse_graph_data(self, graph: RuleGraph) -> dict:
        """解析图数据为字典格式。

        Args:
            graph: 规则图对象

        Returns:
            包含 nodes, edges, variables 的字典
        """
        return {
            "id": graph.id,
            "name": graph.name,
            "description": graph.description,
            "nodes": json.loads(graph.nodes_json),
            "edges": json.loads(graph.edges_json),
            "variables": json.loads(graph.variables_json) if graph.variables_json else {},
            "version": graph.version,
            "is_active": graph.is_active,
        }
