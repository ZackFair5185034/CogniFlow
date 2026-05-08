# -*- coding: utf-8 -*-
"""硬件后端模块。

提供硬件设备检测和推理后端抽象。
"""

from backend.core.backends.base import HardwareInfo, InferenceBackend
from backend.core.backends.auto_detector import DeviceDetector
from backend.core.backends.precision import Precision

__all__ = [
    "HardwareInfo",
    "InferenceBackend",
    "DeviceDetector",
    "Precision",
]
