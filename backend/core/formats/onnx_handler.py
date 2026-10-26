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
        self._letterbox_pad: Optional[tuple] = None  # (pad_left, pad_top, scale, orig_h, orig_w)
        self._class_names: Dict[int, str] = {}  # class_id -> class_name 映射

    @property
    def format(self) -> ModelFormat:
        """返回处理器支持的格式。"""
        return ModelFormat.ONNX

    def load(self, model_path: str, device: str = "cpu", **kwargs) -> None:
        """加载 ONNX 模型。

        Args:
            model_path: .onnx 文件路径
            device: 设备 (cpu/cuda/directml)
            **kwargs: 可包含 class_names (Dict[int, str]), precision (fp32/fp16)
        """
        super().load(model_path, device, **kwargs)

        # 提取类别名称映射
        if "class_names" in kwargs:
            self._class_names = kwargs["class_names"]

        precision = kwargs.get("precision", "fp32")

        import onnxruntime as ort

        # 配置 Session 选项以优化推理性能
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.enable_mem_pattern = True

        # 配置 providers（按优先级排列，可附加 provider 特定选项）
        providers = []
        if device == "cuda":
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        elif device == "directml":
            # DirectML: Windows 通用 GPU 加速，支持 AMD Radeon / NVIDIA / Intel
            # FP16 模式下启用 fp16_enabled 选项，让 GPU 以半精度执行部分算子
            dml_opts = {}
            if precision == "fp16":
                dml_opts["fp16_enabled"] = "1"
            providers = [
                ("DmlExecutionProvider", dml_opts) if dml_opts else "DmlExecutionProvider",
                "CPUExecutionProvider",
            ]
        elif device == "mps":
            providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
        elif device in ("openvino",):
            providers = ["CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]

        self._session = ort.InferenceSession(
            model_path, sess_options=sess_options, providers=providers
        )

        # 诊断日志：确认实际使用的执行提供器
        import logging
        _logger = logging.getLogger("cogniflow")
        _actual_providers = self._session.get_providers()
        _logger.info(
            "ONNX 模型已加载: %s, 请求设备=%s, 实际执行提供器=%s",
            model_path, device, _actual_providers,
        )

        # 获取输入输出信息
        self._input_name = self._session.get_inputs()[0].name
        self._input_shape = self._session.get_inputs()[0].shape
        self._output_names = [o.name for o in self._session.get_outputs()]

        # 提取元数据
        self._extract_metadata()

        # 帧计时计数器（用于周期性诊断日志）
        self._frame_count = 0
        self._preprocess_total_ms = 0.0
        self._infer_total_ms = 0.0
        self._postprocess_total_ms = 0.0

    def _extract_metadata(self) -> None:
        """提取 ONNX 模型元数据。"""
        if self._session is None:
            return

        # 记录实际使用的执行提供器
        actual_providers = self._session.get_providers()
        requested = getattr(self, '_device', 'cpu')

        try:
            model_meta = self._session.get_modelmeta()
            self._metadata = {
                "producer_name": getattr(model_meta, "producer_name", ""),
                "graph_name": getattr(model_meta, "graph_name", ""),
                "input_shape": self._input_shape,
                "format": ModelFormat.ONNX.value,
                "execution_provider": actual_providers[0] if actual_providers else "unknown",
            }
        except Exception:
            self._metadata = {
                "input_shape": self._input_shape,
                "format": ModelFormat.ONNX.value,
                "execution_provider": actual_providers[0] if actual_providers else "unknown",
            }

        # 如果请求了 GPU 但实际用了 CPU，给出警告
        import logging
        _logger = logging.getLogger(__name__)
        gpu_devices = ("cuda", "directml")
        if requested in gpu_devices and actual_providers and actual_providers[0] == "CPUExecutionProvider":
            hint = {
                "cuda": "请确认已安装 onnxruntime-gpu 且 CUDA 可用。",
                "directml": "请确认已安装 onnxruntime-directml。",
            }.get(requested, "")
            _logger.warning(
                f"ONNX: 请求 {requested} 加速但实际使用 CPU。{hint}"
            )

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

        import logging
        _logger = logging.getLogger("cogniflow")

        t0 = time.time()

        # 预处理
        input_data = self._preprocess(image)
        t1 = time.time()

        # 推理
        outputs = self._session.run(self._output_names, {self._input_name: input_data})
        t2 = time.time()

        # 后处理
        detections = self._postprocess(outputs, conf)
        t3 = time.time()

        preprocess_ms = (t1 - t0) * 1000
        infer_ms = (t2 - t1) * 1000
        postprocess_ms = (t3 - t2) * 1000
        total_ms = (t3 - t0) * 1000

        # 累计计时，每 30 帧输出一次诊断
        self._frame_count += 1
        self._preprocess_total_ms += preprocess_ms
        self._infer_total_ms += infer_ms
        self._postprocess_total_ms += postprocess_ms

        if self._frame_count % 30 == 0:
            n = self._frame_count
            avg_pre = self._preprocess_total_ms / n
            avg_inf = self._infer_total_ms / n
            avg_post = self._postprocess_total_ms / n
            avg_total = avg_pre + avg_inf + avg_post
            _logger.info(
                "ONNX 帧诊断 #%d: 预处理=%.1fms(%.0f%%), 推理=%.1fms(%.0f%%), "
                "后处理=%.1fms(%.0f%%), 总=%.1fms, 提供器=%s",
                n,
                avg_pre, avg_pre / avg_total * 100,
                avg_inf, avg_inf / avg_total * 100,
                avg_post, avg_post / avg_total * 100,
                avg_total,
                self._metadata.get("execution_provider", "?"),
            )

        return InferenceResult(
            detections=detections,
            num_detections=len(detections),
            inference_ms=total_ms,
            metadata=self._metadata.copy(),
        )

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图片。

        使用 letterbox 方式将图片缩放到 640x640，保持宽高比并在左侧和顶部填充。

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

    def _postprocess(self, outputs: List[np.ndarray], conf: float) -> List[Dict[str, Any]]:
        """后处理输出。

        YOLOv8 ONNX 输出形状 [batch, 4+num_classes, num_anchors]
        例如 [1, 10, 8400] 其中 10 = 4(bbox) + 6(class_scores)

        每个 class 通道都是独立的置信度分数（已在 ONNX 导出时包含 sigmoid 激活），
        无需 obj * class_scores 乘法。

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

        output = outputs[0]  # shape: [1, 4+num_classes, 8400]

        # 转置: [1, C, 8400] -> [8400, C]
        output = output[0].T

        # 分离各部分
        bboxes_xywh = output[:, :4]     # [8400, 4] bbox 坐标 (cx, cy, w, h)
        class_scores = output[:, 4:]    # [8400, num_classes] 各类别独立置信度（已 sigmoid 激活）

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
        # YOLOv8 ONNX 输出的 bbox 是在 640x640 letterbox 坐标系中的值
        # 需要减去 padding 并除以 scale 来获取原图坐标

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
