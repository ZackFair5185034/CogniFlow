# -*- coding: utf-8 -*-
"""简化版目标检测模型 - 基于 ResNet 的检测器。"""

import torch
import torch.nn as nn
import torchvision
from typing import Dict, List, Tuple


class SimpleDetector(nn.Module):
    """简化目标检测模型。

    架构：
    - 主干：ResNet18（预训练）
    - 检测头：特征图 → bbox 回归 + 类别分类
    """

    def __init__(self, num_classes: int, feature_dim: int = 512):
        super().__init__()
        self.num_classes = num_classes

        # 使用预训练 ResNet18 作为主干
        resnet = torchvision.models.resnet18(weights='IMAGENET1K_V1')
        self.backbone = nn.Sequential(*list(resnet.children())[:-2])  # 去掉 FC 和 AvgPool

        self.feature_dim = feature_dim

        # 特征适配层
        self.feature_adapter = nn.Sequential(
            nn.AdaptiveAvgPool2d((7, 7)),
            nn.Flatten(),
            nn.Linear(512 * 7 * 7, feature_dim),
            nn.ReLU(),
            nn.Dropout(0.5)
        )

        # bbox 回归头 (4 个坐标值)
        self.bbox_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 4)
        )

        # 类别分类头
        self.class_head = nn.Sequential(
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )

        # 置信度头
        self.confidence_head = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """前向传播。

        Args:
            x: 输入图片 [B, C, H, W]

        Returns:
            bboxes: [B, 4] bbox 坐标 (x1, y1, x2, y2) 归一化
            class_logits: [B, num_classes] 类别 logits
            confidence: [B, 1] 置信度
        """
        features = self.backbone(x)
        features = self.feature_adapter(features)

        bboxes = torch.sigmoid(self.bbox_head(features))  # 输出 [0, 1] 范围
        class_logits = self.class_head(features)
        confidence = self.confidence_head(features)

        return bboxes, class_logits, confidence


class DetectionLoss(nn.Module):
    """检测损失函数。"""

    def __init__(self, num_classes: int):
        super().__init__()
        self.num_classes = num_classes
        self.bbox_loss = nn.SmoothL1Loss()
        self.class_loss = nn.CrossEntropyLoss()
        self.confidence_loss = nn.BCELoss()

    def forward(
        self,
        pred_bboxes: torch.Tensor,
        pred_classes: torch.Tensor,
        pred_confidence: torch.Tensor,
        target_bboxes: torch.Tensor,
        target_classes: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """计算损失。"""
        batch_size = pred_bboxes.size(0)

        # bbox 损失
        bbox_loss = self.bbox_loss(pred_bboxes, target_bboxes)

        # 类别损失（简化：只对正样本计算）
        class_loss = self.class_loss(pred_classes, target_classes)

        # 置信度损失
        target_confidence = torch.ones_like(pred_confidence)
        confidence_loss = self.confidence_loss(pred_confidence, target_confidence)

        total_loss = bbox_loss + class_loss + confidence_loss

        return {
            'loss': total_loss,
            'bbox_loss': bbox_loss,
            'class_loss': class_loss,
            'confidence_loss': confidence_loss
        }
