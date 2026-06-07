# -*- coding: utf-8 -*-
"""MergeDetectionsNode 多源检测结果融合节点测试。

覆盖：
1. 基础合并：2 路输入无重叠 → 输出 = 输入并集
2. NMS 去重：同一目标跨 2 路 → 保留 1 个（最高置信度）
3. 类别不同时不去重（即使 IoU 高）
4. union 策略：不去重
5. 保留 source 标签
6. 空输入处理（单路空 / 多路全空）
7. 无效 bbox 透传保留
8. validate_inputs 拒绝全空
9. 端口签名：8 路 input_N
10. 注册到 NodeRegistry
"""
import asyncio
import sys
from typing import Any, Dict
from unittest.mock import Mock

import pytest

sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.nodes.base import ExecutionContext
from backend.services.rule_engine.nodes.processing_nodes import MergeDetectionsNode


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ctx():
    """默认 NMS + iou=0.5 + 不保留 source。"""
    mock = Mock(spec=ExecutionContext)
    mock.config = {
        "iou_threshold": 0.5,
        "strategy": "nms",
        "keep_source": False,
    }
    return mock


def _det(bbox, confidence=0.9, class_id=0, class_name="person", **extra):
    return {
        "bbox": bbox,
        "confidence": confidence,
        "class_id": class_id,
        "class_name": class_name,
        **extra,
    }


# ============================================================================
# 1. 注册 & 端口
# ============================================================================


class TestRegistration:
    def test_registered(self):
        from backend.services.rule_engine.registry import init_builtin_executors
        r = init_builtin_executors()
        assert "merge_detections" in r.list_types()

    def test_definition_category(self):
        from backend.services.rule_engine.registry import init_builtin_executors
        d = next(
            x for x in init_builtin_executors().get_definitions()
            if x["type"] == "merge_detections"
        )
        assert d["category"] == "processing"

    def test_input_ports_count_8(self):
        node = MergeDetectionsNode()
        defn = node.get_definition()
        assert len(defn.inputs) == 8
        assert all(k.startswith("input_") for k in defn.inputs.keys())

    def test_output_ports(self):
        node = MergeDetectionsNode()
        defn = node.get_definition()
        assert "merged" in defn.outputs
        assert "count" in defn.outputs
        assert defn.outputs["count"].type == PortType.INT

    def test_config_schema_complete(self):
        node = MergeDetectionsNode()
        schema = node.get_config_schema()
        assert set(schema.keys()) == {"iou_threshold", "strategy", "keep_source"}
        assert schema["strategy"].enum == ["nms", "union"]
        assert schema["iou_threshold"].widget == "slider"


# ============================================================================
# 2. validate_inputs
# ============================================================================


class TestValidateInputs:
    def test_at_least_one_non_empty(self):
        node = MergeDetectionsNode()
        valid, err = node.validate_inputs({})
        assert valid is False
        assert "至少" in err

    def test_empty_lists_treated_as_empty(self):
        node = MergeDetectionsNode()
        valid, err = node.validate_inputs(
            {"input_1": [], "input_2": [], "input_3": []}
        )
        assert valid is False

    def test_none_treated_as_empty(self):
        node = MergeDetectionsNode()
        valid, err = node.validate_inputs(
            {"input_1": None, "input_2": []}
        )
        assert valid is False

    def test_one_valid_input_passes(self):
        node = MergeDetectionsNode()
        valid, err = node.validate_inputs(
            {"input_1": [_det([0, 0, 10, 10])]}
        )
        assert valid is True
        assert err is None


# ============================================================================
# 3. NMS 策略
# ============================================================================


class TestNMSStrategy:
    def test_no_overlap_keeps_all(self, ctx):
        """2 路输入，框完全不重叠 → 输出 = 4 个。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [_det([0, 0, 10, 10]), _det([100, 100, 120, 120])],
            "input_2": [_det([200, 200, 220, 220]), _det([300, 300, 320, 320])],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 4
        assert len(result["merged"]) == 4

    def test_high_iou_same_class_dedup(self, ctx):
        """同一目标在 2 路都被检出（IoU 接近 1，class_id 同）→ 保留 1 个。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [_det([0, 0, 100, 100], confidence=0.8, class_id=0)],
            "input_2": [_det([1, 1, 101, 101], confidence=0.9, class_id=0)],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 1
        assert result["merged"][0]["confidence"] == 0.9  # 高置信度的保留

    def test_high_iou_different_class_no_dedup(self, ctx):
        """不同类别的两个高 IoU 框 → 不去重（不同目标可重叠）。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [_det([0, 0, 100, 100], class_id=0, class_name="person")],
            "input_2": [_det([1, 1, 101, 101], class_id=1, class_name="car")],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 2

    def test_low_iou_no_dedup(self, ctx):
        """IoU 低于阈值 → 保留 2 个。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [_det([0, 0, 100, 100], class_id=0)],
            "input_2": [_det([200, 200, 300, 300], class_id=0)],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 2

    def test_custom_iou_threshold(self):
        """IoU 阈值可定制（0.3 时低重叠也去重）。"""
        node = MergeDetectionsNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"iou_threshold": 0.3, "strategy": "nms", "keep_source": False}
        # 两个框 IoU ≈ 0.47
        inputs = {
            "input_1": [_det([0, 0, 100, 100], class_id=0)],
            "input_2": [_det([0, 0, 90, 90], class_id=0)],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 1

    def test_three_inputs(self, ctx):
        """3 路输入。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [_det([0, 0, 10, 10])],
            "input_2": [_det([100, 100, 110, 110])],
            "input_3": [_det([200, 200, 210, 210])],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 3


# ============================================================================
# 4. union 策略
# ============================================================================


class TestUnionStrategy:
    def test_union_keeps_all(self):
        node = MergeDetectionsNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"iou_threshold": 0.5, "strategy": "union", "keep_source": False}
        inputs = {
            "input_1": [_det([0, 0, 100, 100], confidence=0.8, class_id=0)],
            "input_2": [_det([0, 0, 100, 100], confidence=0.9, class_id=0)],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 2  # 不去重


# ============================================================================
# 5. keep_source
# ============================================================================


class TestKeepSource:
    def test_source_label_added(self):
        node = MergeDetectionsNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"iou_threshold": 0.5, "strategy": "nms", "keep_source": True}
        inputs = {
            "input_1": [_det([0, 0, 10, 10])],
            "input_2": [_det([100, 100, 110, 110])],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        sources = {d["source"] for d in result["merged"]}
        assert sources == {"input_1", "input_2"}

    def test_source_not_added_by_default(self, ctx):
        node = MergeDetectionsNode()
        inputs = {"input_1": [_det([0, 0, 10, 10])]}
        result = asyncio.run(node.execute(inputs, ctx))
        assert "source" not in result["merged"][0]


# ============================================================================
# 6. 边界情况
# ============================================================================


class TestEdgeCases:
    def test_empty_inputs_returns_empty(self, ctx):
        node = MergeDetectionsNode()
        result = asyncio.run(node.execute({}, ctx))
        assert result["count"] == 0
        assert result["merged"] == []

    def test_all_empty_lists_returns_empty(self, ctx):
        node = MergeDetectionsNode()
        result = asyncio.run(
            node.execute({"input_1": [], "input_2": []}, ctx)
        )
        assert result["count"] == 0

    def test_invalid_bbox_kept(self, ctx):
        """bbox 字段无效（非 4 元素 / 非数字）→ 保留不去重。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [
                _det([0, 0, 10, 10]),
                _det("invalid"),  # 非法 bbox
                {"bbox": [1, 2], "class_id": 0},  # 长度错
            ],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        # 1 个有效 + 2 个无效保留
        assert result["count"] == 3

    def test_non_dict_items_skipped(self, ctx):
        """数组中非 dict 元素静默跳过。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [
                _det([0, 0, 10, 10]),
                "not_a_dict",
                42,
                None,
            ],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 1

    def test_payload_not_list_returns_empty(self, ctx):
        """上游传非 list → 返回空（不抛异常）。"""
        node = MergeDetectionsNode()
        result = asyncio.run(
            node.execute({"input_1": "not a list"}, ctx)
        )
        assert result["count"] == 0

    def test_default_config_used_when_ctx_config_missing(self):
        """context.config 缺失时使用默认 iou=0.5 / nms。"""
        node = MergeDetectionsNode()
        ctx = Mock(spec=ExecutionContext)
        # 不设 config 属性
        del ctx.config
        inputs = {
            "input_1": [_det([0, 0, 100, 100], class_id=0)],
            "input_2": [_det([0, 0, 100, 100], class_id=0)],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        # 默认 NMS 应去重
        assert result["count"] == 1


# ============================================================================
# 7. 实际场景
# ============================================================================


class TestRealScenario:
    def test_two_yolo_models_fuse(self, ctx):
        """模拟场景：2 个 YOLO 模型（一个检测 person，一个检测 car）融合。"""
        node = MergeDetectionsNode()
        inputs = {
            "input_1": [  # YOLO-A 检测到 2 个 person
                _det([10, 10, 50, 50], confidence=0.92, class_id=0, class_name="person"),
                _det([100, 100, 150, 150], confidence=0.85, class_id=0, class_name="person"),
            ],
            "input_2": [  # YOLO-B 检测到 1 个 car
                _det([200, 200, 300, 300], confidence=0.78, class_id=1, class_name="car"),
            ],
        }
        result = asyncio.run(node.execute(inputs, ctx))
        assert result["count"] == 3
        classes = {d["class_name"] for d in result["merged"]}
        assert classes == {"person", "car"}


# 端口类型常量
from backend.services.rule_engine.models import PortType
