# -*- coding: utf-8 -*-
"""YOLO 目标检测训练工具。"""

import os
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from sqlalchemy.orm import Session


def check_gpu_available() -> Dict:
    """检查 GPU 是否可用。

    Returns:
        设备信息字典，包含：
        - available: bool，是否可用
        - device: str，'cuda' 或 'cpu'
        - device_name: str，设备名称
        - memory_total: int，总显存(MB)，仅 CUDA 时有效
        - memory_free: int，可用显存(MB)，仅 CUDA 时有效
    """
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            memory_total = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            memory_free = memory_total  # 简化处理，不计算当前占用
            return {
                "available": True,
                "device": "cuda",
                "device_name": device_name,
                "memory_total": memory_total,
                "memory_free": memory_free,
            }
    except Exception as e:
        print(f"[GPU检测] 失败: {e}")

    return {
        "available": False,
        "device": "cpu",
        "device_name": "CPU",
        "memory_total": 0,
        "memory_free": 0,
    }


def _download_model_with_progress(
    pretrained_model: str,
    save_path: str,
    on_progress: Optional[Callable] = None,
    total_epochs: int = 100,
    stop_event=None,
):
    """下载预训练模型并报告实时进度（百分比）。

    Args:
        pretrained_model: 模型名称，如 yolov8s.pt
        save_path: 本地保存路径
        on_progress: 进度回调 on_progress(epoch, total_epochs, message)
        total_epochs: 用于进度显示的总轮数
        stop_event: 停止事件，可中断下载
    """
    import requests

    if stop_event and stop_event.is_set():
        return

    # Ultralytics 官方资产下载地址
    url = f"https://github.com/ultralytics/assets/releases/download/v0.0.0/{pretrained_model}"

    if on_progress:
        on_progress(0, total_epochs, message=f"正在下载预训练模型 {pretrained_model}... 0%")

    # 流式下载，实时计算百分比
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    block_size = 8192
    last_report_percent = -1  # 避免过于频繁回调
    start_time = time.time()
    last_chunk_time = start_time

    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=block_size):
            # 检查停止信号
            if stop_event and stop_event.is_set():
                f.close()
                os.remove(save_path)
                if on_progress:
                    on_progress(0, total_epochs, message="下载已取消")
                return

            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0 and on_progress:
                    percent = int(downloaded / total_size * 100)
                    # 每变化至少 2% 回调一次，避免高频刷新
                    now = time.time()
                    if percent - last_report_percent >= 2 or percent == 100 or (now - last_chunk_time > 3):
                        last_report_percent = percent
                        last_chunk_time = now
                        elapsed = now - start_time
                        speed = downloaded / elapsed / 1024 if elapsed > 0 else 0
                        on_progress(
                            0, total_epochs,
                            message=f"正在下载预训练模型 {pretrained_model}... {percent}% ({speed:.0f} KB/s)"
                        )

    # 验证文件完整性
    if os.path.getsize(save_path) == 0:
        raise Exception(f"下载的文件为空: {save_path}")

    if on_progress:
        on_progress(0, total_epochs, message=f"预训练模型 {pretrained_model} 下载完成")


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
    pretrained_model: str = "yolov8n.pt",
    stop_event=None,
    on_complete=None,
    on_progress=None,
) -> Dict:
    """使用 YOLO 进行训练。

    Args:
        data_yaml_path: 数据集配置文件路径
        model_save_path: 模型保存路径
        epochs: 训练轮数
        batch_size: 批次大小
        imgsz: 图片尺寸
        device: 训练设备
        pretrained_model: 预训练模型名称 (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)
        stop_event: 停止事件，用于提前终止训练
        on_complete: 完成回调，接收结果字典
        on_progress: 进度回调，接收 (epoch, total_epochs, message) 参数

    Returns:
        训练结果
    """
    import os
    from ultralytics import YOLO

    # 统一数据目录
    _DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

    # 模型缓存目录（YOLO 预训练权重，~100MB/模型）
    cache_dir = os.path.join(_DATA_DIR, "model_cache")
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['YOLO_CACHE_DIR'] = cache_dir

    model_cache_path = os.path.join(cache_dir, pretrained_model)

    need_download = False

    # 清理损坏的模型文件
    if os.path.exists(model_cache_path):
        try:
            # 尝试加载模型验证是否有效
            model = YOLO(model_cache_path)
        except Exception as e:
            # 文件损坏，删除后重新下载
            print(f"[YOLO训练] 模型文件损坏: {model_cache_path}, 错误: {e}")
            os.remove(model_cache_path)
            need_download = True
            if on_progress:
                on_progress(0, epochs, message=f"模型文件损坏，正在重新下载 {pretrained_model}...")
    else:
        need_download = True

    if need_download:
        # 检查是否已被用户停止
        if stop_event and stop_event.is_set():
            if on_progress:
                on_progress(0, epochs, message="训练已取消")
            raise Exception("训练已取消")

        # 使用带真实进度报告的流式下载
        max_retries = 3
        for attempt in range(max_retries):
            if on_progress:
                on_progress(0, epochs, message=f"正在下载预训练模型 {pretrained_model} ({attempt + 1}/{max_retries})...")

            try:
                _download_model_with_progress(
                    pretrained_model, model_cache_path,
                    on_progress=on_progress, total_epochs=epochs,
                    stop_event=stop_event,
                )
                # 如果下载被取消，模型文件已被删除，直接退出
                if stop_event and stop_event.is_set():
                    if on_progress:
                        on_progress(0, epochs, message="训练已取消")
                    raise Exception("训练已取消")
                # 验证下载的模型是否有效
                model = YOLO(model_cache_path)
                break  # 下载成功，跳出重试循环
            except Exception as e:
                err_msg = str(e)
                if "训练已取消" in err_msg:
                    raise  # 用户取消，不重试
                print(f"[YOLO训练] 下载尝试 {attempt + 1} 失败: {e}")
                if attempt == max_retries - 1:
                    error_msg = f"模型下载失败（已重试{max_retries}次）: {str(e)}"
                    if on_progress:
                        on_progress(0, epochs, message=error_msg)
                    raise Exception(error_msg)
                # 删除损坏的文件后重试
                if os.path.exists(model_cache_path):
                    os.remove(model_cache_path)
                if on_progress:
                    on_progress(0, epochs, message=f"下载失败，正在重试 ({attempt + 2}/{max_retries})...")

    # 创建保存目录（统一到 DATA_DIR/runs/ 下）
    runs_base = os.path.join(_DATA_DIR, "runs")
    os.makedirs(runs_base, exist_ok=True)
    save_dir = Path(runs_base) / "train"
    save_dir.mkdir(parents=True, exist_ok=True)

    # 注册训练进度回调，获得真实 epoch 进度
    _training_stopped = False

    def on_epoch_end(trainer):
        """每个 epoch 结束时的回调。"""
        nonlocal _training_stopped
        # 检查停止信号
        if stop_event and stop_event.is_set():
            _training_stopped = True
            raise Exception("训练被用户停止")

        current_epoch = trainer.epoch + 1  # trainer.epoch 从 0 开始
        if on_progress:
            message = f"训练中... Epoch {current_epoch}/{epochs}"
            # trainer.loss 是 tensor，直接取 item
            try:
                loss_val = trainer.loss.item() if hasattr(trainer.loss, 'item') else float(trainer.loss)
                message += f", 损失: {loss_val:.4f}"
            except (TypeError, ValueError, RuntimeError):
                pass
            on_progress(current_epoch, epochs, message=message)

    model.add_callback('on_train_epoch_end', on_epoch_end)

    # 开始训练
    try:
        results = model.train(
            data=data_yaml_path,
            epochs=epochs,
            batch=batch_size,
            imgsz=imgsz,
            device=device,
            project=str(save_dir.parent),
            name=save_dir.stem,
            exist_ok=True,
            verbose=False,
            save=True,
            plots=False,
            patience=0,
        )
    except Exception as e:
        if _training_stopped:
            # 用户主动停止，不视为失败
            print(f"[YOLO训练] 训练被用户停止")
            if on_progress:
                on_progress(0, epochs, message="训练已停止")
            return {
                "success": False,
                "stopped": True,
                "model_path": str(model_save_path),
                "metrics": {},
            }
        raise

    # 更新进度
    if on_progress:
        on_progress(epochs, epochs, message="训练完成")

    # YOLO 将模型保存到 runs/detect/{project}/{name}/weights/
    # 从 results 中获取实际的保存路径
    best_model_path = str(Path(results.save_dir) / "weights" / "best.pt")
    last_model_path = str(Path(results.save_dir) / "weights" / "last.pt")

    # 返回训练结果
    result = {
        "success": True,
        "model_path": str(model_save_path),
        "best_model": best_model_path,
        "last_model": last_model_path,
        "metrics": {
            "mAP50": float(results.results_dict.get('metrics/mAP50(B)', 0)),
            "mAP50-95": float(results.results_dict.get('metrics/mAP50-95(B)', 0)),
        }
    }

    # 如果提供了完成回调，调用它
    if on_complete:
        on_complete(result)

    return result


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
