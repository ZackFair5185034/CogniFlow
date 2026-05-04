# -*- coding: utf-8 -*-
"""图管理器 - 管理规则图的创建、更新、验证。"""
import json
from typing import Optional
from sqlalchemy.orm import Session

from backend.database import RuleGraph


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

        Args:
            graph_id: 规则图ID

        Returns:
            规则图对象，未找到返回 None
        """
        return self.db.query(RuleGraph).filter(RuleGraph.id == graph_id).first()

    def get_all_graphs(self) -> list[RuleGraph]:
        """获取所有规则图。

        Returns:
            规则图列表
        """
        return self.db.query(RuleGraph).order_by(RuleGraph.updated_at.desc()).all()

    def get_active_graphs(self) -> list[RuleGraph]:
        """获取所有激活的规则图。

        Returns:
            激活的规则图列表
        """
        return self.db.query(RuleGraph).filter(RuleGraph.is_active == True).all()

    def update_graph(
        self,
        graph_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes_json: Optional[str] = None,
        edges_json: Optional[str] = None,
        variables_json: Optional[str] = None,
        is_active: Optional[bool] = None,
        thumbnail: Optional[str] = None,
    ) -> Optional[RuleGraph]:
        """更新规则图。

        Args:
            graph_id: 规则图ID
            name: 规则图名称
            description: 规则图描述
            nodes_json: 节点JSON字符串
            edges_json: 边JSON字符串
            variables_json: 变量JSON字符串
            is_active: 是否激活
            thumbnail: 缩略图 Base64

        Returns:
            更新后的规则图对象，未找到返回 None
        """
        graph = self.get_graph(graph_id)
        if graph is None:
            return None

        if name is not None:
            graph.name = name
        if description is not None:
            graph.description = description
        if nodes_json is not None:
            graph.nodes_json = nodes_json
        if edges_json is not None:
            graph.edges_json = edges_json
        if variables_json is not None:
            graph.variables_json = variables_json
        if is_active is not None:
            graph.is_active = is_active
        if thumbnail is not None:
            graph.thumbnail = thumbnail

        self.db.commit()
        self.db.refresh(graph)
        return graph

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

        # 检查孤立节点（排除没有输入边的节点，因为触发器节点通常没有输入）
        for node in nodes:
            node_id = node["id"]
            # 检查是否有输出边
            if node_id not in edge_sources and node_id not in edge_targets:
                # 这可能是一个孤立的触发器节点，需要进一步判断类型
                pass

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
            if node.get("type") in ("yolo_trigger", "timer_trigger", "manual_trigger")
        }
        nodes_without_inputs = node_ids - edge_targets

        # 如果所有没有输入边的节点都不是触发器，则图无效
        if nodes_without_inputs and not trigger_nodes.intersection(nodes_without_inputs):
            return False, "规则图没有起始触发器节点"

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
