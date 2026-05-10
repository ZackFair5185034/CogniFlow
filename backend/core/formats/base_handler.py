# -*- coding: utf-8 -*-
"""模型处理器抽象基类。"""

from abc import ABC
from typing import Dict, Any, List
import numpy as np

from backend.core.interfaces import IModelHandler, InferenceResult
from backend.core.model_format import ModelFormat


class BaseModelHandler(IModelHandler, ABC):
    """模型处理器抽象基类。

    提供通用功能，子类只需实现格式特定逻辑。
    """

    def __init__(self):
        self._model: Any = None
        self._model_path: str = ""
        self._device: str = "cpu"
        self._metadata: Dict[str, Any] = {}

    @property
    def is_loaded(self) -> bool:
        """返回模型是否已加载。"""
        return self._model is not None

    def load(self, model_path: str, device: str = "cpu", **kwargs) -> None:
        """加载模型。

        默认实现检查文件是否存在，子类可重写以添加格式特定逻辑。

        Args:
            model_path: 模型文件路径
            device: 设备标识 (cpu/cuda)
        """
        import os

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        self._model_path = model_path
        self._device = device

    def unload(self) -> None:
        """卸载模型，释放资源。"""
        self._model = None
        self._model_path = ""

    def get_metadata(self) -> Dict[str, Any]:
        """获取模型元数据。"""
        return self._metadata.copy()

    def infer(self, image: np.ndarray, conf: float = 0.25, **kwargs) -> InferenceResult:
        """单图推理 - 子类必须实现。"""
        raise NotImplementedError("子类必须实现 infer() 方法")

    def infer_batch(
        self, images: List[np.ndarray], conf: float = 0.25, **kwargs
    ) -> List[InferenceResult]:
        """批量推理 - 默认逐个推理，子类可优化。"""
        return [self.infer(img, conf, **kwargs) for img in images]
