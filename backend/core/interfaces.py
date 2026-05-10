# -*- coding: utf-8 -*-
"""核心接口定义 - InferenceResult 和 IModelHandler 协议。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any
import numpy as np


@dataclass
class InferenceResult:
    """推理结果数据类。

    Attributes:
        detections: 检测结果列表，每项包含 bbox, confidence, class_id, class_name
        num_detections: 检测数量
        inference_ms: 推理耗时（毫秒）
        metadata: 额外元数据（如模型名称、格式等）
    """

    detections: List[Dict[str, Any]] = field(default_factory=list)
    num_detections: int = 0
    inference_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "detections": self.detections,
            "num_detections": self.num_detections,
            "inference_ms": self.inference_ms,
            "metadata": self.metadata,
        }


class IModelHandler(ABC):
    """模型处理器接口协议。

    所有模型格式处理器必须实现此接口。
    """

    @property
    @abstractmethod
    def format(self) -> "ModelFormat":
        """返回处理器支持的格式。"""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """返回模型是否已加载。"""
        pass

    @abstractmethod
    def load(self, model_path: str, device: str = "cpu", **kwargs) -> None:
        """加载模型。

        Args:
            model_path: 模型文件路径
            device: 设备标识 (cpu/cuda/mps 等)
            **kwargs: 格式特定参数
        """
        pass

    @abstractmethod
    def infer(self, image: np.ndarray, conf: float = 0.25, **kwargs) -> InferenceResult:
        """单图推理。

        Args:
            image: RGB 格式图片数组 (H, W, 3)
            conf: 置信度阈值
            **kwargs: 推理特定参数

        Returns:
            InferenceResult 推理结果
        """
        pass

    @abstractmethod
    def infer_batch(
        self, images: List[np.ndarray], conf: float = 0.25, **kwargs
    ) -> List[InferenceResult]:
        """批量推理。

        Args:
            images: RGB 格式图片数组列表
            conf: 置信度阈值
            **kwargs: 推理特定参数

        Returns:
            InferenceResult 列表
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """卸载模型，释放资源。"""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """获取模型元数据。

        Returns:
            元数据字典（类别名、输入尺寸等）
        """
        pass
