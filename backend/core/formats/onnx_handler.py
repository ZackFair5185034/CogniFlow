# -*- coding: utf-8 -*-
"""ONNX 格式处理器。"""

import time
from typing import Dict, Any, List, Optional
import numpy as np

from backend.core.formats.base_handler import BaseModelHandler
from backend.core.interfaces import InferenceResult
from backend.core.model_format import ModelFormat


class OnnxModelHandler(BaseModelHandler):
    """ONNX 格式处理器。

    使用 onnxruntime 进行推理。
    """

    def __init__(self):
        super().__init__()
        self._session: Optional[Any] = None
        self._input_name: Optional[str] = None
        self._output_names: Optional[List[str]] = None
        self._input_shape: Optional[List[int]] = None

    @property
    def format(self) -> ModelFormat:
        """返回处理器支持的格式。"""
        return ModelFormat.ONNX

    def load(self, model_path: str, device: str = "cpu", **kwargs) -> None:
        """加载 ONNX 模型。

        Args:
            model_path: .onnx 文件路径
            device: 设备 (cpu/cuda/mps)
        """
        super().load(model_path, device, **kwargs)

        import onnxruntime as ort

        # 配置 providers
        providers = []
        if device == "cuda":
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        elif device == "mps":
            providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]

        self._session = ort.InferenceSession(model_path, providers=providers)

        # 获取输入输出信息
        self._input_name = self._session.get_inputs()[0].name
        self._input_shape = self._session.get_inputs()[0].shape
        self._output_names = [o.name for o in self._session.get_outputs()]

        # 提取元数据
        self._extract_metadata()

    def _extract_metadata(self) -> None:
        """提取 ONNX 模型元数据。"""
        if self._session is None:
            return

        try:
            model_meta = self._session.get_modelmeta()
            self._metadata = {
                "producer_name": getattr(model_meta, "producer_name", ""),
                "graph_name": getattr(model_meta, "graph_name", ""),
                "input_shape": self._input_shape,
                "format": ModelFormat.ONNX.value,
            }
        except Exception:
            self._metadata = {
                "input_shape": self._input_shape,
                "format": ModelFormat.ONNX.value,
            }

    def infer(self, image: np.ndarray, conf: float = 0.25, **kwargs) -> InferenceResult:
        """ONNX 单图推理。

        Args:
            image: RGB 格式图片数组 (H, W, 3)
            conf: 置信度阈值（用于后处理）

        Returns:
            InferenceResult 推理结果
        """
        if self._session is None:
            raise RuntimeError("模型未加载，请先调用 load()")

        start_time = time.time()

        # 预处理
        input_data = self._preprocess(image)

        # 推理
        outputs = self._session.run(self._output_names, {self._input_name: input_data})

        inference_ms = (time.time() - start_time) * 1000

        # 后处理
        detections = self._postprocess(outputs, conf)

        return InferenceResult(
            detections=detections,
            num_detections=len(detections),
            inference_ms=inference_ms,
            metadata=self._metadata.copy(),
        )

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图片。

        Args:
            image: RGB 图片数组

        Returns:
            NCHW 格式的输入张量
        """
        import cv2

        # 调整大小为模型输入尺寸（假设 640x640）
        input_size = self._input_shape[2] if self._input_shape and len(self._input_shape) == 4 else 640
        resized = cv2.resize(image, (input_size, input_size))

        # 归一化到 [0, 1]
        normalized = resized.astype(np.float32) / 255.0

        # 转换维度 HWC -> CHW
        transposed = np.transpose(normalized, (2, 0, 1))

        # 添加 batch 维度
        batched = np.expand_dims(transposed, axis=0)

        return batched

    def _postprocess(self, outputs: List[np.ndarray], conf: float) -> List[Dict[str, Any]]:
        """后处理输出。

        YOLOv8 ONNX 输出形状 [batch, (4+1+num_classes), num_anchors]
        例如 [1, 10, 8400] 其中 10 = 4(bbox) + 1(obj) + 6(num_classes)

        Args:
            outputs: 模型输出列表
            conf: 置信度阈值

        Returns:
            检测结果列表
        """
        import numpy as np

        detections = []
        if not outputs or outputs[0] is None:
            return detections

        output = outputs[0]  # shape: [1, 10, 8400]

        # YOLOv8 输出: [batch, (4+1+num_classes), num_anchors]
        # 0-3: bbox (cx, cy, w, h)，4: obj_conf，5-: class_scores
        num_classes = output.shape[1] - 5
        if num_classes < 1:
            num_classes = 6  # 默认值

        # 转置: [1, 10, 8400] -> [1, 8400, 10]
        output = output[0].T  # shape: [8400, 10]

        # 分离各部分
        bboxes_xywh = output[:, :4]     # [8400, 4]
        obj_conf = output[:, 4]          # [8400]
        class_scores = output[:, 5:]     # [8400, num_classes]

        # 计算 class_conf = obj_conf * class_prob (sigmoid)
        # 对 class_scores 做 sigmoid
        class_probs = 1 / (1 + np.exp(-class_scores))  # sigmoid
        class_conf = obj_conf[:, np.newaxis] * class_probs  # [8400, num_classes]

        # 取每个锚框最高置信度类别
        max_class_conf = np.max(class_conf, axis=1)   # [8400]
        max_class_ids = np.argmax(class_conf, axis=1)  # [8400]

        # 应用置信度阈值
        mask = max_class_conf >= conf
        if not np.any(mask):
            return detections

        # 获取满足条件的检测
        final_conf = max_class_conf[mask]
        final_cls_ids = max_class_ids[mask]
        final_xywh = bboxes_xywh[mask]

        # 转换 bbox: xywh -> xyxy (归一化坐标 -> 绝对坐标)
        # output 是归一化的，需要乘以特征图大小
        img_size = 640  # 假设固定输入尺寸
        for i in range(len(final_xywh)):
            cx, cy, w, h = final_xywh[i]
            # 归一化坐标转绝对坐标
            x1 = (cx - w / 2) * img_size
            y1 = (cy - h / 2) * img_size
            x2 = (cx + w / 2) * img_size
            y2 = (cy + h / 2) * img_size

            # clamp 到图像范围
            x1 = max(0, min(x1, img_size))
            y1 = max(0, min(y1, img_size))
            x2 = max(0, min(x2, img_size))
            y2 = max(0, min(y2, img_size))

            detections.append({
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "confidence": round(float(final_conf[i]), 4),
                "class_id": int(final_cls_ids[i]),
                "class_name": f"Class {int(final_cls_ids[i])}",
            })

        # 按置信度排序
        detections.sort(key=lambda x: x["confidence"], reverse=True)

        return detections
