# -*- coding: utf-8 -*-
"""CogniFlow 核心模块 - 模型格式抽象和硬件加速支持。

本模块提供：
- ModelFormat: 模型格式枚举和检测
- IModelHandler: 模型处理器接口协议
- InferenceResult: 推理结果数据结构
- ModelHandlerRegistry: 模型处理器工厂注册表
- DeviceDetector: 硬件设备自动检测
- HardwareInfo: 硬件设备信息
- Precision: 推理精度枚举
"""

from backend.core.model_format import ModelFormat, detect_model_format
from backend.core.interfaces import InferenceResult, IModelHandler
from backend.core.model_registry import ModelHandlerRegistry, init_model_handlers
from backend.core.backends import DeviceDetector, HardwareInfo, Precision

__all__ = [
    "ModelFormat",
    "detect_model_format",
    "InferenceResult",
    "IModelHandler",
    "ModelHandlerRegistry",
    "init_model_handlers",
    "DeviceDetector",
    "HardwareInfo",
    "Precision",
]
