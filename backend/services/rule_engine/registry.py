# -*- coding: utf-8 -*-
"""节点注册表 - 管理所有可用节点类型。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

NodeRegistry 负责：
1. 管理所有可用节点类型的定义（供前端渲染节点面板）
2. 管理节点执行器实例（供执行引擎调用）
3. 提供按类别查询节点的能力
"""
import logging
import os
from typing import Dict, List, Optional, Type

from backend.services.rule_engine.models import (
    NodeDefinition, CategoryInfo, CATEGORIES, CATEGORY_COLORS
)
from .nodes.base import BaseExecutor

logger = logging.getLogger(__name__)

# 开发模式开关：ENV=production 时为 False, 其他情况均为 True
# 用于决定节点重复注册时是 raise (开发环境) 还是 warn (生产环境)
_DEV_MODE: bool = os.getenv("ENV", "development") != "production"


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

        Raises:
            ValueError: 开发环境下, 重复注册同名节点类型时抛出
        """
        if not issubclass(executor_class, BaseExecutor):
            raise ValueError(f"{executor_class} must inherit from BaseExecutor")

        node_type = executor_class.node_type
        if not node_type:
            raise ValueError(f"Node class {executor_class.__name__} must define node_type")

        # P0-C (2026-09-11): 重复注册检测。dev 抛 ValueError 强制发现漏注册;
        # prod 仅 warn, 允许覆盖（避免历史版本节点类型消失导致启动失败）
        if node_type in self._executors:
            existing = self._executors[node_type]
            existing_origin = f"{existing.__module__}.{existing.__name__}"
            new_origin = f"{executor_class.__module__}.{executor_class.__name__}"
            msg = (
                f"节点类型 '{node_type}' 已被 {existing_origin} 注册，"
                f"现被 {new_origin} 覆盖"
            )
            if _DEV_MODE:
                raise ValueError(msg)
            logger.warning(msg)

        self._executors[node_type] = executor_class

    def unregister(self, node_type: str) -> Optional[Type[BaseExecutor]]:
        """注销节点类型。仅供测试使用。

        Args:
            node_type: 节点类型标识

        Returns:
            被注销的节点类, 不存在则返回 None
        """
        return self._executors.pop(node_type, None)

    def log_registered_nodes(self) -> None:
        """启动期输出所有已注册节点清单, 便于排查漏注册 / 误覆盖。

        按类别分组, 标注节点类型总数。
        """
        by_category: Dict[str, List[str]] = {}
        for cls in self._executors.values():
            cat = cls.category.value if hasattr(cls, "category") else "unknown"
            by_category.setdefault(cat, []).append(cls.node_type)

        total = len(self._executors)
        logger.info("=== 已注册节点清单 (共 %d 个) ===", total)
        for cat in sorted(by_category):
            types = sorted(by_category[cat])
            logger.info("  [%s] (%d): %s", cat, len(types), ", ".join(types))

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
                        "required": port.required,  # P1-1 (2026-06-19): 前端必填未连提示需要此字段
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
                        "allow_create": prop.allow_create,
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
                    "required": port.required,  # P1-1 (2026-06-19): 与 get_definitions 保持一致
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
        已注册内置节点的注册表实例（即全局单例）
    """
    # 修复 2026-06-04 验收发现的 P1：在单例上注册而非新建临时实例，
    # 否则 executor 用 get_registry() 拿不到节点（会全部报"未知节点类型"）
    registry = get_registry()

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
        MergeDetectionsNode,
        RoiExtractNode,
    )
    registry.register(CategoryEncodeNode)
    registry.register(FilterNode)
    registry.register(TrackerNode)
    registry.register(ImagePreprocessorNode)
    registry.register(TemplateNode)
    registry.register(MergeDetectionsNode)
    registry.register(RoiExtractNode)

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

    # P0-C (2026-09-11): 启动清单输出, 便于排查漏注册 / 重复覆盖
    registry.log_registered_nodes()

    return registry
