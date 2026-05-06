# -*- coding: utf-8 -*-
"""节点注册表 - 管理所有可用节点类型。"""
from typing import Dict, List, Type, Optional
from .nodes.base import BaseNode


class NodeRegistry:
    """节点注册表 - 管理和实例化所有节点类型。

    使用单例模式确保全局只有一个注册表实例。
    """

    _instance: Optional["NodeRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._nodes: Dict[str, Type[BaseNode]] = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._nodes: Dict[str, Type[BaseNode]] = {}
            self._initialized = True

    def register(self, node_class: Type[BaseNode]) -> None:
        """注册节点类型。

        Args:
            node_class: 节点类
        """
        if not issubclass(node_class, BaseNode):
            raise ValueError(f"{node_class} must inherit from BaseNode")

        node_type = node_class.node_type
        if not node_type:
            raise ValueError(f"Node class {node_class.__name__} must define node_type")

        self._nodes[node_type] = node_class

    def get(self, node_type: str) -> Optional[Type[BaseNode]]:
        """获取节点类型。

        Args:
            node_type: 节点类型标识

        Returns:
            节点类，未找到返回 None
        """
        return self._nodes.get(node_type)

    def create_node(self, node_type: str, node_id: str, config: dict = None) -> Optional[BaseNode]:
        """创建节点实例。

        Args:
            node_type: 节点类型标识
            node_id: 节点实例ID
            config: 节点配置

        Returns:
            节点实例，未找到返回 None
        """
        node_class = self.get(node_type)
        if node_class is None:
            return None
        return node_class(node_id=node_id, config=config)

    def list_types(self) -> List[str]:
        """列出所有注册的节点类型。

        Returns:
            节点类型标识列表
        """
        return list(self._nodes.keys())

    def get_definitions(self) -> List[dict]:
        """获取所有节点定义 - 用于前端渲染节点面板。

        Returns:
            节点定义列表
        """
        definitions = []
        for node_class in self._nodes.values():
            definitions.append(node_class.get_definition())
        return definitions

    def get_by_category(self, category: str) -> List[dict]:
        """按分类获取节点定义。

        Args:
            category: 节点分类

        Returns:
            该分类下的节点定义列表
        """
        return [
            node_class.get_definition()
            for node_class in self._nodes.values()
            if node_class.category.value == category
        ]


def get_registry() -> NodeRegistry:
    """获取全局节点注册表实例。

    Returns:
        NodeRegistry 单例实例
    """
    return NodeRegistry()


def init_builtin_executors() -> NodeRegistry:
    """初始化内置节点注册表。

    Returns:
        已注册内置节点的注册表实例
    """
    registry = NodeRegistry()

    # 避免重复注册
    if registry.list_types():
        return registry

    # 注册触发器节点
    from .nodes.triggers import (
        YOLOTriggerNode,
        TimerTriggerNode,
        ManualTriggerNode,
    )
    registry.register(YOLOTriggerNode)
    registry.register(TimerTriggerNode)
    registry.register(ManualTriggerNode)

    # 注册条件节点
    from .nodes.conditions import (
        ObjectExistsConditionNode,
        ConfidenceThresholdConditionNode,
        VariableConditionNode,
    )
    registry.register(ObjectExistsConditionNode)
    registry.register(ConfidenceThresholdConditionNode)
    registry.register(VariableConditionNode)

    # 注册动作节点
    from .nodes.actions import (
        KeyboardActionNode,
        MouseActionNode,
        WaitActionNode,
        HttpRequestActionNode,
        LogActionNode,
    )
    registry.register(KeyboardActionNode)
    registry.register(MouseActionNode)
    registry.register(WaitActionNode)
    registry.register(HttpRequestActionNode)
    registry.register(LogActionNode)

    # 注册逻辑节点
    from .nodes.logic import (
        BranchNode,
        ParallelBranchNode,
        LoopNode,
        DelayNode,
        SetVariableNode,
    )
    registry.register(BranchNode)
    registry.register(ParallelBranchNode)
    registry.register(LoopNode)
    registry.register(DelayNode)
    registry.register(SetVariableNode)

    return registry
