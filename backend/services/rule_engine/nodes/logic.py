# -*- coding: utf-8 -*-
"""逻辑节点 - 控制流程的逻辑节点。"""
from typing import Optional
from .base import (
    BaseNode, NodeCategory, NodeResult, NodeStatus, ExecutionContext
)


class BranchNode(BaseNode):
    """分支节点 - 根据条件选择执行分支。

    根据输入条件选择执行哪个输出分支。
    """
    node_type = "branch"
    category = NodeCategory.LOGIC
    label = "分支"
    description = "根据条件选择执行分支"
    icon = "mdi:call-split"

    inputs = [
        {"name": "input", "type": "flow", "label": "输入"},
        {"name": "condition", "type": "boolean", "label": "条件"},
    ]
    outputs = [
        {"name": "true", "type": "flow", "label": "条件成立"},
        {"name": "false", "type": "flow", "label": "条件不成立"},
    ]

    config_schema = {
        "type": "object",
        "properties": {}
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行分支选择。"""
        condition = input_data.get("condition", context.get_var("_condition_result", False))

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "branch": "true" if condition else "false",
            }
        )


class ParallelBranchNode(BaseNode):
    """并行分支节点 - 同时执行多个分支。

    配置项:
        branches: list[str] - 分支名称列表
    """
    node_type = "parallel_branch"
    category = NodeCategory.LOGIC
    label = "并行分支"
    description = "同时执行多个分支"
    icon = "mdi:call-merge"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "branch_1", "type": "flow", "label": "分支1"},
        {"name": "branch_2", "type": "flow", "label": "分支2"},
        {"name": "branch_3", "type": "flow", "label": "分支3"},
        {"name": "completed", "type": "flow", "label": "全部完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "max_concurrent": {
                "type": "integer",
                "minimum": 1,
                "default": 3
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行并行分支（由执行器处理实际并行）。"""
        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "branches_triggered": ["branch_1", "branch_2", "branch_3"],
            }
        )


class LoopNode(BaseNode):
    """循环节点 - 循环执行节点。

    配置项:
        max_iterations: int - 最大迭代次数
        continue_on_error: bool - 出错时是否继续
    """
    node_type = "loop"
    category = NodeCategory.LOGIC
    label = "循环"
    description = "循环执行节点"
    icon = "mdi:repeat"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "iteration", "type": "flow", "label": "迭代"},
        {"name": "completed", "type": "flow", "label": "完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "max_iterations": {
                "type": "integer",
                "minimum": 1,
                "default": 10
            },
            "continue_on_error": {
                "type": "boolean",
                "default": False
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行循环（由执行器处理迭代）。"""
        max_iterations = self.config.get("max_iterations", 10)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "max_iterations": max_iterations,
                "current_iteration": 0,
            }
        )


class DelayNode(BaseNode):
    """延迟节点 - 延迟后继续执行。

    配置项:
        delay: float - 延迟时间(秒)
    """
    node_type = "delay"
    category = NodeCategory.LOGIC
    label = "延迟"
    description = "延迟后继续执行"
    icon = "mdi:timer-sand"

    inputs = [
        {"name": "input", "type": "flow", "label": "输入"},
    ]
    outputs = [
        {"name": "output", "type": "flow", "label": "输出"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "delay": {
                "type": "number",
                "minimum": 0,
                "default": 1.0
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行延迟。"""
        import asyncio
        delay = self.config.get("delay", 1.0)
        await asyncio.sleep(delay)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "delayed_seconds": delay,
            }
        )


class SetVariableNode(BaseNode):
    """设置变量节点 - 设置执行上下文中的变量。

    配置项:
        variable_name: str - 变量名
        value: any - 变量值
        value_type: str - 值类型 (static/dynamic)
    """
    node_type = "set_variable"
    category = NodeCategory.LOGIC
    label = "设置变量"
    description = "设置执行上下文中的变量"
    icon = "mdi:variable"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "next", "type": "flow", "label": "完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "variable_name": {
                "type": "string",
                "default": ""
            },
            "value": {
                "type": "string",
                "default": ""
            },
            "value_type": {
                "type": "string",
                "enum": ["static", "dynamic"],
                "default": "static"
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行变量设置。"""
        var_name = self.config.get("variable_name", "")
        value = self.config.get("value", "")
        value_type = self.config.get("value_type", "static")

        if not var_name:
            return NodeResult(
                status=NodeStatus.FAILED,
                error_message="Variable name is required"
            )

        # 如果是动态值，尝试从上下文获取
        if value_type == "dynamic":
            actual_value = context.get_var(value, value)
        else:
            # 尝试类型转换
            actual_value = self._parse_value(value)

        context.set_var(var_name, actual_value)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "variable_name": var_name,
                "value": actual_value,
            }
        )

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
