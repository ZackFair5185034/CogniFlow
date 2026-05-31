# -*- coding: utf-8 -*-
"""处理类节点 - 数据处理变换节点。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

节点分类: processing (#FFFF4C)
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.services.rule_engine.models import NodeDefinition, NodeCategory, PortDefinition, PortType, ConfigSchemaProperty
from backend.services.rule_engine.tracker import SortTracker
from typing import Dict
from .base import BaseExecutor

logger = logging.getLogger(__name__)

# 跨执行调用的跟踪器状态（key: node_id -> SortTracker）
_tracker_states: Dict[str, SortTracker] = {}


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
        raw_mapping = params.get("class_mapping", {})
        # 兼容字符串格式 "person:0,car:1" 和字典格式 {"person": 0, "car": 1}
        if isinstance(raw_mapping, str):
            class_mapping = {}
            for part in raw_mapping.split(","):
                part = part.strip()
                if ":" in part:
                    k, v = part.split(":", 1)
                    class_mapping[k.strip()] = int(v.strip())
                elif part:
                    class_mapping[part] = -1
        else:
            class_mapping = raw_mapping or {}

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
            "class_names": ConfigSchemaProperty(
                type="string",
                title="类别名称",
                description="要保留的类别，多个用逗号分隔，如 person,car,dog",
                default="",
                widget="text",
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
        raw_class_names = params.get("class_names", [])
        # 兼容字符串（逗号分隔，前端 text widget）和列表格式
        class_names = [n.strip() for n in raw_class_names.split(",") if n.strip()] if isinstance(raw_class_names, str) else (raw_class_names or [])
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

    使用 SORT 算法（卡尔曼滤波 + IoU 贪心匹配）。
    跟踪器状态在节点实例间共享（按 node_id 隔离），
    同一节点连续调用可保持目标 ID 稳定。

    配置项:
        max_age: int - 最大丢失帧数 (1-100)
        min_hits: int - 最少命中次数才输出 (1-10)
        iou_threshold: float - IoU 关联阈值 (0.1-0.9)
    """

    node_type = "tracker"
    category = NodeCategory.PROCESSING
    display_name = "目标跟踪"
    description = "对检测到的目标进行跟踪（SORT 算法）"
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
                    description="当前帧检测结果（含 bbox 字段）"
                ),
            },
            outputs={
                "tracked": PortDefinition(
                    name="跟踪结果",
                    type="ARRAY",
                    description="带 track_id 的跟踪结果列表"
                ),
                "track_ids": PortDefinition(
                    name="跟踪ID",
                    type="ARRAY",
                    description="跟踪 ID 列表"
                ),
                "count": PortDefinition(
                    name="跟踪数量",
                    type="INT",
                    description="当前跟踪目标数量"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "max_age": ConfigSchemaProperty(
                type="integer",
                title="最大丢失帧数",
                description="目标丢失多少帧后删除轨迹",
                default=30,
                minimum=1,
                maximum=100,
                step=1,
                widget="slider",
            ),
            "min_hits": ConfigSchemaProperty(
                type="integer",
                title="最少命中次数",
                description="目标连续命中多少次后才输出",
                default=3,
                minimum=1,
                maximum=10,
                step=1,
                widget="slider",
            ),
            "iou_threshold": ConfigSchemaProperty(
                type="number",
                title="IoU 关联阈值",
                description="检测与轨迹匹配的最小 IoU",
                default=0.3,
                minimum=0.1,
                maximum=0.9,
                step=0.05,
                widget="slider",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "detections" not in inputs:
            return False, "缺少检测结果输入"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        max_age = params.get("max_age", 30)
        min_hits = params.get("min_hits", 3)
        iou_threshold = params.get("iou_threshold", 0.3)

        detections = inputs.get("detections", [])

        # 确保输入为列表
        if not isinstance(detections, list):
            return {"error": "检测结果必须是列表格式"}

        # 获取或创建当前节点的跟踪器
        tracker_key = f"{context.execution_id}:{self.node_id}"
        if tracker_key not in _tracker_states:
            _tracker_states[tracker_key] = SortTracker(
                max_age=max_age,
                min_hits=min_hits,
                iou_threshold=iou_threshold,
            )

        tracker = _tracker_states[tracker_key]

        try:
            tracked = tracker.update(detections)
            track_ids = [t.get("track_id", 0) for t in tracked]

            return {
                "tracked": tracked,
                "track_ids": track_ids,
                "count": len(tracked),
            }
        except Exception as e:
            logger.error(f"目标跟踪失败: {e}")
            return {"error": f"目标跟踪失败: {str(e)}"}


class ImagePreprocessorNode(BaseExecutor):
    """图像预处理节点 - 对图像进行预处理。

    支持的操作:
        resize:   缩放到指定宽高
        crop:     居中裁剪到指定宽高
        normalize: 归一化像素值到 [0, 1]

    依赖 opencv-python，未安装时返回原始图片。
    """

    node_type = "image_preprocessor"
    category = NodeCategory.PROCESSING
    display_name = "图像预处理"
    description = "对图像进行缩放/裁剪/归一化等预处理"
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
                    description="待处理的图片路径"
                ),
            },
            outputs={
                "image": PortDefinition(
                    name="处理后图片",
                    type=PortType.IMAGE.value,
                    description="处理后图片路径"
                ),
                "width": PortDefinition(
                    name="宽度",
                    type="INT",
                    description="处理后图片宽度"
                ),
                "height": PortDefinition(
                    name="高度",
                    type="INT",
                    description="处理后图片高度"
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
                enum=["resize", "crop", "normalize"],
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
        if "image" not in inputs or inputs["image"] is None:
            return False, "缺少图片输入"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        operation = params.get("operation", "resize")
        target_w = params.get("width", 640)
        target_h = params.get("height", 640)

        image_input = inputs.get("image")

        # 解析图片路径
        if isinstance(image_input, dict):
            image_path = image_input.get("path", "")
        elif isinstance(image_input, str):
            image_path = image_input
        else:
            return {"error": "无法解析图片输入"}

        if not image_path:
            return {"error": "图片路径为空"}

        # 尝试用 OpenCV 处理
        try:
            import cv2
            import os

            img = cv2.imread(image_path)
            if img is None:
                return {"error": f"无法读取图片: {image_path}"}

            orig_h, orig_w = img.shape[:2]

            if operation == "resize":
                processed = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

            elif operation == "crop":
                # 居中裁剪
                center_x, center_y = orig_w // 2, orig_h // 2
                crop_w = min(target_w, orig_w)
                crop_h = min(target_h, orig_h)
                x1 = max(0, center_x - crop_w // 2)
                y1 = max(0, center_y - crop_h // 2)
                processed = img[y1:y1 + crop_h, x1:x1 + crop_w]
                # 如裁剪后尺寸与目标不一致则缩放
                if processed.shape[1] != target_w or processed.shape[0] != target_h:
                    processed = cv2.resize(processed, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

            elif operation == "normalize":
                # 归一化到 [0, 1]
                processed = img.astype("float32") / 255.0
                # 转回 8bit 保存（乘以 255）
                processed = (processed * 255).astype("uint8")
                if target_w != orig_w or target_h != orig_h:
                    processed = cv2.resize(processed, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

            else:
                return {"error": f"不支持的操作类型: {operation}"}

            # 保存处理结果到临时文件
            from backend.services.rule_engine.utils import get_temp_image_path
            output_path = get_temp_image_path(self.node_id, image_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, processed)

            out_h, out_w = processed.shape[:2]

            return {
                "image": {"path": output_path},
                "width": out_w,
                "height": out_h,
            }

        except ImportError:
            logger.warning("OpenCV (cv2) 未安装，返回原始图片")
            return {
                "image": {"path": image_path},
                "width": 0,
                "height": 0,
                "warning": "OpenCV 未安装，图片未处理",
            }
        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            return {"error": f"图像预处理失败: {str(e)}"}
