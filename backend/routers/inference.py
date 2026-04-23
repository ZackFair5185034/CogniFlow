# -*- coding: utf-8 -*-
"""模型推理路由 - 图片/视频目标检测。"""

import os
import json
import base64
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db, Model
from websocket_manager import ws_manager

router = APIRouter()

# 推理结果保存目录
INFERENCE_OUTPUT_DIR = Path("./inference_output")
INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    model_id: int = None,
    conf_threshold: float = 0.25,
    db: Session = Depends(get_db)
):
    """对单张图片进行目标检测。

    Args:
        file: 上传的图片文件
        model_id: 模型 ID（优先使用）或 file_path
        conf_threshold: 置信度阈值
    """
    # 验证模型
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    # 保存上传的图片
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_path = INFERENCE_OUTPUT_DIR / f"input_{timestamp}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 加载 YOLO 模型并进行推理
        from routers.yolo_training import load_yolo_model, inference_yolo

        detector = load_yolo_model(model.file_path)
        result = inference_yolo(detector, str(file_path), conf_threshold)

        # 绘制检测结果到图片
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)

        # 加载类别信息
        categories = json.loads(model.metrics or '{}').get('categories', []) if model.metrics else []
        if not categories:
            categories = [{'name': f'Class {i}', 'color': '#FF0000'} for i in range(result['num_classes'])]

        # 绘制每个检测框
        for det in result['detections']:
            bbox = det['bbox']  # [x1, y1, x2, y2]
            conf = det['confidence']
            cls_id = det['class_id']
            cls_name = det.get('class_name', categories[cls_id]['name'] if cls_id < len(categories) else f'Class {cls_id}')

            # 颜色基于类别
            color = categories[cls_id]['color'] if cls_id < len(categories) else '#FF0000'

            # 绘制矩形框
            draw.rectangle(bbox, outline=color, width=3)

            # 绘制标签
            label = f"{cls_name} {conf:.2f}"
            draw.text((bbox[0], bbox[1] - 20), label, fill=color)

        # 保存结果图片
        output_path = INFERENCE_OUTPUT_DIR / f"result_{timestamp}_{file.filename}"
        img.save(output_path)

        # 转换为 base64 用于前端显示
        with open(output_path, 'rb') as f:
            result_image_b64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "success": True,
            "original_image": str(file_path),
            "result_image": str(output_path),
            "result_image_base64": f"data:image/jpeg;base64,{result_image_b64}",
            "detections": result['detections'],
            "num_detections": result['num_detections']
        }

    finally:
        # 清理输入文件
        if file_path.exists():
            file_path.unlink()


@router.post("/detect/video")
async def detect_video(
    file: UploadFile = File(...),
    model_id: int = None,
    conf_threshold: float = 0.25,
    db: Session = Depends(get_db)
):
    """对视频进行目标检测（逐帧处理）。

    Args:
        file: 上传的的视频文件
        model_id: 模型 ID
        conf_threshold: 置信度阈值
    """
    # 验证模型
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    # 保存上传的视频
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    input_path = INFERENCE_OUTPUT_DIR / f"video_{timestamp}_{file.filename}"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        import cv2
        from routers.yolo_training import load_yolo_model

        # 加载模型
        detector = load_yolo_model(model.file_path)

        # 获取视频信息
        cap = cv2.VideoCapture(str(input_path))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 输出视频路径
        output_path = INFERENCE_OUTPUT_DIR / f"video_result_{timestamp}_{file.filename}"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        frame_count = 0
        all_detections = []

        # 加载类别信息
        categories = []
        if model.metrics:
            try:
                metrics = json.loads(model.metrics)
                categories = metrics.get('categories', [])
            except:
                pass

        # 逐帧处理
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 保存当前帧进行推理
            temp_frame_path = INFERENCE_OUTPUT_DIR / f"temp_frame_{frame_count}.jpg"
            cv2.imwrite(str(temp_frame_path), frame)

            # YOLO 推理
            results = detector(str(temp_frame_path), conf=conf_threshold, verbose=False)

            frame_detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        cls_name = result.names[cls_id] if cls_id < len(result.names) else f'Class {cls_id}'

                        # 绘制检测框
                        color = (0, 255, 0)  # 绿色
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = f"{cls_name} {conf:.2f}"
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                        frame_detections.append({
                            'frame': frame_count,
                            'bbox': [x1, y1, x2, y2],
                            'confidence': conf,
                            'class_id': cls_id,
                            'class_name': cls_name
                        })

            # 写入输出视频
            out.write(frame)

            # 清理临时帧
            if temp_frame_path.exists():
                temp_frame_path.unlink()

            # 每10帧推送一次进度
            if frame_count % 10 == 0 or frame_count == total_frames:
                progress = int((frame_count / total_frames) * 100)
                await ws_manager.send_launch_update({
                    "type": "video_progress",
                    "frame": frame_count,
                    "total_frames": total_frames,
                    "progress": progress,
                    "current_detections": len(frame_detections)
                })

            all_detections.extend(frame_detections)

        cap.release()
        out.release()

        # 获取输出视频的 base64 缩略图（第一帧）
        cap_out = cv2.VideoCapture(str(output_path))
        ret, thumbnail = cap_out.read()
        cap_out.release()
        thumbnail_b64 = ""
        if ret:
            _, buffer = cv2.imencode('.jpg', thumbnail)
            thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "success": True,
            "video_path": str(output_path),
            "thumbnail_base64": f"data:image/jpeg;base64,{thumbnail_b64}" if thumbnail_b64 else None,
            "total_frames": total_frames,
            "processed_frames": frame_count,
            "total_detections": len(all_detections),
            "detections": all_detections[:100]  # 只返回前100个检测结果
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频处理失败: {str(e)}")

    finally:
        # 清理输入文件
        if input_path.exists():
            input_path.unlink()


@router.get("/models")
async def list_trained_models(db: Session = Depends(get_db)):
    """获取所有有文件路径的模型（可用的训练好的模型）。"""
    models = db.query(Model).filter(
        Model.file_path.isnot(None)
    ).all()

    result = []
    for m in models:
        metrics = None
        if m.metrics:
            try:
                metrics = json.loads(m.metrics)
            except:
                pass

        result.append({
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "file_path": m.file_path,
            "metrics": metrics,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return result
