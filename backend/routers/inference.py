# -*- coding: utf-8 -*-
"""模型推理路由 - 图片/视频目标检测。"""

import os
import json
import base64
import shutil
import threading
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from sqlalchemy.orm import Session

from backend.database import get_db, SessionLocal, Model, ModelFile, InferenceJob
from backend.utils.frame_buffer import stream_job_manager

router = APIRouter()

# 推理结果保存目录（统一使用 DATA_DIR）
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
_DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)
INFERENCE_OUTPUT_DIR = Path(os.path.join(_DATA_DIR, "inference_output"))
INFERENCE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_device(device_preference: str, model) -> str:
    """根据用户偏好和硬件情况解析实际设备（使用启动时缓存）。

    Args:
        device_preference: 用户指定偏好 (auto/cpu/cuda/openvino/directml)
        model: 模型对象

    Returns:
        实际使用的设备字符串
    """
    from backend.core.backends.auto_detector import resolve_device_cached
    return resolve_device_cached(device_preference)


def _select_model_file(db: Session, model: Model, format_preference: str = "auto") -> tuple:
    """根据格式偏好选择模型文件。

    Args:
        db: 数据库会话
        model: 模型对象
        format_preference: 格式偏好 ("auto"/"yolo_pt"/"onnx"/"openvino"/"tensorrt")

    Returns:
        (ModelFile, used_format): 选中的模型文件和实际使用的格式
    """
    import os
    import types

    # 直接查询 ModelFile 表而不是通过关系
    files = db.query(ModelFile).filter(ModelFile.model_id == model.id).all()
    if not files:
        # 兼容旧数据：Model.file_path 存储在 Model 表本身
        if model.file_path and os.path.exists(model.file_path):
            fallback = types.SimpleNamespace(
                file_path=model.file_path,
                format=getattr(model, 'format', 'yolo_pt') or 'yolo_pt',
                is_default=True
            )
            return fallback, fallback.format
        return None, None

    if format_preference == "auto":
        # 自动模式：优先使用默认格式，如果没有默认格式则按性能优先级
        # 首先尝试查找 is_default=True 且文件存在的格式
        for mf in files:
            if mf.is_default and os.path.exists(mf.file_path):
                return mf, mf.format
        # 如果没有默认格式，按性能优先级 tensorrt > openvino > onnx > yolo_pt，同时检查文件存在
        priority = ["tensorrt", "openvino", "onnx", "yolo_pt"]
        for fmt in priority:
            for mf in files:
                if mf.format == fmt and os.path.exists(mf.file_path):
                    return mf, fmt
        # 优先格式都无效，返回第一个存在的文件
        for mf in files:
            if os.path.exists(mf.file_path):
                return mf, mf.format
        return None, None
    else:
        # 指定格式
        for mf in files:
            if mf.format == format_preference and os.path.exists(mf.file_path):
                return mf, format_preference
        # 指定格式文件不存在或格式不存在，返回默认存在的文件
        for mf in files:
            if mf.is_default and os.path.exists(mf.file_path):
                return mf, mf.format
        for mf in files:
            if os.path.exists(mf.file_path):
                return mf, mf.format
        return None, None


# ===== API 端点 =====


@router.post("/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    model_id: int = Query(...),
    conf_threshold: float = Query(default=0.25),
    device: str = Query(default="auto"),  # 推理设备: auto/cpu/cuda
    precision: str = Query(default="fp32"),  # 推理精度: fp32/fp16
    format: str = Query(default="auto"),  # 模型格式: auto/yolo_pt/onnx/openvino/tensorrt
    db: Session = Depends(get_db)
):
    """对单张图片进行目标检测。

    Args:
        file: 上传的图片文件
        model_id: 模型 ID
        conf_threshold: 置信度阈值
        device: 推理设备 (auto/cpu/cuda)
        precision: 推理精度 (fp32/fp16)
        format: 模型格式 (auto=自动选择，否则指定格式)
    """
    # 验证模型
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 根据格式偏好选择模型文件
    model_file, used_format = _select_model_file(db, model, format)
    if not model_file or not os.path.exists(model_file.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    # 保存上传的图片
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_path = INFERENCE_OUTPUT_DIR / f"input_{timestamp}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        from backend.services.inference_service import load_yolo_model, inference_yolo
        import cv2
        import numpy as np

        # 根据模型格式和设备偏好确定实际设备
        actual_device = _resolve_device(device, model)

        # 从 model.metrics 提取 class_names 映射（ONNX/OpenVINO fallback）
        _class_names = None
        if model.metrics:
            try:
                _cats = json.loads(model.metrics).get('categories', [])
                if _cats:
                    _class_names = {i: c['name'] for i, c in enumerate(_cats)}
            except json.JSONDecodeError:
                pass

        detector = load_yolo_model(model_file.file_path, device=actual_device, class_names=_class_names, precision=precision)

        # 读取图片为 numpy 数组
        img = cv2.imread(str(file_path))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 根据 detector 类型选择推理方式
        if hasattr(detector, '_model') and detector._model is None:
            # ONNX 等格式的 handler，没有 _model，直接调用 infer 方法
            infer_result = detector.infer(img_rgb, conf=conf_threshold)
            result = {
                'image_path': str(file_path),
                'num_detections': infer_result.num_detections,
                'detections': infer_result.detections,
            }
        else:
            # YOLO 模型，使用原有的 inference_yolo
            result = inference_yolo(detector, str(file_path), conf_threshold, device=actual_device)

        # 返回原图（画框由前端 SVG overlay 负责）
        with open(file_path, 'rb') as f:
            result_image_b64 = base64.b64encode(f.read()).decode('utf-8')

        # 生成缩略图（输入图缩略图）
        from PIL import Image as PILImage
        thumb_img = PILImage.open(file_path)
        thumb_img.thumbnail((40, 40))
        import io
        thumb_buf = io.BytesIO()
        thumb_img.save(thumb_buf, format='JPEG', quality=60)
        thumb_b64 = base64.b64encode(thumb_buf.getvalue()).decode('utf-8')

        # 构建 name -> color 映射（从 Category 表）
        from backend.routers.category import Category
        name_to_color = {}
        for cat in db.query(Category).filter(Category.is_directory == False).all():
            name_to_color[cat.name] = cat.color

        # 记录到数据库（用输入图路径，支持重新检测）
        import uuid
        record = InferenceJob(
            job_id=str(uuid.uuid4())[:8],
            model_id=model_id,
            file_name=file.filename,
            file_path=str(file_path),  # 输入图路径，保留在磁盘
            file_type="image",
            conf_threshold=conf_threshold,
            device=actual_device,
            precision=precision,
            used_format=used_format,
            status="completed",
            total_detections=result['num_detections'],
            thumbnail=f"data:image/jpeg;base64,{thumb_b64}",
        )
        db.add(record)
        db.commit()

        # 从 model.metrics 读取 categories（用于前端展示标签颜色）
        categories = []
        if model.metrics:
            try:
                categories = json.loads(model.metrics).get('categories', [])
            except json.JSONDecodeError:
                pass

        # 补充 color 字段：从 Category 表按类名查找
        for cat in categories:
            cat['color'] = name_to_color.get(cat['name'], '#FF0000')

        return {
            "success": True,
            "original_image": str(file_path),
            "result_image": str(file_path),
            "result_image_base64": f"data:image/jpeg;base64,{result_image_b64}",
            "detections": result['detections'],
            "num_detections": result['num_detections'],
            "categories": categories,
            "used_format": used_format,  # 实际使用的格式
        }
    except Exception as e:
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

        # 获取模型的所有格式文件（直接查询）
        files = []
        model_files = db.query(ModelFile).filter(ModelFile.model_id == m.id).all()
        for mf in model_files:
            files.append({
                "format": mf.format,
                "file_path": mf.file_path,
                "is_default": mf.is_default,
            })

        result.append({
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "file_path": m.file_path,  # 兼容字段
            "metrics": metrics,
            "files": files,
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
                # 检测 detector 类型
                if hasattr(detector, 'infer'):
                    # ONNX 等 handler，使用 .infer() 方法
                    infer_result = detector.infer(rgb_frame, conf=conf_threshold)
                    detections = []
                    for det in infer_result.detections:
                        detections.append({
                            "bbox": det["bbox"],
                            "class_id": det["class_id"],
                            "class_name": det["class_name"],
                            "confidence": det["confidence"],
                        })
                        total_detections += 1
                else:
                    # PT YOLO 模型，使用调用接口
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

        raw = raw_buffer.get(timeout=0.5)
        if raw is None:
            # 取不到帧时，确认推理是否已结束且缓冲已空
            if job.get("inference_done") and raw_buffer.qsize == 0:
                break
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
    device: str = "cpu",
    precision: str = "fp32",
):
    """后台线程：流式处理视频，推理与编码分离为流水线。

    流水线：
    1. _inference_worker：读取视频帧 → YOLO 推理 → 原始帧入 raw_buffer
    2. _encode_worker：从 raw_buffer 取帧 → JPEG 压缩 → 编码帧入 frame_buffer
    3. ws_stream.py 推送协程：从 frame_buffer 取数据 → WebSocket 推送给前端
    """
    import cv2
    from backend.services.inference_service import load_yolo_model

    if stream_job_manager.get_job_frame_buffer(job_id) is None:
        return

    stream_job_manager.update_job(job_id, status="processing")

    # 从 categories 构建 class_names 映射（作为 ONNX/OpenVINO 的 fallback）
    class_names = {i: cat['name'] for i, cat in enumerate(categories)} if categories else None

    # 加载 YOLO 模型
    detector = load_yolo_model(model_file_path, device=device, class_names=class_names, precision=precision)

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

    # 等待推理线程完成（不设超时，让视频完整跑完）
    inference_thread.join()
    # 等待编码线程消费完剩余帧
    encode_thread.join()

    # 推理和编码都完成后才更新 DB 状态
    job = stream_job_manager.get_job(job_id)
    final_status = job["status"] if job else "completed"
    try:
        db_session = SessionLocal()
        try:
            db_session.query(InferenceJob).filter(
                InferenceJob.job_id == job_id
            ).update({"status": final_status})
            db_session.commit()
        finally:
            db_session.close()
    except Exception:
        pass  # 状态更新失败不影响检测结果


@router.post("/detect/video/stream", status_code=202)
async def detect_video_stream(
    file: UploadFile = File(...),
    model_id: int = Query(...),
    conf_threshold: float = Query(default=0.25),
    device: str = Query(default="auto"),  # 推理设备: auto/cpu/cuda
    precision: str = Query(default="fp32"),  # 推理精度: fp32/fp16
    format: str = Query(default="auto"),  # 模型格式: auto/yolo_pt/onnx/openvino/tensorrt
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

    # 根据格式偏好选择模型文件
    model_file, used_format = _select_model_file(db, model, format)
    if not model_file or not os.path.exists(model_file.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    # 解析实际设备
    actual_device = _resolve_device(device, model)

    # 获取类别信息
    categories = []
    if model.metrics:
        try:
            metrics = json.loads(model.metrics)
            categories = metrics.get('categories', [])
        except json.JSONDecodeError:
            pass

    # 从 Category 表补充颜色（覆盖模型训练时保存的默认色）
    from backend.routers.category import Category as CategoryModel
    name_to_color = {}
    for cat in db.query(CategoryModel).filter(CategoryModel.is_directory == False).all():
        name_to_color[cat.name] = cat.color
    for cat in categories:
        cat['color'] = name_to_color.get(cat['name'], cat.get('color', '#FF0000'))

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
        args=(job_id, model_file.file_path, conf_threshold, categories, str(input_path), actual_device, precision),
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
        device=actual_device,
        precision=precision,
        used_format=used_format,
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
        "used_format": used_format,
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
            "device": getattr(job, 'device', 'cpu') or 'cpu',
            "precision": getattr(job, 'precision', 'fp32') or 'fp32',
            "used_format": getattr(job, 'used_format', 'yolo_pt') or 'yolo_pt',
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
async def rerun_inference_job(
    job_id: str,
    model_id: int = None,
    conf_threshold: float = Query(default=0.25),
    device: str = Query(default="auto"),
    format: str = Query(default="auto"),
    precision: str = Query(default="fp32"),
    db: Session = Depends(get_db)
):
    """使用当前配置（而非历史配置）重新发起检测（图片或视频）。

    Args:
        job_id: 原有任务 ID
        model_id: 模型 ID（默认使用原任务的模型）
        conf_threshold: 置信度阈值
        device: 推理设备 (auto/cpu/cuda)
        format: 模型格式 (auto/yolo_pt/onnx/openvino/tensorrt)
    """
    import asyncio

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

    # 解析实际设备
    actual_device = _resolve_device(device, model)

    # 根据格式偏好选择模型文件
    model_file, used_format = _select_model_file(db, model, format)
    if not model_file or not os.path.exists(model_file.file_path):
        raise HTTPException(status_code=400, detail="模型文件不存在")

    if job.file_type == "video":
        import cv2
        categories = []
        if model.metrics:
            try:
                categories = json.loads(model.metrics).get('categories', [])
            except json.JSONDecodeError:
                pass

        # 从 Category 表补充颜色（覆盖模型训练时保存的默认色）
        from backend.routers.category import Category as CategoryModel
        try:
            name_to_color = {}
            for cat in db.query(CategoryModel).filter(CategoryModel.is_directory == False).all():
                name_to_color[cat.name] = cat.color
            for cat in categories:
                cat['color'] = name_to_color.get(cat['name'], cat.get('color', '#FF0000'))
        except Exception:
            pass  # 颜色获取失败不影响检测流程

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

        # 使用当前UI参数创建新的推理记录
        import uuid as uuid_mod
        new_record = InferenceJob(
            job_id=new_job_id,
            model_id=model.id,
            file_name=job.file_name,
            file_path=job.file_path,
            file_type="video",
            conf_threshold=conf_threshold,
            device=actual_device,
            precision=precision,
            used_format=used_format,
            status="processing",
            total_frames=total_frames,
            thumbnail=job.thumbnail,
        )
        db.add(new_record)
        db.commit()

        thread = threading.Thread(
            target=process_video_stream_background,
            args=(new_job_id, model_file.file_path, conf_threshold, categories, job.file_path, actual_device, precision),
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
            "used_format": used_format,
            "file_type": "video",
        }
    else:
        # 图片：重新执行 detect_image 逻辑（只返回原图，画框由前端负责）
        from backend.services.inference_service import load_yolo_model, inference_yolo

        # 从 model.metrics 提取 class_names（ONNX/OpenVINO fallback）
        _img_class_names = None
        if model.metrics:
            try:
                _img_cats = json.loads(model.metrics).get('categories', [])
                if _img_cats:
                    _img_class_names = {i: c['name'] for i, c in enumerate(_img_cats)}
            except json.JSONDecodeError:
                pass

        detector = load_yolo_model(model_file.file_path, device=actual_device, class_names=_img_class_names, precision=precision)

        # 根据 detector 类型选择推理方式
        if hasattr(detector, '_model') and detector._model is None:
            # ONNX 等格式的 handler
            import cv2
            img = cv2.imread(job.file_path)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            infer_result = detector.infer(img_rgb, conf=conf_threshold)
            result = {
                'num_detections': infer_result.num_detections,
                'detections': infer_result.detections,
            }
        else:
            # YOLO 模型
            result = inference_yolo(detector, job.file_path, conf_threshold, device=actual_device)

        # 返回原图（画框由前端 SVG overlay 负责）
        with open(job.file_path, 'rb') as f:
            result_image_b64 = base64.b64encode(f.read()).decode('utf-8')

        # 生成缩略图
        from PIL import Image as PILImage
        thumb_img = PILImage.open(job.file_path)
        thumb_img.thumbnail((40, 40))
        import io
        thumb_buf = io.BytesIO()
        thumb_img.save(thumb_buf, format='JPEG', quality=60)
        thumb_b64 = base64.b64encode(thumb_buf.getvalue()).decode('utf-8')

        # 使用当前UI参数创建新记录（而非修改历史记录）
        import uuid
        new_record = InferenceJob(
            job_id=str(uuid.uuid4())[:8],
            model_id=model.id,
            file_name=job.file_name,
            file_path=job.file_path,
            file_type="image",
            conf_threshold=conf_threshold,
            device=actual_device,
            precision=precision,
            used_format=used_format,
            status="completed",
            total_detections=result['num_detections'],
            thumbnail=f"data:image/jpeg;base64,{thumb_b64}",
        )
        db.add(new_record)
        db.commit()

        # 构建 name -> color 映射（从 Category 表）
        from backend.routers.category import Category
        cat_name_to_color = {}
        for cat in db.query(Category).filter(Category.is_directory == False).all():
            cat_name_to_color[cat.name] = cat.color

        # 从 model.metrics 读取 categories（用于前端展示）
        categories = []
        if model.metrics:
            try:
                categories = json.loads(model.metrics).get('categories', [])
            except json.JSONDecodeError:
                pass

        # 补充 color 字段：从 Category 表按类名查找
        for cat in categories:
            cat['color'] = cat_name_to_color.get(cat['name'], '#FF0000')

        return {
            "success": True,
            "original_image": job.file_path,
            "result_image": job.file_path,
            "result_image_base64": f"data:image/jpeg;base64,{result_image_b64}",
            "detections": result['detections'],
            "num_detections": result['num_detections'],
            "categories": categories,
            "file_type": "image",
            "used_format": used_format,
        }


@router.post("/detect/stop/{job_id}")
async def stop_video_job(job_id: str):
    """停止流式视频检测任务。"""
    job = stream_job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    stream_job_manager.stop_job(job_id)
    return {"success": True, "message": "推理已停止"}
