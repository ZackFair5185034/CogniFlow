# -*- coding: utf-8 -*-
"""目标检测数据集 - 从图集加载图片和标注用于训练。"""

import torch
from torch.utils.data import Dataset
from PIL import Image
import json
import os
import numpy as np
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session


class AtlasDetectionDataset(Dataset):
    """从图集加载图片和标注用于目标检测训练。

    返回格式：
    - image: Tensor [C, H, W]
    - target: dict {
        'boxes': Tensor [N, 4] (x1, y1, x2, y2),
        'labels': Tensor [N],
        'image_id': int
    }
    """

    def __init__(
        self,
        atlas_id: int,
        db: Session,
        image_size: Tuple[int, int] = (224, 224),
        augment: bool = False
    ):
        self.atlas_id = atlas_id
        self.db = db
        self.image_size = image_size
        self.augment = augment

        # 加载数据
        self.samples = self._load_samples()
        self.categories = self._load_categories()

        # 创建类别映射
        self.cat2idx = {cat['id']: idx for idx, cat in enumerate(self.categories)}
        self.idx2cat = {idx: cat['id'] for idx, cat in enumerate(self.categories)}

    def _load_samples(self) -> List[Dict]:
        """加载图集的图片和标注数据。"""
        from database import Image, Annotation

        images = self.db.query(Image).filter(Image.atlas_id == self.atlas_id).all()
        samples = []

        for img in images:
            if not os.path.exists(img.file_path):
                continue

            annotations = self.db.query(Annotation).filter(Annotation.image_id == img.id).all()

            boxes = []
            labels = []
            for ann in annotations:
                bbox = json.loads(ann.bbox)
                boxes.append(bbox)  # [x, y, w, h]
                labels.append(self.cat2idx.get(ann.category_id, 0))

            if len(boxes) == 0:
                continue

            samples.append({
                'image_path': img.file_path,
                'boxes': boxes,
                'labels': labels,
                'image_id': img.id
            })

        return samples

    def _load_categories(self) -> List[Dict]:
        """加载该图集关联的所有类别。"""
        from database import Category

        # 获取该图集中所有被使用的类别
        categories = self.db.query(Category).filter(
            Category.is_directory == False
        ).all()

        return [{'id': c.id, 'name': c.name, 'color': c.color} for c in categories]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict]:
        sample = self.samples[idx]

        # 加载图片
        image = Image.open(sample['image_path']).convert('RGB')
        orig_w, orig_h = image.size

        # 缩放到目标尺寸
        image = image.resize(self.image_size)
        image = torch.from_numpy(np.array(image)).permute(2, 0, 1).float() / 255.0

        # 转换 bbox 到 [0, 1] 范围并变为 [x1, y1, x2, y2] 格式
        boxes = []
        for box in sample['boxes']:
            x, y, w, h = box
            # 归一化
            x1 = x / orig_w
            y1 = y / orig_h
            x2 = (x + w) / orig_w
            y2 = (y + h) / orig_h
            # 确保在 [0, 1] 范围内
            x1 = max(0, min(1, x1))
            y1 = max(0, min(1, y1))
            x2 = max(0, min(1, x2))
            y2 = max(0, min(1, y2))
            boxes.append([x1, y1, x2, y2])

        target = {
            'boxes': torch.tensor(boxes, dtype=torch.float32),
            'labels': torch.tensor(sample['labels'], dtype=torch.int64),
            'image_id': torch.tensor([sample['image_id']])
        }

        return image, target


def collate_fn(batch):
    """自定义批次整理函数。"""
    images = []
    targets = []
    for img, target in batch:
        images.append(img)
        targets.append(target)
    return torch.stack(images), targets
