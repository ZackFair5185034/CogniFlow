# -*- coding: utf-8 -*-
"""检测类节点 - 目标检测模型节点。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

节点分类: detection (#00f0FF)

重要: YOLOTriggerNode 需要对接 inference_yolo 服务（Phase 6 缺口修复）
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.services.rule_engine.models import (
    NodeDefinition, NodeCategory, PortDefinition, PortType, ConfigSchemaProperty
)
from backend.services.rule_engine.model_cache import ModelCache
from .base import BaseExecutor

logger = logging.getLogger(__name__)


class YOLOModelNode(BaseExecutor):
    """YOLO 目标检测节点。

    对接 inference_yolo 服务进行目标检测。

    配置项:
        model_path: str - 模型文件路径
        model_id: int - 已注册的模型 ID
        confidence: float - 置信度阈值 (0-1)
    """

    node_type = "yolo_model"
    category = NodeCategory.DETECTION
    display_name = "YOLO 检测"
    description = "使用 YOLO 模型进行目标检测"
    icon = "radar"
    color = "#00f0FF"

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
                    name="图片输入",
                    type=PortType.IMAGE.value,
                    required=True,
                    description="待检测的图片"
                ),
            },
            outputs={
                "bboxes": PortDefinition(
                    name="检测框",
                    type=PortType.BBOX.value,
                    description="检测到的目标框列表 [[x1,y1,x2,y2], ...]"
                ),
                "scores": PortDefinition(
                    name="置信度",
                    type=PortType.SCORES.value,
                    description="各检测框对应的置信度"
                ),
                "class_ids": PortDefinition(
                    name="类别ID",
                    type="ARRAY",
                    description="各检测框对应的类别 ID"
                ),
                "class_names": PortDefinition(
                    name="类别名称",
                    type="ARRAY",
                    description="各检测框对应的类别名称"
                ),
                "count": PortDefinition(
                    name="检测数量",
                    type="INT",
                    description="检测到的目标数量"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        """返回节点的可配置参数 schema。"""
        return {
            "model_id": ConfigSchemaProperty(
                type="string",
                title="模型",
                description="选择要使用的 YOLO 检测模型",
                default="",
                widget="model-select",
                required=True,
            ),
            "confidence": ConfigSchemaProperty(
                type="number",
                title="置信度阈值",
                description="只保留置信度 >= threshold 的检测结果",
                default=0.5,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
            ),
            "iou_threshold": ConfigSchemaProperty(
                type="number",
                title="IOU 阈值",
                description="NMS（非极大值抑制）的 IOU 阈值",
                default=0.45,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
            ),
            "max_detections": ConfigSchemaProperty(
                type="integer",
                title="最大检测数",
                description="每张图最多检测多少个目标",
                default=300,
                minimum=1,
                maximum=1000,
                step=1,
                widget="number",
            ),
            "device": ConfigSchemaProperty(
                type="string",
                title="推理设备",
                description="选择模型推理使用的设备",
                default="auto",
                enum=["auto", "cuda", "cpu"],
                widget="dropdown",
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
        model_id = params.get("model_id")
        model_path = params.get("model_path")
        confidence = params.get("confidence", 0.5)
        iou_threshold = params.get("iou_threshold", 0.45)
        max_detections = params.get("max_detections", 300)

        if not model_id and not model_path:
            return {"error": "必须提供 model_id 或 model_path"}

        try:
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

            # 获取模型路径（通过 model_id 查数据库）
            if model_id and not model_path:
                from backend.database import SessionLocal
                from backend.database import Model
                db = SessionLocal()
                try:
                    model_record = db.query(Model).filter(Model.id == model_id).first()
                    if model_record and model_record.model_path:
                        model_path = model_record.model_path
                finally:
                    db.close()

            if not model_path:
                return {"error": f"模型 {model_id} 未找到或无模型文件"}

            # 通过缓存加载模型
            from backend.routers.yolo_training import load_yolo_model, inference_yolo

            cache_key = f"yolo:{model_path}"
            cache = ModelCache.get_instance()
            model = cache.get_or_load(cache_key, lambda: load_yolo_model(model_path))

            # 执行推理
            result = inference_yolo(model, image_path, conf_threshold=confidence)

            detections = result.get("detections", [])

            bboxes = [d.get("bbox", []) for d in detections]
            scores = [d.get("confidence", 0) for d in detections]
            class_ids = [d.get("class_id", 0) for d in detections]
            class_names = [d.get("class_name", "") for d in detections]

            return {
                "bboxes": bboxes,
                "scores": scores,
                "class_ids": class_ids,
                "class_names": class_names,
                "count": len(detections),
                "detections": detections,
            }

        except Exception as e:
            logger.error(f"YOLO 推理失败: {e}")
            return {"error": f"YOLO 推理失败: {str(e)}"}


class YOLOTriggerNode(BaseExecutor):
    """YOLO 触发器节点 - 当检测到指定目标时触发规则。

    对接 inference_yolo 服务进行持续检测。

    配置项:
        model_id: int - 已注册的模型 ID
        model_path: str - 模型文件路径（备用）
        class_names: list[str] - 要检测的类别名称列表
        min_confidence: float - 最小置信度 (0-1)
        max_objects: int - 最大检测数量
        check_interval: float - 检测间隔(秒)

    输出:
        triggered: bool - 是否触发
        detections: array - 检测结果列表
    """

    node_type = "yolo_trigger"
    category = NodeCategory.INPUT  # 作为输入类节点（数据采集）
    display_name = "YOLO 触发器"
    description = "当检测到指定目标时触发规则执行"
    icon = "radar"
    color = "#4CFF4C"  # 使用输入类颜色

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
                    name="图片输入",
                    type=PortType.IMAGE.value,
                    required=False,
                    description="待检测的图片（可选，不提供时使用 trigger_data）"
                ),
            },
            outputs={
                "triggered": PortDefinition(
                    name="触发",
                    type="BOOLEAN",
                    description="是否满足触发条件"
                ),
                "detections": PortDefinition(
                    name="检测结果",
                    type="ARRAY",
                    description="检测到的目标列表"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "model_id": ConfigSchemaProperty(
                type="string",
                title="模型",
                description="选择要使用的 YOLO 检测模型",
                default="",
                widget="model-select",
            ),
            "class_names": ConfigSchemaProperty(
                type="array",
                title="目标类别",
                description="要检测的类别名称列表",
                default=[],
                widget="multiselect",
                enum=["person", "car", "dog", "cat", "bicycle", "truck", "bus"],
            ),
            "min_confidence": ConfigSchemaProperty(
                type="number",
                title="最小置信度",
                description="只保留置信度 >= threshold 的检测结果",
                default=0.5,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
            ),
            "max_objects": ConfigSchemaProperty(
                type="number",
                title="最大检测数",
                description="最多检测多少个目标",
                default=10,
                minimum=1,
                maximum=100,
                step=1,
                widget="number",
            ),
            "device": ConfigSchemaProperty(
                type="string",
                title="推理设备",
                description="选择模型推理使用的设备",
                default="auto",
                enum=["auto", "cuda", "cpu"],
                widget="dropdown",
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
        model_id = params.get("model_id")
        model_path = params.get("model_path")
        class_names = params.get("class_names", [])
        min_confidence = params.get("min_confidence", 0.5)
        max_objects = params.get("max_objects", 10)

        try:
            # 优先使用 context.trigger_data 中的检测结果（外部触发）
            trigger_data = context.trigger_data
            detections = trigger_data.get("detections", [])

            # 如果 trigger_data 没有检测结果，尝试使用 inputs 中的图片进行检测
            if not detections:
                image_input = inputs.get("image")
                if image_input:
                    # 获取图片路径
                    if isinstance(image_input, dict):
                        image_path = image_input.get("path", "")
                    elif isinstance(image_input, str):
                        image_path = image_input
                    else:
                        return {
                            "triggered": False,
                            "detections": [],
                            "error": "无法解析图片输入"
                        }

                    if image_path:
                        # 通过缓存加载模型并执行检测
                        from backend.routers.yolo_training import load_yolo_model, inference_yolo

                        # 获取模型路径
                        if not model_path and model_id:
                            from backend.database import SessionLocal
                            from backend.database import Model
                            db = SessionLocal()
                            try:
                                model_record = db.query(Model).filter(Model.id == model_id).first()
                                if model_record and model_record.model_path:
                                    model_path = model_record.model_path
                            finally:
                                db.close()

                        if model_path:
                            cache_key = f"yolo:{model_path}"
                            cache = ModelCache.get_instance()
                            model = cache.get_or_load(cache_key, lambda: load_yolo_model(model_path))
                            result = inference_yolo(model, image_path, conf_threshold=min_confidence)
                            detections = result.get("detections", [])
                        else:
                            return {
                                "triggered": False,
                                "detections": [],
                                "error": "未配置模型"
                            }

            # 过滤符合条件的检测
            matched = []
            for det in detections:
                confidence = det.get("confidence", 0)
                class_name = det.get("class_name", "")

                if confidence >= min_confidence:
                    if not class_names or class_name in class_names:
                        matched.append(det)
                        if len(matched) >= max_objects:
                            break

            triggered = len(matched) > 0

            # 保存到上下文供后续节点使用
            if matched:
                context.node_results[f"{self.node_id}_detections"] = matched

            return {
                "triggered": triggered,
                "detections": matched,
                "count": len(matched),
            }

        except Exception as e:
            logger.error(f"YOLO 触发器执行失败: {e}")
            return {
                "triggered": False,
                "detections": [],
                "error": str(e)
            }


class ObjectDetectorNode(BaseExecutor):
    """通用目标检测节点 - 支持多种检测模型。

    配置项:
        model_type: str - 模型类型 (yolo/ssd/mtcnn)
        model_path: str - 模型路径
        confidence: float - 置信度阈值
    """

    node_type = "object_detector"
    category = NodeCategory.DETECTION
    display_name = "目标检测"
    description = "通用目标检测节点"
    icon = "eye"
    color = "#00f0FF"

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
                    name="图片输入",
                    type=PortType.IMAGE.value,
                    required=True,
                    description="待检测的图片"
                ),
            },
            outputs={
                "detections": PortDefinition(
                    name="检测结果",
                    type="ARRAY",
                    description="检测到的目标列表"
                ),
                "count": PortDefinition(
                    name="数量",
                    type="INT",
                    description="检测数量"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "model_type": ConfigSchemaProperty(
                type="string",
                title="模型类型",
                description="选择检测模型类型",
                default="yolo",
                widget="dropdown",
                enum=["yolo", "ssd", "mtcnn"],
            ),
            "confidence": ConfigSchemaProperty(
                type="number",
                title="置信度阈值",
                description="只保留置信度 >= threshold 的检测结果",
                default=0.5,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "image" not in inputs:
            return False, "缺少图片输入"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        model_type = params.get("model_type", "yolo")
        model_path = params.get("model_path")
        confidence = params.get("confidence", 0.5)

        if model_type != "yolo":
            return {"error": f"模型类型 '{model_type}' 暂未实现，当前仅支持 yolo"}

        if not model_path:
            return {"error": "必须提供 model_path"}

        try:
            image_input = inputs.get("image")

            if isinstance(image_input, dict):
                image_path = image_input.get("path", "")
            elif isinstance(image_input, str):
                image_path = image_input
            else:
                return {"error": "无法解析图片输入"}

            if not image_path:
                return {"error": "图片路径为空"}

            from backend.routers.yolo_training import load_yolo_model, inference_yolo

            cache_key = f"yolo:{model_path}"
            cache = ModelCache.get_instance()
            model = cache.get_or_load(cache_key, lambda: load_yolo_model(model_path))

            result = inference_yolo(model, image_path, conf_threshold=confidence)
            detections = result.get("detections", [])

            return {
                "detections": detections,
                "count": len(detections),
            }

        except Exception as e:
            logger.error(f"目标检测失败: {e}")
            return {"error": f"目标检测失败: {str(e)}"}
