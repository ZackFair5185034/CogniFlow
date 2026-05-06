# -*- coding: utf-8 -*-
"""触发器节点 - 规则执行的入口节点。

按 Phase 1 设计文档实现 BaseExecutor 模式。
"""
import time
from typing import Any, Dict, Optional, Tuple

from backend.services.rule_engine.models import (
    NodeDefinition, NodeCategory, PortDefinition, PortType
)
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
            }
        )

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
            }
        )

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
            }
        )

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
