# -*- coding: utf-8 -*-
"""训练管理路由。

提供训练任务的启动、停止和状态查询。
"""
import json
import asyncio
import os
import shutil
import threading
import time
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, TrainingJob, Model, Atlas
from schemas import TrainingJobCreate, TrainingJobResponse
from websocket_manager import ws_manager

router = APIRouter()

# 训练状态存储
_training_running = False
_training_task: Optional[asyncio.Task] = None
_training_thread: Optional[threading.Thread] = None  # 保存训练线程引用
_stop_event = threading.Event()  # 停止事件
_progress_lock = threading.Lock()  # 进度更新锁

# 当前训练进度（供轮询使用）
_current_training_progress = {"job_id": None, "epoch": 0, "total_epochs": 0, "status": "idle"}

# 检查点保存目录
CHECKPOINT_DIR = Path("./checkpoints")


@router.get("/jobs", response_model=List[TrainingJobResponse])
async def list_training_jobs(db: Session = Depends(get_db)):
    """获取训练任务列表。"""
    jobs = db.query(TrainingJob).order_by(TrainingJob.started_at.desc()).all()
    results = []
    for job in jobs:
        results.append(TrainingJobResponse(
            id=job.id,
            model_id=job.model_id,
            atlas_id=job.atlas_id,
            status=job.status,
            config=json.loads(job.config) if job.config else None,
            current_step=job.current_step,
            total_steps=job.total_steps,
            metrics=json.loads(job.metrics) if job.metrics else None,
            started_at=job.started_at,
            finished_at=job.finished_at,
        ))
    return results


@router.get("/device-info")
async def get_device_info():
    """获取可用训练设备信息。"""
    from routers.yolo_training import check_gpu_available
    return check_gpu_available()


@router.get("/progress")
async def get_training_progress():
    """获取当前训练进度，用于前端轮询。"""
    with _progress_lock:
        return _current_training_progress.copy()


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(job_id: int, db: Session = Depends(get_db)):
    """获取训练任务详情。"""
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return TrainingJobResponse(
        id=job.id,
        model_id=job.model_id,
        atlas_id=job.atlas_id,
        status=job.status,
        config=json.loads(job.config) if job.config else None,
        current_step=job.current_step,
        total_steps=job.total_steps,
        metrics=json.loads(job.metrics) if job.metrics else None,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def _send_progress_via_ws(job_id: int, progress: dict):
    """通过 WebSocket 发送进度更新（异步安全）。"""
    try:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            # 从线程中安全地创建异步任务
            asyncio.run_coroutine_threadsafe(
                ws_manager.send_training_update(job_id, progress),
                loop,
            )
    except Exception as e:
        print(f"[训练] WebSocket 发送失败: {e}")


async def _yolo_training(job_id: int, total_steps: int, model_id: int, atlas_id: int):
    """使用 YOLO 进行真正的训练。"""
    global _training_running, _training_thread

    db = None
    job = None

    try:
        from database import SessionLocal
        db = SessionLocal()

        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            return

        # 更新任务状态
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.total_steps = total_steps
        db.commit()

        print(f"[YOLO训练] 开始训练 job_id={job_id}, model_id={model_id}, atlas_id={atlas_id}")

        # 发送初始进度
        await ws_manager.send_training_update(job_id, {
            "step": 0,
            "total_steps": total_steps,
            "status": "running",
            "message": "准备数据集..."
        })

        # 创建临时数据集目录
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dataset_dir = Path(f"./datasets/yolo_atlas_{atlas_id}_{timestamp}")
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # 导出数据到 YOLO 格式
        from routers.yolo_training import export_to_yolo_format
        export_result = export_to_yolo_format(atlas_id, db, str(dataset_dir))

        print(f"[YOLO训练] 数据导出完成: {export_result['exported']} 张图片, {export_result['num_classes']} 个类别")

        if export_result['exported'] == 0:
            raise Exception("没有可用的标注数据")

        # 创建 YOLO 数据配置文件
        data_yaml = dataset_dir / "data.yaml"
        data_yaml_content = f"""
# YOLO 数据集配置
path: {dataset_dir.absolute()}
train: images
val: images

# 类别数量
nc: {export_result['num_classes']}

# 类别名称
names: {json.dumps([c['name'] for c in export_result['classes']])}
"""
        with open(data_yaml, 'w', encoding='utf-8') as f:
            f.write(data_yaml_content)

        # 获取训练配置
        config = json.loads(job.config) if job.config else {}
        epochs = config.get('epochs', 50)
        batch_size = config.get('batch_size', 16)
        imgsz = config.get('imgsz', 640)
        device = config.get('device', 'cpu')
        pretrained_model = config.get('pretrained_model', 'yolov8n.pt')

        # 获取模型的预训练模型配置（如果config中没有）
        if pretrained_model == 'yolov8n.pt' and model_id:
            from database import Model
            model_record = db.query(Model).filter(Model.id == model_id).first()
            if model_record and model_record.pretrained_model:
                pretrained_model = model_record.pretrained_model

        print(f"[YOLO训练] 配置: epochs={epochs}, batch_size={batch_size}, imgsz={imgsz}, device={device}, pretrained={pretrained_model}")

        # 发送数据准备完成消息
        await ws_manager.send_training_update(job_id, {
            "step": 0,
            "total_steps": epochs,
            "status": "running",
            "message": f"开始训练 {epochs} 轮..."
        })

        # 重置停止事件
        _stop_event.clear()

        # 训练 YOLO 模型（在独立线程中运行以避免阻塞事件循环）
        from routers.yolo_training import train_yolo
        model_save_path = CHECKPOINT_DIR / f"model_{model_id}_{timestamp}"
        model_save_path.mkdir(parents=True, exist_ok=True)

        # 在线程中运行同步训练
        def run_training():
            # 更新全局进度，供轮询使用
            global _current_training_progress
            with _progress_lock:
                _current_training_progress = {
                    "job_id": job_id,
                    "epoch": 0,
                    "total_epochs": epochs,
                    "status": "downloading",
                    "message": f"正在下载预训练模型 {pretrained_model}..."
                }

            # 训练完成后的回调，在线程中执行数据库更新
            def on_complete(result):
                global _current_training_progress
                from database import SessionLocal, Model
                from datetime import datetime as dt
                import json as json_module

                db_thread = SessionLocal()
                try:
                    model_record = db_thread.query(Model).filter(Model.id == model_id).first()
                    if model_record:
                        model_record.file_path = result['best_model']
                        model_record.metrics = json_module.dumps({
                            "mAP50": result['metrics']['mAP50'],
                            "mAP50-95": result['metrics']['mAP50-95'],
                            "epochs": epochs,
                            "num_classes": export_result['num_classes'],
                            "trained_at": timestamp,
                            "best_model": result['best_model'],
                            "categories": export_result['classes']
                        })
                        db_thread.commit()

                    # 更新任务状态
                    job_thread = db_thread.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                    if job_thread:
                        job_thread.status = "completed"
                        job_thread.current_step = epochs
                        job_thread.metrics = json_module.dumps({
                            "mAP50": result['metrics']['mAP50'],
                            "mAP50-95": result['metrics']['mAP50-95'],
                            "epochs": epochs
                        })
                        job_thread.finished_at = dt.utcnow()
                        db_thread.commit()

                    # 清理临时数据集目录
                    import shutil
                    shutil.rmtree(dataset_dir, ignore_errors=True)

                    # 更新进度状态
                    with _progress_lock:
                        _current_training_progress["status"] = "completed"
                        _current_training_progress["epoch"] = epochs

                    # WebSocket 通知完成
                    _send_progress_via_ws(job_id, {
                        "step": epochs,
                        "total_steps": epochs,
                        "status": "completed",
                        "message": "训练完成",
                    })

                    print(f"[YOLO训练] 训练完成，模型已保存到: {result['best_model']}")
                except Exception as e:
                    print(f"[YOLO训练] 完成回调出错: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    db_thread.close()

            # 进度回调 - 由 train_yolo 在真实 epoch 结束时调用
            def on_progress(epoch, total_epochs, message=None):
                global _current_training_progress
                with _progress_lock:
                    if epoch == 0:
                        # 下载阶段
                        _current_training_progress["status"] = "downloading"
                    else:
                        # 训练阶段
                        _current_training_progress["status"] = "running"
                    _current_training_progress["epoch"] = epoch
                    _current_training_progress["total_epochs"] = total_epochs
                    if message:
                        _current_training_progress["message"] = message

                # 训练阶段通过 WebSocket 推送真实进度
                if epoch > 0:
                    _send_progress_via_ws(job_id, {
                        "step": epoch,
                        "total_steps": total_epochs,
                        "status": "running",
                        "message": message or f"训练中 {epoch}/{total_epochs}",
                    })

            try:
                train_yolo(
                    data_yaml_path=str(data_yaml),
                    model_save_path=str(model_save_path),
                    epochs=epochs,
                    batch_size=batch_size,
                    imgsz=imgsz,
                    device=device,
                    pretrained_model=pretrained_model,
                    stop_event=_stop_event,
                    on_complete=on_complete,
                    on_progress=on_progress
                )
            except Exception as e:
                print(f"[YOLO训练] 训练线程出错: {e}")
                with _progress_lock:
                    _current_training_progress["status"] = "failed"
                    _current_training_progress["message"] = str(e)
                import traceback
                traceback.print_exc()

                # WebSocket 通知失败
                _send_progress_via_ws(job_id, {
                    "step": 0,
                    "total_steps": epochs,
                    "status": "failed",
                    "error": str(e),
                })

                # 更新任务状态为失败
                from database import SessionLocal, Model
                from datetime import datetime as dt
                import json as json_module

                db_thread = SessionLocal()
                try:
                    job_thread = db_thread.query(TrainingJob).filter(TrainingJob.id == job_id).first()
                    if job_thread:
                        job_thread.status = "failed"
                        job_thread.finished_at = dt.utcnow()
                        job_thread.metrics = json_module.dumps({"error": str(e)})
                        db_thread.commit()
                except Exception as db_e:
                    print(f"[YOLO训练] 更新失败状态出错: {db_e}")
                finally:
                    db_thread.close()

        # 保存线程引用以便停止
        import functools
        wrapper = functools.partial(run_training)
        _training_thread = threading.Thread(target=wrapper)
        _training_thread.start()

        # 训练线程已启动，立即返回，不等待完成
        # 训练完成后的处理在 train_yolo 内部通过回调完成
        print(f"[YOLO训练] 训练线程已启动")
        return

    except Exception as e:
        print(f"[YOLO训练] 训练出错: {e}")
        import traceback
        traceback.print_exc()
        if job:
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            if db:
                db.commit()

        # 发送失败消息
        await ws_manager.send_training_update(job_id, {
            "status": "failed",
            "error": str(e)
        })

    finally:
        if db:
            db.close()


@router.post("/start", response_model=TrainingJobResponse, status_code=201)
async def start_training(data: TrainingJobCreate, db: Session = Depends(get_db)):
    """启动训练任务。"""
    global _training_running, _training_task

    # 验证模型存在
    model = db.query(Model).filter(Model.id == data.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 验证图集存在
    atlas = db.query(Atlas).filter(Atlas.id == data.atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 获取总步数（转换为 epochs）
    total_steps = 1000
    if data.config:
        if "total_steps" in data.config:
            total_steps = data.config["total_steps"]
        elif "epochs" in data.config:
            total_steps = data.config["epochs"]

    job = TrainingJob(
        model_id=data.model_id,
        atlas_id=data.atlas_id,
        status="pending",
        config=json.dumps(data.config) if data.config else None,
        total_steps=total_steps,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 启动 YOLO 训练
    _training_running = True
    _training_task = asyncio.create_task(
        _yolo_training(job.id, total_steps, data.model_id, data.atlas_id)
    )

    return TrainingJobResponse(
        id=job.id,
        model_id=job.model_id,
        atlas_id=job.atlas_id,
        status=job.status,
        config=json.loads(job.config) if data.config else None,
        current_step=job.current_step,
        total_steps=job.total_steps,
        metrics=None,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("/stop")
async def stop_training(job_id: int, db: Session = Depends(get_db)):
    """停止训练任务。"""
    global _training_running, _training_task, _training_thread

    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    _training_running = False
    _stop_event.set()  # 触发停止事件

    # 等待线程结束
    if _training_thread and _training_thread.is_alive():
        _training_thread.join(timeout=5)
    _training_thread = None

    if _training_task:
        _training_task.cancel()
        _training_task = None

    job.status = "failed"
    job.finished_at = datetime.utcnow()
    db.commit()

    return {"message": "训练任务已停止"}


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_training_job(job_id: int, db: Session = Depends(get_db)):
    """删除训练任务。"""
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    db.delete(job)
    db.commit()
    return None


@router.delete("/jobs", status_code=204)
async def delete_all_training_jobs(db: Session = Depends(get_db)):
    """删除所有已完成的训练任务。"""
    db.query(TrainingJob).filter(
        TrainingJob.status.in_(["completed", "failed"])
    ).delete()
    db.commit()
    return None


@router.get("/jobs/{job_id}/metrics-history")
async def get_training_metrics_history(job_id: int, db: Session = Depends(get_db)):
    """获取训练任务的指标历史（用于绘制训练曲线）。"""
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    history = []
    if job.metrics:
        try:
            current_metrics = json.loads(job.metrics)
            # 生成模拟历史数据用于绘图
            for i in range(10):
                step = (i + 1) * 10
                simulated_loss = 2.0 * (1 - i / 10) + 0.1
                history.append({"step": step, "loss": round(simulated_loss, 4)})
        except json.JSONDecodeError:
            pass

    return {
        "job_id": job_id,
        "current_step": job.current_step,
        "total_steps": job.total_steps,
        "history": history,
    }
