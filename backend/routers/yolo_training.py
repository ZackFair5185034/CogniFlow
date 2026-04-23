# -*- coding: utf-8 -*-
"""YOLO 目标检测训练工具。"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session


def export_to_yolo_format(atlas_id: int, db: Session, output_dir: str) -> Dict:
    """将图集数据导出为 YOLO 格式。

    YOLO 格式：
    - images/: *.jpg 图片
    - labels/: *.txt 标注文件（每行: class_id x_center y_center width height）

    Args:
        atlas_id: 图集 ID
        db: 数据库会话
        output_dir: 输出目录

    Returns:
        导出统计信息
    """
    from database import Image, Annotation, Category

    # 创建目录结构
    images_dir = Path(output_dir) / "images"
    labels_dir = Path(output_dir) / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    # 获取该图集的所有类别并创建映射
    categories = db.query(Category).filter(Category.is_directory == False).all()
    cat2idx = {cat.id: idx for idx, cat in enumerate(categories)}
    idx2cat = {idx: cat.id for idx, cat in enumerate(categories)}

    # 保存类别映射
    classes_info = []
    for cat in categories:
        classes_info.append({
            'id': cat2idx[cat.id],
            'name': cat.name,
            'color': cat.color
        })

    with open(Path(output_dir) / "classes.json", 'w', encoding='utf-8') as f:
        json.dump(classes_info, f, ensure_ascii=False, indent=2)

    # 获取该图集的所有图片
    images = db.query(Image).filter(Image.atlas_id == atlas_id).all()

    exported_count = 0
    skipped_count = 0

    for img in images:
        # 跳过不存在的文件
        if not os.path.exists(img.file_path):
            skipped_count += 1
            continue

        # 获取该图片的标注
        annotations = db.query(Annotation).filter(Annotation.image_id == img.id).all()

        # 复制图片
        img_ext = Path(img.file_path).suffix
        img_name = f"img_{img.id}{img_ext}"
        shutil.copy(img.file_path, images_dir / img_name)

        # 生成标注文件
        label_lines = []
        img_w = img.width or 224
        img_h = img.height or 224

        for ann in annotations:
            if ann.category_id not in cat2idx:
                continue

            class_id = cat2idx[ann.category_id]
            bbox = json.loads(ann.bbox)  # [x, y, w, h]

            x, y, w, h = bbox
            # 转换为 YOLO 格式（归一化的中心点 + 宽高）
            x_center = (x + w / 2) / img_w
            y_center = (y + h / 2) / img_h
            norm_w = w / img_w
            norm_h = h / img_h

            # 确保在 [0, 1] 范围内
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            norm_w = max(0, min(1, norm_w))
            norm_h = max(0, min(1, norm_h))

            label_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")

        # 写入标注文件
        label_name = f"img_{img.id}.txt"
        with open(labels_dir / label_name, 'w') as f:
            f.write("\n".join(label_lines))

        exported_count += 1

    return {
        "images_dir": str(images_dir),
        "labels_dir": str(labels_dir),
        "exported": exported_count,
        "skipped": skipped_count,
        "num_classes": len(categories),
        "classes": classes_info
    }


def train_yolo(
    data_yaml_path: str,
    model_save_path: str,
    epochs: int = 100,
    batch_size: int = 16,
    imgsz: int = 640,
    device: str = "cpu",
    stop_event=None
) -> Dict:
    """使用 YOLO 进行训练。

    Args:
        data_yaml_path: 数据集配置文件路径
        model_save_path: 模型保存路径
        epochs: 训练轮数
        batch_size: 批次大小
        imgsz: 图片尺寸
        device: 训练设备
        stop_event: 停止事件，用于提前终止训练

    Returns:
        训练结果
    """
    from ultralytics import YOLO

    # 加载预训练模型（使用 YOLOv8n nano 模型，快速训练）
    model = YOLO('yolov8n.pt')

    # 创建保存目录
    save_dir = Path(model_save_path)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 开始训练
    results = model.train(
        data=data_yaml_path,
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project=str(save_dir.parent),
        name=save_dir.stem,
        exist_ok=True,
        verbose=False,  # 减少输出
        save=True,
        plots=False,  # 禁用自动绘图以加快速度
        patience=0  # 禁用早停
    )

    # YOLO 将模型保存到 runs/detect/{project}/{name}/weights/
    # 从 results 中获取实际的保存路径
    best_model_path = str(Path(results.save_dir) / "weights" / "best.pt")
    last_model_path = str(Path(results.save_dir) / "weights" / "last.pt")

    # 返回训练结果
    return {
        "success": True,
        "model_path": str(model_save_path),
        "best_model": best_model_path,
        "last_model": last_model_path,
        "metrics": {
            "mAP50": float(results.results_dict.get('metrics/mAP50(B)', 0)),
            "mAP50-95": float(results.results_dict.get('metrics/mAP50-95(B)', 0)),
        }
    }


def load_yolo_model(model_path: str):
    """加载 YOLO 模型用于推理。"""
    from ultralytics import YOLO
    return YOLO(model_path)


def inference_yolo(model, image_path: str, conf_threshold: float = 0.25) -> Dict:
    """使用 YOLO 模型进行推理。

    Args:
        model: 加载的 YOLO 模型
        image_path: 图片路径
        conf_threshold: 置信度阈值

    Returns:
        检测结果
    """
    results = model(image_path, conf=conf_threshold)

    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                detections.append({
                    'bbox': box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
                    'confidence': float(box.conf[0]),
                    'class_id': int(box.cls[0]),
                    'class_name': result.names[int(box.cls[0])]
                })

    return {
        'image_path': image_path,
        'num_detections': len(detections),
        'detections': detections
    }
