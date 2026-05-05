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

from backend.database import get_db, SessionLocal, Model, InferenceJob
from backend.utils.frame_buffer import stream_job_manager

router = APIRouter()

# 推理结果保存目录（统一使用 DATA_DIR）
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
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
        from backend.routers.yolo_training import load_yolo_model, inference_yolo

        detector = load_yolo_model(model.file_path)
        result = inference_yolo(detector, str(file_path), conf_threshold)

        # 绘制检测结果
        from PIL import Image, ImageDraw
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)

        categories = json.loads(model.metrics or '{}').get('categories', []) if model.metrics else []
        if not categories:
            class_ids = set(det['class_id'] for det in result['detections'])
            categories = [{'name': f'Class {i}', 'color': '#FF0000'} for i in range(max(class_ids) + 1) if i in class_ids] if class_ids else []

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

        # 生成缩略图（结果图缩略图）
        from PIL import Image as PILImage
        thumb_img = PILImage.open(output_path)
        thumb_img.thumbnail((40, 40))
        import io
        thumb_buf = io.BytesIO()
        thumb_img.save(thumb_buf, format='JPEG', quality=60)
        thumb_b64 = base64.b64encode(thumb_buf.getvalue()).decode('utf-8')

        # 记录到数据库（用输入图路径，支持重新检测）
        import uuid
        record = InferenceJob(
            job_id=str(uuid.uuid4())[:8],
            model_id=model_id,
            file_name=file.filename,
            file_path=str(file_path),  # 输入图路径，保留在磁盘
            file_type="image",
            conf_threshold=conf_threshold,
            status="completed",
            total_detections=result['num_detections'],
            thumbnail=f"data:image/jpeg;base64,{thumb_b64}",
        )
        db.add(record)
        db.commit()

        return {
            "success": True,
            "original_image": str(file_path),
            "result_image": str(output_path),
            "result_image_base64": f"data:image/jpeg;base64,{result_image_b64}",
            "detections": result['detections'],
            "num_detections": result['num_detections']
        }
    except Exception:
        # 检测失败时不记录
        raise HTTPException(status_code=500, detail="图片检测失败")


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
            "created_at": int(m.created_at.timestamp() * 1000) if m.created_at else int(datetime.now().timestamp() * 1000)
        })

    return result


# ===== 流式视频检测（实时推送模式）=====


def _inference_worker(
    job_id: str,
    detector,
    input_path: str,
    fps: int,
    total_frames: int,
    conf_threshold: float,
):
    """推理线程：读取视频帧，执行 YOLO 推理，放入原始帧缓冲。

    消费者：_encode_worker
    """
    import cv2
    import time
    from backend.utils.frame_buffer import RawFrameResult

    raw_buffer = stream_job_manager.get_job_raw_buffer(job_id)
    if raw_buffer is None:
        return

    cap = cv2.VideoCapture(input_path)
    try:
        frame_count = 0
        total_detections = 0
        skip_count = 0  # 连续跳帧计数

        while True:
            if stream_job_manager.is_job_stopped(job_id):
                break

            # 自适应抽帧：原始帧缓冲将满时跳过部分帧
            if raw_buffer.qsize >= 8:
                skip_count += 1
            else:
                skip_count = 0

            if skip_count > 0:
                # 跳过当前帧的推理，直接读取下一帧
                frame_count += 1
                ret = cap.grab()  # 不解码，快速跳到下一帧
                if not ret:
                    break
                skip_count -= 1
                continue

            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            frame_start = time.time()

            # BGR -> RGB，用于 YOLO 推理
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            try:
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

            # 原始帧入队（编码线程会处理压缩）
            raw_result = RawFrameResult(
                frame_id=frame_count,
                timestamp=frame_count / fps,
                frame_bgr=frame,
                detections=detections,
                inference_ms=inference_ms,
            )
            raw_buffer.put(raw_result)

            # 更新进度
            if frame_count % 10 == 0 or frame_count == total_frames:
                progress = int((frame_count / total_frames) * 100) if total_frames > 0 else 0
                stream_job_manager.update_job(job_id,
                    current_frame=frame_count,
                    progress=progress,
                    total_detections=total_detections,
                )

        # 标记推理完成（编码线程需要知道何时停止）
        stream_job_manager.update_job(job_id,
            inference_done=True,
            final_frame_count=frame_count,
            final_total_detections=total_detections,
        )

    except Exception as e:
        stream_job_manager.update_job(job_id, status="failed", error=str(e))
    finally:
        cap.release()


def _encode_worker(job_id: str):
    """编码线程：从原始帧缓冲取帧，JPEG 压缩后放入推送缓冲。

    消费者：ws_stream.py 的推送协程
    """
    import cv2
    import time
    from backend.utils.frame_buffer import FrameResult

    raw_buffer = stream_job_manager.get_job_raw_buffer(job_id)
    frame_buffer = stream_job_manager.get_job_frame_buffer(job_id)
    if raw_buffer is None or frame_buffer is None:
        return

    while True:
        # 检查是否应结束
        job = stream_job_manager.get_job(job_id)
        if job is None:
            break
        if job["status"] in ("failed", "stopped"):
            break
        if job.get("inference_done") and raw_buffer.qsize == 0:
            break

        raw = raw_buffer.get(timeout=0.5)
        if raw is None:
            continue

        try:
            # 动态 JPEG quality：根据原始帧缓冲积压情况调整
            qsize = raw_buffer.qsize
            if qsize >= 2:
                jpeg_quality = 50  # 缓冲快满，降质量
            elif qsize >= 1:
                jpeg_quality = 70  # 有一定积压，中等质量
            else:
                jpeg_quality = 85  # 正常质量
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
            _, buffer = cv2.imencode('.jpg', raw.frame_bgr, encode_param)
            image_bytes = buffer.tobytes()

            # 编码后的帧入推送队列
            frame_result = FrameResult(
                frame_id=raw.frame_id,
                timestamp=raw.timestamp,
                image_bytes=image_bytes,
                detections=raw.detections,
                inference_ms=raw.inference_ms,
            )
            frame_buffer.put(frame_result)
        except Exception:
            continue

    # 标记编码完成
    job = stream_job_manager.get_job(job_id)
    if job and job["status"] not in ("failed", "stopped"):
        stream_job_manager.update_job(job_id,
            status="completed",
            progress=100,
            current_frame=job.get("final_frame_count", 0),
            total_detections=job.get("final_total_detections", 0),
        )


def process_video_stream_background(
    job_id: str,
    model_file_path: str,
    conf_threshold: float,
    categories: list,
    input_path: str,
):
    """后台线程：流式处理视频，推理与编码分离为流水线。

    流水线：
    1. _inference_worker：读取视频帧 → YOLO 推理 → 原始帧入 raw_buffer
    2. _encode_worker：从 raw_buffer 取帧 → JPEG 压缩 → 编码帧入 frame_buffer
    3. ws_stream.py 推送协程：从 frame_buffer 取数据 → WebSocket 推送给前端
    """
    import cv2
    from backend.routers.yolo_training import load_yolo_model

    if stream_job_manager.get_job_frame_buffer(job_id) is None:
        return

    stream_job_manager.update_job(job_id, status="processing")

    # 加载 YOLO 模型
    detector = load_yolo_model(model_file_path)

    # 获取视频信息
    cap = cv2.VideoCapture(input_path)
    fps = round(cap.get(cv2.CAP_PROP_FPS)) or 24
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    stream_job_manager.update_job(job_id,
        total_frames=total_frames,
        fps=fps,
    )

    # 启动推理线程
    inference_thread = threading.Thread(
        target=_inference_worker,
        args=(job_id, detector, input_path, fps, total_frames, conf_threshold),
        daemon=True,
    )
    inference_thread.start()

    # 启动编码线程
    encode_thread = threading.Thread(
        target=_encode_worker,
        args=(job_id,),
        daemon=True,
    )
    encode_thread.start()

    # 等待推理线程完成
    inference_thread.join()
    # 等待编码线程消费完剩余帧
    encode_thread.join()

    # 更新任务状态为完成
    try:
        db_session = SessionLocal()
        try:
            db_session.query(InferenceJob).filter(
                InferenceJob.job_id == job_id
            ).update({"status": "completed"})
            db_session.commit()
        finally:
            db_session.close()
    except Exception:
        pass  # 状态更新失败不影响检测结果


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

    # 提前生成缩略图（取中间帧）
    video_thumbnail = None
    try:
        cap = cv2.VideoCapture(str(input_path))
        mid_frame = max(0, total_frames // 2)
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        cap.release()
        if ret:
            from PIL import Image as PILImage
            import io
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = PILImage.fromarray(rgb)
            pil_img.thumbnail((40, 40))
            buf = io.BytesIO()
            pil_img.save(buf, format='JPEG', quality=60)
            thumb_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            video_thumbnail = f"data:image/jpeg;base64,{thumb_b64}"
    except Exception:
        pass  # 缩略图生成失败不影响检测

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

    # 记录到数据库
    inference_job = InferenceJob(
        job_id=job_id,
        model_id=model_id,
        file_name=file.filename,
        file_path=str(input_path),
        file_type="video",
        conf_threshold=conf_threshold,
        status="processing",
        thumbnail=video_thumbnail,
    )
    db.add(inference_job)
    db.commit()

    return {
        "success": True,
        "job_id": job_id,
        "stream_url": f"/ws/inference/stream/{job_id}",
        "video_info": {
            "fps": int(fps),
            "total_frames": total_frames,
            "duration": round(total_frames / fps) if fps > 0 else 0,
        },
        "categories": categories,
    }


@router.get("/jobs")
async def list_inference_jobs(db: Session = Depends(get_db)):
    """获取最近 20 条推理记录，按时间倒序。"""
    jobs = db.query(InferenceJob).order_by(
        InferenceJob.created_at.desc()
    ).limit(20).all()

    result = []
    for job in jobs:
        model = db.query(Model).filter(Model.id == job.model_id).first()
        result.append({
            "id": job.id,
            "job_id": job.job_id,
            "model_id": job.model_id,
            "model_name": model.name if model else "",
            "file_name": job.file_name,
            "file_path": job.file_path,
            "file_type": job.file_type,
            "conf_threshold": job.conf_threshold,
            "status": job.status,
            "total_frames": job.total_frames,
            "total_detections": job.total_detections,
            "thumbnail": job.thumbnail,
            "created_at": (job.created_at.isoformat() + 'Z') if job.created_at else None,
            "finished_at": (job.finished_at.isoformat() + 'Z') if job.finished_at else None,
        })
    return result


@router.delete("/jobs")
async def clear_inference_jobs(db: Session = Depends(get_db)):
    """清除所有推理记录。"""
    db.query(InferenceJob).delete()
    db.commit()
    return {"success": True, "message": "已清除所有历史记录"}


@router.post("/jobs/{job_id}/rerun")
async def rerun_inference_job(job_id: str, model_id: int = None, conf_threshold: float = 0.25, db: Session = Depends(get_db)):
    """复用已有记录的配置重新发起检测（图片或视频）。"""
    job = db.query(InferenceJob).filter(InferenceJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="记录不存在")

    if not os.path.exists(job.file_path):
        raise HTTPException(status_code=400, detail="文件已不存在，请重新上传")

    model = db.query(Model).filter(Model.id == (model_id or job.model_id)).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    if job.file_type == "video":
        import cv2
        categories = []
        if model.metrics:
            try:
                categories = json.loads(model.metrics).get('categories', [])
            except json.JSONDecodeError:
                pass

        cap = cv2.VideoCapture(job.file_path)
        fps = round(cap.get(cv2.CAP_PROP_FPS)) or 24
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        from backend.utils.frame_buffer import stream_job_manager
        new_job_id, frame_buffer = stream_job_manager.create_job(
            input_path=job.file_path,
            model_id=model.id,
            conf_threshold=conf_threshold,
            categories=categories,
            fps=fps,
            total_frames=total_frames,
        )

        thread = threading.Thread(
            target=process_video_stream_background,
            args=(new_job_id, model.file_path, conf_threshold, categories, job.file_path),
            daemon=True,
        )
        thread.start()

        return {
            "success": True,
            "job_id": new_job_id,
            "stream_url": f"/ws/inference/stream/{new_job_id}",
            "video_info": {
                "fps": int(fps),
                "total_frames": total_frames,
                "duration": round(total_frames / fps) if fps > 0 else 0,
            },
            "categories": categories,
            "file_type": "video",
        }
    else:
        # 图片：重新执行 detect_image 逻辑
        from backend.routers.yolo_training import load_yolo_model, inference_yolo
        from PIL import Image as PILImage, ImageDraw

        detector = load_yolo_model(model.file_path)
        result = inference_yolo(detector, job.file_path, conf_threshold)

        # 绘制检测结果
        img = PILImage.open(job.file_path)
        draw = ImageDraw.Draw(img)

        categories = []
        if model.metrics:
            try:
                metrics_json = json.loads(model.metrics)
                categories = metrics_json.get('categories', [])
            except json.JSONDecodeError:
                pass
        if not categories:
            class_ids = set(det['class_id'] for det in result['detections'])
            categories = [{'name': f'Class {i}', 'color': '#FF0000'} for i in range(max(class_ids) + 1) if i in class_ids] if class_ids else []

        for det in result['detections']:
            bbox = det['bbox']
            conf = det['confidence']
            cls_id = det['class_id']
            cls_name = det.get('class_name', categories[cls_id]['name'] if cls_id < len(categories) else f'Class {cls_id}')
            color = categories[cls_id]['color'] if cls_id < len(categories) else '#FF0000'
            draw.rectangle(bbox, outline=color, width=3)
            label = f"{cls_name} {conf:.2f}"
            draw.text((bbox[0], bbox[1] - 20), label, fill=color)

        output_path = INFERENCE_OUTPUT_DIR / f"result_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{job.file_name}"
        img.save(output_path)

        with open(output_path, 'rb') as f:
            result_image_b64 = base64.b64encode(f.read()).decode('utf-8')

        # 更新原记录的检测结果和完成时间
        job.status = "completed"
        job.total_detections = result['num_detections']
        job.finished_at = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "original_image": job.file_path,
            "result_image": str(output_path),
            "result_image_base64": f"data:image/jpeg;base64,{result_image_b64}",
            "detections": result['detections'],
            "num_detections": result['num_detections'],
            "file_type": "image",
            "categories": categories,
        }


@router.post("/detect/stop/{job_id}")
async def stop_video_job(job_id: str):
    """停止流式视频检测任务。"""
    job = stream_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    stream_job_manager.stop_job(job_id)
    return {"success": True, "message": "推理已停止"}
