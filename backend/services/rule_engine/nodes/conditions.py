# -*- coding: utf-8 -*-
"""条件节点 - 实现各种条件判断逻辑。"""
from typing import Optional
from .base import (
    BaseNode, NodeCategory, NodeResult, NodeStatus, ExecutionContext
)


class ObjectExistsConditionNode(BaseNode):
    """目标存在条件 - 检查是否检测到指定目标。

    配置项:
        class_names: list[str] - 要检查的类别名称
        min_count: int - 最小数量
        comparison: str - 比较方式 (gte/lte/eq/gt/lt)
    """
    node_type = "object_exists_condition"
    category = NodeCategory.CONDITION
    label = "目标存在"
    description = "检查是否检测到指定目标"
    icon = "mdi:checkbox-marked"

    inputs = [
        {"name": "detections", "type": "array", "label": "检测结果"},
    ]
    outputs = [
        {"name": "true", "type": "flow", "label": "条件成立"},
        {"name": "false", "type": "flow", "label": "条件不成立"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "class_names": {
                "type": "array",
                "items": {"type": "string"},
                "default": []
            },
            "min_count": {
                "type": "integer",
                "minimum": 1,
                "default": 1
            },
            "comparison": {
                "type": "string",
                "enum": ["gte", "lte", "eq", "gt", "lt"],
                "default": "gte"
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行条件检查。"""
        detections = input_data.get("detections", [])
        class_names = self.config.get("class_names", [])
        min_count = self.config.get("min_count", 1)
        comparison = self.config.get("comparison", "gte")

        # 过滤符合条件的检测
        matched = [
            d for d in detections
            if not class_names or d.get("class") in class_names
        ]

        count = len(matched)

        # 执行比较
        result = self._compare(count, comparison, min_count)

        context.set_var("_condition_result", result)
        context.set_var("_matched_count", count)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "result": result,
                "matched_count": count,
                "matched_detections": matched,
            }
        )

    def _compare(self, count: int, op: str, threshold: int) -> bool:
        """执行比较操作。"""
        ops = {
            "gte": count >= threshold,
            "lte": count <= threshold,
            "eq": count == threshold,
            "gt": count > threshold,
            "lt": count < threshold,
        }
        return ops.get(op, False)


class ConfidenceThresholdConditionNode(BaseNode):
    """置信度阈值条件 - 检查检测置信度是否满足要求。

    配置项:
        min_confidence: float - 最小置信度 (0-1)
    """
    node_type = "confidence_threshold_condition"
    category = NodeCategory.CONDITION
    label = "置信度阈值"
    description = "检查检测置信度是否满足要求"
    icon = "mdi:percent"

    inputs = [
        {"name": "detections", "type": "array", "label": "检测结果"},
    ]
    outputs = [
        {"name": "true", "type": "flow", "label": "条件成立"},
        {"name": "false", "type": "flow", "label": "条件不成立"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "min_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "default": 0.5
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行置信度检查。"""
        detections = input_data.get("detections", [])
        min_confidence = self.config.get("min_confidence", 0.5)

        # 检查是否有任何检测满足置信度要求
        valid_detections = [
            d for d in detections
            if d.get("confidence", 0) >= min_confidence
        ]

        result = len(valid_detections) > 0

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "result": result,
                "valid_count": len(valid_detections),
                "max_confidence": max([d.get("confidence", 0) for d in detections], default=0),
            }
        )


class VariableConditionNode(BaseNode):
    """变量条件 - 检查变量的值是否满足条件。

    配置项:
        variable_name: str - 变量名
        expected_value: any - 期望值
        comparison: str - 比较方式
    """
    node_type = "variable_condition"
    category = NodeCategory.CONDITION
    label = "变量条件"
    description = "检查变量的值是否满足条件"
    icon = "mdi:variable"

    inputs = []
    outputs = [
        {"name": "true", "type": "flow", "label": "条件成立"},
        {"name": "false", "type": "flow", "label": "条件不成立"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "variable_name": {
                "type": "string",
                "default": ""
            },
            "expected_value": {
                "type": "string",
                "default": ""
            },
            "comparison": {
                "type": "string",
                "enum": ["eq", "ne", "gt", "lt", "gte", "lte", "contains"],
                "default": "eq"
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行变量检查。"""
        var_name = self.config.get("variable_name", "")
        expected = self.config.get("expected_value", "")
        comparison = self.config.get("comparison", "eq")

        actual = context.get_var(var_name)

        # 类型转换
        try:
            expected_float = float(expected)
            actual_float = float(actual) if actual is not None else None
            result = self._compare_values(actual_float, comparison, expected_float)
        except (ValueError, TypeError):
            result = self._compare_values(str(actual), comparison, str(expected))

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "result": result,
                "variable_name": var_name,
                "actual_value": actual,
            }
        )

    def _compare_values(self, actual, op: str, expected) -> bool:
        """执行值比较。"""
        ops = {
            "eq": actual == expected,
            "ne": actual != expected,
            "gt": actual > expected,
            "lt": actual < expected,
            "gte": actual >= expected,
            "lte": actual <= expected,
            "contains": expected in str(actual) if actual else False,
        }
        return ops.get(op, False)
