# -*- coding: utf-8 -*-
"""OpenVINO 格式处理器。

使用 Intel OpenVINO Runtime 进行推理，
支持 Intel/AMD GPU（通过 OpenVINO GPU 插件）。
"""

import time
import os
from typing import Dict, Any, List, Optional
import numpy as np

from backend.core.formats.base_handler import BaseModelHandler
from backend.core.interfaces import InferenceResult
from backend.core.model_format import ModelFormat


class OpenVinoModelHandler(BaseModelHandler):
    """OpenVINO 格式处理器。

    使用 openvino.Core() 加载 IR 模型（.xml + .bin），
    支持 GPU（Intel/AMD）和 CPU 设备。
    """

    def __init__(self):
        super().__init__()
        self._compiled_model: Optional[Any] = None
        self._input_shape: Optional[List[int]] = None
        self._letterbox_pad: Optional[tuple] = None  # (pad_left, pad_top, scale, orig_h, orig_w)
        self._class_names: Dict[int, str] = {}  # class_id -> class_name 映射

    @property
    def format(self) -> ModelFormat:
        """返回处理器支持的格式。"""
        return ModelFormat.OPENVINO

    def load(self, model_path: str, device: str = "cpu", **kwargs) -> None:
        """加载 OpenVINO 模型。

        Args:
            model_path: .xml 模型描述文件路径（自动关联同目录 .bin 权重文件）
            device: 设备标识 (cpu/cuda/openvino)
            **kwargs: 可包含 class_names (Dict[int, str]) 类别名称映射
        """
        super().load(model_path, device, **kwargs)

        # 提取类别名称映射
        if "class_names" in kwargs:
            self._class_names = kwargs["class_names"]

        import openvino as ov

        core = ov.Core()

        # 设备映射：OpenVINO 的设备概念与 PyTorch/ONNX 不同
        # "GPU" = GPU 插件（支持 Intel/AMD，通过 OpenCL/Level Zero）
        # "CPU" = CPU 插件
        if device in ("openvino", "cuda", "gpu"):
            if "GPU" in core.available_devices:
                ov_device = "GPU"
            else:
                ov_device = "CPU"
        else:
            ov_device = "CPU"

        # 解析实际模型文件路径（ultralytics 导出可能返回目录路径）
        xml_path = self._resolve_xml_path(model_path)
        if not xml_path:
            raise FileNotFoundError(f"未找到 OpenVINO IR 模型文件 (.xml): {model_path}")

        # GPU 性能优化
        if ov_device == "GPU":
            try:
                core.set_property("GPU", {"PERFORMANCE_HINT": "THROUGHPUT"})
            except Exception:
                pass  # 非 Intel GPU 可能不支持部分属性

        # 编译模型到目标设备
        self._compiled_model = core.compile_model(xml_path, ov_device)

        # 获取输入输出信息
        input_tensor = self._compiled_model.input(0)
        self._input_shape = list(input_tensor.shape)

        # 提取元数据
        self._extract_metadata(core, xml_path)

    def _resolve_xml_path(self, model_path: str) -> Optional[str]:
        """解析 .xml 模型文件的实际路径。

        ultralytics 导出 OpenVINO 格式时可能返回目录路径（包含 model.xml），
        也可能直接返回 .xml 文件路径。

        Args:
            model_path: 模型路径

        Returns:
            .xml 文件路径，未找到返回 None
        """
        if model_path.endswith(".xml"):
            if os.path.exists(model_path):
                return model_path
            return None

        # 可能是目录路径，在其中查找 .xml
        if os.path.isdir(model_path):
            for f in os.listdir(model_path):
                if f.endswith(".xml"):
                    return os.path.join(model_path, f)
            return None

        return None

    def _extract_metadata(self, core=None, xml_path: str = "") -> None:
        """提取 OpenVINO 模型元数据。"""
        if self._compiled_model is None:
            return

        self._metadata = {
            "input_shape": self._input_shape,
            "format": ModelFormat.OPENVINO.value,
        }

    def infer(self, image: np.ndarray, conf: float = 0.25, **kwargs) -> InferenceResult:
        """OpenVINO 单图推理。

        Args:
            image: RGB 格式图片数组 (H, W, 3)
            conf: 置信度阈值（用于后处理）

        Returns:
            InferenceResult 推理结果
        """
        if self._compiled_model is None:
            raise RuntimeError("模型未加载，请先调用 load()")

        start_time = time.time()

        # 预处理
        input_data = self._preprocess(image)

        # 推理
        outputs = self._compiled_model([input_data])

        inference_ms = (time.time() - start_time) * 1000

        # 取第一个输出张量
        output_tensor = list(outputs.values())[0]

        # 后处理
        detections = self._postprocess(output_tensor, conf)

        return InferenceResult(
            detections=detections,
            num_detections=len(detections),
            inference_ms=inference_ms,
            metadata=self._metadata.copy(),
        )

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图片。

        使用 letterbox 方式将图片缩放到 640x640，保持宽高比并填充。

        Args:
            image: RGB 图片数组

        Returns:
            NCHW 格式的输入张量
        """
        import cv2

        input_size = self._input_shape[2] if self._input_shape and len(self._input_shape) == 4 else 640

        orig_h, orig_w = image.shape[:2]

        # 计算缩放因子，保持宽高比
        scale = input_size / max(orig_h, orig_w)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        # 保存 letterbox 信息用于后处理
        pad_left = (input_size - new_w) // 2
        pad_top = (input_size - new_h) // 2
        self._letterbox_pad = (pad_left, pad_top, scale, orig_h, orig_w)

        # 缩放图片
        resized = cv2.resize(image, (new_w, new_h))

        # 创建 640x640 的画布并填充
        padded = np.zeros((input_size, input_size, 3), dtype=image.dtype)
        padded[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized

        # 归一化到 [0, 1]
        normalized = padded.astype(np.float32) / 255.0

        # 转换维度 HWC -> CHW
        transposed = np.transpose(normalized, (2, 0, 1))

        # 添加 batch 维度
        batched = np.expand_dims(transposed, axis=0)

        return batched

    def _postprocess(self, output: np.ndarray, conf: float) -> List[Dict[str, Any]]:
        """后处理输出。

        YOLOv8 OpenVINO IR 输出格式与 ONNX 一致：
        [batch, 4+num_classes, num_anchors] 每个 class 通道独立置信度（已 sigmoid 激活）。

        Args:
            output: 模型输出张量
            conf: 置信度阈值

        Returns:
            检测结果列表
        """
        import numpy as np

        detections = []
        if output is None or output.size == 0:
            return detections

        # 确保输出为 [N, C] 格式
        if output.ndim == 3:
            output = output[0]  # [1, C, 8400] -> [C, 8400]
            output = output.T    # [C, 8400] -> [8400, C]
        elif output.ndim == 2:
            # 已经是 [8400, C] 格式
            pass

        # 分离各部分
        bboxes_xywh = output[:, :4]     # [8400, 4] bbox 坐标 (cx, cy, w, h)
        class_scores = output[:, 4:]    # [8400, num_classes] 各类别独立置信度

        # 取每个锚框最高置信度类别
        max_class_conf = np.max(class_scores, axis=1)  # [8400]
        max_class_ids = np.argmax(class_scores, axis=1)  # [8400]

        # 应用置信度阈值
        mask = max_class_conf >= conf
        if not np.any(mask):
            return detections

        # 获取满足条件的检测
        final_conf = max_class_conf[mask]
        final_cls_ids = max_class_ids[mask]
        final_xywh = bboxes_xywh[mask]

        # 获取 letterbox 信息用于坐标逆变换
        pad_left, pad_top, scale, orig_h, orig_w = self._letterbox_pad if self._letterbox_pad else (0, 0, 1.0, 640, 640)

        # 转换 bbox: xywh -> xyxy 并进行 letterbox 逆变换
        all_boxes = []
        all_scores = []
        all_class_ids = []

        for i in range(len(final_xywh)):
            cx, cy, w, h = final_xywh[i]

            # 转换中心点+尺寸格式为角点格式
            x1 = cx - w / 2
            y1 = cy - h / 2
            x2 = cx + w / 2
            y2 = cy + h / 2

            # 逆 letterbox 变换：减去 padding 并除以 scale
            x1 = (x1 - pad_left) / scale
            y1 = (y1 - pad_top) / scale
            x2 = (x2 - pad_left) / scale
            y2 = (y2 - pad_top) / scale

            # clamp 到图像范围（原图尺寸）
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))

            # 确保 bbox 有效（宽度和高度大于0）
            if x2 - x1 < 1 or y2 - y1 < 1:
                continue

            all_boxes.append([x1, y1, x2, y2])
            all_scores.append(final_conf[i])
            all_class_ids.append(final_cls_ids[i])

        if not all_boxes:
            return detections

        # NMS 处理去除重复检测
        boxes_np = np.array(all_boxes)
        scores_np = np.array(all_scores)
        class_ids_np = np.array(all_class_ids)

        # 对每个类别分别做 NMS
        keep_indices = []
        for cls_id in np.unique(class_ids_np):
            cls_mask = class_ids_np == cls_id
            cls_boxes = boxes_np[cls_mask]
            cls_scores = scores_np[cls_mask]

            if len(cls_boxes) == 0:
                continue

            # 计算 box 面积
            x1, y1, x2, y2 = cls_boxes.T
            areas = (x2 - x1) * (y2 - y1)

            # 按分数排序
            order = cls_scores.argsort()[::-1]

            while len(order) > 0:
                i = order[0]
                keep_indices.append(np.where(cls_mask)[0][i])

                if len(order) == 1:
                    break

                # 计算 IoU
                xx1 = np.maximum(cls_boxes[i, 0], cls_boxes[order[1:], 0])
                yy1 = np.maximum(cls_boxes[i, 1], cls_boxes[order[1:], 1])
                xx2 = np.minimum(cls_boxes[i, 2], cls_boxes[order[1:], 2])
                yy2 = np.minimum(cls_boxes[i, 3], cls_boxes[order[1:], 3])

                w = np.maximum(0.0, xx2 - xx1)
                h = np.maximum(0.0, yy2 - yy1)
                inter = w * h

                iou = inter / (areas[i] + areas[order[1:]] - inter)

                # 保留 IoU < thresh 的
                keep_mask = iou <= 0.5
                order = order[1:][keep_mask]

        # 按置信度排序
        keep_indices = sorted(keep_indices, key=lambda i: all_scores[i], reverse=True)

        for i in keep_indices:
            cls_id = int(all_class_ids[i])
            detections.append({
                "bbox": [int(x) for x in all_boxes[i]],
                "confidence": round(float(all_scores[i]), 4),
                "class_id": cls_id,
                "class_name": self._class_names.get(cls_id, f"Class {cls_id}"),
            })

        return detections
