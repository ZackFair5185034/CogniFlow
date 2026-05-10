# -*- coding: utf-8 -*-
"""模型格式枚举和扩展名检测。"""

from enum import Enum
from pathlib import Path
from typing import Dict, List


class ModelFormat(Enum):
    """支持的模型格式枚举。"""

    YOLO_PT = "yolo_pt"  # Ultralytics YOLO .pt 格式
    ONNX = "onnx"  # ONNX Runtime 格式
    OPENVINO = "openvino"  # Intel OpenVINO 格式
    TENSORRT = "tensorrt"  # NVIDIA TensorRT 格式
    PYTORCH = "pytorch"  # 通用 PyTorch .pt/.pth 格式

    @classmethod
    def from_path(cls, path: str) -> "ModelFormat":
        """根据文件路径推断格式。

        Args:
            path: 模型文件路径或 OpenVINO 导出目录

        Returns:
            ModelFormat 枚举值，默认为 YOLO_PT
        """
        import os

        suffix = Path(path).suffix.lower()
        format_map: Dict[str, "ModelFormat"] = {
            ".pt": cls.YOLO_PT,
            ".pth": cls.PYTORCH,
            ".onnx": cls.ONNX,
            ".xml": cls.OPENVINO,
            ".engine": cls.TENSORRT,
            ".plan": cls.TENSORRT,
        }

        detected = format_map.get(suffix)
        if detected is not None:
            return detected

        # suffix 为空时可能是目录路径（ultralytics 导出 OpenVINO 返回目录）
        if os.path.isdir(path):
            for f in os.listdir(path):
                if f.endswith(".xml"):
                    return cls.OPENVINO

        return cls.YOLO_PT

    @property
    def file_extensions(self) -> List[str]:
        """获取该格式对应的文件扩展名列表。"""
        extensions_map = {
            ModelFormat.YOLO_PT: [".pt"],
            ModelFormat.ONNX: [".onnx"],
            ModelFormat.OPENVINO: [".xml", ".bin"],
            ModelFormat.TENSORRT: [".engine", ".plan"],
            ModelFormat.PYTORCH: [".pt", ".pth"],
        }
        return extensions_map.get(self, [])

    @property
    def display_name(self) -> str:
        """获取格式的显示名称。"""
        names = {
            ModelFormat.YOLO_PT: "YOLO (.pt)",
            ModelFormat.ONNX: "ONNX",
            ModelFormat.OPENVINO: "OpenVINO",
            ModelFormat.TENSORRT: "TensorRT",
            ModelFormat.PYTORCH: "PyTorch",
        }
        return names.get(self, self.value)

    def __str__(self) -> str:
        return self.value


def detect_model_format(path: str) -> ModelFormat:
    """检测模型文件格式。

    Args:
        path: 模型文件路径

    Returns:
        ModelFormat 枚举值
    """
    return ModelFormat.from_path(path)
