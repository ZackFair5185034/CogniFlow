# -*- coding: utf-8 -*-
"""规则引擎节点执行器综合测试 — 节点用法、连接关系、参数配置详解。

本文档同时充当使用指南，每个测试类包含：
- 节点用途说明
- 输入/输出端口定义
- 参数配置说明
- 与其他节点的连接关系
- 典型使用场景

============================================================================
一、节点类型概览
============================================================================

| 类别       | 颜色    | 节点                  | 端口类型                  | 说明               |
|------------|---------|-----------------------|---------------------------|--------------------|
| INPUT      | #4CFF4C | ImageCapture          | IMAGE →                   | 图像采集            |
| INPUT      | #4CFF4C | VideoCapture          | IMAGE →                   | 视频采集            |
| INPUT      | #4CFF4C | ScreenCapture         | IMAGE →                   | 屏幕截图            |
| INPUT      | #4CFF4C | ManualTrigger         | TRIGGER →                 | 手动触发            |
| INPUT      | #4CFF4C | TimerTrigger          | TRIGGER →                 | 定时触发            |
| INPUT      | #4CFF4C | CronTrigger           | TRIGGER →                 | Cron 触发           |
| INPUT      | #4CFF4C | WebhookTrigger        | TRIGGER →                 | Webhook 触发         |
| INPUT      | #4CFF4C | ApiTrigger            | TRIGGER →                 | API 触发            |
| INPUT      | #4CFF4C | YOLOTrigger           | IMAGE →, BOOLEAN+ARRAY    | 检测到目标时触发     |
| DETECTION  | #00f0FF | YOLOModel             | IMAGE → BBOX+SCORES       | YOLO 目标检测        |
| DETECTION  | #00f0FF | ObjectDetector        | IMAGE → ARRAY             | 通用目标检测          |
| PROCESSING | #FFFF4C | ImagePreprocessor     | IMAGE → IMAGE             | 图像预处理            |
| PROCESSING | #FFFF4C | Filter                | ARRAY → ARRAY             | 检测结果过滤          |
| PROCESSING | #FFFF4C | Tracker               | ARRAY → ARRAY             | 目标跟踪（SORT）      |
| PROCESSING | #FFFF4C | CategoryEncode        | ARRAY → ARRAY             | 类别名称/ID 互转      |
| PROCESSING | #FFFF4C | Template              | OBJECT → STRING+OBJECT    | 文本/JSON 模板渲染    |
| PROCESSING | #FFFF4C | MergeDetections       | ARRAY×8 → ARRAY           | 多源检测结果融合      |
| PROCESSING | #FFFF4C | RoiExtract            | IMAGE+ARRAY → IMAGE       | 按 BBOX 裁剪 ROI       |
| ACTION     | #FF7F4C | LogAction             | STRING →                  | 日志输出              |
| ACTION     | #FF7F4C | MouseAction           | BBOX+INT →                | 鼠标操作              |
| ACTION     | #FF7F4C | KeyboardAction        | STRING →                  | 键盘操作              |
| ACTION     | #FF7F4C | HttpRequestAction     | OBJECT →                  | HTTP 请求             |
| ACTION     | #FF7F4C | WaitAction            | -                         | 等待延迟              |
| LOGIC      | #DC4FDC | Branch                | BOOLEAN → ANY             | 条件分支              |
| LOGIC      | #DC4FDC | ParallelBranch        | TRIGGER → CONTROL×N       | 并行分支              |
| LOGIC      | #DC4FDC | Delay                 | -                         | 延时控制              |
| LOGIC      | #DC4FDC | SetVariable           | ANY → OBJECT              | 变量赋值              |
| LOGIC      | #DC4FDC | Counter               | TRIGGER → INT             | 计数循环              |
| LOGIC      | #DC4FDC | ObjectExistsCondition | ARRAY → BOOLEAN           | 检测目标存在判断       |
| LOGIC      | #DC4FDC | ConfidenceThreshold   | ARRAY → BOOLEAN+FLOAT     | 置信度阈值判断         |
| LOGIC      | #DC4FDC | VariableCondition     | - → BOOLEAN+ANY           | 变量条件判断          |
| OUTPUT     | #FF4C4C | SaveResult            | ANY →                     | 结果保存              |
| OUTPUT     | #FF4C4C | Notification          | STRING →                  | 桌面通知              |
| OUTPUT     | #FF4C4C | Display               | IMAGE →                   | 图像显示              |

============================================================================
二、典型连接模式（节点间数据流）
============================================================================

=== 模式 1: 基础检测流水线 ===
  ImageCapture → YOLOModel → Filter → SaveResult

  数据流:
    {path: str}         {bboxes, scores,      {filtered, count}  ->  保存到文件
                          class_ids, count}
  说明: 采集图片 → 检测目标 → 过滤低置信度 → 保存结果

=== 模式 2: 预处理增强流水线 ===
  ImageCapture → ImagePreprocessor → YOLOModel → Tracker → Notification

  数据流:
    {path} → resize/crop/normalize → 检测 → 跟踪ID分配 → 通知

  说明: 图片先缩放/裁剪再检测，跟踪器给每个目标分配稳定 ID，
        多次检测间保持目标身份一致

=== 模式 3: 条件触发流水线 ===
  TimerTrigger → YOLOModel → Branch
                              ├→ true  → MouseAction (点击检测到的目标)
                              └→ false → LogAction ("未检测到目标")

  说明: 定时触发检测流程，检测到目标则执行鼠标点击，
        否则仅记录日志

=== 模式 4: YOLO 触发模式 ===
  YOLOTrigger → ObjectExistsCondition → Notification
                                         └→ (满足条件时发送通知)

  说明: YOLO 触发器持续检测视频流，当检测到指定类别目标时
        发送桌面通知。ObjectExistsCondition 可进一步过滤。

=== 模式 5: 多模型并行检测 ===
  ImageCapture ─┬→ YOLOModel (人头检测) ─┐
                │                        ├→ 手动合并（需 merge_detections 节点）
                └→ YOLOModel (车辆检测) ─┘

  说明: 同一张图片送入多个模型检测，结果待合并后统一处理。
        目前 merge_detections 节点尚在规划中。

============================================================================
三、节点参数配置速查
============================================================================

- ImageCapture:     {path: string, interval: float}
- YOLOModel:        {model_id: string, confidence: float[0-1], iou_threshold: float[0-1],
                     max_detections: int[1-1000], device: auto|cuda|cpu}
- ObjectDetector:   {model_type: yolo|ssd|mtcnn, model_path: string, confidence: float[0-1]}
- ImagePreprocessor:{operation: resize|crop|normalize, width: int[16-4096], height: int[16-4096]}
- Filter:           {filter_by: class|confidence|count, min_confidence: float[0-1],
                     max_count: int[1-1000]}
- Tracker:          {max_age: int[1-100], min_hits: int[1-10], iou_threshold: float[0.1-0.9]}
- CategoryEncode:   {class_mapping: string (格式: "name:id,name:id")}
- Branch:           {condition_input: string}
- Delay:            {delay_seconds: float}
- LogAction:        {message: string, level: info|warn|error}
- MouseAction:      {action: click|move|double_click, button: left|right|middle}
- Notification:     {title: string, message: string, type: success|warning|info|error}
- SetVariable:      {variable_name: string, value: any}
- Counter:          {start: int, end: int, step: int}
- ObjectExistsCondition: {target_class: string, min_count: int}
- ConfidenceThreshold:   {threshold: float[0-1], operator: gt|gte|lt|lte}
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Any, Dict

import sys
sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.nodes.base import BaseExecutor, ExecutionContext
from backend.services.rule_engine.models import NodeCategory, NodeDefinition, PortDefinition
from backend.services.rule_engine.model_cache import ModelCache


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_model_cache():
    """每个测试前重置模型缓存，避免测试间相互影响。"""
    ModelCache.get_instance().clear()
    yield


@pytest.fixture
def mock_context():
    """创建模拟执行上下文。

    模拟 ExecutionContext 中的常用字段：
    - execution_id: 执行记录 ID
    - trigger_type: 触发类型 (manual/timer/webhook)
    - trigger_data: 触发时携带的数据
    - node_results: 节点输出缓存，node_id -> output_data
    - variables: 规则变量
    """
    ctx = Mock(spec=ExecutionContext)
    ctx.execution_id = 1
    ctx.trigger_type = "manual"
    ctx.trigger_data = {}
    ctx.node_results = {}
    ctx.node_status = {}
    ctx.variables = {"counter": 0, "threshold": 0.5}
    ctx.config = {}
    ctx.cancelled = False
    ctx.ws_manager = None
    return ctx


@pytest.fixture
def sample_image_dict():
    """模拟图片输入 - 字典格式。

    这是 ImageCapture 节点的标准输出格式，
    也是大多数接受 IMAGE 类型输入的节点的输入格式。
    """
    return {"path": "/tmp/test_image.jpg", "width": 640, "height": 480}


@pytest.fixture
def sample_image_str():
    """模拟图片输入 - 字符串格式。

    部分节点也接受纯字符串作为图片路径。
    """
    return "/tmp/test_image.jpg"


@pytest.fixture
def sample_detections():
    """模拟 YOLO 检测结果列表。

    格式与 YOLOModelNode / ObjectDetectorNode 的输出一致。
    每个检测项包含:
    - bbox: [x1, y1, x2, y2] - 检测框坐标
    - confidence: float - 置信度
    - class_id: int - 类别 ID
    - class_name: str - 类别名称
    """
    return [
        {"bbox": [50, 50, 150, 200], "confidence": 0.95, "class_id": 0, "class_name": "person"},
        {"bbox": [100, 100, 300, 250], "confidence": 0.87, "class_id": 1, "class_name": "car"},
        {"bbox": [200, 50, 280, 180], "confidence": 0.45, "class_id": 0, "class_name": "person"},
        {"bbox": [400, 300, 500, 400], "confidence": 0.92, "class_id": 2, "class_name": "dog"},
    ]


@pytest.fixture
def mock_yolo_inference():
    """模拟 YOLO 推理函数。

    模拟 backend.routers.yolo_training 中的
    load_yolo_model() 和 inference_yolo() 函数。
    """

    def _make_mock(detections=None):
        mock_model = MagicMock()
        mock_model.__class__.__name__ = "YOLO"

        mock_inference = MagicMock(return_value={
            "detections": detections or [
                {"bbox": [50, 50, 150, 200], "confidence": 0.95, "class_id": 0, "class_name": "person"},
            ],
            "image_width": 640,
            "image_height": 480,
            "inference_time": 0.05,
        })

        return mock_model, mock_inference

    return _make_mock


@pytest.fixture
def mock_cv2():
    """模拟 OpenCV 图像处理函数。

    模拟 cv2.imread, cv2.resize, cv2.imwrite。
    """

    def _make_mock():
        import numpy as np
        mock_img = np.zeros((480, 640, 3), dtype=np.uint8)

        with patch('cv2.imread', return_value=mock_img) as mock_imread, \
             patch('cv2.resize', return_value=mock_img[:320, :320]) as mock_resize, \
             patch('cv2.imwrite', return_value=True) as mock_imwrite, \
             patch('os.makedirs', return_value=None):
            yield

    return _make_mock


# ============================================================================
# 0. ModelCache 测试
# ============================================================================

class TestModelCache:
    """ModelCache — LRU 模型缓存单例。

    用途: 缓存已加载的 YOLO/ONNX 模型实例，避免同一模型在规则图的
          多个节点或多个执行批次中被重复加载。

    配置:
        max_size (默认 5): 最多缓存几个模型，超出淘汰最久未使用的
        ttl (默认 600秒):  缓存过期时间

    连接关系: NodeRegistry → 检测类节点 (YOLOModel / ObjectDetector / YOLOTrigger)
    依赖方向: 检测节点内部使用，对画布用户透明
    """

    def test_singleton_pattern(self):
        """验证 ModelCache 是单例，全局只有一个实例。"""
        cache1 = ModelCache.get_instance()
        cache2 = ModelCache.get_instance()
        assert cache1 is cache2

    def test_put_and_get(self):
        """基本存取：put 存入后可 get 取出。"""
        cache = ModelCache.get_instance()
        cache.put("model_a", "fake_model_object")
        result = cache.get("model_a")
        assert result == "fake_model_object"

    def test_get_missing(self):
        """取未缓存的 key 返回 None。"""
        cache = ModelCache.get_instance()
        assert cache.get("nonexistent") is None

    def test_get_or_load_caches_result(self):
        """get_or_load: 首次调用执行 loader 并缓存，再次调用直接返回。"""
        cache = ModelCache.get_instance()
        call_count = 0

        def loader():
            nonlocal call_count
            call_count += 1
            return "loaded_model"

        # 第一次应调用 loader
        result1 = cache.get_or_load("key1", loader)
        assert result1 == "loaded_model"
        assert call_count == 1

        # 第二次不应调用 loader
        result2 = cache.get_or_load("key1", loader)
        assert result2 == "loaded_model"
        assert call_count == 1  # 未再调用

    def test_lru_eviction(self):
        """LRU 淘汰：超过 max_size 时淘汰最久未访问的 key。"""
        cache = ModelCache(max_size=2, ttl=600)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # 应淘汰 a

        assert cache.get("a") is None  # 已淘汰
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_access_refreshes(self):
        """访问 key 会更新其 LRU 位置，避免被淘汰。"""
        cache = ModelCache(max_size=2, ttl=600)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")          # 访问 a，使其变为最近使用
        cache.put("c", 3)       # 应淘汰 b（a 被访问过）

        assert cache.get("a") == 1
        assert cache.get("b") is None  # 被淘汰
        assert cache.get("c") == 3

    def test_clear(self):
        """clear 清空所有缓存。"""
        cache = ModelCache.get_instance()
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0
        assert cache.get("a") is None

    def test_remove(self):
        """remove 主动移除指定 key。"""
        cache = ModelCache.get_instance()
        cache.put("a", 1)
        cache.remove("a")
        assert cache.get("a") is None

    def test_keys(self):
        """keys 返回当前所有缓存的 key 列表。"""
        cache = ModelCache.get_instance()
        cache.put("x", 1)
        cache.put("y", 2)
        assert set(cache.keys()) == {"x", "y"}


# ============================================================================
# 1. 检测类节点
# ============================================================================

class TestYOLOModelNode:
    """YOLOModelNode — YOLO 目标检测节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    接收一张图片，使用 YOLO 模型检测其中的目标。
    输出检测框、置信度、类别 ID/名称、检测数量。

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        image (IMAGE, 必需): 待检测的图片
            - 字典格式: {"path": "/图片/路径.jpg"}
            - 字符串格式: "/图片/路径.jpg"

    输出:
        bboxes     (BBOX):   检测框列表 [[x1,y1,x2,y2], ...]
        scores     (SCORES): 各框置信度 [0.95, 0.87, ...]
        class_ids  (ARRAY):  类别 ID 列表 [0, 1, ...]
        class_names (ARRAY): 类别名称列表 ["person", "car", ...]
        count      (INT):    检测到的目标数量

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    model_id (string, 必需):     模型标识（数据库中的模型 ID）
    confidence (float, 0-1):     置信度阈值，默认 0.5
    iou_threshold (float, 0-1):  NMS 的 IOU 阈值，默认 0.45
    max_detections (int, 1-1000):每图最大检测数，默认 300
    device (auto|cuda|cpu):      推理设备，默认 auto

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    上游: ImageCapture / VideoCapture / ScreenCapture / ImagePreprocessor
    下游: Filter / Tracker / Branch / ObjectExistsCondition / SaveResult

    完整链:
      ImageCapture → YOLOModel → Filter → Tracker → Notification
      采集        → 检测      → 过滤   → 跟踪    → 通知
    """

    def test_node_type_and_category(self):
        """节点类型标识为 yolo_model，类别为 DETECTION。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        defn = node.get_definition()
        assert defn.type == "yolo_model"
        assert defn.category == NodeCategory.DETECTION.value

    def test_definition_has_ports(self):
        """定义中包含输入端口 (image) 和 5 个输出端口。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        defn = node.get_definition()
        assert "image" in defn.inputs
        assert all(p in defn.outputs for p in ["bboxes", "scores", "class_ids", "class_names", "count"])

    def test_validate_inputs_missing_image(self):
        """缺少 image 输入时校验不通过。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        valid, err = node.validate_inputs({})
        assert valid is False
        assert err is not None

    def test_validate_inputs_valid(self):
        """提供 image 输入时校验通过。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        valid, err = node.validate_inputs({"image": "/tmp/test.jpg"})
        assert valid is True

    def test_execute_no_model_id(self):
        """未配置 model_id 或 model_path 时返回错误。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        node.config = {"params": {}}
        result = asyncio.run(node.execute({"image": "/tmp/test.jpg"}, Mock()))
        assert "error" in result
        assert "model_id" in result["error"]

    def test_execute_parse_image_input_dict(self, mock_context):
        """image 为字典格式 {path: str} 时正常解析。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        node.config = {"params": {"model_path": "/models/yolov8n.pt"}}
        with patch('backend.routers.yolo_training.load_yolo_model') as mock_load, \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_infer.return_value = {
                "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9, "class_id": 0, "class_name": "person"}],
            }
            result = asyncio.run(node.execute({"image": {"path": "/tmp/test.jpg"}}, mock_context))
        assert "bboxes" in result
        assert result["count"] == 1

    def test_execute_parse_image_input_str(self, mock_context):
        """image 为字符串格式时正常解析。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        node.config = {"params": {"model_path": "/models/yolov8n.pt"}}
        with patch('backend.routers.yolo_training.load_yolo_model') as mock_load, \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_infer.return_value = {
                "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9, "class_id": 0, "class_name": "person"}],
            }
            result = asyncio.run(node.execute({"image": "/tmp/test.jpg"}, mock_context))
        assert "bboxes" in result

    def test_execute_model_cache_integration(self, mock_context):
        """同一模型路径多次执行应命中缓存，不重复调用 load_yolo_model。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        cache = ModelCache.get_instance()

        node1 = YOLOModelNode(node_id="node_a", config={"params": {"model_path": "/models/yolo.pt"}})
        node2 = YOLOModelNode(node_id="node_b", config={"params": {"model_path": "/models/yolo.pt"}})

        with patch('backend.routers.yolo_training.load_yolo_model') as mock_load, \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_model = MagicMock()
            mock_load.return_value = mock_model
            mock_infer.return_value = {"detections": []}

            # 第一次执行，应调用 load_yolo_model
            asyncio.run(node1.execute({"image": "/tmp/img.jpg"}, mock_context))
            assert mock_load.call_count == 1

            # 第二次执行（同一模型路径），应命中缓存
            asyncio.run(node2.execute({"image": "/tmp/img.jpg"}, mock_context))
            assert mock_load.call_count == 1  # 未再调用

    def test_execute_empty_image_path(self, mock_context):
        """图片路径为空时返回错误。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        node.config = {"params": {"model_path": "/model.pt"}}
        result = asyncio.run(node.execute({"image": {"path": ""}}, mock_context))
        assert "error" in result


class TestObjectDetectorNode:
    """ObjectDetectorNode — 通用目标检测节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    通用检测节点，支持多种模型后端（当前仅实现 YOLO）。
    与 YOLOModelNode 的区别在于输出更简洁，只返回 detections 列表。

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        image (IMAGE, 必需): 待检测图片

    输出:
        detections (ARRAY): 检测结果列表
            [{"bbox": [...], "confidence": 0.95, "class_id": 0, "class_name": "person"}, ...]
        count (INT): 检测数量

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    model_type (dropdown): yolo / ssd / mtcnn，当前仅 yolo 可用
    model_path (string):   模型文件路径
    confidence (slider):   置信度阈值 0-1，默认 0.5

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    上游: ImageCapture / ImagePreprocessor
    下游: Filter / SaveResult

    完整链:
      ImageCapture → ObjectDetector → Filter → SaveResult
    """

    def test_node_type_and_category(self):
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        assert node.get_definition().type == "object_detector"
        assert node.get_definition().category == NodeCategory.DETECTION.value

    def test_validate_inputs_missing_image(self):
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        valid, err = node.validate_inputs({})
        assert valid is False

    def test_validate_inputs_valid(self):
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        valid, err = node.validate_inputs({"image": "test.jpg"})
        assert valid is True

    def test_execute_no_model_path(self, mock_context):
        """不提供 model_path 时返回错误。"""
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        node.config = {"params": {"model_type": "yolo"}}
        result = asyncio.run(node.execute({"image": "test.jpg"}, mock_context))
        assert "error" in result

    def test_execute_unsupported_model_type(self, mock_context):
        """非 yolo 的 model_type 返回明确错误。"""
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        node.config = {"params": {"model_type": "ssd", "model_path": "/m.pt"}}
        result = asyncio.run(node.execute({"image": "test.jpg"}, mock_context))
        assert "error" in result
        assert "ssd" in result["error"]

    def test_execute_success(self, mock_context):
        """正常执行返回 detections 和 count。"""
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        node.config = {"params": {"model_path": "/models/yolo.pt"}}

        with patch('backend.routers.yolo_training.load_yolo_model') as mock_load, \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_infer.return_value = {
                "detections": [
                    {"bbox": [0, 0, 10, 10], "confidence": 0.9, "class_id": 0, "class_name": "person"},
                ],
            }
            result = asyncio.run(node.execute({"image": "test.jpg"}, mock_context))

        assert "detections" in result
        assert "count" in result
        assert result["count"] == 1


class TestYOLOTriggerNode:
    """YOLOTriggerNode — YOLO 触发器节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    持续检测图片/视频流中的目标，当检测到指定类别的目标时触发规则。
    归类为 INPUT 类型（颜色绿色），作为规则执行的起点。

    有两种使用方式:
    1. 外部触发: 通过 trigger_data 传入检测结果
    2. 内部检测: 接收图片输入并执行 YOLO 推理

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        image (IMAGE, 可选): 待检测图片

    输出:
        triggered (BOOLEAN):  是否满足触发条件
        detections (ARRAY):   匹配的检测结果列表
        count (INT):          匹配数量

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    model_id (string):       模型标识
    class_names (multiselect): 要检测的目标类别，如 ["person", "car"]
    min_confidence (slider):   最小置信度 0-1，默认 0.5
    max_objects (number):      最大检测数 1-100，默认 10
    device (dropdown):         auto / cuda / cpu

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    下游: Branch / ObjectExistsCondition / Notification

    完整链:
      YOLOTrigger → ObjectExistsCondition → Notification
      (检测到 person) → (存在目标?) → (发送通知)
    """

    def test_node_type_and_category(self):
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
        node = YOLOTriggerNode()
        assert node.get_definition().type == "yolo_trigger"
        # YOLOTrigger 归类为 INPUT，使用绿色风格
        assert node.get_definition().category == NodeCategory.INPUT.value

    def test_execute_trigger_data_detected(self, mock_context):
        """trigger_data 中有检测结果且满足条件时 triggered=true。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
        node = YOLOTriggerNode()
        node.config = {"params": {"class_names": ["person"], "min_confidence": 0.5}}
        mock_context.trigger_data = {
            "detections": [
                {"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"},
                {"bbox": [20, 20, 30, 30], "confidence": 0.82, "class_name": "car"},
            ],
        }

        result = asyncio.run(node.execute({}, mock_context))
        assert result["triggered"] is True
        assert result["count"] >= 1

    def test_execute_trigger_data_not_matching(self, mock_context):
        """检测结果不满足条件时 triggered=false。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
        node = YOLOTriggerNode()
        node.config = {"params": {"class_names": ["dog", "cat"], "min_confidence": 0.5}}
        mock_context.trigger_data = {
            "detections": [
                {"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"},
            ],
        }

        result = asyncio.run(node.execute({}, mock_context))
        assert result["triggered"] is False
        assert result["count"] == 0

    def test_execute_low_confidence_filtered(self, mock_context):
        """置信度低于 min_confidence 的检测被过滤。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
        node = YOLOTriggerNode()
        node.config = {"params": {"class_names": [], "min_confidence": 0.9}}
        mock_context.trigger_data = {
            "detections": [
                {"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"},
                {"bbox": [20, 20, 30, 30], "confidence": 0.45, "class_name": "car"},
            ],
        }

        result = asyncio.run(node.execute({}, mock_context))
        assert result["count"] == 1  # 只保留置信度 0.95 的

    def test_execute_from_image_input(self, mock_context):
        """通过 image 输入执行推理。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
        node = YOLOTriggerNode()
        node.config = {"params": {"model_path": "/models/yolo.pt", "min_confidence": 0.5}}

        with patch('backend.routers.yolo_training.load_yolo_model') as mock_load, \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_infer.return_value = {
                "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9, "class_name": "person"}],
            }
            result = asyncio.run(node.execute({"image": "/tmp/test.jpg"}, mock_context))

        assert "triggered" in result
        assert result["count"] > 0

    def test_execute_saves_to_context(self, mock_context):
        """匹配的检测结果写入 context.node_results。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
        node = YOLOTriggerNode(node_id="trigger_1")
        node.config = {"params": {"class_names": ["person"], "min_confidence": 0.5}}
        mock_context.trigger_data = {
            "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"}],
        }

        asyncio.run(node.execute({}, mock_context))
        key = "trigger_1_detections"
        assert key in mock_context.node_results
        assert len(mock_context.node_results[key]) > 0


# ============================================================================
# 2. 处理类节点
# ============================================================================

class TestImagePreprocessorNode:
    """ImagePreprocessorNode — 图像预处理节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    对图片进行预处理操作，输出处理后的图片路径。
    通常放在 ImageCapture 之后、检测节点之前，用于统一图片尺寸。

    支持三种操作:
    - resize:    缩放至目标宽高 (默认 640x640)
    - crop:      居中裁剪至目标宽高
    - normalize: 归一化像素值 (除以 255) 并可选缩放

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        image (IMAGE, 必需): 待处理图片路径

    输出:
        image  (IMAGE): 处理后图片路径 {"path": "/output.jpg"}
        width  (INT):   处理后图片宽度
        height (INT):   处理后图片高度

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    operation (dropdown): resize / crop / normalize
    width (number):       目标宽度 16-4096，默认 640
    height (number):      目标高度 16-4096，默认 640

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    上游: ImageCapture / VideoCapture
    下游: YOLOModel / ObjectDetector / Display

    完整链:
      ImageCapture → ImagePreprocessor → YOLOModel → Filter → Tracker
      (采集)      → (resize 到 640x640) → (检测)  → (过滤) → (跟踪)
    """

    def test_node_type_and_category(self):
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        assert node.get_definition().type == "image_preprocessor"
        assert node.get_definition().category == NodeCategory.PROCESSING.value

    def test_validate_inputs_missing(self):
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        valid, err = node.validate_inputs({})
        assert valid is False

    def test_validate_inputs_valid(self):
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        valid, err = node.validate_inputs({"image": "/test.jpg"})
        assert valid is True

    def test_execute_parse_dict_input(self, mock_context):
        """接受字典格式输入 {"path": "..."}。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        node.config = {"params": {"operation": "resize", "width": 320, "height": 240}}

        # OpenCV 未安装时返回 fallback
        import numpy as np
        mock_cv2 = MagicMock()
        mock_cv2.imread.side_effect = ImportError
        with patch.dict('sys.modules', {'cv2': mock_cv2}):
            result = asyncio.run(node.execute({"image": {"path": "/test.jpg"}}, mock_context))

        assert "warning" in result or "error" in result

    def test_execute_parse_str_input(self, mock_context):
        """接受字符串格式输入。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        node.config = {"params": {"operation": "resize"}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.side_effect = ImportError
        with patch.dict('sys.modules', {'cv2': mock_cv2}):
            result = asyncio.run(node.execute({"image": "/test.jpg"}, mock_context))

        assert result is not None

    def test_execute_empty_path(self, mock_context):
        """空路径返回错误。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        node.config = {"params": {}}
        result = asyncio.run(node.execute({"image": {"path": ""}}, mock_context))
        assert "error" in result

    def test_execute_unsupported_operation(self, mock_context):
        """不支持的操作类型返回错误。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        import numpy as np
        node = ImagePreprocessorNode()
        node.config = {"params": {"operation": "invalid_op", "width": 640, "height": 480}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
        with patch.dict('sys.modules', {'cv2': mock_cv2}):
            result = asyncio.run(node.execute({"image": "/test.jpg"}, mock_context))
        assert "error" in result
        assert "不支持" in result["error"]

    def test_execute_resize_with_cv2(self, mock_context):
        """OpenCV 可用时执行 resize 操作。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        import numpy as np

        mock_img = np.zeros((480, 640, 3), dtype=np.uint8)

        node = ImagePreprocessorNode(node_id="pre_1")
        node.config = {"params": {"operation": "resize", "width": 320, "height": 240}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.return_value = mock_img
        mock_cv2.resize.return_value = np.zeros((240, 320, 3), dtype=np.uint8)
        mock_cv2.imwrite.return_value = True

        with patch.dict('sys.modules', {'cv2': mock_cv2}), \
             patch('os.makedirs', return_value=None):

            result = asyncio.run(node.execute({"image": "/tmp/test.jpg"}, mock_context))

        assert "image" in result
        assert isinstance(result["image"], dict)
        assert "path" in result["image"]
        assert result["width"] == 320
        assert result["height"] == 240

    def test_execute_crop_with_cv2(self, mock_context):
        """执行 crop 操作。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        import numpy as np

        mock_img = np.zeros((480, 640, 3), dtype=np.uint8)

        node = ImagePreprocessorNode(node_id="pre_2")
        node.config = {"params": {"operation": "crop", "width": 200, "height": 200}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.return_value = mock_img
        mock_cv2.resize.return_value = mock_img[:200, :200]
        mock_cv2.imwrite.return_value = True

        with patch.dict('sys.modules', {'cv2': mock_cv2}), \
             patch('os.makedirs', return_value=None):

            result = asyncio.run(node.execute({"image": "/tmp/test.jpg"}, mock_context))

        assert "image" in result

    def test_execute_normalize_with_cv2(self, mock_context):
        """执行 normalize 操作。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        import numpy as np

        mock_img = np.zeros((480, 640, 3), dtype=np.uint8)

        node = ImagePreprocessorNode(node_id="pre_3")
        node.config = {"params": {"operation": "normalize"}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.return_value = mock_img
        mock_cv2.resize.return_value = mock_img
        mock_cv2.imwrite.return_value = True

        with patch.dict('sys.modules', {'cv2': mock_cv2}), \
             patch('os.makedirs', return_value=None):

            result = asyncio.run(node.execute({"image": "/tmp/test.jpg"}, mock_context))

        assert "image" in result

    def test_fallback_when_cv2_missing(self, mock_context):
        """OpenCV 未安装时返回原始图片（不报错）。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        node.config = {"params": {"operation": "resize"}}

        # cv2 实际未安装，execute 内部的 try/except ImportError 会处理
        result = asyncio.run(node.execute({"image": {"path": "/test.jpg"}}, mock_context))
        # 应返回原始路径 + warning
        assert "image" in result


class TestFilterNode:
    """FilterNode — 检测结果过滤节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    按类别、置信度、数量过滤检测结果。
    通常放在 YOLOModel 或 ObjectDetector 之后。

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        detections (ARRAY, 必需): 检测结果列表

    输出:
        filtered (ARRAY): 过滤后的结果列表
        count (INT):      过滤后数量

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    filter_by (dropdown):   过滤方式 class / confidence / count
    min_confidence (slider):最小置信度 0-1，默认 0.5
    min_count (number):     最少保留数量，默认 0
    max_count (number):     最多保留数量，默认 999

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    上游: YOLOModel / ObjectDetector
    下游: Tracker / SaveResult / Notification

    完整链:
      YOLOModel → Filter → SaveResult
      (检测)    → (只保留 person, 置信度>0.7) → (保存)
    """

    def test_node_type(self):
        from backend.services.rule_engine.nodes.processing_nodes import FilterNode
        node = FilterNode()
        assert node.get_definition().type == "filter"

    def test_filter_by_confidence(self, mock_context, sample_detections):
        """按置信度过滤，去除低置信度检测。"""
        from backend.services.rule_engine.nodes.processing_nodes import FilterNode
        node = FilterNode()
        node.config = {"params": {"filter_by": "confidence", "min_confidence": 0.8}}

        result = asyncio.run(node.execute({"detections": sample_detections}, mock_context))
        # 0.95, 0.87, 0.92 均 >= 0.8，保留 3 个
        assert result["count"] == 3

    def test_filter_by_count(self, mock_context, sample_detections):
        """按数量范围过滤。"""
        from backend.services.rule_engine.nodes.processing_nodes import FilterNode
        node = FilterNode()
        node.config = {"params": {"filter_by": "count", "min_count": 1, "max_count": 2}}

        result = asyncio.run(node.execute({"detections": sample_detections}, mock_context))
        assert result["count"] == 1  # 从 index 1 到 2 取 1 个

    def test_filter_empty_input(self, mock_context):
        """空输入返回空结果，不报错。"""
        from backend.services.rule_engine.nodes.processing_nodes import FilterNode
        node = FilterNode()
        result = asyncio.run(node.execute({"detections": []}, mock_context))
        assert result["count"] == 0

    def test_filter_no_params(self, mock_context, sample_detections):
        """不配置过滤参数时返回所有结果。"""
        from backend.services.rule_engine.nodes.processing_nodes import FilterNode
        node = FilterNode()
        result = asyncio.run(node.execute({"detections": sample_detections}, mock_context))
        assert result["count"] == len(sample_detections)


class TestTrackerNode:
    """TrackerNode — SORT 多目标跟踪节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    使用 SORT 算法（卡尔曼滤波 + IoU 贪心匹配）对检测结果进行多目标跟踪。
    连续帧调用同一节点时，同一目标的 track_id 保持稳定。

    关键行为:
    - 同目标连续帧间保持 track_id 不变
    - 目标丢失超过 max_age 帧后删除轨迹
    - 新目标自动分配新的 track_id
    - 可配置 min_hits 过滤偶然出现的噪点检测
    - 跟踪器状态按 execution_id:node_id 隔离

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        detections (ARRAY, 必需): 检测结果列表
            每项需包含 bbox: [x1, y1, x2, y2]

    输出:
        tracked   (ARRAY): 跟踪结果列表
            [{track_id, bbox, age, hit_count}, ...]
        track_ids (ARRAY): 跟踪 ID 列表 [1, 2, 3, ...]
        count     (INT):   当前跟踪目标数量

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    max_age (slider):     最大丢失帧数 1-100，默认 30
    min_hits (slider):    最少命中次数才输出 1-10，默认 3
    iou_threshold (slider): IoU 关联阈值 0.1-0.9，默认 0.3

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    上游: YOLOModel / ObjectDetector / Filter
    下游: MouseAction / Notification / SaveResult

    完整链:
      ImageCapture → YOLOModel → Filter → Tracker → MouseAction
      (采集)      → (检测)    → (过滤) → (跟踪)  → (点击跟踪目标)
    """

    def test_node_type_and_category(self):
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        node = TrackerNode()
        defn = node.get_definition()
        assert defn.type == "tracker"
        assert defn.category == NodeCategory.PROCESSING.value

    def test_validate_inputs_missing(self):
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        node = TrackerNode()
        valid, err = node.validate_inputs({})
        assert valid is False

    def test_validate_inputs_valid(self):
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        node = TrackerNode()
        valid, err = node.validate_inputs({"detections": []})
        assert valid is True

    def test_execute_empty_detections(self, mock_context):
        """空检测列表返回空跟踪结果。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        from backend.services.rule_engine.nodes.processing_nodes import _tracker_states
        _tracker_states.clear()

        node = TrackerNode(node_id="track_1")
        result = asyncio.run(node.execute({"detections": []}, mock_context))
        assert result["count"] == 0
        assert result["tracked"] == []

    def test_execute_not_list(self, mock_context):
        """非列表输入返回错误。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        node = TrackerNode()
        result = asyncio.run(node.execute({"detections": "not_a_list"}, mock_context))
        assert "error" in result

    def test_execute_first_frame_creates_tracks(self, mock_context):
        """第一帧检测创建新轨迹。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        from backend.services.rule_engine.nodes.processing_nodes import _tracker_states
        _tracker_states.clear()

        node = TrackerNode(node_id="track_a")
        node.config = {"params": {"min_hits": 1}}  # 无需等待直接输出

        detections = [
            {"bbox": [0, 0, 10, 10], "confidence": 0.9},
            {"bbox": [50, 50, 60, 60], "confidence": 0.8},
        ]

        result = asyncio.run(node.execute({"detections": detections}, mock_context))
        assert result["count"] == 2
        assert len(result["track_ids"]) == 2
        assert result["track_ids"][0] != result["track_ids"][1]

    def test_track_id_stable_across_frames(self, mock_context):
        """同一目标在连续帧间 track_id 不变。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        from backend.services.rule_engine.nodes.processing_nodes import _tracker_states
        _tracker_states.clear()

        node = TrackerNode(node_id="track_b")
        node.config = {"params": {"min_hits": 1, "max_age": 10, "iou_threshold": 0.3}}

        # 第1帧: 一个目标
        r1 = asyncio.run(node.execute({
            "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9}]
        }, mock_context))
        track_id = r1["track_ids"][0]

        # 第2帧: 同一目标微小移动
        r2 = asyncio.run(node.execute({
            "detections": [{"bbox": [2, 2, 12, 12], "confidence": 0.9}]
        }, mock_context))
        assert r2["track_ids"][0] == track_id, "同目标应保持 ID"

    def test_new_id_after_track_lost(self, mock_context):
        """目标丢失后再出现分配新 ID。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        from backend.services.rule_engine.nodes.processing_nodes import _tracker_states
        _tracker_states.clear()

        node = TrackerNode(node_id="track_c")
        node.config = {"params": {"min_hits": 1, "max_age": 2}}

        # 第1帧: 出现
        r1 = asyncio.run(node.execute({
            "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9}]
        }, mock_context))
        old_id = r1["track_ids"][0]

        # 第2-4帧: 无检测（丢失）
        asyncio.run(node.execute({"detections": []}, mock_context))
        asyncio.run(node.execute({"detections": []}, mock_context))
        asyncio.run(node.execute({"detections": []}, mock_context))

        # 第5帧: 重新出现（已超过 max_age=2）
        r2 = asyncio.run(node.execute({
            "detections": [{"bbox": [5, 5, 15, 15], "confidence": 0.9}]
        }, mock_context))
        assert r2["track_ids"][0] != old_id, "丢失后应重新分配 ID"

    def test_min_hits_filter(self, mock_context):
        """min_hits 控制输出时机，偶现检测在前几帧被过滤。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        from backend.services.rule_engine.nodes.processing_nodes import _tracker_states
        _tracker_states.clear()

        node = TrackerNode(node_id="track_d")
        node.config = {"params": {"min_hits": 5, "max_age": 10}}

        # 前 3 帧: 目标出现但未满足 min_hits=5
        for _ in range(3):
            result = asyncio.run(node.execute({
                "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9}]
            }, mock_context))

        # min_hits=5 意味着需连续命中 5 帧才输出
        assert result["count"] == 0, "min_hits=5 未满足前不应输出"

        # 继续命中 2 帧
        for _ in range(2):
            result = asyncio.run(node.execute({
                "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9}]
            }, mock_context))

        assert result["count"] == 1, "min_hits=5 满足后应输出"


class TestCategoryEncodeNode:
    """CategoryEncodeNode — 类别编码节点。

    ═══════════════════════════════════════════════════════════════
    用途
    ═══════════════════════════════════════════════════════════════
    在类别名称和 ID 之间建立映射关系。
    有些模型输出名称、有些输出 ID，用此节点统一。

    ═══════════════════════════════════════════════════════════════
    端口
    ═══════════════════════════════════════════════════════════════
    输入:
        class_names (ARRAY, 必需): 类别名称列表

    输出:
        class_ids (ARRAY):  映射后的类别 ID 列表
        class_names (ARRAY): 原始类别名称列表

    ═══════════════════════════════════════════════════════════════
    参数配置
    ═══════════════════════════════════════════════════════════════
    class_mapping (text): 类别映射表
        格式: "name:id,name:id"
        示例: "person:0,car:1,dog:2"

    ═══════════════════════════════════════════════════════════════
    典型连接
    ═══════════════════════════════════════════════════════════════
    上游: YOLOModel (class_names 输出)
    下游: Filter / SaveResult
    """

    def test_node_type(self):
        from backend.services.rule_engine.nodes.processing_nodes import CategoryEncodeNode
        node = CategoryEncodeNode()
        assert node.get_definition().type == "category_encode"

    def test_encode_names_to_ids(self, mock_context):
        from backend.services.rule_engine.nodes.processing_nodes import CategoryEncodeNode
        node = CategoryEncodeNode()
        node.config = {"params": {"class_mapping": {"person": 0, "car": 1, "dog": 2}}}
        result = asyncio.run(node.execute({
            "class_names": ["person", "dog", "person", "car"]
        }, mock_context))
        assert result["class_ids"] == [0, 2, 0, 1]

    def test_unknown_name_returns_minus_one(self, mock_context):
        from backend.services.rule_engine.nodes.processing_nodes import CategoryEncodeNode
        node = CategoryEncodeNode()
        node.config = {"params": {"class_mapping": {"person": 0}}}
        result = asyncio.run(node.execute({
            "class_names": ["person", "unknown"]
        }, mock_context))
        assert result["class_ids"] == [0, -1]

    def test_validate_inputs(self):
        from backend.services.rule_engine.nodes.processing_nodes import CategoryEncodeNode
        node = CategoryEncodeNode()
        valid, err = node.validate_inputs({})
        assert valid is False
        valid, err = node.validate_inputs({"class_names": []})
        assert valid is True


# ============================================================================
# 3. 集成测试 — 节点间数据流验证
# ============================================================================

class TestDetectionToFilterPipeline:
    """集成测试: YOLOModel → Filter 数据流。

     上游(YOLOModel)            下游(Filter)
    ┌─────────────────┐       ┌────────────────┐
    │ bboxes: [...]   │       │ detections     │
    │ scores: [0.95,  │  ──→  │  → filtered    │
    │         0.45]   │       │  → count       │
    │ class_ids: [...]│       └────────────────┘
    │ count: 2        │
    └─────────────────┘

    说明: YOLOModel 的输出 scores/bboxes 等需要组装为
          Filter 的输入格式 [{bbox, confidence, class_name}, ...]。
    """

    def test_filter_removes_low_confidence(self, mock_context):
        """检测结果经 Filter 过滤后低置信度条目被移除。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        from backend.services.rule_engine.nodes.processing_nodes import FilterNode

        # Step 1: 模拟 YOLOModel 执行
        yolo = YOLOModelNode()
        yolo.config = {"params": {"model_path": "/models/yolo.pt"}}

        with patch('backend.routers.yolo_training.load_yolo_model'), \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_infer.return_value = {
                "detections": [
                    {"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_id": 0, "class_name": "person"},
                    {"bbox": [20, 20, 30, 30], "confidence": 0.45, "class_id": 1, "class_name": "car"},
                ],
            }
            yolo_result = asyncio.run(yolo.execute({"image": "/tmp/test.jpg"}, mock_context))

        # Step 2: 组装 YOLO 输出为 Filter 的 detections 输入
        detections = []
        for i in range(yolo_result["count"]):
            detections.append({
                "bbox": yolo_result["bboxes"][i],
                "confidence": yolo_result["scores"][i],
                "class_id": yolo_result["class_ids"][i],
                "class_name": yolo_result["class_names"][i],
            })

        # Step 3: Filter 执行
        filter_node = FilterNode()
        filter_node.config = {"params": {"min_confidence": 0.8}}
        filter_result = asyncio.run(filter_node.execute({"detections": detections}, mock_context))

        assert filter_result["count"] == 1
        assert filter_result["filtered"][0]["class_name"] == "person"


class TestTrackerIntegration:
    """集成测试: YOLOModel → Filter → Tracker 流水线。

    完整流水线模拟:
    1. YOLOModel 检测图片中的目标
    2. Filter 过滤低置信度检测
    3. Tracker 为过滤后的结果分配 track_id
    4. 连续帧调用验证 track_id 稳定性

    参数传递:
      YOLO bboxes → 组装为 detections[{bbox, confidence}] → Filter → Tracker

    使用场景:
      视频流目标检测 + 跟踪，可用于计数、轨迹分析等。
      例如: 检测行人 → 跟踪行人运动轨迹 → 统计人流量。
    """

    def test_full_pipeline(self, mock_context):
        """完整检测-过滤-跟踪流水线。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode, FilterNode
        from backend.services.rule_engine.nodes.processing_nodes import _tracker_states

        # 每帧的模拟检测数据（person 持续出现，car 从第2帧出现）
        frames = [
            [{"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"}],
            [{"bbox": [3, 3, 13, 13], "confidence": 0.93, "class_name": "person"}],
            [{"bbox": [5, 5, 15, 15], "confidence": 0.91, "class_name": "person"}],
        ]

        _tracker_states.clear()
        filter_node = FilterNode()
        filter_node.config = {"params": {"min_confidence": 0.6}}

        tracker_node = TrackerNode(node_id="integration_tracker")
        tracker_node.config = {"params": {"min_hits": 1, "max_age": 10, "iou_threshold": 0.3}}

        previous_ids = None

        for frame_idx, detections in enumerate(frames):
            filter_result = asyncio.run(filter_node.execute({"detections": detections}, mock_context))
            filtered = filter_result["filtered"]

            tracker_result = asyncio.run(tracker_node.execute({"detections": filtered}, mock_context))

            if frame_idx == 0:
                assert tracker_result["count"] == 1
                previous_ids = tracker_result["track_ids"]
            else:
                # 同一目标在连续帧中 track_id 保持不变
                assert tracker_result["track_ids"] == previous_ids, \
                    f"第{frame_idx + 1}帧 track_id 应与第1帧一致"


class TestPreprocessAndDetect:
    """集成测试: ImagePreprocessor → YOLOModel 流水线。

    ImagePreprocessor 的输出格式是 {"path": output_path}，
    YOLOModel 接受 {"path": path} 或 "path" 两种格式。

    数据流:
      ImagePreprocessor          →  YOLOModel
      {"image": {"path": out}}  →  读取图片 → 检测

    使用场景:
      采集的图片分辨率不统一（如 1920x1080 截图），
      需要先 ImagePreprocessor resize 到 640x640
      再送入 YOLOModel 检测。
    """

    def test_preprocessor_output_feeds_yolo(self, mock_context):
        """ImagePreprocessor 的输出可被 YOLOModel 正确接收。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        import numpy as np

        mock_img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Step 1: ImagePreprocessor resize
        pre = ImagePreprocessorNode(node_id="pre")
        pre.config = {"params": {"operation": "resize", "width": 320, "height": 320}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.return_value = mock_img
        mock_cv2.resize.return_value = np.zeros((320, 320, 3), dtype=np.uint8)
        mock_cv2.imwrite.return_value = True

        with patch.dict('sys.modules', {'cv2': mock_cv2}), \
             patch('os.makedirs', return_value=None):

            pre_result = asyncio.run(pre.execute(
                {"image": "/tmp/original.jpg"}, mock_context
            ))

        # Step 2: 预处理结果送入 YOLOModel
        yolo = YOLOModelNode()
        yolo.config = {"params": {"model_path": "/models/yolo.pt"}}

        with patch('backend.services.rule_engine.model_cache.ModelCache.get_or_load') as mock_load, \
             patch('backend.routers.yolo_training.load_yolo_model'), \
             patch('backend.routers.yolo_training.inference_yolo') as mock_infer:
            mock_infer.return_value = {
                "detections": [{"bbox": [0, 0, 10, 10], "confidence": 0.9, "class_id": 0, "class_name": "person"}],
            }
            yolo_result = asyncio.run(yolo.execute(
                {"image": pre_result["image"]}, mock_context
            ))

        assert yolo_result["count"] > 0


class TestTimerTriggeredPipeline:
    """集成测试: TimerTrigger → YOLOModel → LogAction 流水线。

    模拟定时触发场景:
    1. TimerTrigger 生成触发信号
    2. YOLOModel 执行检测（通过 trigger_data 传入检测结果）
    3. LogAction 输出日志

    该模式适用于: 每隔 N 秒截图检测一次，记录检测结果到日志。
    """

    def test_trigger_to_log_flow(self, mock_context):
        """定时触发 → 检测 → 日志。"""
        from backend.services.rule_engine.nodes.triggers import TimerTriggerNode
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode

        # Step 1: TimerTrigger 触发
        timer = TimerTriggerNode()
        timer.config = {"params": {"interval_seconds": 5}}

        # Step 2: YOLOTrigger 接收到触发数据
        trigger = YOLOTriggerNode(node_id="yt")
        trigger.config = {"params": {"class_names": ["person"], "min_confidence": 0.5}}

        mock_context.trigger_data = {
            "detections": [
                {"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"},
            ],
        }

        result = asyncio.run(trigger.execute({}, mock_context))
        assert result["triggered"] is True
        assert "detections" in result
        assert result["detections"][0]["class_name"] == "person"

    def test_trigger_no_match_skips_action(self, mock_context):
        """没有匹配的检测结果时 triggered=false。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode

        trigger = YOLOTriggerNode()
        trigger.config = {"params": {"class_names": ["dog"], "min_confidence": 0.5}}
        mock_context.trigger_data = {
            "detections": [
                {"bbox": [0, 0, 10, 10], "confidence": 0.95, "class_name": "person"},
            ],
        }

        result = asyncio.run(trigger.execute({}, mock_context))
        assert result["triggered"] is False


# ============================================================================
# 4. 边界条件和异常处理测试
# ============================================================================

class TestEdgeCases:
    """边界条件测试 — 各种异常输入和极端情况。"""

    @pytest.mark.parametrize("node_cls, config, inputs, expected_key", [
        (
            "YOLOModelNode",
            {"params": {}},
            {},
            "error",
        ),
        (
            "ObjectDetectorNode",
            {"params": {}},
            {},
            "error",
        ),
        (
            "ImagePreprocessorNode",
            {"params": {"operation": "resize"}},
            {},
            "error",
        ),
        (
            "TrackerNode",
            {"params": {}},
            {"detections": None},
            "error",
        ),
    ])
    def test_node_error_handling(self, node_cls, config, inputs, expected_key, mock_context):
        """各种异常输入应返回包含 error 的 dict。"""
        import importlib
        from backend.services.rule_engine.nodes import detection_nodes, processing_nodes

        cls = getattr(detection_nodes, node_cls, None) or getattr(processing_nodes, node_cls)
        node = cls()
        node.config = config

        result = asyncio.run(node.execute(inputs, mock_context))
        assert expected_key in result

    def test_yolo_model_invalid_image_input(self, mock_context):
        """无法解析的图片输入返回错误。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        node.config = {"params": {"model_path": "/model.pt"}}

        # 传入数字等非法类型
        result = asyncio.run(node.execute({"image": 12345}, mock_context))
        assert "error" in result
        assert any(w in result["error"] for w in ["解析", "输入"])

    def test_invalid_image_path(self, mock_context):
        """图片路径为空字符串返回错误。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        node.config = {"params": {"model_path": "/model.pt"}}
        result = asyncio.run(node.execute({"image": {"path": ""}}, mock_context))
        assert "error" in result

    def test_tracker_detection_values_error(self, mock_context):
        """跟踪器输入非列表时处理正确。"""
        from backend.services.rule_engine.nodes.processing_nodes import TrackerNode
        node = TrackerNode()
        result = asyncio.run(node.execute({"detections": "invalid"}, mock_context))
        assert "error" in result

    def test_image_preprocessor_unreadable_image(self, mock_context):
        """OpenCV 无法读取图片时返回错误。"""
        from backend.services.rule_engine.nodes.processing_nodes import ImagePreprocessorNode
        node = ImagePreprocessorNode()
        node.config = {"params": {"operation": "resize", "width": 640, "height": 480}}

        mock_cv2 = MagicMock()
        mock_cv2.imread.return_value = None
        with patch.dict('sys.modules', {'cv2': mock_cv2}):
            result = asyncio.run(node.execute({"image": "/nonexistent.jpg"}, mock_context))
        assert "error" in result
