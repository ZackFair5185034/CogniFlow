# -*- coding: utf-8 -*-
"""Region Pydantic model 与 screen_capture.region 序列化测试。

覆盖：
1. Region 实例化与字段验证
2. Region 序列化（model_dump / model_dump_json）
3. Region 反序列化（model_validate）
4. ScreenCaptureNode.execute() 的 region 序列化场景：
   - 合法 dict → 标准 Region dict
   - None → 透传 None
   - 非法 dict（缺字段）→ 透传原始值（容错）
   - Region 实例 → dump 为 dict
"""
import asyncio
import json
import sys

import pytest

sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.models import Region
from backend.services.rule_engine.nodes.input_nodes import ScreenCaptureNode
from backend.services.rule_engine.nodes.base import ExecutionContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_context():
    """模拟执行上下文。"""
    return ExecutionContext(
        execution_id=1,
        trigger_type='manual',
        trigger_data={},
        config={},
    )


# ============================================================================
# 1. Region Pydantic model 单元测试
# ============================================================================

class TestRegionModel:
    """Region Pydantic model 行为测试。"""

    def test_region_required_fields_only(self):
        """只传必填字段（x, y, width, height）应成功实例化。"""
        r = Region(x=0, y=0, width=1920, height=1080)
        assert r.x == 0
        assert r.y == 0
        assert r.width == 1920
        assert r.height == 1080
        assert r.monitor is None  # monitor 可选，默认 None

    def test_region_with_monitor(self):
        """显式指定 monitor 应保留。"""
        r = Region(x=100, y=200, width=800, height=600, monitor=1)
        assert r.monitor == 1

    def test_region_width_must_be_positive(self):
        """width < 1 应校验失败。"""
        with pytest.raises(Exception):
            Region(x=0, y=0, width=0, height=100)

    def test_region_height_must_be_positive(self):
        """height < 1 应校验失败。"""
        with pytest.raises(Exception):
            Region(x=0, y=0, width=100, height=0)

    def test_region_missing_required_field(self):
        """缺少必填字段应校验失败。"""
        with pytest.raises(Exception):
            Region(x=0, y=0, width=100)  # 缺 height

    def test_region_serialize_to_dict(self):
        """model_dump() 应输出标准 dict。"""
        r = Region(x=10, y=20, width=800, height=600, monitor=1)
        d = r.model_dump()
        assert d == {"x": 10, "y": 20, "width": 800, "height": 600, "monitor": 1}

    def test_region_serialize_to_json(self):
        """model_dump_json() 输出应为合法 JSON 字符串。"""
        r = Region(x=10, y=20, width=800, height=600)
        js = r.model_dump_json()
        parsed = json.loads(js)
        assert parsed == {"x": 10, "y": 20, "width": 800, "height": 600, "monitor": None}

    def test_region_deserialize_from_dict(self):
        """model_validate(dict) 应能正确反序列化。"""
        raw = {"x": 10, "y": 20, "width": 800, "height": 600, "monitor": 1}
        r = Region.model_validate(raw)
        assert r.x == 10
        assert r.monitor == 1

    def test_region_deserialize_optional_monitor_omitted(self):
        """反序列化时省略 monitor 字段应默认为 None。"""
        raw = {"x": 0, "y": 0, "width": 100, "height": 100}
        r = Region.model_validate(raw)
        assert r.monitor is None


# ============================================================================
# 2. ScreenCaptureNode region 序列化场景测试
# ============================================================================

class TestScreenCaptureRegionSerialization:
    """ScreenCaptureNode.execute() 中 region 字段的序列化行为。"""

    def _make_node(self, region_param):
        """创建带指定 region 配置的 ScreenCaptureNode。"""
        node = ScreenCaptureNode()
        node.config = {"params": {"region": region_param}}
        return node

    def test_execute_with_valid_region_dict(self, mock_context):
        """合法 region dict 应序列化为标准 Region dict 输出。"""
        node = self._make_node({"x": 0, "y": 0, "width": 800, "height": 600})
        result = asyncio.run(node.execute({}, mock_context))
        assert result["region"] == {
            "x": 0, "y": 0, "width": 800, "height": 600, "monitor": None
        }

    def test_execute_with_region_dict_including_monitor(self, mock_context):
        """含 monitor 字段的 region dict 应被完整序列化。"""
        node = self._make_node({"x": 100, "y": 200, "width": 1280, "height": 720, "monitor": 1})
        result = asyncio.run(node.execute({}, mock_context))
        assert result["region"]["monitor"] == 1

    def test_execute_with_none_region(self, mock_context):
        """None region 应透传为 None（表示全屏采集）。"""
        node = self._make_node(None)
        result = asyncio.run(node.execute({}, mock_context))
        assert result["region"] is None

    def test_execute_with_invalid_region_dict_falls_back(self, mock_context):
        """非法 region dict（缺字段）应透传原始值，不阻塞主流程。"""
        invalid = {"x": 0, "y": 0}  # 缺 width, height
        node = self._make_node(invalid)
        result = asyncio.run(node.execute({}, mock_context))
        # 透传原始值，不抛异常
        assert result["region"] == invalid

    def test_execute_with_region_instance(self, mock_context):
        """Region 实例输入应被 dump 为 dict。"""
        r = Region(x=10, y=20, width=800, height=600, monitor=2)
        node = self._make_node(r)
        result = asyncio.run(node.execute({}, mock_context))
        assert result["region"] == {
            "x": 10, "y": 20, "width": 800, "height": 600, "monitor": 2
        }

    def test_execute_without_region_param(self, mock_context):
        """无 region 配置参数时应返回 None（默认全屏）。"""
        node = ScreenCaptureNode()
        node.config = {"params": {}}
        result = asyncio.run(node.execute({}, mock_context))
        assert result["region"] is None

    def test_output_image_is_placeholder(self, mock_context):
        """image 字段仍为 None 占位（TODO 待对接真实截图服务）。"""
        node = self._make_node({"x": 0, "y": 0, "width": 800, "height": 600})
        result = asyncio.run(node.execute({}, mock_context))
        assert "image" in result
        assert result["image"] is None
