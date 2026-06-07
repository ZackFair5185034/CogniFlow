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
from .base import BaseExecutor, ExecutionContext

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


# ============================================================================
# 模板渲染节点 - 用变量插值生成文本/JSON 输出
# ============================================================================

import json
import re


def _resolve_scope_key(scope: Dict[str, Any], dotted_key: str) -> Any:
    """解析嵌套 key（如 'user.name'）从 scope dict 中取值。

    中间任意一段缺失返回 None，不抛异常（避免阻塞模板渲染主流程）。
    """
    current: Any = scope
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _interpolate_template(template: str, scope: Dict[str, Any]) -> str:
    """简单变量插值：支持 {{var}} 与 {{a.b.c}} 两种语法。

    未定义变量替换为空字符串（不抛异常）。
    """
    if not template:
        return ""
    pattern = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")
    return pattern.sub(
        lambda m: str(_resolve_scope_key(scope, m.group(1)) or ""),
        template,
    )


class TemplateNode(BaseExecutor):
    """模板渲染节点 — 用变量插值生成文本或 JSON 输出。

    用途：
    - 拼接 webhook payload / SQL 语句 / 日志消息等结构化输出
    - 把上游检测结果格式化为可视化文本

    模板语法：`{{var_name}}` 或 `{{nested.key}}`

    变量来源（按优先级合并，高优先级覆盖低优先级）：
    1. inputs.data — 上游 OBJECT 输入
    2. context.variables — 规则图级变量
    3. context.trigger_data — 触发数据（作为 `trigger.*` 访问）

    输出：
    - result: 渲染结果（parse_as=text 时为字符串；parse_as=json 时为解析后的对象）
    - raw: 始终为字符串形式的渲染结果（便于排查与日志记录）
    """

    node_type = "template"
    category = NodeCategory.PROCESSING
    display_name = "模板渲染"
    description = "用变量插值生成文本或 JSON 输出"
    icon = "file-text"
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
                "data": PortDefinition(
                    name="数据",
                    type="OBJECT",
                    required=False,
                    description="上游提供的对象数据（其字段可在模板中通过 {{key}} 引用）",
                ),
            },
            outputs={
                "result": PortDefinition(
                    name="渲染结果",
                    type="STRING",
                    description="渲染后的文本或 JSON 对象",
                ),
                "raw": PortDefinition(
                    name="原始文本",
                    type="STRING",
                    description="始终为字符串形式的渲染结果",
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "template": ConfigSchemaProperty(
                type="string",
                title="模板",
                description="支持 {{var}} 与 {{nested.key}} 插值；未定义变量替换为空字符串",
                default="",
                widget="textarea",
            ),
            "parse_as": ConfigSchemaProperty(
                type="string",
                title="输出格式",
                description="text 渲染为字符串；json 解析为对象（解析失败回退为字符串）",
                default="text",
                enum=["text", "json"],
                widget="dropdown",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context,
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        template = params.get("template", "")
        parse_as = params.get("parse_as", "text")

        # 合并变量作用域（后 update 覆盖先 update，故高优先级放最后）：
        # 触发数据 < 规则图变量 < 上游 inputs
        scope: Dict[str, Any] = {}
        trigger_data = getattr(context, "trigger_data", None)
        if isinstance(trigger_data, dict) and trigger_data:
            scope["trigger"] = trigger_data
        if getattr(context, "variables", None):
            scope.update(context.variables)
        upstream_data = inputs.get("data")
        if isinstance(upstream_data, dict):
            scope.update(upstream_data)

        raw = _interpolate_template(template, scope)

        if parse_as == "json":
            try:
                return {"result": json.loads(raw), "raw": raw}
            except (json.JSONDecodeError, TypeError):
                # 解析失败时回退为字符串，便于下游继续处理
                return {"result": raw, "raw": raw}

        return {"result": raw, "raw": raw}


class MergeDetectionsNode(BaseExecutor):
    """多源检测结果融合节点。

    接收多个 ARRAY 输入（每个数组的元素是 dict，至少含 bbox/confidence/
    class_id/class_name 字段；典型上游为 YOLOModel / ObjectDetector /
    Filter / Tracker），合并后按 IoU 阈值去重，输出统一格式的 ARRAY。

    与 Tracker 节点的区别：Tracker 维护时序跟踪（同一目标跨帧保持 ID），
    本节点是"多模型/多源单帧融合"，无时序假设。

    配置项:
        iou_threshold: float - IoU 阈值，超过此值的检测框视为同一目标
        strategy: str - 融合策略（nms/union）
            nms:  跨输入按 IoU 去重，保留置信度最高的
            union: 简单拼接，不去重（保留所有结果）
        keep_source: bool - 是否在每个检测 dict 中保留 source 字段
    """

    node_type = "merge_detections"
    category = NodeCategory.PROCESSING
    display_name = "检测结果融合"
    description = "合并多个检测源的检测结果，按 IoU 去重（多 YOLO 模型融合）"
    icon = "merge"
    color = "#FFFF4C"

    def get_definition(self) -> NodeDefinition:
        # 动态输入端口列表（input_1, input_2, ..., input_N）
        # 至少 2 个，最多 8 个输入
        max_inputs = 8
        inputs_def = {
            f"input_{i+1}": PortDefinition(
                name=f"检测源 {i+1}",
                type="ARRAY",
                required=False,
                description=f"第 {i+1} 路检测源输出（dict 列表）"
            )
            for i in range(max_inputs)
        }
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs=inputs_def,
            outputs={
                "merged": PortDefinition(
                    name="融合结果",
                    type="ARRAY",
                    description="去重后的合并检测列表"
                ),
                "count": PortDefinition(
                    name="数量",
                    type="INT",
                    description="融合后检测框数量"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "iou_threshold": ConfigSchemaProperty(
                type="number",
                title="IoU 阈值",
                description="IoU 超过此值的两个检测框视为同一目标（0.0-1.0）",
                default=0.5,
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                widget="slider",
            ),
            "strategy": ConfigSchemaProperty(
                type="string",
                title="融合策略",
                description="nms=按 IoU 去重保留最高置信度；union=简单拼接不去重",
                default="nms",
                widget="dropdown",
                enum=["nms", "union"],
            ),
            "keep_source": ConfigSchemaProperty(
                type="boolean",
                title="保留来源标签",
                description="在每个检测 dict 中添加 source 字段（input_1/input_2/...）",
                default=False,
                widget="checkbox",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """校验：至少 1 路非空输入。"""
        active = [v for v in inputs.values() if v is not None and v != []]
        if not active:
            return False, "至少需要 1 路非空检测源输入"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        cfg = context.config if hasattr(context, "config") else {}
        iou_threshold = float(cfg.get("iou_threshold", 0.5))
        strategy = cfg.get("strategy", "nms")
        keep_source = bool(cfg.get("keep_source", False))

        # 1) 收集所有非空输入
        all_detections: List[Dict[str, Any]] = []
        for port_name, payload in inputs.items():
            if payload is None or payload == []:
                continue
            if not isinstance(payload, list):
                return {"merged": [], "count": 0}
            for det in payload:
                if not isinstance(det, dict):
                    continue
                item = dict(det)  # 拷贝避免修改上游数据
                if keep_source:
                    item["source"] = port_name
                all_detections.append(item)

        if not all_detections:
            return {"merged": [], "count": 0}

        # 2) union 策略：直接返回
        if strategy == "union":
            return {"merged": all_detections, "count": len(all_detections)}

        # 3) nms 策略：按置信度降序贪心去重
        all_detections.sort(
            key=lambda d: float(d.get("confidence", d.get("score", 0.0))),
            reverse=True,
        )
        kept: List[Dict[str, Any]] = []
        for det in all_detections:
            bbox = det.get("bbox", [])
            if not _is_valid_bbox(bbox):
                # 无效 bbox 直接保留（无法做 IoU 比较）
                kept.append(det)
                continue
            # 与已保留的所有框比较
            duplicate = False
            for kept_det in kept:
                kept_bbox = kept_det.get("bbox", [])
                if not _is_valid_bbox(kept_bbox):
                    continue
                iou = _compute_iou(bbox, kept_bbox)
                # 类别不同则不去重（不同目标可重叠）
                if (
                    iou >= iou_threshold
                    and det.get("class_id", -1) == kept_det.get("class_id", -1)
                    and det.get("class_id", -1) != -1
                ):
                    duplicate = True
                    break
                # 类别字段缺失时也按 IoU 去重（兜底）
                if (
                    iou >= iou_threshold
                    and det.get("class_id") is None
                    and kept_det.get("class_id") is None
                ):
                    duplicate = True
                    break
            if not duplicate:
                kept.append(det)

        return {"merged": kept, "count": len(kept)}


def _is_valid_bbox(bbox: Any) -> bool:
    """校验 bbox 是否为 [x1, y1, x2, y2] 形式且坐标合法。"""
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    try:
        x1, y1, x2, y2 = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return False
    return x2 > x1 and y2 > y1


def _compute_iou(b1: List[float], b2: List[float]) -> float:
    """计算两个 [x1, y1, x2, y2] 框的 IoU。"""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, b1[2] - b1[0]) * max(0.0, b1[3] - b1[1])
    area2 = max(0.0, b2[2] - b2[0]) * max(0.0, b2[3] - b2[1])
    union = area1 + area2 - inter
    if union <= 0:
        return 0.0
    return inter / union


class RoiExtractNode(BaseExecutor):
    """按 BBOX 裁剪图像 ROI 区域。

    输入 image（IMAGE，路径字符串或 {"path": str} dict）+ detections（ARRAY，
    含 bbox 字段的检测列表），输出每张 ROI 裁剪后的图片（IMAGE 端口，
    {"path": str}）+ 元数据（orig_width/orig_height/roi_count/bboxes）。

    典型用法：YOLOModel → RoiExtract → ImagePreprocessor（缩放到统一尺寸）
    → 次级模型（如 OCR、分类器）。

    与 ImagePreprocessor 的区别：ImagePreprocessor 居中裁剪整张图；
    本节点按 BBOX 列表从原图逐个裁剪，每个检测目标一张 ROI。

    配置项:
        padding: float - bbox 周边扩展比例（0.0 = 严格裁剪，0.1 = 外扩 10%）
        min_size: int - 裁剪后最小边长（小于则跳过该 ROI）
        max_rois: int - 最多保留的 ROI 数量（按 confidence 降序）
        output_format: str - 输出图片格式（jpg/png，缺省沿用输入）

    依赖 opencv-python（cv2）。未安装时返回原图，附加 warning。
    """

    node_type = "roi_extract"
    category = NodeCategory.PROCESSING
    display_name = "ROI 裁剪"
    description = "按 BBOX 从原图裁剪 ROI 区域（每个检测目标一张）"
    icon = "crop"
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
                    name="原图",
                    type=PortType.IMAGE.value,
                    required=True,
                    description="原图路径或 {path: str}"
                ),
                "detections": PortDefinition(
                    name="检测结果",
                    type="ARRAY",
                    required=True,
                    description="含 bbox 字段的检测列表（来自 YOLOModel/Filter/Tracker）"
                ),
            },
            outputs={
                "roi": PortDefinition(
                    name="ROI 图片",
                    type=PortType.IMAGE.value,
                    description="第一张 ROI（{path: str}）"
                ),
                "roi_count": PortDefinition(
                    name="ROI 数量",
                    type="INT",
                    description="实际裁剪得到的 ROI 数量"
                ),
                "width": PortDefinition(
                    name="宽度",
                    type="INT",
                    description="ROI 宽度（像素，第一张）"
                ),
                "height": PortDefinition(
                    name="高度",
                    type="INT",
                    description="ROI 高度（像素，第一张）"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "padding": ConfigSchemaProperty(
                type="number",
                title="扩展比例",
                description="bbox 周边扩展比例（0.0 = 严格裁剪，0.1 = 外扩 10%）",
                default=0.0,
                minimum=0.0,
                maximum=0.5,
                step=0.05,
                widget="slider",
            ),
            "min_size": ConfigSchemaProperty(
                type="integer",
                title="最小边长",
                description="裁剪后最小边长（像素），小于则跳过该 ROI",
                default=4,
                minimum=1,
                maximum=1024,
                step=1,
                widget="number",
            ),
            "max_rois": ConfigSchemaProperty(
                type="integer",
                title="最大 ROI 数",
                description="最多保留的 ROI 数量（按 confidence 降序截取）",
                default=10,
                minimum=1,
                maximum=100,
                step=1,
                widget="number",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not inputs.get("image"):
            return False, "缺少必需参数 'image'"
        if not inputs.get("detections"):
            return False, "缺少必需参数 'detections'"
        return True, None

    @staticmethod
    def _extract_image_path(image: Any) -> Optional[str]:
        """从 IMAGE 端口数据中提取路径字符串。"""
        if isinstance(image, str):
            return image
        if isinstance(image, dict):
            return image.get("path")
        return None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        cfg = context.config if hasattr(context, "config") else {}
        padding = float(cfg.get("padding", 0.0))
        min_size = int(cfg.get("min_size", 4))
        max_rois = int(cfg.get("max_rois", 10))

        image_path = self._extract_image_path(inputs.get("image"))
        if not image_path:
            return {"error": "无效的 image 输入（需 str 或 {path: str}）"}

        detections = inputs.get("detections") or []
        if not isinstance(detections, list):
            return {"error": "无效的 detections 输入（需 list）"}

        # 按 confidence 降序截取前 max_rois
        sorted_dets = sorted(
            detections,
            key=lambda d: float(d.get("confidence", d.get("score", 0.0)) or 0.0),
            reverse=True,
        )[:max_rois]

        # cv2 可选
        try:
            import cv2  # type: ignore
        except ImportError:
            logger.warning("OpenCV (cv2) 未安装，ROI 裁剪不可用")
            return {
                "roi": {"path": image_path},
                "roi_count": 0,
                "width": 0,
                "height": 0,
                "warning": "OpenCV 未安装，ROI 裁剪未执行",
            }

        try:
            img = cv2.imread(image_path)
            if img is None:
                return {"error": f"无法读取图片: {image_path}"}
            orig_h, orig_w = img.shape[:2]
        except Exception as e:
            return {"error": f"读取图片失败: {str(e)}"}

        # 逐个 ROI 裁剪
        from backend.services.rule_engine.utils import get_temp_image_path

        roi_paths: List[str] = []
        roi_bboxes: List[List[float]] = []
        first_size: Optional[tuple] = None
        for det in sorted_dets:
            bbox = det.get("bbox", [])
            if not _is_valid_bbox(bbox):
                continue
            x1, y1, x2, y2 = (float(v) for v in bbox)

            # 应用 padding（外扩）：padding 表示总膨胀比例
            # 例 bbox=50, padding=0.2 → 总尺寸 60 (每边 +5 = 50*0.2/2)
            if padding > 0:
                bw = x2 - x1
                bh = y2 - y1
                dx = bw * padding / 2.0
                dy = bh * padding / 2.0
                x1 -= dx
                y1 -= dy
                x2 += dx
                y2 += dy

            # 裁剪到图像边界
            ix1 = max(0, int(x1))
            iy1 = max(0, int(y1))
            ix2 = min(orig_w, int(x2))
            iy2 = min(orig_h, int(y2))

            cw = ix2 - ix1
            ch = iy2 - iy1
            if cw < min_size or ch < min_size:
                continue

            cropped = img[iy1:iy2, ix1:ix2]
            if cropped.size == 0:
                continue

            output_path = get_temp_image_path(
                f"{self.node_id}_roi{len(roi_paths)}", image_path
            )
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, cropped)
            roi_paths.append(output_path)
            roi_bboxes.append([ix1, iy1, ix2, iy2])
            if first_size is None:
                first_size = (cw, ch)

        if not roi_paths:
            return {
                "roi": {"path": image_path},
                "roi_count": 0,
                "width": orig_w,
                "height": orig_h,
            }

        first_w, first_h = first_size
        return {
            "roi": {"path": roi_paths[0]},
            "roi_count": len(roi_paths),
            "width": first_w,
            "height": first_h,
            "_all_rois": roi_paths,  # 附加字段，便于调试
            "_all_bboxes": roi_bboxes,
        }
