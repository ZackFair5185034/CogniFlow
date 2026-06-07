# -*- coding: utf-8 -*-
"""推理精度枚举定义。"""

from enum import Enum


class Precision(Enum):
    """推理精度枚举。

    - FP32: 单精度浮点，兼容最好
    - FP16: 半精度浮点，速度快，显存省
    - INT8: 整数量化，速度最快，精度略降
    """

    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"

    @property
    def display_name(self) -> str:
        """获取精度的显示名称。"""
        names = {
            Precision.FP32: "FP32 (单精度)",
            Precision.FP16: "FP16 (半精度)",
            Precision.INT8: "INT8 (整数量化)",
        }
        return names.get(self, self.value)

    @property
    def description(self) -> str:
        """获取精度的描述。"""
        descriptions = {
            Precision.FP32: "兼容性好，速度一般",
            Precision.FP16: "速度提升30-50%，显存减半",
            Precision.INT8: "速度最快，精度略降",
        }
        return descriptions.get(self, "")

    def supports_device(self, device_type: str) -> bool:
        """检查该精度是否支持指定设备。

        Args:
            device_type: 设备类型 (cpu/cuda/openvino/tensorrt)

        Returns:
            是否支持
        """
        if self == Precision.FP32:
            return True
        if self == Precision.FP16:
            return device_type in ("cuda", "tensorrt")
        if self == Precision.INT8:
            return device_type in ("cpu", "cuda", "openvino")
        return False
