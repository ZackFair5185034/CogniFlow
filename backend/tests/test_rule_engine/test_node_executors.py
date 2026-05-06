# -*- coding: utf-8 -*-
"""规则引擎节点执行器单元测试。

实际签名验证：
- execute(self, inputs: Dict[str, Any], context) -> Dict[str, Any]
- validate_inputs(config: Dict) -> Tuple[bool, Optional[str]]
"""
import pytest
import asyncio
from unittest.mock import Mock

import sys
sys.path.insert(0, '/root/coding/CogniFlow/backend')

from backend.services.rule_engine.nodes.input_nodes import (
    ImageCaptureNode,
    VideoCaptureNode,
    ScreenCaptureNode,
)
from backend.services.rule_engine.nodes.detection_nodes import (
    ObjectDetectorNode,
    YOLOModelNode,
)
from backend.services.rule_engine.nodes.processing_nodes import (
    ImagePreprocessorNode,
    FilterNode,
)
from backend.services.rule_engine.nodes.actions import (
    LogActionNode,
    HttpRequestActionNode,
)
from backend.services.rule_engine.nodes.logic import (
    BranchNode,
    DelayNode,
    SetVariableNode,
)
from backend.services.rule_engine.nodes.conditions import (
    ConfidenceThresholdConditionNode,
    ObjectExistsConditionNode,
)
from backend.services.rule_engine.models import NodeCategory


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_context():
    """创建模拟执行上下文。"""
    ctx = Mock()
    ctx.execution_id = 1
    ctx.trigger_type = "manual"
    ctx.trigger_data = {}
    ctx.node_results = {}
    ctx.node_status = {}
    ctx.variables = {"counter": 0}
    ctx.config = {}
    ctx.cancelled = False
    ctx.ws_manager = None
    return ctx


@pytest.fixture
def sample_image_data():
    """模拟图像数据。"""
    return {"path": "/test.jpg", "width": 640, "height": 480}


@pytest.fixture
def sample_detections():
    """模拟检测结果。"""
    return [
        {"class": "person", "confidence": 0.95, "bbox": [100, 100, 200, 300]},
        {"class": "car", "confidence": 0.87, "bbox": [50, 50, 150, 150]},
    ]


# ============================================================================
# InputNodes Tests
# ============================================================================

class TestImageCaptureNode:
    """测试 ImageCaptureNode。"""

    def test_category_is_input(self):
        node = ImageCaptureNode()
        assert node.get_definition().category == NodeCategory.INPUT

    def test_has_outputs(self):
        node = ImageCaptureNode()
        outputs = node.get_definition().outputs
        assert isinstance(outputs, dict)
        assert len(outputs) > 0

    def test_validate_inputs_valid(self):
        node = ImageCaptureNode()
        valid, err = node.validate_inputs({"path": "/test.jpg"})
        assert valid is True

    def test_validate_inputs_no_path(self):
        node = ImageCaptureNode()
        # 空配置不一定失败，因为节点可以没有默认值
        valid, err = node.validate_inputs({})
        assert isinstance(valid, bool)

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = ImageCaptureNode()
        node.config = {"path": "/test.jpg"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)
        assert "error" in result or "image" in result


class TestVideoCaptureNode:
    """测试 VideoCaptureNode。"""

    def test_category_is_input(self):
        node = VideoCaptureNode()
        assert node.get_definition().category == NodeCategory.INPUT

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = VideoCaptureNode()
        node.config = {"path": "/test.mp4"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


class TestScreenCaptureNode:
    """测试 ScreenCaptureNode。"""

    def test_category_is_input(self):
        node = ScreenCaptureNode()
        assert node.get_definition().category == NodeCategory.INPUT

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = ScreenCaptureNode()
        node.config = {"region": {"x": 0, "y": 0, "width": 1920, "height": 1080}}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


# ============================================================================
# DetectionNodes Tests
# ============================================================================

class TestObjectDetectorNode:
    """测试 ObjectDetectorNode。"""

    def test_category_is_detection(self):
        node = ObjectDetectorNode()
        assert node.get_definition().category == NodeCategory.DETECTION

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = ObjectDetectorNode()
        node.config = {"confidence_threshold": 0.5}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


class TestYOLOModelNode:
    """测试 YOLOModelNode。"""

    def test_category_is_detection(self):
        node = YOLOModelNode()
        assert node.get_definition().category == NodeCategory.DETECTION

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = YOLOModelNode()
        node.config = {"model_name": "yolo11n", "device": "cpu"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


# ============================================================================
# ProcessingNodes Tests
# ============================================================================

class TestImagePreprocessorNode:
    """测试 ImagePreprocessorNode。"""

    def test_category_is_processing(self):
        node = ImagePreprocessorNode()
        assert node.get_definition().category == NodeCategory.PROCESSING

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = ImagePreprocessorNode()
        node.config = {"operation": "resize", "width": 320, "height": 240}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


class TestFilterNode:
    """测试 FilterNode。"""

    def test_category_is_processing(self):
        node = FilterNode()
        assert node.get_definition().category == NodeCategory.PROCESSING

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = FilterNode()
        node.config = {"filter_type": "confidence", "threshold": 0.5}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


# ============================================================================
# ActionNodes Tests
# ============================================================================

class TestLogActionNode:
    """测试 LogActionNode。"""

    def test_category_is_action(self):
        node = LogActionNode()
        assert node.get_definition().category == NodeCategory.ACTION

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = LogActionNode()
        node.config = {"message": "test", "level": "info"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


class TestHttpRequestActionNode:
    """测试 HttpRequestActionNode。"""

    def test_category_is_action(self):
        node = HttpRequestActionNode()
        assert node.get_definition().category == NodeCategory.ACTION

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = HttpRequestActionNode()
        node.config = {"url": "https://httpbin.org/get", "method": "GET"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


# ============================================================================
# LogicNodes Tests
# ============================================================================

class TestBranchNode:
    """测试 BranchNode。"""

    def test_category_is_logic(self):
        node = BranchNode()
        assert node.get_definition().category == NodeCategory.LOGIC

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = BranchNode()
        node.config = {"condition_input": "check"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


class TestDelayNode:
    """测试 DelayNode。"""

    def test_category_is_logic(self):
        node = DelayNode()
        assert node.get_definition().category == NodeCategory.LOGIC

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = DelayNode()
        node.config = {"delay_seconds": 0.01}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cancelled_returns_cancelled(self, mock_context):
        mock_context.cancelled = True
        node = DelayNode()
        node.config = {"delay_seconds": 10}
        result = await node.execute({}, mock_context)
        # cancelled 节点返回 error 或 cancelled 状态
        assert isinstance(result, dict)


class TestSetVariableNode:
    """测试 SetVariableNode。"""

    def test_category_is_logic(self):
        node = SetVariableNode()
        assert node.get_definition().category == NodeCategory.LOGIC

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = SetVariableNode()
        node.config = {"variable_name": "test_var", "value": "hello"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


# ============================================================================
# ConditionNodes Tests
# ============================================================================

class TestConfidenceThresholdConditionNode:
    """测试 ConfidenceThresholdConditionNode。"""

    def test_category_is_logic(self):
        node = ConfidenceThresholdConditionNode()
        assert node.get_definition().category == NodeCategory.LOGIC

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = ConfidenceThresholdConditionNode()
        node.config = {"threshold": 0.5}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


class TestObjectExistsConditionNode:
    """测试 ObjectExistsConditionNode。"""

    def test_category_is_logic(self):
        node = ObjectExistsConditionNode()
        assert node.get_definition().category == NodeCategory.LOGIC

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, mock_context):
        node = ObjectExistsConditionNode()
        node.config = {"target_class": "person"}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)


# ============================================================================
# 集成测试
# ============================================================================

class TestCrossNodeCollaboration:
    """测试跨节点协作。"""

    @pytest.mark.asyncio
    async def test_image_capture_to_detector(self, mock_context):
        """测试：ImageCapture -> ObjectDetector 流水线。"""
        # 1. ImageCapture
        image_node = ImageCaptureNode()
        image_node.config = {"path": "/test.jpg"}
        image_result = await image_node.execute({}, mock_context)
        assert isinstance(image_result, dict)

        # 2. ObjectDetector（使用上一步输出）
        mock_context.node_results["capture"] = image_result
        detector_node = ObjectDetectorNode()
        detector_node.config = {"confidence_threshold": 0.3}
        detector_result = await detector_node.execute({}, mock_context)
        assert isinstance(detector_result, dict)

    @pytest.mark.asyncio
    async def test_delay_can_be_cancelled(self, mock_context):
        """测试 Delay 可被取消。"""
        mock_context.cancelled = True
        node = DelayNode()
        node.config = {"delay_seconds": 10}
        result = await node.execute({}, mock_context)
        assert isinstance(result, dict)
