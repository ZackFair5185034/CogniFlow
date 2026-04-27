# -*- coding: utf-8 -*-
"""模型推理路由 - 图片/视频目标检测。"""

import os
import json
import asyncio
import base64
import shutil
import threading
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db, Model
from websocket_manager import ws_manager

router = APIRouter()

# 推理结果保存目录
INFERENCE_OUTPUT_DIR = Path("./inference_output")
INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== 视频检测任务管理器 =====

class VideoJobManager:
    """视频检测任务管理器（线程安全）。"""

    def __init__(self):
        self._jobs: dict = {}
        self._lock = threading.Lock()

    def create_job(self, input_path: str, model_id: int, conf_threshold: float, categories: list) -> str:
        """创建视频检测任务，返回 job_id。"""
        job_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "pending",            # pending -> processing -> completed / failed
                "progress": 0,                   # 0-100
                "current_frame": 0,
                "total_frames": 0,
                "input_path": input_path,
                "result_path": None,
                "error": None,
                "model_id": model_id,
                "conf_threshold": conf_threshold,
                "categories": categories,
                "detections_count": 0,
                "fps": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
        return job_id

    def update_job(self, job_id: str, **kwargs):
        """更新任务状态（线程安全）。"""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)

    def get_job(self, job_id: str) -> Optional[dict]:
        """获取任务状态。"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.copy() if job else None

    def cleanup_old_jobs(self, max_age_hours: int = 2):
        """清理超过 max_age_hours 的旧任务及其结果文件。"""
        with self._lock:
            now = datetime.utcnow()
            to_remove = []
            for job_id, job in self._jobs.items():
                created = datetime.fromisoformat(job["created_at"])
                if (now - created).total_seconds() > max_age_hours * 3600:
                    to_remove.append(job_id)
            for job_id in to_remove:
                job = self._jobs.pop(job_id)
                # 清理结果文件
                if job.get("result_path") and os.path.exists(job["result_path"]):
                    try:
                        os.unlink(job["result_path"])
                    except OSError:
                        pass
                # 清理输入文件
                if job.get("input_path") and os.path.exists(job["input_path"]):
                    try:
                        os.unlink(job["input_path"])
                    except OSError:
                        pass


video_job_manager = VideoJobManager()


def _send_ws_update(data: dict, loop: asyncio.AbstractEventLoop):
    """从后台线程通过主事件循环发送 WebSocket 更新。"""
    try:
        asyncio.run_coroutine_threadsafe(
            ws_manager.send_launch_update(data), loop
        )
    except Exception:
        pass


def process_video_background(
    job_id: str,
    model_file_path: str,
    conf_threshold: float,
    categories: list,
    input_path: str,
    loop: asyncio.AbstractEventLoop,
):
    """后台线程：逐帧处理视频检测。"""
    import cv2
    from routers.yolo_training import load_yolo_model

    try:
        video_job_manager.update_job(job_id, status="processing")

        # 加载 YOLO 模型
        detector = load_yolo_model(model_file_path)

        # 获取视频信息
        cap = cv2.VideoCapture(input_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        video_job_manager.update_job(job_id, total_frames=total_frames, fps=fps)

        # 输出视频
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = INFERENCE_OUTPUT_DIR / f"video_result_{job_id}_{timestamp}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        frame_count = 0
        total_detections = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 保存临时帧进行 YOLO 推理
            temp_path = str(INFERENCE_OUTPUT_DIR / f"temp_{job_id}_{frame_count}.jpg")
            cv2.imwrite(temp_path, frame)

            try:
                results = detector(temp_path, conf=conf_threshold, verbose=False)
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            conf = float(box.conf[0])
                            cls_id = int(box.cls[0])
                            cls_name = result.names[cls_id] if cls_id < len(result.names) else f'Class {cls_id}'

                            # 绘制检测框
                            color = (0, 255, 0)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            label = f"{cls_name} {conf:.2f}"
                            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            total_detections += 1
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            # 写入输出视频
            out.write(frame)

            # 每 5 帧或最后一帧时更新进度
            if frame_count % 5 == 0 or frame_count == total_frames:
                progress = int((frame_count / total_frames) * 100) if total_frames > 0 else 0
                video_job_manager.update_job(
                    job_id,
                    current_frame=frame_count,
                    progress=min(progress, 99),
                    detections_count=total_detections,
                )
                _send_ws_update({
                    "type": "video_progress",
                    "job_id": job_id,
                    "frame": frame_count,
                    "total_frames": total_frames,
                    "progress": min(progress, 99),
                    "detections_count": total_detections,
                }, loop)

        cap.release()
        out.release()

        video_job_manager.update_job(
            job_id,
            status="completed",
            progress=100,
            current_frame=total_frames,
            result_path=str(output_path),
        )

        _send_ws_update({
            "type": "video_complete",
            "job_id": job_id,
            "total_frames": total_frames,
            "detections_count": total_detections,
        }, loop)

    except Exception as e:
        video_job_manager.update_job(job_id, status="failed", error=str(e))
        _send_ws_update({
            "type": "video_error",
            "job_id": job_id,
            "error": str(e),
        }, loop)


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


@router.post("/detect/video", status_code=202)
async def detect_video(
    file: UploadFile = File(...),
    model_id: int = None,
    conf_threshold: float = 0.25,
    db: Session = Depends(get_db)
):
    """提交视频检测任务（异步）。返回 job_id，前端轮询进度。"""
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
    input_path = INFERENCE_OUTPUT_DIR / f"video_{timestamp}_{file.filename}"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 创建检测任务
    job_id = video_job_manager.create_job(
        input_path=str(input_path),
        model_id=model_id,
        conf_threshold=conf_threshold,
        categories=categories,
    )

    # 获取当前事件循环，传递给后台线程用于 WebSocket 推送
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    # 后台线程处理（daemon 确保主进程退出时自动终止）
    thread = threading.Thread(
        target=process_video_background,
        args=(job_id, model.file_path, conf_threshold, categories, str(input_path), loop),
        daemon=True,
    )
    thread.start()

    return {
        "success": True,
        "job_id": job_id,
        "message": "视频检测任务已创建",
    }


@router.get("/video/status/{job_id}")
async def get_video_job_status(job_id: str):
    """获取视频检测任务状态。"""
    job = video_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.get("/video/result/{job_id}")
async def get_video_result(job_id: str):
    """获取视频检测结果文件。"""
    job = video_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务未完成，当前状态: " + job["status"])
    if not job["result_path"] or not os.path.exists(job["result_path"]):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    filename = os.path.basename(job["result_path"])
    return FileResponse(
        job["result_path"],
        media_type="video/mp4",
        filename=filename,
    )


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
