# -*- coding: utf-8 -*-
"""硬件设备自动检测。"""

from typing import Any, Dict, Optional

from backend.core.backends.base import HardwareInfo


class DeviceDetector:
    """硬件设备检测器。

    自动检测系统可用的推理设备。
    """

    @staticmethod
    def detect_all() -> Dict[str, HardwareInfo]:
        """检测所有可用的推理设备。

        Returns:
            设备字典，key 为设备类型 (cpu/cuda/openvino/tensorrt)
        """
        devices: Dict[str, HardwareInfo] = {}

        # CPU - 始终可用
        devices["cpu"] = HardwareInfo(
            device_type="cpu",
            device_name="CPU",
            supports_fp16=False,
            supports_int8=True,
        )

        # CUDA - 检测 PyTorch CUDA
        cuda_info = DeviceDetector._detect_cuda()
        if cuda_info is not None:
            devices["cuda"] = cuda_info

        # OpenVINO - 检测 Intel OpenVINO
        openvino_info = DeviceDetector._detect_openvino()
        if openvino_info is not None:
            devices["openvino"] = openvino_info

        # TensorRT - 检测 NVIDIA TensorRT
        tensorrt_info = DeviceDetector._detect_tensorrt()
        if tensorrt_info is not None:
            devices["tensorrt"] = tensorrt_info

        return devices

    @staticmethod
    def _detect_cuda() -> Optional[HardwareInfo]:
        """检测 CUDA 可用性。

        Returns:
            CUDA 设备信息，如果不可用返回 None
        """
        try:
            import torch

            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                memory_total = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
                memory_free = memory_total  # 简化处理

                # Ampere 架构及更新支持 FP16
                device_capability = torch.cuda.get_device_capability(0)
                supports_fp16 = device_capability[0] >= 7  # Ampere+ (7.0)

                return HardwareInfo(
                    device_type="cuda",
                    device_name=device_name,
                    memory_total_mb=memory_total,
                    memory_free_mb=memory_free,
                    supports_fp16=supports_fp16,
                    supports_int8=True,
                    extra={"cuda_version": torch.version.cuda},
                )
        except Exception:
            pass

        return None

    @staticmethod
    def _detect_openvino() -> Optional[HardwareInfo]:
        """检测 OpenVINO 可用性。

        Returns:
            OpenVINO 设备信息，如果不可用返回 None
        """
        try:
            import openvino

            # 获取可用设备
            core = openvino.Core()
            devices = core.available_devices

            if not devices:
                return None

            # 优先使用 GPU
            device_name = "Intel"
            if "GPU" in devices:
                device_name = "Intel GPU"
            elif "CPU" in devices:
                device_name = "Intel CPU"

            return HardwareInfo(
                device_type="openvino",
                device_name=device_name,
                supports_fp16=True,
                supports_int8=True,
                extra={"available_devices": devices},
            )
        except ImportError:
            pass
        except Exception:
            pass

        return None

    @staticmethod
    def _detect_tensorrt() -> Optional[HardwareInfo]:
        """检测 TensorRT 可用性。

        Returns:
            TensorRT 设备信息，如果不可用返回 None
        """
        try:
            import tensorrt

            # TensorRT 通常与 CUDA 一起使用
            return HardwareInfo(
                device_type="tensorrt",
                device_name="NVIDIA TensorRT",
                supports_fp16=True,
                supports_int8=True,
            )
        except ImportError:
            pass
        except Exception:
            pass

        return None

    @staticmethod
    def pick_best(preference: str = "auto", precision: str = "fp32") -> str:
        """自动选择最佳设备。

        Args:
            preference: 用户偏好 (auto/cpu/cuda/openvino/tensorrt)
            precision: 推理精度 (fp32/fp16/int8)

        Returns:
            最佳设备字符串
        """
        devices = DeviceDetector.detect_all()

        # 用户明确指定
        if preference in devices:
            # 检查精度支持
            hw_info = devices[preference]
            if precision == "fp16" and not hw_info.supports_fp16:
                # 不支持 FP16，降级
                pass
            elif precision == "int8" and not hw_info.supports_int8:
                pass
            else:
                return preference

        # 自动选择
        if preference == "cuda" or preference == "auto":
            if "cuda" in devices:
                if precision == "fp16" and not devices["cuda"].supports_fp16:
                    pass  # 不支持 FP16，继续检查其他
                else:
                    return "cuda"

        if preference == "tensorrt" or preference == "auto":
            if "tensorrt" in devices:
                return "tensorrt"

        if preference == "openvino" or preference == "auto":
            if "openvino" in devices:
                return "openvino"

        # 默认 CPU
        return "cpu"

    @staticmethod
    def get_device_info_summary() -> Dict[str, Any]:
        """获取设备信息摘要。

        Returns:
            设备信息摘要字典
        """
        devices = DeviceDetector.detect_all()

        return {
            "devices": {k: v.to_dict() for k, v in devices.items()},
            "recommended": DeviceDetector.pick_best(),
        }
