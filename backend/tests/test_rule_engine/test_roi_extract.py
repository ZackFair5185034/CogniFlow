# -*- coding: utf-8 -*-
"""RoiExtractNode ROI 裁剪节点测试。

覆盖：
1. 端口签名：image + detections in / roi + count + width + height out
2. validate_inputs 必填校验
3. 注册到 NodeRegistry
4. IMAGE 输入支持 str / {"path": str} 两种格式
5. cv2 不可用时降级（返回原图 + warning）
6. 无效 bbox 跳过
7. max_rois 截取
8. padding 外扩
9. min_size 过滤
10. 真实图片端到端（用 numpy 生成测试图）
"""
import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.nodes.base import ExecutionContext
from backend.services.rule_engine.nodes.processing_nodes import RoiExtractNode


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ctx():
    """默认配置：padding=0, min_size=4, max_rois=10。"""
    mock = Mock(spec=ExecutionContext)
    mock.config = {"padding": 0.0, "min_size": 4, "max_rois": 10}
    return mock


@pytest.fixture
def sample_image_path(tmp_path):
    """生成 100x100 白色测试图。"""
    try:
        import cv2
        import numpy as np
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        path = str(tmp_path / "test.png")
        cv2.imwrite(path, img)
        return path
    except ImportError:
        pytest.skip("cv2/numpy 未安装")


def _det(bbox, confidence=0.9, class_id=0):
    return {"bbox": bbox, "confidence": confidence, "class_id": class_id}


# ============================================================================
# 1. 端口 & 配置
# ============================================================================


class TestDefinition:
    def test_input_ports(self):
        node = RoiExtractNode()
        d = node.get_definition()
        assert set(d.inputs.keys()) == {"image", "detections"}
        assert d.inputs["image"].type == "IMAGE"
        assert d.inputs["detections"].type == "ARRAY"

    def test_output_ports(self):
        node = RoiExtractNode()
        d = node.get_definition()
        assert set(d.outputs.keys()) == {"roi", "roi_count", "width", "height"}
        assert d.outputs["roi"].type == "IMAGE"
        assert d.outputs["roi_count"].type == "INT"
        assert d.outputs["width"].type == "INT"
        assert d.outputs["height"].type == "INT"

    def test_config_schema(self):
        node = RoiExtractNode()
        schema = node.get_config_schema()
        assert set(schema.keys()) == {"padding", "min_size", "max_rois"}
        assert schema["padding"].widget == "slider"
        assert schema["min_size"].widget == "number"
        assert schema["max_rois"].widget == "number"

    def test_category(self):
        from backend.services.rule_engine.models import NodeCategory
        assert RoiExtractNode().category == NodeCategory.PROCESSING


# ============================================================================
# 2. 注册
# ============================================================================


class TestRegistration:
    def test_registered(self):
        from backend.services.rule_engine.registry import init_builtin_executors
        r = init_builtin_executors()
        assert "roi_extract" in r.list_types()

    def test_total_count_34(self):
        from backend.services.rule_engine.registry import init_builtin_executors
        r = init_builtin_executors()
        # 32 (含 template) + merge_detections + roi_extract = 34
        assert len(r.list_types()) == 34


# ============================================================================
# 3. validate_inputs
# ============================================================================


class TestValidateInputs:
    def test_missing_image(self):
        node = RoiExtractNode()
        valid, err = node.validate_inputs({"detections": [_det([0, 0, 10, 10])]})
        assert valid is False
        assert "image" in err

    def test_missing_detections(self):
        node = RoiExtractNode()
        valid, err = node.validate_inputs({"image": "/tmp/a.png"})
        assert valid is False
        assert "detections" in err

    def test_empty_detections(self):
        node = RoiExtractNode()
        valid, err = node.validate_inputs({"image": "/tmp/a.png", "detections": []})
        assert valid is False

    def test_both_present(self):
        node = RoiExtractNode()
        valid, err = node.validate_inputs(
            {"image": "/tmp/a.png", "detections": [_det([0, 0, 10, 10])]}
        )
        assert valid is True
        assert err is None


# ============================================================================
# 4. 输入格式
# ============================================================================


class TestInputFormats:
    def test_image_as_string(self, sample_image_path, ctx):
        node = RoiExtractNode()
        result = asyncio.run(
            node.execute(
                {"image": sample_image_path, "detections": [_det([10, 10, 50, 50])]},
                ctx,
            )
        )
        assert "error" not in result
        assert result["roi_count"] == 1

    def test_image_as_dict(self, sample_image_path, ctx):
        node = RoiExtractNode()
        result = asyncio.run(
            node.execute(
                {"image": {"path": sample_image_path}, "detections": [_det([10, 10, 50, 50])]},
                ctx,
            )
        )
        assert "error" not in result
        assert result["roi_count"] == 1

    def test_invalid_image_format(self, ctx):
        node = RoiExtractNode()
        result = asyncio.run(
            node.execute(
                {"image": 42, "detections": [_det([0, 0, 10, 10])]},
                ctx,
            )
        )
        assert "error" in result


# ============================================================================
# 5. cv2 不可用降级
# ============================================================================


class TestCV2Fallback:
    def test_cv2_missing_returns_warning(self, sample_image_path):
        """cv2 不可用时返回原图 + warning。"""
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.0, "min_size": 4, "max_rois": 10}
        with patch.dict("sys.modules", {"cv2": None}):
            result = asyncio.run(
                node.execute(
                    {"image": sample_image_path, "detections": [_det([10, 10, 50, 50])]},
                    ctx,
                )
            )
        assert result["roi_count"] == 0
        assert "warning" in result
        assert "OpenCV" in result["warning"]


# ============================================================================
# 6. 边界情况
# ============================================================================


class TestEdgeCases:
    def test_invalid_bbox_skipped(self, sample_image_path, ctx):
        node = RoiExtractNode()
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,
                    "detections": [
                        _det("invalid"),
                        {"bbox": [1, 2]},
                        _det([10, 10, 50, 50]),  # 唯一有效
                    ],
                },
                ctx,
            )
        )
        assert result["roi_count"] == 1

    def test_max_rois_truncation(self, sample_image_path):
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.0, "min_size": 4, "max_rois": 2}
        # 5 个有效检测
        dets = [
            _det([10, 10, 30, 30], confidence=0.9),
            _det([40, 40, 60, 60], confidence=0.8),
            _det([70, 70, 90, 90], confidence=0.7),
            _det([10, 10, 20, 20], confidence=0.6),  # 与第一个重叠
            _det([30, 30, 40, 40], confidence=0.5),
        ]
        result = asyncio.run(
            node.execute({"image": sample_image_path, "detections": dets}, ctx)
        )
        assert result["roi_count"] == 2

    def test_min_size_filter(self, sample_image_path):
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.0, "min_size": 50, "max_rois": 10}
        dets = [
            _det([10, 10, 20, 20]),  # 10x10 < 50 → 跳过
            _det([40, 40, 90, 90]),  # 50x50 ≥ 50 → 保留
        ]
        result = asyncio.run(
            node.execute({"image": sample_image_path, "detections": dets}, ctx)
        )
        assert result["roi_count"] == 1

    def test_empty_detections(self, sample_image_path, ctx):
        node = RoiExtractNode()
        result = asyncio.run(
            node.execute({"image": sample_image_path, "detections": []}, ctx)
        )
        # 空列表 → 0 个 ROI
        assert result["roi_count"] == 0

    def test_padding_expansion(self, sample_image_path):
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.2, "min_size": 4, "max_rois": 10}
        # bbox 50x50 + 20% padding = 60x60
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,
                    "detections": [_det([20, 20, 70, 70])],
                },
                ctx,
            )
        )
        assert result["roi_count"] == 1
        # 60x60 ROI
        assert result["width"] == 60
        assert result["height"] == 60

    def test_padding_50_percent(self, sample_image_path):
        """padding=0.5 → bbox 50x50 + 50% total = 75x75（每边 +12.5）"""
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.5, "min_size": 4, "max_rois": 10}
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,
                    "detections": [_det([20, 20, 70, 70])],  # 50x50
                },
                ctx,
            )
        )
        assert result["roi_count"] == 1
        assert result["width"] == 75
        assert result["height"] == 75

    def test_padding_zero_no_expansion(self, sample_image_path):
        """padding=0 → 严格裁剪 bbox 原尺寸"""
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.0, "min_size": 4, "max_rois": 10}
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,
                    "detections": [_det([20, 20, 70, 70])],  # 50x50
                },
                ctx,
            )
        )
        assert result["width"] == 50
        assert result["height"] == 50

    def test_padding_clamped_to_image_bounds(self, sample_image_path):
        """padding 0.5 让 50x50 bbox 扩到 75x75 (padding 0.5 远超 0.1 边界时不应被裁剪)"""
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        ctx.config = {"padding": 0.5, "min_size": 4, "max_rois": 10}
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,  # 100x100
                    "detections": [_det([20, 20, 70, 70])],  # 50x50
                },
                ctx,
            )
        )
        assert result["roi_count"] == 1
        # bbox=[7.5,7.5,82.5,82.5], int 后 75x75（未触顶 100）
        assert result["width"] == 75
        assert result["height"] == 75

    def test_padding_truly_exceeds_bounds(self, sample_image_path):
        """padding 让 bbox 超出 100x100 图边界时，应被 clamp 而不报错"""
        node = RoiExtractNode()
        ctx = Mock(spec=ExecutionContext)
        # 用一个本来就靠边的大 bbox + padding 让它出界
        ctx.config = {"padding": 0.5, "min_size": 4, "max_rois": 10}
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,  # 100x100
                    "detections": [_det([80, 80, 99, 99])],  # 19x19 靠右下
                },
                ctx,
            )
        )
        assert result["roi_count"] == 1
        # bbox=[75.25,75.25,103.75,103.75] → clamp 到 100 → width=25, height=25
        assert result["width"] == 25
        assert result["height"] == 25

    def test_clamp_to_image_bounds(self, sample_image_path, ctx):
        """bbox 超出图像边界时裁剪到图像范围（不报错）。"""
        node = RoiExtractNode()
        result = asyncio.run(
            node.execute(
                {
                    "image": sample_image_path,  # 100x100
                    "detections": [_det([-50, -50, 50, 50])],  # 部分越界
                },
                ctx,
            )
        )
        # 裁剪到 [0:50, 0:50] = 50x50
        assert result["roi_count"] == 1
        assert result["width"] == 50
        assert result["height"] == 50


# ============================================================================
# 7. 实际场景
# ============================================================================


class TestRealScenario:
    def test_yolo_to_roi_pipeline(self, sample_image_path, ctx):
        """YOLO → ROI 端到端：3 个检测 → 3 个 ROI。"""
        node = RoiExtractNode()
        # 模拟 YOLOModel 输出
        yolo_output = [
            {"bbox": [10, 10, 30, 30], "confidence": 0.95, "class_id": 0, "class_name": "person"},
            {"bbox": [50, 50, 80, 80], "confidence": 0.85, "class_id": 0, "class_name": "person"},
            {"bbox": [20, 60, 40, 90], "confidence": 0.70, "class_id": 1, "class_name": "car"},
        ]
        result = asyncio.run(
            node.execute({"image": sample_image_path, "detections": yolo_output}, ctx)
        )
        assert result["roi_count"] == 3
        # 第一张 ROI 是最高置信度那张
        assert result["width"] == 20  # 30-10
        assert result["height"] == 20
