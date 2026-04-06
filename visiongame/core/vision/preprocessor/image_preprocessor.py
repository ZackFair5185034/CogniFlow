"""VisionGame 图像预处理器模块 - 提供图像预处理和数据增强功能。"""

from typing import Tuple, List, Optional, Union
from pathlib import Path
import numpy as np
import torch
from torchvision import transforms

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class ImagePreprocessor:
    """图像预处理器，支持数据增强。

    支持功能：
    - 缩放和归一化
    - 数据增强
    - 批量处理
    """

    def __init__(
        self,
        image_size: Tuple[int, int] = (224, 224),
        normalize: bool = True,
        mean: List[float] = None,
        std: List[float] = None,
        augmentation: bool = False,
    ):
        """初始化预处理器。

        Args:
            image_size: 目标 (宽度, 高度)。
            normalize: 是否归一化图像。
            mean: 归一化均值。
            std: 归一化标准差。
            augmentation: 是否启用数据增强。
        """
        self.image_size = image_size
        self.normalize = normalize
        self.augmentation = augmentation

        if mean is None:
            mean = [0.485, 0.456, 0.406]
        if std is None:
            std = [0.229, 0.224, 0.225]

        self.mean = mean
        self.std = std

        # 构建转换管道
        self._build_transforms()

    def _build_transforms(self) -> None:
        """构建转换管道。"""
        transform_list = []

        # 缩放
        transform_list.append(transforms.Resize(self.image_size))

        # 转换为张量
        transform_list.append(transforms.ToTensor())

        # 归一化
        if self.normalize:
            transform_list.append(
                transforms.Normalize(mean=self.mean, std=self.std)
            )

        if self.augmentation:
            # 数据增强转换
            aug_transforms = [
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
                transforms.RandomGrayscale(p=0.1),
            ]
            # 在归一化之前插入增强
            if self.normalize:
                aug_transforms.insert(-1, transforms.Normalize(mean=self.mean, std=self.std))
            self.transform = transforms.Compose(transform_list[:-1] + aug_transforms if self.normalize else transforms.Compose(transform_list + aug_transforms))
        else:
            self.transform = transforms.Compose(transform_list)

    def __call__(self, image: np.ndarray) -> torch.Tensor:
        """预处理单张图像。

        Args:
            image: 输入图像 (H, W, C) RGB 格式。

        Returns:
            预处理后的张量 (C, H, W)。
        """
        if not CV2_AVAILABLE:
            raise ImportError("图像处理需要安装 OpenCV")

        # 确保 RGB 格式
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)

        # 转换为张量并应用转换
        # OpenCV 使用 HWC，transforms 期望 CHW 张量
        image_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0

        if self.normalize:
            for t, m, s in zip(image_tensor, self.mean, self.std):
                t.sub_(m).div_(s)

        # 缩放
        if image_tensor.shape[1:] != self.image_size[::-1]:
            image_tensor = torch.nn.functional.interpolate(
                image_tensor.unsqueeze(0),
                size=self.image_size[::-1],
                mode="bilinear",
                align_corners=False
            ).squeeze(0)

        return image_tensor

    def preprocess_batch(self, images: List[np.ndarray]) -> torch.Tensor:
        """预处理一批图像。

        Args:
            images: 输入图像列表。

        Returns:
            批次张量 (B, C, H, W)。
        """
        tensors = [self(img) for img in images]
        return torch.stack(tensors)

    def denormalize(self, tensor: torch.Tensor) -> np.ndarray:
        """将张量反归一化回图像。

        Args:
            tensor: 归一化张量 (C, H, W) 或 (B, C, H, W)。

        Returns:
            RGB 格式的图像数组 (H, W, C)。
        """
        if tensor.ndim == 4:
            tensor = tensor[0]  # 取批次中的第一个

        result = tensor.clone()
        if self.normalize:
            for t, m, s in zip(result, self.mean, self.std):
                t.mul_(s).add_(m)

        result = result.permute(1, 2, 0).numpy()
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        return result
