# -*- coding: utf-8 -*-
"""处理类节点 - 数据处理变换节点。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

节点分类: processing (#FFFF4C)
"""
from typing import Any, Dict, List, Optional, Tuple

from backend.services.rule_engine.models import NodeDefinition, NodeCategory, PortDefinition, PortType, ConfigSchemaProperty
from typing import Dict
from .base import BaseExecutor


class CategoryEncodeNode(BaseExecutor):
    """类别编码节点 - 将类别名称转换为 ID 或反之。

    配置项:
        class_mapping: dict - 类别映射表 {name: id}
    """

    node_type = "category_encode"
    category = NodeCategory.PROCESSING
    display_name = "类别编码"
    description = "将类别名称与 ID 相互转换"
    icon = "tag"
    color = "#FFFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "class_names": PortDefinition(
                    name="类别名称",
                    type="ARRAY",
                    required=True,
                    description="类别名称列表"
                ),
            },
            outputs={
                "class_ids": PortDefinition(
                    name="类别ID",
                    type="ARRAY",
                    description="类别 ID 列表"
                ),
                "class_names": PortDefinition(
                    name="类别名称",
                    type="ARRAY",
                    description="类别名称列表（带映射）"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "class_mapping": ConfigSchemaProperty(
                type="string",
                title="类别映射",
                description="格式: name:id, 如 person:0,car:1",
                default="",
                widget="text",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "class_names" not in inputs:
            return False, "缺少类别名称输入"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        class_mapping = params.get("class_mapping", {})

        class_names = inputs.get("class_names", [])

        # 名称 -> ID
        class_ids = [class_mapping.get(name, -1) for name in class_names]

        return {
            "class_ids": class_ids,
            "class_names": class_names,
        }


class FilterNode(BaseExecutor):
    """过滤节点 - 根据条件过滤检测结果。

    配置项:
        filter_by: str - 过滤方式 (class/confidence/count)
        class_names: list[str] - 要保留的类别
        min_confidence: float - 最小置信度
        min_count: int - 最小数量
        max_count: int - 最大数量
    """

    node_type = "filter"
    category = NodeCategory.PROCESSING
    display_name = "结果过滤"
    description = "根据条件过滤检测结果"
    icon = "filter"
    color = "#FFFF4C"

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
                    description="待过滤的检测结果"
                ),
            },
            outputs={
                "filtered": PortDefinition(
                    name="过滤结果",
                    type="ARRAY",
                    description="过滤后的结果"
                ),
                "count": PortDefinition(
                    name="数量",
                    type="INT",
                    description="过滤后数量"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "filter_by": ConfigSchemaProperty(
                type="string",
                title="过滤方式",
                description="按什么条件过滤",
                default="confidence",
                widget="dropdown",
                enum=["class", "confidence", "count"],
            ),
            "min_confidence": ConfigSchemaProperty(
                type="number",
                title="最小置信度",
                description="只保留置信度 >= 此值的结果",
                default=0.5,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
            ),
            "min_count": ConfigSchemaProperty(
                type="integer",
                title="最小数量",
                description="最少保留多少个结果",
                default=0,
                minimum=0,
                maximum=100,
                step=1,
                widget="number",
            ),
            "max_count": ConfigSchemaProperty(
                type="integer",
                title="最大数量",
                description="最多保留多少个结果",
                default=999,
                minimum=1,
                maximum=1000,
                step=1,
                widget="number",
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
        filter_by = params.get("filter_by", "confidence")
        class_names = params.get("class_names", [])
        min_confidence = params.get("min_confidence", 0.0)
        min_count = params.get("min_count", 0)
        max_count = params.get("max_count", 999)

        detections = inputs.get("detections", [])

        # 按类别过滤
        if class_names:
            detections = [
                d for d in detections
                if d.get("class_name") in class_names or d.get("class") in class_names
            ]

        # 按置信度过滤
        if min_confidence > 0:
            detections = [
                d for d in detections
                if d.get("confidence", 0) >= min_confidence
            ]

        # 按数量限制
        filtered = detections[min_count:max_count]

        return {
            "filtered": filtered,
            "count": len(filtered),
        }


class TrackerNode(BaseExecutor):
    """目标跟踪节点 - 对检测到的目标进行跟踪。

    配置项:
        tracker_type: str - 跟踪算法 (sort/deepsort/bytetrack)
        max_age: int - 最大丢失帧数
    """

    node_type = "tracker"
    category = NodeCategory.PROCESSING
    display_name = "目标跟踪"
    description = "对检测到的目标进行跟踪"
    icon = "route"
    color = "#FFFF4C"

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
                    description="当前帧检测结果"
                ),
            },
            outputs={
                "tracked": PortDefinition(
                    name="跟踪结果",
                    type="ARRAY",
                    description="带跟踪 ID 的结果"
                ),
                "track_ids": PortDefinition(
                    name="跟踪ID",
                    type="ARRAY",
                    description="跟踪 ID 列表"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "tracker_type": ConfigSchemaProperty(
                type="string",
                title="跟踪算法",
                description="目标跟踪算法",
                default="sort",
                widget="dropdown",
                enum=["sort", "deepsort", "bytetrack"],
            ),
            "max_age": ConfigSchemaProperty(
                type="integer",
                title="最大丢失帧数",
                description="目标丢失多少帧后删除",
                default=30,
                minimum=1,
                maximum=100,
                step=1,
                widget="number",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        # TODO: 实现实际跟踪算法
        detections = inputs.get("detections", [])

        return {
            "tracked": detections,
            "track_ids": [d.get("track_id", i) for i, d in enumerate(detections)],
        }


class ImagePreprocessorNode(BaseExecutor):
    """图像预处理节点 - 对图像进行预处理。

    配置项:
        operation: str - 操作类型 (resize/crop/normalize/augment)
        width: int - 目标宽度
        height: int - 目标高度
    """

    node_type = "image_preprocessor"
    category = NodeCategory.PROCESSING
    display_name = "图像预处理"
    description = "对图像进行预处理"
    icon = "image-edit"
    color = "#FFFF4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "image": PortDefinition(
                    name="图片",
                    type=PortType.IMAGE.value,
                    required=True,
                    description="待处理的图片"
                ),
            },
            outputs={
                "image": PortDefinition(
                    name="处理后图片",
                    type=PortType.IMAGE.value,
                    description="处理后的图片"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "operation": ConfigSchemaProperty(
                type="string",
                title="操作类型",
                description="图像预处理操作",
                default="resize",
                widget="dropdown",
                enum=["resize", "crop", "normalize", "augment"],
            ),
            "width": ConfigSchemaProperty(
                type="integer",
                title="目标宽度",
                description="预处理后图片宽度",
                default=640,
                minimum=16,
                maximum=4096,
                step=1,
                widget="number",
            ),
            "height": ConfigSchemaProperty(
                type="integer",
                title="目标高度",
                description="预处理后图片高度",
                default=640,
                minimum=16,
                maximum=4096,
                step=1,
                widget="number",
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
        operation = params.get("operation", "resize")
        width = params.get("width", 640)
        height = params.get("height", 640)

        image = inputs.get("image")

        if image is None:
            return {"error": "图片为空"}

        # TODO: 实现实际预处理
        return {
            "image": image,
            "operation": operation,
            "width": width,
            "height": height,
        }
