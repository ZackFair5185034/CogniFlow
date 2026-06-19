# -*- coding: utf-8 -*-
"""YOLO 节点 device 字段支持测试。

Phase 14 修复：YOLOModelNode / YOLOTriggerNode schema 有 device 配置项
（auto/cuda/cpu）但 execute() 从未读取。修复后：
1. execute() 必须从 params 读取 device 并传给 load_yolo_model / inference_yolo
2. ModelCache cache_key 必须包含 device，否则不同设备会复用同一模型
3. inference_yolo 必须支持 device 参数
"""
import asyncio
import inspect
import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, '/home/coding/PRIVATE_WORKSPACE/CogniFlow')

from backend.services.rule_engine.nodes.detection_nodes import (
    YOLOModelNode, YOLOTriggerNode
)
from backend.services.rule_engine.nodes.base import ExecutionContext


def _ctx():
    return MagicMock(spec=ExecutionContext)


class TestInferenceYoloDeviceParam:
    """inference_yolo 必须支持 device 参数。"""

    def test_signature_accepts_device(self):
        # BE-P0-1 (2026-06-19): 推理函数迁到 services.inference_service
        from backend.services.inference_service import inference_yolo
        sig = inspect.signature(inference_yolo)
        assert "device" in sig.parameters
        assert sig.parameters["device"].default == "cpu"

    def test_passes_device_to_model_call(self):
        """inference_yolo 应把 device 作为关键字透传给 model() 调用。

        之前的实现额外调用了 model.to(target_device)，那是冗余且有副作用的
        —— 永久 in-place 修改 cached 实例，且 except: pass 会静默吞掉真实错误
        （如 CUDA 不可用）。修复后改用 Ultralytics 原生 device= 关键字参数，
        既不修改 cached 实例，也不会吞错。
        """
        # BE-P0-1 (2026-06-19): 推理函数迁到 services.inference_service
        from backend.services import inference_service
        mock_model = MagicMock()
        mock_model.return_value = []

        inference_service.inference_yolo(mock_model, "/tmp/x.jpg",
                                          conf_threshold=0.5, device="cuda:0")

        # 不应再调用 model.to() —— 防止永久修改 cached 实例
        mock_model.to.assert_not_called()
        # model() 必须以 device="cuda:0" 关键字透传
        mock_model.assert_called_with("/tmp/x.jpg", conf=0.5, device="cuda:0")

    def test_device_auto_skips_to_call(self):
        """device='auto' 时不显式调用 model.to()，让 Ultralytics 自动选择。"""
        # BE-P0-1 (2026-06-19): 推理函数迁到 services.inference_service
        from backend.services import inference_service
        mock_model = MagicMock()
        mock_model.return_value = []

        inference_service.inference_yolo(mock_model, "/tmp/x.jpg",
                                          conf_threshold=0.5, device="auto")

        mock_model.to.assert_not_called()
        mock_model.assert_called_with("/tmp/x.jpg", conf=0.5, device=None)


class TestYOLONodeModelIdType:
    """model_id schema 应为 integer (与 DB Model.id 类型一致)。"""

    def test_yolo_model_model_id_type(self):
        node = YOLOModelNode()
        schema = node.get_config_schema()
        assert schema["model_id"].type == "integer"
        assert schema["model_id"].widget == "model-select"

    def test_yolo_trigger_model_id_type(self):
        node = YOLOTriggerNode()
        schema = node.get_config_schema()
        assert schema["model_id"].type == "integer"
        assert schema["model_id"].widget == "model-select"


class TestYOLOModelNodeDevice:
    """YOLOModelNode 读取 device 字段并透传。"""

    def test_cache_key_includes_device(self):
        """execute() 的 ModelCache cache_key 必须包含 device。"""
        node = YOLOModelNode(node_id="n1", config={
            "params": {"model_id": 1, "device": "cuda:0"}
        })
        ctx = _ctx()
        with patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "inference_yolo", new=AsyncMock(return_value={"detections": []}), create=True,
        ), patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "load_yolo_model", return_value=MagicMock(), create=True,
        ), patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "ModelCache", create=True,
        ) as CacheMock, patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "SessionLocal", create=True,
        ) as SL:
            db_session = SL.return_value
            db_session.query.return_value.filter.return_value.first.return_value = MagicMock(
                file_path="/tmp/m.pt"
            )
            CacheMock.get_instance.return_value.get_or_load.return_value = MagicMock()

            asyncio.run(node.execute({"image": "/tmp/i.jpg"}, ctx))

        cache_call_args = CacheMock.get_instance.return_value.get_or_load.call_args
        cache_key = cache_call_args[0][0]
        assert "cuda:0" in cache_key, f"cache_key 应包含 device，实际: {cache_key}"


class TestYOLOTriggerNodeDevice:
    """YOLOTriggerNode 读取 device 字段。"""

    def test_cache_key_includes_device(self):
        node = YOLOTriggerNode(node_id="n2", config={
            "params": {"model_id": 1, "device": "cpu"}
        })
        ctx = _ctx()
        ctx.trigger_data = {"detections": []}  # 走自己推理路径

        with patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "inference_yolo", new=AsyncMock(return_value={"detections": []}), create=True,
        ), patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "load_yolo_model", return_value=MagicMock(), create=True,
        ), patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "ModelCache", create=True,
        ) as CacheMock, patch.object(
            sys.modules["backend.services.rule_engine.nodes.detection_nodes"],
            "SessionLocal", create=True,
        ) as SL:
            db_session = SL.return_value
            db_session.query.return_value.filter.return_value.first.return_value = MagicMock(
                file_path="/tmp/m.pt"
            )
            CacheMock.get_instance.return_value.get_or_load.return_value = MagicMock()

            asyncio.run(node.execute({"image": "/tmp/i.jpg"}, ctx))

        cache_call_args = CacheMock.get_instance.return_value.get_or_load.call_args
        cache_key = cache_call_args[0][0]
        assert "cpu" in cache_key
