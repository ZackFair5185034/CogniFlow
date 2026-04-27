"""CogniFlow CNN 特征编码器模块 - 提供多种骨干网络的特征提取。"""

from typing import Optional, Tuple
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from torchvision import models


class CNNEncoder(nn.Module):
    """基于 CNN 的特征编码器。

    支持多种骨干网络：
    - ResNet18, ResNet34, ResNet50
    - MobileNetV2, V3
    - EfficientNet-B0
    """

    BACKBONES = {
        "resnet18": {"model": models.resnet18, "feature_dim": 512},
        "resnet34": {"model": models.resnet34, "feature_dim": 512},
        "resnet50": {"model": models.resnet50, "feature_dim": 2048},
        "mobilenet_v2": {"model": models.mobilenet_v2, "feature_dim": 1280},
        "mobilenet_v3_small": {"model": models.mobilenet_v3_small, "feature_dim": 576},
        "mobilenet_v3_large": {"model": models.mobilenet_v3_large, "feature_dim": 960},
        "efficientnet_b0": {"model": models.efficientnet_b0, "feature_dim": 1280},
    }

    def __init__(
        self,
        backbone: str = "resnet18",
        pretrained: bool = True,
        feature_dim: Optional[int] = None,
        freeze_backbone: bool = False,
    ):
        """初始化 CNN 编码器。

        Args:
            backbone: 骨干网络名称。
            pretrained: 是否使用预训练权重。
            feature_dim: 输出特征维度 (None = 使用骨干网络默认值)。
            freeze_backbone: 是否冻结骨干网络权重。
        """
        super().__init__()

        if backbone not in self.BACKBONES:
            raise ValueError(f"未知的骨干网络: {backbone}。可用选项: {list(self.BACKBONES.keys())}")

        self.backbone_name = backbone
        self.pretrained = pretrained

        # Load backbone
        backbone_fn = self.BACKBONES[backbone]["model"]
        self.backbone = backbone_fn(pretrained=pretrained)

        # Get feature dimension
        default_dim = self.BACKBONES[backbone]["feature_dim"]
        self.feature_dim = feature_dim or default_dim

        # 替换分类层以获取特征
        if "resnet" in backbone:
            self.backbone.fc = nn.Identity()
        elif "mobilenet" in backbone or "efficientnet" in backbone:
            self.backbone.classifier = nn.Identity()

        # 如果需要自定义特征维度，添加投影头
        if self.feature_dim != default_dim:
            self.projection = nn.Sequential(
                nn.Linear(default_dim, self.feature_dim),
                nn.ReLU(),
            )
        else:
            self.projection = nn.Identity()

        # 如果请求冻结骨干网络
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False
            if hasattr(self, "projection"):
                for param in self.projection.parameters():
                    param.requires_grad = True  # 保持投影层可训练

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """从图像中提取特征。

        Args:
            x: 输入张量 (B, C, H, W)。

        Returns:
            特征张量 (B, feature_dim)。
        """
        with torch.set_grad_enabled(self.training):
            features = self.backbone(x)
            features = self.projection(features)
        return features

    def extract(self, images: torch.Tensor) -> torch.Tensor:
        """提取特征（forward 的别名）。"""
        return self.forward(images)

    @classmethod
    def list_backbones(cls) -> list:
        """列出可用的骨干网络名称。"""
        return list(cls.BACKBONES.keys())

    def load_weights(self, path: Path) -> None:
        """从文件加载模型权重。

        Args:
            path:  checkpoint 文件路径。
        """
        checkpoint = torch.load(path, map_location="cpu")
        if "state_dict" in checkpoint:
            self.load_state_dict(checkpoint["state_dict"])
        else:
            self.load_state_dict(checkpoint)

    def save_weights(self, path: Path) -> None:
        """保存模型权重到文件。

        Args:
            path: 输出路径。
        """
        torch.save({"state_dict": self.state_dict()}, path)
