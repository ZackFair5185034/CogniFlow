# -*- coding: utf-8 -*-
"""训练管理路由。

提供训练任务的启动、停止和状态查询。
"""
import json
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, TrainingJob, Model, Atlas
from schemas import TrainingJobCreate, TrainingJobResponse

router = APIRouter()


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


@router.post("/start", response_model=TrainingJobResponse, status_code=201)
async def start_training(data: TrainingJobCreate, db: Session = Depends(get_db)):
    """启动训练任务。"""
    # 验证模型存在
    model = db.query(Model).filter(Model.id == data.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 验证图集存在
    atlas = db.query(Atlas).filter(Atlas.id == data.atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    job = TrainingJob(
        model_id=data.model_id,
        atlas_id=data.atlas_id,
        status="pending",
        config=json.dumps(data.config) if data.config else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # TODO: 实际启动训练进程
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
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="训练任务不存在")

    job.status = "failed"
    job.finished_at = datetime.utcnow()
    db.commit()

    # TODO: 实际停止训练进程
    return {"message": "训练任务已停止"}
