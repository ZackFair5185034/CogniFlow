# -*- coding: utf-8 -*-
"""条件类节点 - 条件判断逻辑节点。

按 Phase 1 设计文档实现 BaseExecutor 模式。

节点分类: logic (#DC4FDC)
"""
from typing import Any, Dict, Optional, Tuple

from backend.services.rule_engine.models import (
    NodeDefinition, NodeCategory, PortDefinition, PortType, ConfigSchemaProperty
)
from typing import Dict
from .base import BaseExecutor


class ObjectExistsConditionNode(BaseExecutor):
    """目标存在条件 - 检查是否检测到指定目标。

    配置项:
        class_names: list[str] - 要检查的类别名称
        min_count: int - 最小数量
        comparison: str - 比较方式 (gte/lte/eq/gt/lt)
    """

    node_type = "object_exists_condition"
    category = NodeCategory.LOGIC
    display_name = "目标存在"
    description = "检查是否检测到指定目标"
    icon = "checkbox-marked"
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
                "detections": PortDefinition(
                    name="检测结果",
                    type="ARRAY",
                    required=True,
                    description="检测结果列表"
                ),
            },
            outputs={
                "result": PortDefinition(
                    name="结果",
                    type="BOOLEAN",
                    description="条件是否满足"
                ),
                "matched_count": PortDefinition(
                    name="匹配数量",
                    type="INT",
                    description="符合条件的数量"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "class_names": ConfigSchemaProperty(
                type="array",
                title="目标类别",
                description="要检查的类别名称列表（可输入上游 yolo 检测节点输出的实际类别）",
                default=[],
                widget="multiselect",
                enum=[],
                allow_create=True,
            ),
            "min_count": ConfigSchemaProperty(
                type="number",
                title="最小数量",
                description="满足条件的最小数量",
                default=1,
                minimum=0,
                maximum=1000,
                step=1,
                widget="number",
            ),
            "comparison": ConfigSchemaProperty(
                type="string",
                title="比较方式",
                description="数量比较方式",
                default="gte",
                widget="dropdown",
                enum=["gte", "lte", "eq", "gt", "lt"],
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
        class_names = params.get("class_names", [])
        min_count = params.get("min_count", 1)
        comparison = params.get("comparison", "gte")

        detections = inputs.get("detections", [])

        # 过滤符合条件的检测
        matched = [
            d for d in detections
            if not class_names or d.get("class_name") in class_names or d.get("class") in class_names
        ]

        count = len(matched)
        result = self._compare(count, comparison, min_count)

        return {
            "result": result,
            "matched_count": count,
            "matched_detections": matched,
        }

    def _compare(self, count: int, op: str, threshold: int) -> bool:
        ops = {
            "gte": count >= threshold,
            "lte": count <= threshold,
            "eq": count == threshold,
            "gt": count > threshold,
            "lt": count < threshold,
        }
        return ops.get(op, False)


class ConfidenceThresholdConditionNode(BaseExecutor):
    """置信度阈值条件 - 检查检测置信度是否满足要求。

    配置项:
        min_confidence: float - 最小置信度 (0-1)
    """

    node_type = "confidence_threshold_condition"
    category = NodeCategory.LOGIC
    display_name = "置信度阈值"
    description = "检查检测置信度是否满足要求"
    icon = "percent"
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
                "detections": PortDefinition(
                    name="检测结果",
                    type="ARRAY",
                    required=True,
                    description="检测结果列表"
                ),
            },
            outputs={
                "result": PortDefinition(
                    name="结果",
                    type="BOOLEAN",
                    description="条件是否满足"
                ),
                "max_confidence": PortDefinition(
                    name="最大置信度",
                    type="FLOAT",
                    description="最高置信度值"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "min_confidence": ConfigSchemaProperty(
                type="number",
                title="最小置信度",
                description="要求的最小置信度阈值",
                default=0.5,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
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
        min_confidence = params.get("min_confidence", 0.5)

        detections = inputs.get("detections", [])

        valid_detections = [
            d for d in detections
            if d.get("confidence", 0) >= min_confidence
        ]

        result = len(valid_detections) > 0
        max_conf = max([d.get("confidence", 0) for d in detections], default=0)

        return {
            "result": result,
            "valid_count": len(valid_detections),
            "max_confidence": max_conf,
        }


class VariableConditionNode(BaseExecutor):
    """变量条件 - 检查变量的值是否满足条件。

    配置项:
        variable_name: str - 变量名
        expected_value: any - 期望值
        comparison: str - 比较方式
    """

    node_type = "variable_condition"
    category = NodeCategory.LOGIC
    display_name = "变量条件"
    description = "检查变量的值是否满足条件"
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
            inputs={},
            outputs={
                "result": PortDefinition(
                    name="结果",
                    type="BOOLEAN",
                    description="条件是否满足"
                ),
                "actual_value": PortDefinition(
                    name="实际值",
                    type="ANY",
                    description="变量的实际值"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "variable_name": ConfigSchemaProperty(
                type="string",
                title="变量名",
                description="要检查的变量名称",
                default="",
                widget="text",
            ),
            "expected_value": ConfigSchemaProperty(
                type="string",
                title="期望值",
                description="与变量比较的期望值",
                default="",
                widget="text",
            ),
            "comparison": ConfigSchemaProperty(
                type="string",
                title="比较方式",
                description="比较方式",
                default="eq",
                widget="dropdown",
                enum=["eq", "ne", "gt", "lt", "gte", "lte", "contains"],
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
        var_name = params.get("variable_name", "")
        expected = params.get("expected_value", "")
        comparison = params.get("comparison", "eq")

        actual = context.variables.get(var_name)

        # 类型转换比较
        try:
            expected_float = float(expected)
            actual_float = float(actual) if actual is not None else None
            result = self._compare_values(actual_float, comparison, expected_float)
        except (ValueError, TypeError):
            result = self._compare_values(str(actual), comparison, str(expected))

        return {
            "result": result,
            "variable_name": var_name,
            "actual_value": actual,
        }

    def _compare_values(self, actual, op: str, expected) -> bool:
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
