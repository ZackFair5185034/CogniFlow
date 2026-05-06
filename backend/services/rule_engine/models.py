# -*- coding: utf-8 -*-
"""规则引擎数据模型 - Pydantic 模型定义。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PortType(str, Enum):
    """端口数据类型枚举。"""
    IMAGE = "IMAGE"
    BBOX = "BBOX"
    MASK = "MASK"
    SCORES = "SCORES"
    TRIGGER = "TRIGGER"
    CONTROL = "CONTROL"
    MODEL = "MODEL"
    ANY = "ANY"


class PortDefinition(BaseModel):
    """端口定义 - 描述节点的输入或输出端口。"""
    name: str = Field(..., description="端口显示名称")
    type: str = Field(..., description="数据类型：IMAGE/BBOX/MASK/SCORES/TRIGGER/CONTROL/MODEL/ANY")
    required: bool = Field(True, description="是否为必需端口")
    default: Any = Field(None, description="默认值（未连接时使用）")
    description: str = Field("", description="端口功能描述")


class NodeCategory(str, Enum):
    """节点分类枚举 - 按设计文档的 6 大类。"""
    INPUT = "input"       # 输入类：ImageCapture, VideoCapture, ScreenCapture
    DETECTION = "detection"  # 检测类：YOLOModel, ObjectDetector
    PROCESSING = "processing"  # 处理类：CategoryEncode, Filter, Tracker
    ACTION = "action"     # 动作类：MouseClick, KeyPress, Notification
    LOGIC = "logic"      # 逻辑类：Condition, Timer, Counter, Switch
    OUTPUT = "output"    # 输出类：ActionOutput, SaveResult


class CategoryInfo(BaseModel):
    """节点类别信息。"""
    name: str
    display_name: str
    color: str
    icon: str

    # 类别元数据
    description: str = ""


class ConfigSchemaProperty(BaseModel):
    """节点配置项的 schema 定义。"""
    type: str = Field(..., description="类型：string/number/integer/boolean")
    title: str = Field(..., description="前端显示名称")
    description: str = Field("", description="配置项说明")
    default: Any = Field(None, description="默认值")
    minimum: Optional[float] = Field(None, description="最小值（number/integer）")
    maximum: Optional[float] = Field(None, description="最大值（number/integer）")
    step: Optional[float] = Field(None, description="步进值（slider）")
    enum: Optional[List[Any]] = Field(None, description="枚举选项（dropdown）")
    widget: str = Field("text", description="控件类型：text/number/slider/dropdown/model-select/checkbox/file-path/textarea/code")
    required: bool = Field(False, description="是否为必填项")


class NodeDefinition(BaseModel):
    """节点定义 - 描述节点类型的元信息。"""
    type: str = Field(..., description="节点类型标识，如 'yolo_model'")
    category: str = Field(..., description="所属类别：input/detection/processing/action/logic/output")
    display_name: str = Field(..., description="前端显示名称")
    description: str = Field("", description="节点功能描述")
    icon: str = Field("circle", description="图标名称")
    color: str = Field("#7D7D7D", description="节点颜色（十六进制）")
    inputs: Dict[str, PortDefinition] = Field(default_factory=dict, description="输入端口定义")
    outputs: Dict[str, PortDefinition] = Field(default_factory=dict, description="输出端口定义")
    config_schema: Dict[str, ConfigSchemaProperty] = Field(default_factory=dict, description="节点可配置参数定义")


class NodeDefinitionsResponse(BaseModel):
    """节点定义响应（API 返回格式）。"""
    nodes: List[NodeDefinition]
    categories: List[CategoryInfo]


class ExecutionContextData(BaseModel):
    """执行上下文数据模型（用于 WebSocket 传输等）。"""
    execution_id: int
    trigger_type: str
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    node_count: int = 0


# 类别颜色常量（供前端使用）
CATEGORY_COLORS: Dict[str, str] = {
    NodeCategory.INPUT.value: "#4CFF4C",
    NodeCategory.DETECTION.value: "#00f0FF",
    NodeCategory.PROCESSING.value: "#FFFF4C",
    NodeCategory.ACTION.value: "#FF7F4C",
    NodeCategory.LOGIC.value: "#DC4FDC",
    NodeCategory.OUTPUT.value: "#FF4C4C",
}

# 类别显示信息
CATEGORIES: List[CategoryInfo] = [
    CategoryInfo(
        name=NodeCategory.INPUT.value,
        display_name="输入",
        color=CATEGORY_COLORS[NodeCategory.INPUT.value],
        icon="upload",
        description="外部数据采集节点"
    ),
    CategoryInfo(
        name=NodeCategory.DETECTION.value,
        display_name="检测",
        color=CATEGORY_COLORS[NodeCategory.DETECTION.value],
        icon="radar",
        description="目标检测模型节点"
    ),
    CategoryInfo(
        name=NodeCategory.PROCESSING.value,
        display_name="处理",
        color=CATEGORY_COLORS[NodeCategory.PROCESSING.value],
        icon="process",
        description="数据处理变换节点"
    ),
    CategoryInfo(
        name=NodeCategory.ACTION.value,
        display_name="动作",
        color=CATEGORY_COLORS[NodeCategory.ACTION.value],
        icon="cursor",
        description="外部操作执行节点"
    ),
    CategoryInfo(
        name=NodeCategory.LOGIC.value,
        display_name="逻辑",
        color=CATEGORY_COLORS[NodeCategory.LOGIC.value],
        icon="branch",
        description="流程控制节点"
    ),
    CategoryInfo(
        name=NodeCategory.OUTPUT.value,
        display_name="输出",
        color=CATEGORY_COLORS[NodeCategory.OUTPUT.value],
        icon="download",
        description="结果输出节点"
    ),
]
