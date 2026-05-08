# -*- coding: utf-8 -*-
"""YOLO .pt 格式处理器。"""

import time
from typing import Dict, Any, List
import numpy as np

from backend.core.formats.base_handler import BaseModelHandler
from backend.core.interfaces import InferenceResult
from backend.core.model_format import ModelFormat


class YoloModelHandler(BaseModelHandler):
    """YOLO .pt 格式处理器。

    封装 ultralytics.YOLO 的加载和推理逻辑。
    """

    @property
    def format(self) -> ModelFormat:
        """返回处理器支持的格式。"""
        return ModelFormat.YOLO_PT

    def load(self, model_path: str, device: str = "cpu", **kwargs) -> None:
        """加载 YOLO 模型。

        Args:
            model_path: .pt 文件路径
            device: 设备 (cpu/cuda)
        """
        super().load(model_path, device, **kwargs)

        from ultralytics import YOLO

        self._model = YOLO(model_path)
        self._device = device

        # 提取模型元数据
        self._extract_metadata()

    def _extract_metadata(self) -> None:
        """从模型提取元数据。"""
        if self._model is None:
            return

        try:
            ckpt = self._model.ckpt
            names = self._safe_get(ckpt, "model", "names", default={})
            yaml_info = self._safe_get(ckpt, "model", "yaml", default={})
            nc = self._safe_get(yaml_info, "nc", default=len(names))
            if nc is None:
                nc = len(names) if names else 0

            self._metadata = {
                "num_classes": nc,
                "names": names,
                "format": ModelFormat.YOLO_PT.value,
            }
        except Exception:
            self._metadata = {"num_classes": 0, "names": {}, "format": ModelFormat.YOLO_PT.value}

    @staticmethod
    def _safe_get(obj: Any, *keys, default=None) -> Any:
        """安全获取嵌套字典属性。

        Args:
            obj: 初始对象
            *keys: 嵌套键序列
            default: 默认值

        Returns:
            获取的值或默认值
        """
        for k in keys:
            if obj is None:
                return default
            if isinstance(obj, dict):
                obj = obj.get(k)
            elif isinstance(obj, (list, tuple)):
                obj = obj[k] if k < len(obj) else None
            else:
                obj = getattr(obj, k, None)
            if obj is None:
                return default
        return obj

    def infer(self, image: np.ndarray, conf: float = 0.25, **kwargs) -> InferenceResult:
        """YOLO 单图推理。

        Args:
            image: RGB 格式图片数组 (H, W, 3)
            conf: 置信度阈值

        Returns:
            InferenceResult 推理结果
        """
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 load()")

        start_time = time.time()

        # YOLO 推理
        results = self._model(image, conf=conf, verbose=False)

        inference_ms = (time.time() - start_time) * 1000

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0])
                    detections.append({
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": round(float(box.conf[0]), 4),
                        "class_id": cls_id,
                        "class_name": (
                            result.names[cls_id]
                            if cls_id < len(result.names)
                            else f"Class {cls_id}"
                        ),
                    })

        return InferenceResult(
            detections=detections,
            num_detections=len(detections),
            inference_ms=inference_ms,
            metadata=self._metadata.copy(),
        )
