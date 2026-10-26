# -*- coding: utf-8 -*-
"""Pydantic 模型 - API 请求/响应数据模型。

用于请求验证和响应序列化。
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ============ Atlas Schemas ============

class AtlasBase(BaseModel):
    """图集基础模型。"""
    name: str
    description: Optional[str] = None


class AtlasCreate(AtlasBase):
    """创建图集请求。"""
    pass


class AtlasUpdate(BaseModel):
    """更新图集请求。"""
    name: Optional[str] = None
    description: Optional[str] = None


class AtlasResponse(AtlasBase):
    """图集响应。"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Image Schemas ============

class ImageBase(BaseModel):
    """图片基础模型。"""
    file_path: str
    directory: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ImageResponse(ImageBase):
    """图片响应。"""
    id: int
    atlas_id: int
    annotated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Category Schemas ============

class CategoryBase(BaseModel):
    """类别基础模型。"""
    name: str
    color: str = "#FF0000"
    is_directory: bool = False  # True=目录, False=标签
    parent_id: Optional[int] = None  # 父节点ID，支持嵌套


class CategoryCreate(CategoryBase):
    """创建类别请求。"""
    pass


class CategoryUpdate(BaseModel):
    """更新类别请求。"""
    name: Optional[str] = None
    color: Optional[str] = None
    is_directory: Optional[bool] = None
    parent_id: Optional[int] = None


class CategoryResponse(BaseModel):
    """类别响应。"""
    id: int
    name: str
    color: str
    is_directory: bool
    parent_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class CategoryExportNode(BaseModel):
    """类别导出节点（递归）。"""
    name: str
    color: str
    is_directory: bool
    children: List["CategoryExportNode"] = []

CategoryExportNode.model_rebuild()


class CategoryImportPayload(BaseModel):
    """类别导入请求。"""
    version: int = 1
    categories: List[CategoryExportNode]


class CategoryImportResult(BaseModel):
    """类别导入结果。"""
    created: int = 0
    skipped: int = 0
    errors: List[str] = []


# ============ Annotation Schemas ============

class AnnotationBase(BaseModel):
    """标注基础模型。"""
    category_id: int
    bbox: List[float]  # [x, y, w, h]


class AnnotationCreate(AnnotationBase):
    """创建标注请求。"""
    image_id: int


class AnnotationUpdate(BaseModel):
    """更新标注请求。"""
    category_id: Optional[int] = None
    bbox: Optional[List[float]] = None


class AnnotationResponse(AnnotationBase):
    """标注响应。"""
    id: int
    image_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Model Schemas ============

class ModelBase(BaseModel):
    """模型基础模型。"""
    name: str
    version: Optional[str] = None
    pretrained_model: Optional[str] = "yolov8n.pt"
    file_path: Optional[str] = None
    format: Optional[str] = "yolo_pt"  # 当前格式
    device_preference: Optional[str] = "auto"  # 设备偏好
    precision: Optional[str] = "fp32"  # 推理精度


class ModelFileResponse(BaseModel):
    """模型文件响应。"""
    id: int
    model_id: int
    format: str
    file_path: str
    file_size: Optional[int]
    precision: str
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelCreate(ModelBase):
    """创建模型请求。"""
    atlas_id: Optional[int] = None


class ModelUpdate(BaseModel):
    """更新模型请求。"""
    name: Optional[str] = None
    version: Optional[str] = None
    pretrained_model: Optional[str] = None
    file_path: Optional[str] = None
    metrics: Optional[dict] = None
    format: Optional[str] = None
    available_formats: Optional[List[str]] = None
    device_preference: Optional[str] = None
    precision: Optional[str] = None
    input_shape: Optional[str] = None


class ModelResponse(ModelBase):
    """模型响应。"""
    id: int
    atlas_id: Optional[int]
    metrics: Optional[dict]
    is_best: bool
    created_at: datetime
    files: List[ModelFileResponse] = []
    input_shape: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============ Model Export Schemas ============

class ModelExportRequest(BaseModel):
    """模型导出请求。"""
    target_format: str  # "onnx", "openvino", "tensorrt"
    half: bool = False  # 是否导出为 FP16
    device: str = "cpu"  # 导出设备


class ModelExportResponse(BaseModel):
    """模型导出响应。"""
    success: bool
    output_path: str
    file_size: int
    available_formats: List[str]
    target_format: str
    half: bool


# ============ TrainingJob Schemas ============

class TrainingJobBase(BaseModel):
    """训练任务基础模型。"""
    model_id: int
    atlas_id: int


class TrainingJobCreate(TrainingJobBase):
    """创建训练任务请求。"""
    config: Optional[dict] = None


class TrainingJobResponse(TrainingJobBase):
    """训练任务响应。"""
    id: int
    status: str
    config: Optional[dict]
    current_step: int
    total_steps: Optional[int]
    metrics: Optional[dict]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============ WebSocket 消息 ============

class TrainingUpdate(BaseModel):
    """训练状态更新消息。"""
    type: str = "training_update"
    data: dict


# ============ RuleEngine Schemas ============

class NodeDefinition(BaseModel):
    """节点定义 - 描述节点的结构和配置选项。"""
    type: str  # 节点类型唯一标识
    category: str  # 节点分类: trigger/condition/action/logic/tool
    label: str  # 显示名称
    description: Optional[str] = None
    icon: Optional[str] = None  # 图标名称
    inputs: List[dict] = []  # 输入端口定义 [{name, type, label}]
    outputs: List[dict] = []  # 输出端口定义 [{name, type, label}]
    config_schema: dict = {}  # 节点配置项定义


class GraphNode(BaseModel):
    """规则图中的节点。"""
    id: str
    type: str
    position: dict  # {x, y}
    data: dict = {}  # 节点配置数据


class GraphEdge(BaseModel):
    """规则图中的连接边。"""
    id: str
    source: str  # 源节点ID
    target: str  # 目标节点ID
    source_handle: Optional[str] = None  # 源端口
    target_handle: Optional[str] = None  # 目标端口


class RuleGraphBase(BaseModel):
    """规则图基础模型。"""
    name: str
    description: Optional[str] = None
    nodes_json: str = "[]"
    edges_json: str = "[]"
    variables_json: Optional[str] = None
    version: str = "1.0.0"
    is_active: bool = False
    cron_expression: Optional[str] = None  # 定时触发 Cron 表达式
    thumbnail: Optional[str] = None
    webhook_api_key: Optional[str] = None  # Webhook API Key（仅在响应中显示，创建后不可读取）


class RuleGraphCreate(RuleGraphBase):
    """创建规则图请求。"""
    pass


class RuleGraphUpdate(BaseModel):
    """更新规则图请求。"""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes_json: Optional[str] = None
    edges_json: Optional[str] = None
    variables_json: Optional[str] = None
    is_active: Optional[bool] = None
    cron_expression: Optional[str] = None
    thumbnail: Optional[str] = None


class RuleGraphResponse(RuleGraphBase):
    """规则图响应。"""
    id: int
    # 兼容历史数据：早期插入的规则图可能没有时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionHistoryResponse(BaseModel):
    """执行历史响应。"""
    id: int
    graph_id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    trigger_type: Optional[str]
    result_json: Optional[str]
    logs_json: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ExecutionTrigger(BaseModel):
    """执行触发请求。"""
    graph_id: int
    trigger_type: str = "manual"  # yolo/timer/manual/http
    trigger_data: Optional[dict] = None
    # 延后启动: 为 True 时只创建执行记录并返回 execution_id,
    # 由前端连上 WebSocket 后再调用 /executions/{execution_id}/start 真正触发。
    # 用于消除「先 POST 执行再连 WS」的竞态窗口。
    defer_start: bool = False


class ExecutionResponse(BaseModel):
    """执行结果响应。"""
    execution_id: int
    status: str
    result: Optional[dict] = None
