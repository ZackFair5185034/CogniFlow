"""VisionGame UI 检测器模块 - 游戏屏幕 UI 元素检测。"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np
import torch
import torch.nn as nn
from torchvision import models
from torchvision.ops import nms


@dataclass
class Detection:
    """检测结果。"""
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    score: float
    label: int
    label_name: str


class UIDetector(nn.Module):
    """游戏屏幕 UI 元素检测器。

    支持功能：
    - 边界框检测
    - 多尺度检测
    - NMS 后处理
    """

    def __init__(
        self,
        num_classes: int = 80,
        backbone: str = "resnet18",
        pretrained: bool = True,
        score_thresh: float = 0.5,
        nms_thresh: float = 0.4,
    ):
        """初始化 UI 检测器。

        Args:
            num_classes: 检测类别数量。
            backbone: 骨干网络架构。
            pretrained: 是否使用预训练权重。
            score_thresh: 置信度阈值。
            nms_thresh: NMS IoU 阈值。
        """
        super().__init__()

        self.num_classes = num_classes
        self.score_thresh = score_thresh
        self.nms_thresh = nms_thresh

        # 简单的 FPN 类骨干网络
        if backbone == "resnet18":
            backbone_model = models.resnet18(pretrained=pretrained)
            c3_channels, c4_channels = 128, 256
        else:
            backbone_model = models.resnet18(pretrained=pretrained)
            c3_channels, c4_channels = 128, 256

        # 特征提取器（移除最后几层）
        self.backbone = nn.Sequential(*list(backbone_model.children())[:-4])
        self.feat_channels = 128

        # 检测头（简化的 RetinaNet 风格）
        self.num_anchors = 9
        self.cls_layer = nn.Conv2d(self.feat_channels, self.num_anchors * num_classes, 3, padding=1)
        self.reg_layer = nn.Conv2d(self.feat_channels, self.num_anchors * 4, 3, padding=1)

        # 默认锚框（会根据游戏自定义）
        self.anchors = self._generate_anchors()

    def _generate_anchors(self, strides: List[int] = [8, 16, 32]) -> torch.Tensor:
        """生成锚框。"""
        anchors_list = []
        for stride in strides:
            for i in range(stride, 224, stride):
                for j in range(stride, 224, stride):
                    for h, w in [(0.5, 0.5), (1.0, 0.5), (0.5, 1.0)]:
                        x = j / 224
                        y = i / 224
                        anchors_list.append([x - w/2, y - h/2, x + w/2, y + h/2])
        return torch.tensor(anchors_list, dtype=torch.float32)

    def forward(
        self,
        x: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """前向传播。

        Args:
            x: 输入图像 (B, C, H, W)。

        Returns:
            (cls_logits, bbox_regression) 元组。
        """
        features = self.backbone(x)
        cls_logits = self.cls_layer(features)
        bbox_reg = self.reg_layer(features)
        return cls_logits, bbox_reg

    def detect(
        self,
        images: torch.Tensor,
        orig_sizes: Optional[List[Tuple[int, int]]] = None,
    ) -> List[List[Detection]]:
        """检测图像中的 UI 元素。

        Args:
            images: 输入图像 (B, C, H, W)。
            orig_sizes: 用于坐标转换的原始图像尺寸。

        Returns:
            每张图像的检测结果列表。
        """
        self.eval()
        with torch.no_grad():
            cls_logits, bbox_reg = self.forward(images)

            # 展平预测结果
            B = cls_logits.shape[0]
            cls_logits = cls_logits.permute(0, 2, 3, 1).reshape(B, -1, self.num_classes)
            bbox_reg = bbox_reg.permute(0, 2, 3, 1).reshape(B, -1, 4)

            all_detections = []
            for i in range(B):
                scores = cls_logits[i].sigmoid()
                boxes = bbox_reg[i]

                # 应用锚框
                anchors = self.anchors.to(images.device)
                boxes = boxes * anchors[:, 2:4] + anchors[:, 0:2]
                boxes = boxes.clamp(0, 1)

                # 每类别 NMS
                detections = []
                for cls_id in range(self.num_classes):
                    cls_scores = scores[:, cls_id]
                    mask = cls_scores > self.score_thresh
                    if not mask.any():
                        continue

                    cls_boxes = boxes[mask]
                    cls_scores = cls_scores[mask]

                    # NMS
                    keep = nms(cls_boxes * 224, cls_scores, self.nms_thresh)
                    for idx in keep:
                        x1, y1, x2, y2 = cls_boxes[idx].tolist()
                        detections.append(Detection(
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            score=cls_scores[idx].item(),
                            label=cls_id,
                            label_name=f"class_{cls_id}",
                        ))

                all_detections.append(detections)

            return all_detections
