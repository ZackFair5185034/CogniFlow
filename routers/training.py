# -*- coding: utf-8 -*-
"""训练管理路由。

提供训练任务的启动、停止和状态查询。
"""
import json
import asyncio
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, TrainingJob, Model, Atlas
from schemas import TrainingJobCreate, TrainingJobResponse
from websocket_manager import ws_manager

router = APIRouter()

# 模拟训练状态存储（实际项目中应使用进程间通信或数据库）
_training_simulator_running = False
_training_simulator_task: Optional[asyncio.Task] = None


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


async def _simulate_training(job_id: int, total_steps: int):
    """模拟训练过程，每秒更新一次进度。"""
    import asyncio
    global _training_simulator_running

    job = None
    try:
        # 获取数据库会话
        from database import SessionLocal
        db = SessionLocal()

        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.total_steps = total_steps
        db.commit()

        for step in range(1, total_steps + 1):
            if not _training_simulator_running:
                break

            job.current_step = step
            # 模拟 loss 下降
            loss = 2.0 * (1 - step / total_steps) + 0.1
            job.metrics = json.dumps({
                "loss": round(loss, 4),
                "step": step,
            })
            db.commit()

            # 通过 WebSocket 发送进度
            await ws_manager.send_training_update(job_id, {
                "step": step,
                "total_steps": total_steps,
                "loss": round(loss, 4),
            })

            await asyncio.sleep(0.1)  # 模拟 100ms 训练时间

        if _training_simulator_running:
            job.status = "completed"
        else:
            job.status = "failed"
        job.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        if job:
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        if db:
            db.close()


@router.post("/start", response_model=TrainingJobResponse, status_code=201)
async def start_training(data: TrainingJobCreate, db: Session = Depends(get_db)):
    """启动训练任务。"""
    global _training_simulator_running, _training_simulator_task

    # 验证模型存在
    model = db.query(Model).filter(Model.id == data.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 验证图集存在
    atlas = db.query(Atlas).filter(Atlas.id == data.atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 获取总步数
    total_steps = 1000
    if data.config and "total_steps" in data.config:
        total_steps = data.config["total_steps"]

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

    # 启动模拟训练
    _training_simulator_running = True
    _training_simulator_task = asyncio.create_task(_simulate_training(job.id, total_steps))

    return TrainingJobResponse(
        id=job.id,
        model_id=job.model_id,
        atlas_id=job.atlas_id,
        status=job.status,
        config=json.loads(job.config) if job.config else None,
        current_step=job.current_step,
        total_steps=job.total_steps,
        metrics=None,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.post("/stop")
async def stop_training(job_id: int, db: Session = Depends(get_db)):
    """停止训练任务。"""
    global _training_simulator_running, _training_simulator_task

    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    _training_simulator_running = False
    if _training_simulator_task:
        _training_simulator_task.cancel()
        _training_simulator_task = None

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
            current_step = current_metrics.get("step", 0)
            for step in range(1, min(current_step + 1, 101)):
                simulated_loss = 2.0 * (1 - step / 100) + 0.1
                history.append({"step": step, "loss": round(simulated_loss, 4)})
        except json.JSONDecodeError:
            pass

    return {
        "job_id": job_id,
        "current_step": job.current_step,
        "total_steps": job.total_steps,
        "history": history,
    }
