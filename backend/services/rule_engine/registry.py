# -*- coding: utf-8 -*-
"""节点注册表 - 管理所有可用节点类型。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

NodeRegistry 负责：
1. 管理所有可用节点类型的定义（供前端渲染节点面板）
2. 管理节点执行器实例（供执行引擎调用）
3. 提供按类别查询节点的能力
"""
from typing import Dict, List, Optional, Type

from backend.services.rule_engine.models import (
    NodeDefinition, CategoryInfo, CATEGORIES, CATEGORY_COLORS
)
from .nodes.base import BaseExecutor


class NodeRegistry:
    """节点注册表 - 统一管理所有节点定义和执行器。

    使用单例模式确保全局只有一个注册表实例。
    """

    _instance: Optional["NodeRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._executors: Dict[str, Type[BaseExecutor]] = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._executors: Dict[str, Type[BaseExecutor]] = {}
            self._initialized = True

    def register(self, executor_class: Type[BaseExecutor]) -> None:
        """注册节点执行器类。

        Args:
            executor_class: 节点执行器类（必须继承 BaseExecutor）
        """
        if not issubclass(executor_class, BaseExecutor):
            raise ValueError(f"{executor_class} must inherit from BaseExecutor")

        node_type = executor_class.node_type
        if not node_type:
            raise ValueError(f"Node class {executor_class.__name__} must define node_type")

        self._executors[node_type] = executor_class

    def get(self, node_type: str) -> Optional[Type[BaseExecutor]]:
        """获取节点执行器类。

        Args:
            node_type: 节点类型标识

        Returns:
            节点执行器类，未找到返回 None
        """
        return self._executors.get(node_type)

    def create_node(self, node_type: str, node_id: str = None, config: dict = None) -> Optional[BaseExecutor]:
        """创建节点实例。

        Args:
            node_type: 节点类型标识
            node_id: 节点实例ID
            config: 节点配置

        Returns:
            节点实例，未找到返回 None
        """
        executor_class = self.get(node_type)
        if executor_class is None:
            return None
        return executor_class(node_id=node_id, config=config)

    def list_types(self) -> List[str]:
        """列出所有注册的节点类型。

        Returns:
            节点类型标识列表
        """
        return list(self._executors.keys())

    def get_definitions(self) -> List[dict]:
        """获取所有节点定义 - 用于前端渲染节点面板。

        Returns:
            节点定义列表（字典格式），转换为前端兼容格式：
            - display_name -> label
            - inputs/outputs: Dict -> List[{name, type, label, description}]
        """
        definitions = []
        for executor_class in self._executors.values():
            executor = executor_class()
            defn = executor.get_definition()
            # 转换为前端兼容格式
            definition_dict = {
                "type": defn.type,
                "category": defn.category,
                "label": defn.display_name,
                "description": defn.description,
                "icon": defn.icon,
                "color": defn.color,
                "inputs": [
                    {
                        "name": name,
                        "type": port.type,
                        "label": port.name,
                        "description": port.description,
                    }
                    for name, port in defn.inputs.items()
                ],
                "outputs": [
                    {
                        "name": name,
                        "type": port.type,
                        "label": port.name,
                        "description": port.description,
                    }
                    for name, port in defn.outputs.items()
                ],
                "config_schema": {
                    key: {
                        "type": prop.type,
                        "title": prop.title,
                        "description": prop.description,
                        "default": prop.default,
                        "minimum": prop.minimum,
                        "maximum": prop.maximum,
                        "step": prop.step,
                        "enum": prop.enum,
                        "widget": prop.widget,
                        "required": prop.required,
                    }
                    for key, prop in defn.config_schema.items()
                } if defn.config_schema else {},
            }
            definitions.append(definition_dict)
        return definitions

    def _convert_to_frontend_format(self, defn: "NodeDefinition") -> dict:
        """将 NodeDefinition 转换为前端兼容格式。"""
        return {
            "type": defn.type,
            "category": defn.category,
            "label": defn.display_name,
            "description": defn.description,
            "icon": defn.icon,
            "color": defn.color,
            "inputs": [
                {
                    "name": name,
                    "type": port.type,
                    "label": port.name,
                    "description": port.description,
                }
                for name, port in defn.inputs.items()
            ],
            "outputs": [
                {
                    "name": name,
                    "type": port.type,
                    "label": port.name,
                    "description": port.description,
                }
                for name, port in defn.outputs.items()
            ],
            "config_schema": getattr(defn, 'config_schema', {}),
        }

    def get_definitions_by_category(self) -> Dict[str, List[dict]]:
        """按分类获取所有节点定义。

        Returns:
            分类到节点定义列表的映射
        """
        result: Dict[str, List[dict]] = {cat.name: [] for cat in CATEGORIES}

        for executor_class in self._executors.values():
            executor = executor_class()
            definition = executor.get_definition()
            category = definition.category
            if category in result:
                result[category].append(self._convert_to_frontend_format(definition))

        return result

    def get_by_category(self, category: str) -> List[dict]:
        """按分类获取节点定义。

        Args:
            category: 节点分类

        Returns:
            该分类下的节点定义列表
        """
        result = []
        for executor_class in self._executors.values():
            definition = executor_class().get_definition()
            if definition.category == category:
                result.append(self._convert_to_frontend_format(definition))
        return result

    def get_categories(self) -> List[CategoryInfo]:
        """获取所有类别定义。"""
        return CATEGORIES


def get_registry() -> NodeRegistry:
    """获取全局节点注册表实例。

    Returns:
        NodeRegistry 单例实例
    """
    return NodeRegistry()


def init_builtin_executors() -> NodeRegistry:
    """初始化内置节点注册表。

    按 Phase 1 设计文档注册所有 6 类节点：
    - input: ImageCapture, VideoCapture, ScreenCapture
    - detection: YOLOModel, YOLOTrigger, ObjectDetector
    - processing: CategoryEncode, Filter, Tracker, ImagePreprocessor
    - action: KeyboardAction, MouseAction, WaitAction, HttpRequestAction, LogAction
    - logic: Branch, ParallelBranch, Delay, SetVariable, Counter
    - output: SaveResult, Notification, Display

    Returns:
        已注册内置节点的注册表实例
    """
    registry = NodeRegistry()

    # 避免重复注册
    if registry.list_types():
        return registry

    # ===== 输入类节点 =====
    from .nodes.input_nodes import (
        ImageCaptureNode,
        VideoCaptureNode,
        ScreenCaptureNode,
    )
    registry.register(ImageCaptureNode)
    registry.register(VideoCaptureNode)
    registry.register(ScreenCaptureNode)

    # 触发器节点（归类为 input）
    from .nodes.triggers import (
        ManualTriggerNode,
        TimerTriggerNode,
        CronTriggerNode,
        WebhookTriggerNode,
        ApiTriggerNode,
    )
    registry.register(ManualTriggerNode)
    registry.register(TimerTriggerNode)
    registry.register(CronTriggerNode)
    registry.register(WebhookTriggerNode)
    registry.register(ApiTriggerNode)

    # ===== 检测类节点 =====
    from .nodes.detection_nodes import (
        YOLOModelNode,
        YOLOTriggerNode,
        ObjectDetectorNode,
    )
    registry.register(YOLOModelNode)
    registry.register(YOLOTriggerNode)
    registry.register(ObjectDetectorNode)

    # ===== 处理类节点 =====
    from .nodes.processing_nodes import (
        CategoryEncodeNode,
        FilterNode,
        TrackerNode,
        ImagePreprocessorNode,
        TemplateNode,
    )
    registry.register(CategoryEncodeNode)
    registry.register(FilterNode)
    registry.register(TrackerNode)
    registry.register(ImagePreprocessorNode)
    registry.register(TemplateNode)

    # ===== 动作类节点 =====
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

    # ===== 逻辑类节点 =====
    from .nodes.logic import (
        BranchNode,
        ParallelBranchNode,
        DelayNode,
        SetVariableNode,
        CounterNode,
    )
    registry.register(BranchNode)
    registry.register(ParallelBranchNode)
    registry.register(DelayNode)
    registry.register(SetVariableNode)
    registry.register(CounterNode)

    # ===== 条件类节点 =====
    from .nodes.conditions import (
        ObjectExistsConditionNode,
        ConfidenceThresholdConditionNode,
        VariableConditionNode,
    )
    registry.register(ObjectExistsConditionNode)
    registry.register(ConfidenceThresholdConditionNode)
    registry.register(VariableConditionNode)

    # ===== 输出类节点 =====
    from .nodes.output_nodes import (
        SaveResultNode,
        NotificationNode,
        DisplayNode,
    )
    registry.register(SaveResultNode)
    registry.register(NotificationNode)
    registry.register(DisplayNode)

    return registry
