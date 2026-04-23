# -*- coding: utf-8 -*-
"""节点基类 - 所有节点类型的父类。

定义了节点的通用接口和执行框架。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class NodeCategory(Enum):
    """节点分类枚举。"""
    TRIGGER = "trigger"  # 触发器 - 规则执行入口
    CONDITION = "condition"  # 条件 - 判断逻辑
    ACTION = "action"  # 动作 - 执行操作
    LOGIC = "logic"  # 逻辑 - 控制流
    TOOL = "tool"  # 工具 - 辅助功能


class NodeStatus(Enum):
    """节点执行状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeResult:
    """节点执行结果。"""
    status: NodeStatus
    output_data: dict = field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """执行上下文 - 贯穿整个图执行过程。"""
    variables: dict = field(default_factory=dict)  # 全局变量
    execution_id: Optional[int] = None  # 当前执行记录ID
    trigger_data: dict = field(default_factory=dict)  # 触发数据
    logs: list = field(default_factory=list)  # 执行日志

    def set_var(self, key: str, value: Any) -> None:
        """设置变量。"""
        self.variables[key] = value

    def get_var(self, key: str, default: Any = None) -> Any:
        """获取变量。"""
        return self.variables.get(key, default)


class BaseNode(ABC):
    """节点基类 - 所有节点必须继承此类。

    属性:
        node_type: 节点类型唯一标识
        category: 节点分类
        label: 显示名称
        description: 节点描述
        inputs: 输入端口定义 [{name, type, label}]
        outputs: 输出端口定义 [{name, type, label}]
        config_schema: 节点配置项
    """

    node_type: str = ""
    category: NodeCategory = NodeCategory.ACTION
    label: str = ""
    description: str = ""
    icon: str = ""

    inputs: list = []
    outputs: list = []

    def __init__(self, node_id: str, config: dict = None):
        """初始化节点。

        Args:
            node_id: 节点唯一ID
            config: 节点配置参数
        """
        self.node_id = node_id
        self.config = config or {}

    async def execute(self, context: ExecutionContext, input_data: dict = None) -> NodeResult:
        """执行节点。

        子类必须实现此方法。

        Args:
            context: 执行上下文
            input_data: 上游节点传递的输入数据

        Returns:
            NodeResult: 执行结果
        """
        try:
            result = await self._execute(context, input_data or {})
            return result
        except Exception as e:
            return NodeResult(
                status=NodeStatus.FAILED,
                error_message=str(e)
            )

    @abstractmethod
    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """实际执行逻辑 - 子类实现。

        Args:
            context: 执行上下文
            input_data: 输入数据

        Returns:
            NodeResult: 执行结果
        """
        pass

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """验证节点配置。

        Returns:
            (是否有效, 错误信息)
        """
        return True, None

    @classmethod
    def get_definition(cls) -> dict:
        """获取节点定义 - 用于前端渲染节点面板。

        Returns:
            节点定义字典
        """
        return {
            "type": cls.node_type,
            "category": cls.category.value,
            "label": cls.label,
            "description": cls.description,
            "icon": cls.icon,
            "inputs": cls.inputs,
            "outputs": cls.outputs,
            "config_schema": getattr(cls, "config_schema", {}),
        }
