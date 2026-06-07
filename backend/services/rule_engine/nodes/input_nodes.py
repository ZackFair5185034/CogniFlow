# -*- coding: utf-8 -*-
"""输入类节点 - 外部数据采集节点。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

节点分类: input (#4CFF4C)
"""
import asyncio
from typing import Any, Dict, Optional, Tuple

from backend.services.rule_engine.models import NodeDefinition, NodeCategory, PortDefinition, PortType, ConfigSchemaProperty, Region
from typing import Dict
from .base import BaseExecutor


class ImageCaptureNode(BaseExecutor):
    """图片采集节点 - 从文件或 URL 采集单张图片。

    配置项:
        source: str - 图片路径或 URL
    """

    node_type = "image_capture"
    category = NodeCategory.INPUT
    display_name = "图片输入"
    description = "从文件路径或 URL 采集单张图片"
    icon = "image"
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
                "image": PortDefinition(
                    name="图片",
                    type=PortType.IMAGE.value,
                    description="采集到的图片数据"
                ),
                "width": PortDefinition(
                    name="宽度",
                    type="INT",
                    description="图片宽度（像素）"
                ),
                "height": PortDefinition(
                    name="高度",
                    type="INT",
                    description="图片高度（像素）"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "source": ConfigSchemaProperty(
                type="string",
                title="图片路径",
                description="本地文件路径或 HTTP/HTTPS URL",
                default="",
                widget="file-picker",
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
        source = params.get("source", "")

        if not source:
            return {"error": "图片源不能为空"}

        try:
            # 实际图片读取逻辑
            from PIL import Image
            import os

            if source.startswith(("http://", "https://")):
                # 从 URL 读取
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(source)
                    response.raise_for_status()
                    image_data = response.content
            else:
                # 从本地文件读取
                if not os.path.exists(source):
                    return {"error": f"文件不存在: {source}"}
                with open(source, "rb") as f:
                    image_data = f.read()

            # 获取图片尺寸
            from io import BytesIO
            img = Image.open(BytesIO(image_data))
            width, height = img.size

            return {
                "image": image_data,
                "width": width,
                "height": height,
                "path": source,
            }
        except Exception as e:
            return {"error": f"图片读取失败: {str(e)}"}


class VideoCaptureNode(BaseExecutor):
    """视频流采集节点 - 从摄像头或视频文件采集帧。

    配置项:
        source: str - 视频源（如 /dev/video0 或视频文件路径）
        fps: int - 采集帧率
    """

    node_type = "video_capture"
    category = NodeCategory.INPUT
    display_name = "视频输入"
    description = "从摄像头或视频文件持续采集帧"
    icon = "video"
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
                "image": PortDefinition(
                    name="帧图片",
                    type=PortType.IMAGE.value,
                    description="采集到的视频帧"
                ),
                "frame_id": PortDefinition(
                    name="帧序号",
                    type="INT",
                    description="帧序号"
                ),
                "timestamp": PortDefinition(
                    name="时间戳",
                    type="FLOAT",
                    description="时间戳（秒）"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "source": ConfigSchemaProperty(
                type="string",
                title="视频源",
                description="/dev/video0 或视频文件路径",
                default="video0",
                widget="text",
            ),
            "fps": ConfigSchemaProperty(
                type="number",
                title="帧率",
                description="每秒采集帧数",
                default=30,
                minimum=1,
                maximum=120,
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
        source = params.get("source", "video0")
        fps = params.get("fps", 30)

        # TODO: 实现实际视频帧读取
        # 当前为占位实现
        frame_count = context.node_results.get("_frame_count", 0) + 1

        return {
            "image": None,  # 占位
            "frame_id": frame_count,
            "timestamp": frame_count / fps if fps > 0 else 0,
        }


class ScreenCaptureNode(BaseExecutor):
    """屏幕采集节点 - 截取屏幕或窗口内容。

    配置项:
        region: dict - 采集区域 {x, y, width, height}，None 表示全屏
        source: str - 采集源 (screen/window)
    """

    node_type = "screen_capture"
    category = NodeCategory.INPUT
    display_name = "屏幕截图"
    description = "截取屏幕或窗口内容"
    icon = "monitor"
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
                "image": PortDefinition(
                    name="截图",
                    type=PortType.IMAGE.value,
                    description="屏幕截图"
                ),
                "region": PortDefinition(
                    name="区域",
                    type="OBJECT",
                    description="采集区域信息",
                    required=False
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "source": ConfigSchemaProperty(
                type="string",
                title="采集源",
                description="screen(全屏) 或 window(窗口)",
                default="screen",
                enum=["screen", "window"],
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
        raw_region = params.get("region", None)

        # TODO: 对接屏幕截图服务
        # from engine.core.data_input.capture import ScreenCapturer
        # capturer = ScreenCapturer()
        # image_data = await capturer.capture(region=raw_region)

        # region 输出遵循 Region Pydantic model 序列化格式（dict），
        # 下游节点可通过 Region.model_validate() 安全解析。
        serialized_region = None
        if isinstance(raw_region, dict):
            try:
                serialized_region = Region.model_validate(raw_region).model_dump()
            except Exception:
                # 配置数据不合法时透传原始值，避免阻塞屏幕采集主流程
                serialized_region = raw_region
        elif isinstance(raw_region, Region):
            serialized_region = raw_region.model_dump()
        else:
            serialized_region = raw_region  # None 或其他类型直接透传

        return {
            "image": None,  # 占位
            "region": serialized_region,
        }
