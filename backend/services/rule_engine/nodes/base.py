# -*- coding: utf-8 -*-
"""节点执行器基类 - 所有节点类型的父类。

按 Phase 1 设计文档实现 BaseExecutor 模式：
docs/research/rule-engine-phase1-node-registry.md

所有节点执行器必须继承 BaseExecutor，并实现：
1. get_definition() - 返回节点定义
2. validate_inputs() - 校验输入参数
3. execute() - 执行节点逻辑（必须是 async）

P0-A (2026-09-11): 新增 ConfigSchema 与 validate_config() 提供强类型配置校验。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, ValidationError

from backend.services.rule_engine.models import (
    NodeDefinition,
    NodeCategory,
    PortDefinition,
    ConfigSchemaProperty,
    ExecutionContextData,
)


@dataclass
class NodeStatus:
    """节点执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class NodeResult:
    """节点执行结果。"""
    status: str
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


class BaseExecutor(ABC):
    """节点执行器基类。

    所有节点执行器必须继承此类，并实现：
    1. get_definition() - 返回节点定义
    2. validate_inputs() - 校验输入参数
    3. execute() - 执行节点逻辑

    使用示例：
        class MyNodeExecutor(BaseExecutor):
            def get_definition(self) -> NodeDefinition:
                return NodeDefinition(...)

            def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
                if "data" not in inputs:
                    return False, "缺少必需参数 'data'"
                return True, None

            async def execute(self, inputs, context) -> Dict[str, Any]:
                return {"result": process(inputs["data"])}
    """

    # 节点类型标识（子类必须定义）
    node_type: str = ""
    category: NodeCategory = NodeCategory.ACTION
    display_name: str = ""
    description: str = ""
    icon: str = "circle"
    color: str = "#7D7D7D"

    # 节点级默认超时（秒），None 表示使用执行上下文的全局超时（默认 300s）。
    # 子类可覆盖此值以调整特定节点的超时阈值。
    # 例如：yolo_model 节点加载大型模型可能需要更长时间，可设为 600。
    default_timeout: Optional[float] = None

    # P0-A (2026-09-11): 节点配置 schema 类（Pydantic BaseModel 子类）。
    # 子类可覆盖此值声明本节点配置的强类型 schema。
    # - None（默认）：节点无需配置, validate_config 直接放行
    # - Type[BaseModel]：必须继承 NodeConfigSchema (extra='forbid')
    ConfigSchema: Optional[Type[BaseModel]] = None

    def __init__(self, node_id: str = None, config: dict = None):
        """初始化节点执行器。

        Args:
            node_id: 节点实例ID
            config: 节点配置
        """
        self.node_id = node_id
        self.config = config or {}

    @abstractmethod
    def get_definition(self) -> NodeDefinition:
        """返回节点的完整定义。

        Returns:
            NodeDefinition 对象，包含节点的所有元信息
        """
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """校验输入参数是否满足要求。

        在节点执行前调用，用于验证输入数据的合法性。
        不合法的输入应返回 (False, error_message)，而非抛异常。

        Args:
            inputs: 节点输入数据字典

        Returns:
            (is_valid, error_message) 元组
            - is_valid: 输入是否合法
            - error_message: 错误描述（如果非法）
        """
        pass

    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行节点逻辑。

        这是节点的核心执行方法，由执行引擎在拓扑排序后调用。

        Args:
            inputs: 节点输入数据（已解析变量引用）
            context: 执行上下文（包含变量、执行结果缓存等）

        Returns:
            节点输出数据字典，key 为输出端口名称

        Raises:
            ExecutorError: 执行失败时抛出（包含节点 ID 和类型信息）
        """
        pass

    def get_required_inputs(self) -> List[str]:
        """返回必需输入端口名称列表。"""
        definition = self.get_definition()
        return [
            name for name, port in definition.inputs.items()
            if port.required
        ]

    def get_optional_defaults(self) -> Dict[str, Any]:
        """返回有默认值的可选输入端口及其默认值。"""
        definition = self.get_definition()
        return {
            name: port.default
            for name, port in definition.inputs.items()
            if not port.required and port.default is not None
        }

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        """返回节点的可配置参数 schema。

        子类可以覆盖此方法定义自己的配置项。
        返回空字典表示该节点无需配置。
        """
        return {}

    def validate_config(
        self, config: Optional[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """P0-A (2026-09-11): 强类型校验节点配置。

        与 validate_inputs 不同：
        - validate_inputs: 校验运行时输入数据（上游边传来的值）
        - validate_config: 校验用户保存的静态配置（节点面板设置）

        调用时机：
        1. graph_manager.update_graph / create_graph (保存期 soft warn)
        2. executor._execute_node (执行期 hard fail)

        Returns:
            (is_valid, error_message, sanitized_config)
            - is_valid: 配置是否合法
            - error_message: 错误描述（如果非法）
            - sanitized_config: 校验后的配置（已填默认值、丢弃未知字段）

        注意：当 ConfigSchema=None 时直接放行, 不做校验 (向后兼容无配置节点)。
        """
        raw = dict(config or {})
        if self.ConfigSchema is None:
            return True, None, raw
        try:
            validated = self.ConfigSchema.model_validate(raw)
        except ValidationError as e:
            # 友好格式化: loc.msg 形式
            errors: List[str] = []
            for err in e.errors():
                loc = ".".join(str(p) for p in err.get("loc", [])) or "<root>"
                msg = err.get("msg", "unknown error")
                errors.append(f"{loc}: {msg}")
            return False, "; ".join(errors), raw
        return True, None, validated.model_dump()

    def merge_with_defaults(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """将可选输入与默认值合并。"""
        result = dict(inputs)
        for name, default in self.get_optional_defaults().items():
            if name not in result or result[name] is None:
                result[name] = default
        return result

    @classmethod
    def get_category(cls) -> NodeCategory:
        """获取节点类别。"""
        return cls.category

    @classmethod
    def get_node_type(cls) -> str:
        """获取节点类型标识。"""
        return cls.node_type
