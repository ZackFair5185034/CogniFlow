# -*- coding: utf-8 -*-
"""硬件信息数据和推理后端抽象。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class HardwareInfo:
    """硬件设备信息。

    Attributes:
        device_type: 设备类型 (cpu/cuda/openvino/tensorrt)
        device_name: 设备名称
        memory_total_mb: 总显存/内存 (MB)
        memory_free_mb: 可用显存/内存 (MB)
        supports_fp16: 是否支持 FP16
        supports_int8: 是否支持 INT8
    """

    device_type: str
    device_name: str
    memory_total_mb: int = 0
    memory_free_mb: int = 0
    supports_fp16: bool = False
    supports_int8: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """获取设备的显示名称（用于前端下拉框）。"""
        if self.device_type == "cpu":
            return f"CPU ({self.device_name})"
        elif self.device_type == "cuda":
            return f"GPU: {self.device_name} (CUDA)"
        elif self.device_type == "openvino":
            return f"{self.device_name}"
        elif self.device_type == "directml":
            return f"GPU: {self.device_name} (DirectML)"
        elif self.device_type == "directml":
            return f"GPU: {self.device_name} (DirectML)"
        elif self.device_type == "tensorrt":
            return f"GPU: {self.device_name} (TensorRT)"
        return self.device_name

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "device_type": self.device_type,
            "device_name": self.device_name,
            "display_name": self.display_name,
            "memory_total_mb": self.memory_total_mb,
            "memory_free_mb": self.memory_free_mb,
            "supports_fp16": self.supports_fp16,
            "supports_int8": self.supports_int8,
            **self.extra,
        }


class InferenceBackend(ABC):
    """推理后端抽象基类。

    定义推理后端的通用接口。
    """

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """返回后端类型。"""
        pass

    @abstractmethod
    def get_hardware_info(self) -> HardwareInfo:
        """获取硬件信息。"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用。"""
        pass

    @abstractmethod
    def create_session(self, model_path: str, device: str = "cpu") -> Any:
        """创建推理会话。

        Args:
            model_path: 模型文件路径
            device: 设备标识

        Returns:
            推理会话对象
        """
        pass
