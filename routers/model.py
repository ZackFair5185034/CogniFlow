# -*- coding: utf-8 -*-
"""模型管理路由。

提供模型的元数据管理和最佳模型设置。
"""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Model
from schemas import ModelCreate, ModelUpdate, ModelResponse

router = APIRouter()


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
    model = Model(
        name=data.name,
        version=data.version,
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
        file_path=m.file_path,
        atlas_id=m.atlas_id,
        metrics=json.loads(m.metrics) if m.metrics else None,
        is_best=m.is_best,
        created_at=m.created_at,
    )
