# -*- coding: utf-8 -*-
"""硬件设备自动检测。

设备检测在应用启动时执行一次，结果缓存复用，避免每次请求都重复检测。
"""

import logging
from typing import Any, Dict, Optional

from backend.core.backends.base import HardwareInfo

_logger = logging.getLogger(__name__)

# 启动时初始化的缓存
_device_cache: Optional[Dict[str, Any]] = None


def init_device_cache():
    """应用启动时调用一次，检测并缓存所有可用设备。"""
    global _device_cache
    _logger.info("正在检测推理设备...")
    _device_cache = DeviceDetector.detect_all()
    summary = {k: v.to_dict() for k, v in _device_cache.items()}
    recommended = DeviceDetector.pick_best()
    _logger.info(f"设备检测完成: {list(_device_cache.keys())}, 推荐: {recommended}")
    return {"devices": summary, "recommended": recommended}


def get_cached_device_info() -> Dict[str, Any]:
    """获取缓存的设备信息，如果尚未初始化则实时检测。"""
    global _device_cache
    if _device_cache is None:
        _logger.warning("设备缓存未初始化，执行实时检测（应在启动时调用 init_device_cache）")
        return init_device_cache()
    summary = {k: v.to_dict() for k, v in _device_cache.items()}
    recommended = DeviceDetector.pick_best()
    return {"devices": summary, "recommended": recommended}


def resolve_device_cached(preference: str = "auto") -> str:
    """使用缓存的设备信息解析最佳设备。

    Args:
        preference: 用户偏好 (auto/cpu/cuda/openvino/directml)

    Returns:
        实际使用的设备字符串
    """
    if preference in ("cpu", "cuda", "openvino", "directml"):
        return preference

    return DeviceDetector.pick_best(preference)


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

        # DirectML - Windows 通用 GPU 加速（AMD Radeon / NVIDIA / Intel）
        directml_info = DeviceDetector._detect_directml()
        if directml_info is not None:
            devices["directml"] = directml_info

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

            # 获取具体设备名称
            device_name = "CPU"
            try:
                if "GPU" in devices:
                    gpu_name = core.get_property("GPU", "FULL_DEVICE_NAME")
                    device_name = f"GPU: {gpu_name} (OpenVINO)"
                elif "CPU" in devices:
                    device_name = "CPU (OpenVINO)"
            except Exception:
                if "GPU" in devices:
                    device_name = "GPU (OpenVINO)"
                elif "CPU" in devices:
                    device_name = "CPU (OpenVINO)"

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
    def _detect_directml() -> Optional[HardwareInfo]:
        """检测 DirectML 可用性（Windows 通用 GPU 加速）。

        通过 ONNX Runtime 的 DmlExecutionProvider 检测，
        支持 AMD Radeon / NVIDIA / Intel 显卡。

        Returns:
            DirectML 设备信息，如果不可用返回 None
        """
        try:
            import onnxruntime as ort

            if "DmlExecutionProvider" in ort.get_available_providers():
                # 尝试获取 GPU 名称
                gpu_name = "DirectML GPU"
                try:
                    import subprocess
                    result = subprocess.run(
                        ['powershell', '-Command',
                         'Get-CimInstance Win32_VideoController | Where-Object {$_.Name -notlike "*Oray*" -and $_.Name -notlike "*Virtual*"} | Select-Object -ExpandProperty Name -First 1'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.stdout.strip():
                        gpu_name = result.stdout.strip()
                except Exception:
                    pass

                return HardwareInfo(
                    device_type="directml",
                    device_name=gpu_name,
                    supports_fp16=True,
                    supports_int8=False,
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

        if preference == "directml" or preference == "auto":
            if "directml" in devices:
                return "directml"

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
