# -*- coding: utf-8 -*-
"""模型管理路由。

提供模型的元数据管理和最佳模型设置。
"""
import json
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db, Model
from schemas import ModelCreate, ModelUpdate, ModelResponse

router = APIRouter()

# 模型存储根目录
MODEL_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads", "models")


@router.get("", response_model=List[ModelResponse])
async def list_models(db: Session = Depends(get_db)):
    """获取模型列表。"""
    models = db.query(Model).order_by(Model.created_at.desc()).all()
    results = []
    for m in models:
        results.append(ModelResponse(
            id=m.id,
            name=m.name,
            version=m.version,
            pretrained_model=m.pretrained_model,
            file_path=m.file_path,
            atlas_id=m.atlas_id,
            metrics=json.loads(m.metrics) if m.metrics else None,
            is_best=m.is_best,
            created_at=m.created_at,
        ))
    return results


@router.post("", response_model=ModelResponse, status_code=201)
async def create_model(data: ModelCreate, db: Session = Depends(get_db)):
    """创建新模型记录。"""
    # 检查名称+版本组合是否已存在
    existing = db.query(Model).filter(
        Model.name == data.name,
        Model.version == data.version
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"模型 '{data.name}' (版本: {data.version or '无'}) 已存在")

    model = Model(
        name=data.name,
        version=data.version,
        pretrained_model=data.pretrained_model,
        file_path=data.file_path,
        atlas_id=data.atlas_id,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return ModelResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        pretrained_model=model.pretrained_model,
        file_path=model.file_path,
        atlas_id=model.atlas_id,
        metrics=None,
        is_best=model.is_best,
        created_at=model.created_at,
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int, db: Session = Depends(get_db)):
    """获取模型详情。"""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")
    return ModelResponse(
        id=m.id,
        name=m.name,
        version=m.version,
        pretrained_model=m.pretrained_model,
        file_path=m.file_path,
        atlas_id=m.atlas_id,
        metrics=json.loads(m.metrics) if m.metrics else None,
        is_best=m.is_best,
        created_at=m.created_at,
    )


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: int,
    data: ModelUpdate,
    db: Session = Depends(get_db)
):
    """更新模型。"""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")

    if data.name is not None:
        m.name = data.name
    if data.version is not None:
        m.version = data.version
    if data.pretrained_model is not None:
        m.pretrained_model = data.pretrained_model
    if data.file_path is not None:
        m.file_path = data.file_path
    if data.metrics is not None:
        m.metrics = json.dumps(data.metrics)

    db.commit()
    db.refresh(m)
    return ModelResponse(
        id=m.id,
        name=m.name,
        version=m.version,
        pretrained_model=m.pretrained_model,
        file_path=m.file_path,
        atlas_id=m.atlas_id,
        metrics=json.loads(m.metrics) if m.metrics else None,
        is_best=m.is_best,
        created_at=m.created_at,
    )


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int, db: Session = Depends(get_db)):
    """删除模型。"""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")

    db.delete(m)
    db.commit()
    return None


@router.post("/{model_id}/set-best", response_model=ModelResponse)
async def set_best_model(model_id: int, db: Session = Depends(get_db)):
    """将模型设为最佳模型。"""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 取消其他最佳模型
    db.query(Model).filter(Model.is_best == True).update({"is_best": False})

    m.is_best = True
    db.commit()
    db.refresh(m)
    return ModelResponse(
        id=m.id,
        name=m.name,
        version=m.version,
        pretrained_model=m.pretrained_model,
        file_path=m.file_path,
        atlas_id=m.atlas_id,
        metrics=json.loads(m.metrics) if m.metrics else None,
        is_best=m.is_best,
        created_at=m.created_at,
    )


@router.post("/{model_id}/upload", response_model=ModelResponse)
async def upload_model_file(
    model_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传模型文件。"""
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 确保上传目录存在
    os.makedirs(MODEL_STORAGE_DIR, exist_ok=True)

    # 保存模型文件
    file_path = os.path.join(MODEL_STORAGE_DIR, f"model_{model_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # 更新模型记录
    m.file_path = file_path
    db.commit()
    db.refresh(m)

    return ModelResponse(
        id=m.id,
        name=m.name,
        version=m.version,
        pretrained_model=m.pretrained_model,
        file_path=m.file_path,
        atlas_id=m.atlas_id,
        metrics=json.loads(m.metrics) if m.metrics else None,
        is_best=m.is_best,
        created_at=m.created_at,
    )


@router.get("/{model_id}/training-history")
async def get_model_training_history(model_id: int, db: Session = Depends(get_db)):
    """获取模型的训练历史。"""
    from database import TrainingJob

    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="模型不存在")

    jobs = db.query(TrainingJob).filter(
        TrainingJob.model_id == model_id
    ).order_by(TrainingJob.started_at.desc()).all()

    results = []
    for job in jobs:
        results.append({
            "id": job.id,
            "status": job.status,
            "config": json.loads(job.config) if job.config else None,
            "current_step": job.current_step,
            "total_steps": job.total_steps,
            "metrics": json.loads(job.metrics) if job.metrics else None,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        })
    return results
