# -*- coding: utf-8 -*-
"""触发器节点 - 规则执行的入口节点。

按 Phase 1 设计文档实现 BaseExecutor 模式。
"""
import time
from typing import Any, Dict, Optional, Tuple

from backend.services.rule_engine.models import (
    NodeDefinition, NodeCategory, PortDefinition, PortType, ConfigSchemaProperty
)
from typing import Dict
from .base import BaseExecutor


class ManualTriggerNode(BaseExecutor):
    """手动触发器 - 手动触发规则执行。

    用于测试或手动控制场景。
    """

    node_type = "manual_trigger"
    category = NodeCategory.INPUT
    display_name = "手动触发"
    description = "手动触发规则执行"
    icon = "play"
    color = "#4CFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={},
            outputs={
                "triggered": PortDefinition(
                    name="触发",
                    type="BOOLEAN",
                    description="是否触发"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {}  # 手动触发器无需配置

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        return {
            "triggered": True,
            "timestamp": time.time(),
        }


class TimerTriggerNode(BaseExecutor):
    """定时器触发器 - 按固定间隔触发规则。

    配置项:
        interval: float - 触发间隔(秒)
        enabled: bool - 是否启用
    """

    node_type = "timer_trigger"
    category = NodeCategory.INPUT
    display_name = "定时器触发"
    description = "按固定时间间隔触发规则执行"
    icon = "timer"
    color = "#4CFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={},
            outputs={
                "triggered": PortDefinition(
                    name="触发",
                    type="BOOLEAN",
                    description="是否触发"
                ),
                "timestamp": PortDefinition(
                    name="时间戳",
                    type="FLOAT",
                    description="触发时间戳"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "interval": ConfigSchemaProperty(
                type="number",
                title="触发间隔",
                description="触发间隔时间（秒）",
                default=5.0,
                minimum=0.1,
                maximum=3600,
                step=0.5,
                widget="slider",
            ),
            "enabled": ConfigSchemaProperty(
                type="boolean",
                title="启用状态",
                description="是否启用定时器",
                default=True,
                widget="dropdown",
                enum=["true", "false"],
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        interval = params.get("interval", 5.0)
        enabled = params.get("enabled", True)

        # TODO: 实现时间间隔控制（需要记录上次触发时间）
        # 当前为占位实现
        triggered = enabled

        return {
            "triggered": triggered,
            "timestamp": time.time(),
            "interval": interval,
        }


class CronTriggerNode(BaseExecutor):
    """Cron 触发器 - 按 Cron 表达式触发规则。

    配置项:
        cron: str - Cron 表达式
        timezone: str - 时区
    """

    node_type = "cron_trigger"
    category = NodeCategory.INPUT
    display_name = "Cron 触发"
    description = "按 Cron 表达式触发规则执行"
    icon = "clock"
    color = "#4CFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={},
            outputs={
                "triggered": PortDefinition(
                    name="触发",
                    type="BOOLEAN",
                    description="是否触发"
                ),
                "timestamp": PortDefinition(
                    name="时间戳",
                    type="FLOAT",
                    description="触发时间戳"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "cron": ConfigSchemaProperty(
                type="string",
                title="Cron 表达式",
                description="标准 Cron 格式，如 0 * * * *",
                default="0 * * * *",
                widget="text",
            ),
            "timezone": ConfigSchemaProperty(
                type="string",
                title="时区",
                description="时区名称，如 Asia/Shanghai",
                default="Asia/Shanghai",
                widget="dropdown",
                enum=["Asia/Shanghai", "UTC", "America/New_York", "Europe/London", "Japan"],
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        cron_expr = params.get("cron", "0 * * * *")
        timezone = params.get("timezone", "Asia/Shanghai")

        # Cron 触发器的实际调度由 RuleScheduler 管理
        # 此节点仅在触发时返回结果
        return {
            "triggered": True,
            "timestamp": time.time(),
            "cron": cron_expr,
        }


class WebhookTriggerNode(BaseExecutor):
    """Webhook 触发器 - 接收 HTTP 请求触发规则。

    配置项:
        path: str - Webhook 路径
        method: str - HTTP 方法 (GET/POST)
        auth_token: str - 认证令牌（可选）

    注意: Webhook 触发器的实际 HTTP 端点由调度器/路由器创建。
    此节点在接收请求时返回结果。
    """

    node_type = "webhook_trigger"
    category = NodeCategory.INPUT
    display_name = "Webhook 触发"
    description = "接收 HTTP 请求触发规则执行"
    icon = "webhook"
    color = "#4CFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={},
            outputs={
                "triggered": PortDefinition(
                    name="触发",
                    type="BOOLEAN",
                    description="是否触发"
                ),
                "request_data": PortDefinition(
                    name="请求数据",
                    type="ANY",
                    description="HTTP 请求数据"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "path": ConfigSchemaProperty(
                type="string",
                title="Webhook 路径",
                description="Webhook 端点路径，如 /webhook/myrule",
                default="/webhook/trigger",
                widget="text",
            ),
            "method": ConfigSchemaProperty(
                type="string",
                title="HTTP 方法",
                description="支持的 HTTP 方法",
                default="POST",
                widget="dropdown",
                enum=["GET", "POST", "PUT", "DELETE"],
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        path = params.get("path", "")
        method = params.get("method", "POST")

        # 从上下文获取触发数据
        request_data = context.trigger_data or {}

        return {
            "triggered": True,
            "path": path,
            "method": method,
            "request_data": request_data,
            "timestamp": time.time(),
        }


class ApiTriggerNode(BaseExecutor):
    """API 触发器 - 通过内部 API 调用触发规则。

    配置项:
        api_name: str - API 名称
        api_params: dict - API 参数

    用于规则之间的内部调用或消息队列触发。
    """

    node_type = "api_trigger"
    category = NodeCategory.INPUT
    display_name = "API 触发"
    description = "通过 API 调用触发规则执行"
    icon = "api"
    color = "#4CFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={},
            outputs={
                "triggered": PortDefinition(
                    name="触发",
                    type="BOOLEAN",
                    description="是否触发"
                ),
                "api_response": PortDefinition(
                    name="API响应",
                    type="ANY",
                    description="API 响应数据"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "api_name": ConfigSchemaProperty(
                type="string",
                title="API 名称",
                description="调用的 API 名称",
                default="",
                widget="text",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        api_name = params.get("api_name", "")
        api_params = params.get("api_params", {})

        # 从上下文获取触发数据
        trigger_data = context.trigger_data or {}

        return {
            "triggered": True,
            "api_name": api_name,
            "api_params": api_params,
            "trigger_data": trigger_data,
            "timestamp": time.time(),
        }
