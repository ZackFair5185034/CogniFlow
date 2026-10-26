# -*- coding: utf-8 -*-
"""采集节点测试 - 屏幕/视频采集必须返回真实图像。"""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.services.rule_engine.nodes.input_nodes import (
    ScreenCaptureNode,
    VideoCaptureNode,
)


class TestScreenCaptureNode:
    """屏幕截图节点。"""

    @pytest.mark.asyncio
    async def test_returns_real_image(self):
        """必须返回真实采集到的图像, 不是 None。"""
        frame = np.zeros((10, 20, 3), dtype=np.uint8)
        capture = MagicMock()
        capture.capture.return_value = frame

        node = ScreenCaptureNode(node_id="n1", config={"params": {}})
        with patch(
            "engine.core.data_input.capture.screen_capture.ScreenCapture",
            return_value=capture,
        ):
            result = await node.execute({}, MagicMock())

        assert result["image"] is not None
        assert result["image"].shape == (10, 20, 3)

    @pytest.mark.asyncio
    async def test_raises_when_backend_unavailable(self):
        """采集后端不可用时显式报错。"""
        node = ScreenCaptureNode(node_id="n1", config={"params": {}})

        with patch(
            "engine.core.data_input.capture.screen_capture.ScreenCapture",
            side_effect=RuntimeError("mss 不可用"),
        ):
            with pytest.raises(Exception) as excinfo:
                await node.execute({}, MagicMock())

        assert "mss 不可用" in str(excinfo.value)


class TestVideoCaptureNode:
    """视频采集节点。"""

    @pytest.mark.asyncio
    async def test_returns_real_frame(self):
        """必须返回真实读到的帧, 不是 None。"""
        frame = np.zeros((5, 8, 3), dtype=np.uint8)
        reader = MagicMock()
        reader.read.return_value = frame

        node = VideoCaptureNode(node_id="n1", config={"params": {"source": "video.mp4"}})
        with patch(
            "engine.core.data_input.capture.video_reader.VideoReader",
            return_value=reader,
        ):
            result = await node.execute({}, MagicMock())

        assert result["image"] is not None
        assert result["image"].shape == (5, 8, 3)

    @pytest.mark.asyncio
    async def test_video_ended_returns_none_image(self):
        """视频读完了返回 None 是合法语义(区别于「没实现」)。"""
        reader = MagicMock()
        reader.read.return_value = None

        node = VideoCaptureNode(node_id="n1", config={"params": {"source": "video.mp4"}})
        with patch(
            "engine.core.data_input.capture.video_reader.VideoReader",
            return_value=reader,
        ):
            result = await node.execute({}, MagicMock())

        assert result["image"] is None
