# -*- coding: utf-8 -*-
"""YOLO 模型导出工具。"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.model_format import ModelFormat


class YoloExporter:
    """YOLO 模型导出器。

    将 YOLO .pt 模型导出为其他格式。
    """

    @staticmethod
    def export(
        model_path: str,
        target_format: ModelFormat,
        output_dir: str,
        half: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """导出 YOLO 模型到目标格式。

        Args:
            model_path: 源 .pt 模型路径
            target_format: 目标格式
            output_dir: 输出目录
            half: 是否导出为半精度 (FP16)
            **kwargs: 导出特定参数

        Returns:
            导出结果字典，包含 output_path, file_size 等

        Raises:
            ValueError: 不支持的目标格式
            RuntimeError: 导出失败
        """
        from ultralytics import YOLO

        # 支持导出的格式映射
        export_format_map = {
            ModelFormat.ONNX: "onnx",
            ModelFormat.OPENVINO: "openvino",
            ModelFormat.TENSORRT: "engine",
        }

        if target_format not in export_format_map:
            raise ValueError(f"YOLO 导出不支持目标格式: {target_format.value}")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 加载模型
        model = YOLO(model_path)

        # 导出
        export_format = export_format_map[target_format]

        try:
            export_path = model.export(
                format=export_format,
                half=half,
                **kwargs
            )
        except Exception as e:
            raise RuntimeError(f"导出失败: {e}")

        # 获取导出文件的实际路径
        if export_path is None or not os.path.exists(export_path):
            # ultralytics 可能返回 None，尝试推断输出路径
            stem = Path(model_path).stem
            ext = target_format.file_extensions[0] if target_format.file_extensions else ""
            export_path = os.path.join(output_dir, f"{stem}{ext}")
            if not os.path.exists(export_path):
                export_path = model_path + ext if ext else export_path

        return {
            "success": True,
            "source_format": ModelFormat.YOLO_PT.value,
            "target_format": target_format.value,
            "output_path": export_path,
            "file_size": os.path.getsize(export_path) if os.path.exists(export_path) else 0,
            "half": half,
        }

    @staticmethod
    def export_to_onnx(
        model_path: str,
        output_dir: str,
        half: bool = False,
        simplify: bool = True,
        dynamic: bool = True,
    ) -> Dict[str, Any]:
        """导出为 ONNX 格式。

        Args:
            model_path: 源 .pt 模型路径
            output_dir: 输出目录
            half: 是否导出为 FP16
            simplify: 是否简化模型
            dynamic: 是否使用动态尺寸

        Returns:
            导出结果
        """
        return YoloExporter.export(
            model_path=model_path,
            target_format=ModelFormat.ONNX,
            output_dir=output_dir,
            half=half,
            simplify=simplify,
            dynamic=dynamic,
        )

    @staticmethod
    def export_to_tensorrt(
        model_path: str,
        output_dir: str,
        half: bool = False,
    ) -> Dict[str, Any]:
        """导出为 TensorRT 格式。

        Args:
            model_path: 源 .pt 模型路径
            output_dir: 输出目录
            half: 是否导出为 FP16

        Returns:
            导出结果
        """
        return YoloExporter.export(
            model_path=model_path,
            target_format=ModelFormat.TENSORRT,
            output_dir=output_dir,
            half=half,
        )

    @staticmethod
    def export_to_openvino(
        model_path: str,
        output_dir: str,
        half: bool = False,
    ) -> Dict[str, Any]:
        """导出为 OpenVINO 格式。

        Args:
            model_path: 源 .pt 模型路径
            output_dir: 输出目录
            half: 是否导出为 FP16

        Returns:
            导出结果
        """
        return YoloExporter.export(
            model_path=model_path,
            target_format=ModelFormat.OPENVINO,
            output_dir=output_dir,
            half=half,
        )


def export_model(
    model_path: str,
    target_format: str,
    output_dir: str,
    half: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """便捷导出函数。

    Args:
        model_path: 源模型路径
        target_format: 目标格式字符串 ("onnx", "openvino", "tensorrt")
        output_dir: 输出目录
        half: 是否导出为半精度
        **kwargs: 其他导出参数

    Returns:
        导出结果
    """
    format_map = {
        "onnx": ModelFormat.ONNX,
        "openvino": ModelFormat.OPENVINO,
        "tensorrt": ModelFormat.TENSORRT,
    }

    model_format = format_map.get(target_format.lower())
    if model_format is None:
        raise ValueError(f"不支持的目标格式: {target_format}")

    return YoloExporter.export(
        model_path=model_path,
        target_format=model_format,
        output_dir=output_dir,
        half=half,
        **kwargs
    )
