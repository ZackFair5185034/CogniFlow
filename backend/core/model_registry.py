# -*- coding: utf-8 -*-
"""模型处理器注册表 - 工厂模式实现。"""

import os
from typing import Dict, Type, Optional, List

from backend.core.model_format import ModelFormat, detect_model_format
from backend.core.interfaces import IModelHandler


class ModelHandlerRegistry:
    """模型处理器注册表。

    单例模式，管理所有格式的模型处理器。
    参考 backend/services/rule_engine/registry.py 的工厂模式实现。
    """

    _instance: Optional["ModelHandlerRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: Dict[ModelFormat, Type[IModelHandler]] = {}
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._handlers: Dict[ModelFormat, Type[IModelHandler]] = {}
            self._initialized = True

    def register(self, model_format: ModelFormat, handler_class: Type[IModelHandler]) -> None:
        """注册模型处理器。

        Args:
            model_format: 模型格式枚举
            handler_class: 处理器类（必须实现 IModelHandler）
        """
        if not issubclass(handler_class, IModelHandler):
            raise ValueError(f"{handler_class.__name__} 必须实现 IModelHandler 接口")

        self._handlers[model_format] = handler_class

    def get_handler_class(self, model_format: ModelFormat) -> Optional[Type[IModelHandler]]:
        """获取指定格式的处理器类。

        Args:
            model_format: 模型格式枚举

        Returns:
            处理器类，未找到返回 None
        """
        return self._handlers.get(model_format)

    def from_path(self, model_path: str, device: str = "cpu", **kwargs) -> IModelHandler:
        """根据模型文件路径创建处理器实例。

        自动检测格式并创建对应处理器。

        Args:
            model_path: 模型文件路径
            device: 设备标识
            **kwargs: 格式特定参数

        Returns:
            模型处理器实例

        Raises:
            FileNotFoundError: 模型文件不存在
            ValueError: 不支持的模型格式
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        model_format = detect_model_format(model_path)
        handler_class = self.get_handler_class(model_format)

        if handler_class is None:
            raise ValueError(
                f"不支持的模型格式: {model_format.value}，请先注册处理器"
            )

        handler = handler_class()
        handler.load(model_path, device, **kwargs)

        return handler

    def list_formats(self) -> List[ModelFormat]:
        """列出所有已注册的格式。

        Returns:
            ModelFormat 枚举列表
        """
        return list(self._handlers.keys())

    def is_format_supported(self, model_format: ModelFormat) -> bool:
        """检查格式是否支持。

        Args:
            model_format: 模型格式枚举

        Returns:
            是否支持
        """
        return model_format in self._handlers


def init_model_handlers() -> ModelHandlerRegistry:
    """初始化内置模型处理器。

    Returns:
        已注册内置处理器的注册表实例
    """
    registry = ModelHandlerRegistry()

    # 避免重复注册
    if registry.list_formats():
        return registry

    # 注册内置处理器
    from backend.core.formats.yolo_handler import YoloModelHandler
    from backend.core.formats.onnx_handler import OnnxModelHandler
    from backend.core.formats.openvino_handler import OpenVinoModelHandler

    registry.register(ModelFormat.YOLO_PT, YoloModelHandler)
    registry.register(ModelFormat.ONNX, OnnxModelHandler)
    registry.register(ModelFormat.OPENVINO, OpenVinoModelHandler)

    return registry


def create_model_handler(
    model_path: str, device: str = "cpu", **kwargs
) -> IModelHandler:
    """根据模型文件路径创建处理器实例。

    便捷函数，自动初始化注册表。

    Args:
        model_path: 模型文件路径
        device: 设备标识
        **kwargs: 格式特定参数

    Returns:
        模型处理器实例
    """
    init_model_handlers()
    return ModelHandlerRegistry().from_path(model_path, device, **kwargs)
