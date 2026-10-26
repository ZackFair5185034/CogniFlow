# -*- coding: utf-8 -*-
"""推理服务 - 跨 router/service 共用的 YOLO/ONNX/OpenVINO 推理原语。

设计动机 (BE-P0-1, 2026-06-19):
- 之前 load_yolo_model / inference_yolo 实现在 backend/routers/yolo_training.py,
  被 backend/services/rule_engine/nodes/detection_nodes.py 反向依赖
  (函数内 from backend.routers.yolo_training import ...).
- 依赖方向反了, service 层不该 import router 层.
- 抽到本模块后:
  - routers/yolo_training.py 不再 export 推理函数, 仅做 HTTP 编解码
  - routers/inference.py 改为 import 本模块
  - rule_engine 节点 import 本模块 (顶部, 不再函数内延迟)

层次: services.inference_service → core.model_registry (合规)
      services.rule_engine.nodes.detection_nodes → services.inference_service (合规)
      routers.yolo_training / routers.inference → services.inference_service (合规)
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger("cogniflow")


def load_yolo_model(
    model_path: str,
    device: str = "cpu",
    class_names: dict = None,
    precision: str = "fp32",
):
    """加载 YOLO/ONNX/OpenVINO 模型用于推理。

    Args:
        model_path: 模型文件路径
        device: 设备标识 (cpu/cuda/directml/openvino)
        class_names: 类别名称映射 {id: name}，用于 ONNX/OpenVINO 格式的 fallback
        precision: 推理精度 (fp32/fp16)，仅对 ONNX DirectML/CUDA 有效

    Returns:
        YOLO 模型实例（向后兼容），或 handler 本身（如果是 ONNX 等格式）
    """
    from backend.core.model_registry import ModelHandlerRegistry, init_model_handlers

    # 初始化内置处理器
    init_model_handlers()

    logger.info("load_yolo_model: 路径=%s, 设备=%s, 精度=%s", model_path, device, precision)

    # 如果是 ONNX 或 OpenVINO 格式，尝试从对应 PT 文件提取类别名称
    extra_kwargs = {}
    extra_kwargs["precision"] = precision
    _is_onnx_ov = model_path.endswith((".onnx", ".xml")) or (
        os.path.isdir(model_path) and any(f.endswith(".xml") for f in (os.listdir(model_path) if os.path.isdir(model_path) else []))
    )
    if _is_onnx_ov:
        logger.info("load_yolo_model: 检测到 ONNX/OpenVINO 格式，文件=%s", model_path)
        pt_path = _find_pt_model(model_path)
        if pt_path:
            names = _extract_class_names(pt_path)
            if names:
                extra_kwargs["class_names"] = names

        # fallback：从 DB 传入的类别名称（PT 文件找不到时使用）
        if not extra_kwargs.get("class_names") and class_names:
            extra_kwargs["class_names"] = class_names
    else:
        logger.info("load_yolo_model: YOLO PT 格式，文件=%s", model_path)

    # 通过注册表创建处理器
    handler = ModelHandlerRegistry().from_path(model_path, device=device, **extra_kwargs)
    logger.info(
        "load_yolo_model: 处理器类型=%s, 有_model=%s",
        type(handler).__name__,
        hasattr(handler, "_model") and handler._model is not None,
    )

    # 返回原始 YOLO 实例供现有代码使用（向后兼容）
    if hasattr(handler, "_model") and handler._model is not None:
        logger.info("load_yolo_model: 返回 YOLO 模型实例")
        return handler._model
    # ONNX 等格式没有 _model，返回 handler 本身
    logger.info("load_yolo_model: 返回 handler 本身 (ONNX/OpenVINO)")
    return handler


def _find_pt_model(model_path: str) -> Optional[str]:
    """查找与指定模型对应的 PT 模型文件。

    搜索策略：
    1. 同目录下同名 .pt 文件
    2. 目录本身是 OpenVINO 导出目录时，在上级查找
    3. 父目录下任意 .pt 文件
    """
    # 如果是目录（OpenVINO 导出目录），在上级目录查找
    if os.path.isdir(model_path):
        parent_dir = os.path.dirname(model_path)
        if os.path.exists(parent_dir):
            for f in os.listdir(parent_dir):
                if f.endswith(".pt"):
                    return os.path.join(parent_dir, f)
        return None

    # 同名替换扩展名
    pt_path = model_path.rsplit(".", 1)[0] + ".pt"
    if os.path.exists(pt_path):
        return pt_path

    # 处理可能的命名差异（如 model_best.onnx -> best.pt）
    base_dir = os.path.dirname(model_path)
    if os.path.exists(base_dir):
        for f in os.listdir(base_dir):
            if f.endswith(".pt"):
                return os.path.join(base_dir, f)

    return None


def _extract_class_names(pt_model_path: str) -> Optional[Dict[int, str]]:
    """从 PT 模型文件中提取类别名称映射。"""
    try:
        import torch

        ckpt = torch.load(pt_model_path, map_location="cpu", weights_only=False)
        model = ckpt.get("model")
        if model and hasattr(model, "names"):
            return model.names
    except Exception:
        pass

    return None


def inference_yolo(
    model,
    image_path: str,
    conf_threshold: float = 0.25,
    device: str = "cpu",
) -> Dict:
    """使用 YOLO 模型进行推理。

    Args:
        model: 加载的 YOLO 模型
        image_path: 图片路径
        conf_threshold: 置信度阈值
        device: 推理设备 (cpu/cuda/auto/directml)

    Returns:
        检测结果字典
    """
    # Ultralytics YOLO 支持 device 关键字：把 model 临时 to(device) 后推理
    # 注意：不要调用 model.to(target_device) —— 那会永久 in-place 修改 cached 实例，
    # 后续 model(...) 的 device= 关键字已能处理 device 切换（一次性、临时）。
    target_device = None if device == "auto" else device
    results = model(image_path, conf=conf_threshold, device=target_device)

    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                detections.append({
                    'bbox': box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
                    'confidence': float(box.conf[0]),
                    'class_id': int(box.cls[0]),
                    'class_name': result.names[int(box.cls[0])]
                })

    return {
        'image_path': image_path,
        'num_detections': len(detections),
        'detections': detections
    }
