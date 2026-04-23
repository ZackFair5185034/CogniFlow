# -*- coding: utf-8 -*-
"""触发器节点 - 规则执行的入口节点。"""
from typing import Optional
from .base import (
    BaseNode, NodeCategory, NodeResult, NodeStatus, ExecutionContext
)


class YOLOTriggerNode(BaseNode):
    """YOLO 触发器 - 当检测到指定目标时触发规则。

    配置项:
        class_names: list[str] - 要检测的类别名称列表
        min_confidence: float - 最小置信度 (0-1)
        max_objects: int - 最大检测数量
        check_interval: float - 检测间隔(秒)
    """
    node_type = "yolo_trigger"
    category = NodeCategory.TRIGGER
    label = "YOLO 触发器"
    description = "当检测到指定目标时触发规则执行"
    icon = "mdi:radar"

    inputs = []
    outputs = [
        {"name": "triggered", "type": "boolean", "label": "触发"},
        {"name": "detections", "type": "array", "label": "检测结果"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "class_names": {
                "type": "array",
                "items": {"type": "string"},
                "default": []
            },
            "min_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "default": 0.5
            },
            "max_objects": {
                "type": "integer",
                "minimum": 1,
                "default": 10
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行 YOLO 触发检测。"""
        class_names = self.config.get("class_names", [])
        min_confidence = self.config.get("min_confidence", 0.5)
        max_objects = self.config.get("max_objects", 10)

        # 从触发数据中获取检测结果
        detections = context.trigger_data.get("detections", [])
        triggered = False
        matched = []

        for det in detections:
            if det.get("confidence", 0) >= min_confidence:
                if not class_names or det.get("class") in class_names:
                    matched.append(det)
                    if len(matched) >= max_objects:
                        break

        if matched:
            triggered = True
            context.set_var("_last_detections", matched)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "triggered": triggered,
                "detections": matched,
            }
        )


class TimerTriggerNode(BaseNode):
    """定时器触发器 - 按固定间隔触发规则。

    配置项:
        interval: float - 触发间隔(秒)
        enabled: bool - 是否启用
    """
    node_type = "timer_trigger"
    category = NodeCategory.TRIGGER
    label = "定时器触发器"
    description = "按固定时间间隔触发规则执行"
    icon = "mdi:timer"

    inputs = []
    outputs = [
        {"name": "triggered", "type": "boolean", "label": "触发"},
        {"name": "timestamp", "type": "number", "label": "时间戳"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "interval": {
                "type": "number",
                "minimum": 0.1,
                "default": 5.0
            },
            "enabled": {
                "type": "boolean",
                "default": True
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行定时器检查。"""
        import time
        interval = self.config.get("interval", 5.0)
        enabled = self.config.get("enabled", True)

        # 简单实现：每次都触发，实际使用时需要记录上次触发时间
        triggered = enabled

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "triggered": triggered,
                "timestamp": time.time(),
            }
        )


class ManualTriggerNode(BaseNode):
    """手动触发器 - 手动触发规则执行。

    用于测试或手动控制场景。
    """
    node_type = "manual_trigger"
    category = NodeCategory.TRIGGER
    label = "手动触发器"
    description = "手动触发规则执行"
    icon = "mdi:hand-pointing-right"

    inputs = []
    outputs = [
        {"name": "triggered", "type": "boolean", "label": "触发"},
    ]

    config_schema = {
        "type": "object",
        "properties": {}
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行手动触发。"""
        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "triggered": True,
            }
        )
