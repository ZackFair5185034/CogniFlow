# -*- coding: utf-8 -*-
"""模型推理路由 - 图片/视频目标检测。"""

import os
import json
import base64
import shutil
import threading
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db, Model
from utils.frame_buffer import stream_job_manager

router = APIRouter()

# 推理结果保存目录（统一使用 DATA_DIR）
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)
INFERENCE_OUTPUT_DIR = Path(os.path.join(_DATA_DIR, "inference_output"))
INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== API 端点 =====


@router.post("/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    model_id: int = None,
    conf_threshold: float = 0.25,
    db: Session = Depends(get_db)
):
    """对单张图片进行目标检测。"""
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
        from routers.yolo_training import load_yolo_model, inference_yolo

        detector = load_yolo_model(model.file_path)
        result = inference_yolo(detector, str(file_path), conf_threshold)

        # 绘制检测结果
        from PIL import Image, ImageDraw
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)

        categories = json.loads(model.metrics or '{}').get('categories', []) if model.metrics else []
        if not categories:
            categories = [{'name': f'Class {i}', 'color': '#FF0000'} for i in range(result['num_classes'])]

        for det in result['detections']:
            bbox = det['bbox']
            conf = det['confidence']
            cls_id = det['class_id']
            cls_name = det.get('class_name', categories[cls_id]['name'] if cls_id < len(categories) else f'Class {cls_id}')
            color = categories[cls_id]['color'] if cls_id < len(categories) else '#FF0000'
            draw.rectangle(bbox, outline=color, width=3)
            label = f"{cls_name} {conf:.2f}"
            draw.text((bbox[0], bbox[1] - 20), label, fill=color)

        output_path = INFERENCE_OUTPUT_DIR / f"result_{timestamp}_{file.filename}"
        img.save(output_path)

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
        if file_path.exists():
            file_path.unlink()


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
            except json.JSONDecodeError:
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


# ===== 流式视频检测（实时推送模式）=====


def process_video_stream_background(
    job_id: str,
    model_file_path: str,
    conf_threshold: float,
    categories: list,
    input_path: str,
):
    """后台线程：流式处理视频，边推理边将结果放入帧缓冲队列。

    生产者-消费者模式：
    - 本函数为生产者，将推理结果放入 FrameBuffer
    - ws_stream.py 的推送协程为消费者，从 FrameBuffer 取数据推送给前端
    """
    import cv2
    import time
    from utils.frame_buffer import FrameResult
    from routers.yolo_training import load_yolo_model

    frame_buffer = stream_job_manager.get_job_frame_buffer(job_id)
    if frame_buffer is None:
        return

    try:
        stream_job_manager.update_job(job_id, status="processing")

        # 加载 YOLO 模型
        detector = load_yolo_model(model_file_path)

        # 获取视频信息
        cap = cv2.VideoCapture(input_path)
        fps = round(cap.get(cv2.CAP_PROP_FPS)) or 24
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        stream_job_manager.update_job(job_id,
            total_frames=total_frames,
            fps=fps,
        )

        frame_count = 0
        total_detections = 0
        start_time = time.time()

        while True:
            # 检查是否被停止
            if stream_job_manager.is_job_stopped(job_id):
                break

            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            frame_start = time.time()

            # BGR -> RGB，用于 YOLO 推理
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            try:
                # YOLO 推理
                results = detector(rgb_frame, conf=conf_threshold, verbose=False)

                detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            conf = float(box.conf[0])
                            cls_id = int(box.cls[0])
                            cls_name = result.names[cls_id] if cls_id < len(result.names) else f'Class {cls_id}'

                            detections.append({
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "class_id": cls_id,
                                "class_name": cls_name,
                                "confidence": round(conf, 4),
                            })
                            total_detections += 1
            except Exception:
                detections = []

            inference_ms = int((time.time() - frame_start) * 1000)

            # JPEG 压缩并转为 base64
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            image_base64 = base64.b64encode(buffer).decode('utf-8')

            # 构建帧结果，放入队列
            frame_result = FrameResult(
                frame_id=frame_count,
                timestamp=frame_count / fps,
                image_base64=image_base64,
                detections=detections,
                inference_ms=inference_ms,
            )
            frame_buffer.put(frame_result)

            # 更新进度
            if frame_count % 10 == 0 or frame_count == total_frames:
                progress = int((frame_count / total_frames) * 100) if total_frames > 0 else 0
                stream_job_manager.update_job(job_id,
                    current_frame=frame_count,
                    progress=progress,
                    total_detections=total_detections,
                )

        cap.release()

        # 标记完成
        stream_job_manager.update_job(job_id,
            status="completed",
            progress=100,
            current_frame=total_frames,
            total_detections=total_detections,
        )

    except Exception as e:
        stream_job_manager.update_job(job_id, status="failed", error=str(e))


@router.post("/detect/video/stream", status_code=202)
async def detect_video_stream(
    file: UploadFile = File(...),
    model_id: int = None,
    conf_threshold: float = 0.25,
    db: Session = Depends(get_db)
):
    """提交流式视频检测任务。

    边推理边通过 WebSocket 推送实时帧给前端。
    前端需连接 WS /ws/inference/stream/{job_id} 接收帧数据。
    """
    # 验证模型
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    # 获取类别信息
    categories = []
    if model.metrics:
        try:
            metrics = json.loads(model.metrics)
            categories = metrics.get('categories', [])
        except json.JSONDecodeError:
            pass

    # 保存上传的视频
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    input_path = INFERENCE_OUTPUT_DIR / f"stream_{timestamp}_{file.filename}"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 获取视频基本信息（用于立即返回）
    import cv2
    cap = cv2.VideoCapture(str(input_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # 创建流式推理任务
    job_id, frame_buffer = stream_job_manager.create_job(
        input_path=str(input_path),
        model_id=model_id,
        conf_threshold=conf_threshold,
        categories=categories,
        fps=fps,
        total_frames=total_frames,
    )

    # 后台线程执行推理
    thread = threading.Thread(
        target=process_video_stream_background,
        args=(job_id, model.file_path, conf_threshold, categories, str(input_path)),
        daemon=True,
    )
    thread.start()

    return {
        "success": True,
        "job_id": job_id,
        "stream_url": f"/ws/inference/stream/{job_id}",
        "video_info": {
            "fps": int(fps),
            "total_frames": total_frames,
            "duration": round(total_frames / fps) if fps > 0 else 0,
        }
    }


@router.post("/detect/stop/{job_id}")
async def stop_video_job(job_id: str):
    """停止流式视频检测任务。"""
    job = stream_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    stream_job_manager.stop_job(job_id)
    return {"success": True, "message": "推理已停止"}
