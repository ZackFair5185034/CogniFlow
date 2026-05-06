# -*- coding: utf-8 -*-
"""逻辑类节点 - 流程控制节点。

按 Phase 1 设计文档实现 BaseExecutor 模式。

节点分类: logic (#DC4FDC)
"""
import asyncio
from typing import Any, Dict, Optional, Tuple

from backend.services.rule_engine.models import (
    NodeDefinition, NodeCategory, PortDefinition, PortType
)
from .base import BaseExecutor


class BranchNode(BaseExecutor):
    """分支节点 - 根据条件选择执行分支。

    根据输入条件选择执行哪个输出分支。
    """

    node_type = "branch"
    category = NodeCategory.LOGIC
    display_name = "分支"
    description = "根据条件选择执行分支"
    icon = "split"
    color = "#DC4FDC"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "condition": PortDefinition(
                    name="条件",
                    type="BOOLEAN",
                    required=True,
                    description="分支条件"
                ),
            },
            outputs={
                "true": PortDefinition(
                    name="条件成立",
                    type=PortType.CONTROL.value,
                    description="条件成立时的输出"
                ),
                "false": PortDefinition(
                    name="条件不成立",
                    type=PortType.CONTROL.value,
                    description="条件不成立时的输出"
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
        condition = inputs.get("condition", False)

        return {
            "branch": "true" if condition else "false",
            "condition_result": condition,
        }


class ParallelBranchNode(BaseExecutor):
    """并行分支节点 - 同时执行多个分支。

    配置项:
        max_concurrent: int - 最大并发数
    """

    node_type = "parallel_branch"
    category = NodeCategory.LOGIC
    display_name = "并行分支"
    description = "同时执行多个分支"
    icon = "merge"
    color = "#DC4FDC"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "branch_1": PortDefinition(
                    name="分支1",
                    type=PortType.CONTROL.value,
                    description="分支1输出"
                ),
                "branch_2": PortDefinition(
                    name="分支2",
                    type=PortType.CONTROL.value,
                    description="分支2输出"
                ),
                "branch_3": PortDefinition(
                    name="分支3",
                    type=PortType.CONTROL.value,
                    description="分支3输出"
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
        max_concurrent = params.get("max_concurrent", 3)

        return {
            "branches_triggered": ["branch_1", "branch_2", "branch_3"],
            "max_concurrent": max_concurrent,
        }


class DelayNode(BaseExecutor):
    """延迟节点 - 延迟后继续执行。

    配置项:
        delay: float - 延迟时间(秒)
    """

    node_type = "delay"
    category = NodeCategory.LOGIC
    display_name = "延迟"
    description = "延迟后继续执行"
    icon = "clock"
    color = "#DC4FDC"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "input": PortDefinition(
                    name="输入",
                    type=PortType.CONTROL.value,
                    description="输入信号"
                ),
            },
            outputs={
                "output": PortDefinition(
                    name="输出",
                    type=PortType.CONTROL.value,
                    description="延迟后的输出"
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
        delay = params.get("delay", 1.0)

        await asyncio.sleep(delay)

        return {
            "delayed_seconds": delay,
        }


class SetVariableNode(BaseExecutor):
    """设置变量节点 - 设置执行上下文中的变量。

    配置项:
        variable_name: str - 变量名
        value: any - 变量值
        value_type: str - 值类型 (static/dynamic)
    """

    node_type = "set_variable"
    category = NodeCategory.LOGIC
    display_name = "设置变量"
    description = "设置执行上下文中的变量"
    icon = "variable"
    color = "#DC4FDC"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    required=False,
                    description="触发信号"
                ),
            },
            outputs={
                "next": PortDefinition(
                    name="完成",
                    type=PortType.CONTROL.value,
                    description="完成信号"
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
        var_name = params.get("variable_name", "")
        value = params.get("value", "")
        value_type = params.get("value_type", "static")

        if not var_name:
            return {"error": "变量名不能为空"}

        # 如果是动态值，尝试从上下文获取
        if value_type == "dynamic":
            actual_value = context.variables.get(value, value)
        else:
            actual_value = self._parse_value(value)

        # 设置变量到上下文
        context.variables[var_name] = actual_value

        return {
            "variable_name": var_name,
            "value": actual_value,
        }

    def _parse_value(self, value: str):
        """解析值类型。"""
        # 尝试解析为数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 解析为布尔值
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # 返回字符串
        return value


class CounterNode(BaseExecutor):
    """计数器节点 - 计数执行次数。

    配置项:
        variable_name: str - 计数器变量名
        increment: int - 每次增量
        reset_on_trigger: bool - 触发时重置
    """

    node_type = "counter"
    category = NodeCategory.LOGIC
    display_name = "计数器"
    description = "计数执行次数"
    icon = "counter"
    color = "#DC4FDC"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="计数触发"
                ),
            },
            outputs={
                "count": PortDefinition(
                    name="计数",
                    type="INT",
                    description="当前计数值"
                ),
                "overflow": PortDefinition(
                    name="溢出",
                    type="BOOLEAN",
                    description="是否达到上限"
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
        var_name = params.get("variable_name", "_counter")
        increment = params.get("increment", 1)
        reset_on_trigger = params.get("reset_on_trigger", False)
        max_value = params.get("max_value", 999999)

        current = context.variables.get(var_name, 0)

        if reset_on_trigger:
            current = increment
        else:
            current += increment

        overflow = current >= max_value
        if overflow:
            current = 0

        context.variables[var_name] = current

        return {
            "count": current,
            "overflow": overflow,
        }
