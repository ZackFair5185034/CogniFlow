# -*- coding: utf-8 -*-
"""节点基类 - 所有节点类型的父类。
定义节点的通用接口和执行框架。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class NodeCategory(Enum):
    """节点分类枚举。"""
    TRIGGER = "trigger"
    CONDITION = "condition"
    ACTION = "action"
    LOGIC = "logic"
    TOOL = "tool"


class NodeStatus(Enum):
    """节点执行状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class NodeResult:
    """节点执行结果。"""
    status: NodeStatus
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


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


class BaseNode(ABC):
    """节点基类 - 所有节点必须继承此类。

    属性:
        node_type: 节点类型唯一标识
        category: 节点分类
        display_name: 显示名称
        description: 节点描述
    """

    node_type: str = ""
    category: NodeCategory = NodeCategory.ACTION
    display_name: str = ""
    description: str = ""

    def __init__(self, node_id: str, config: dict = None):
        """初始化节点。

        Args:
            node_id: 节点实例ID
            config: 节点配置
        """
        self.node_id = node_id
        self.config = config or {}

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """执行节点。

        Args:
            inputs: 输入数据
            context: 执行上下文

        Returns:
            输出数据字典
        """
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, str]:
        """验证输入数据。

        Args:
            inputs: 输入数据

        Returns:
            (是否有效, 错误信息)
        """
        return True, ""

    def get_outputs(self) -> Dict[str, Any]:
        """获取节点输出定义。"""
        return {}
