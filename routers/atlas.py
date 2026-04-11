# -*- coding: utf-8 -*-
"""图集管理路由 - Atlas CRUD 操作。

提供图集的创建、读取、更新、删除功能。
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db, Atlas, Image
from schemas import AtlasCreate, AtlasUpdate, AtlasResponse

router = APIRouter()


@router.get("", response_model=List[AtlasResponse])
async def list_atlases(db: Session = Depends(get_db)):
    """获取图集列表。"""
    return db.query(Atlas).order_by(Atlas.created_at.desc()).all()


@router.post("", response_model=AtlasResponse, status_code=201)
async def create_atlas(atlas_data: AtlasCreate, db: Session = Depends(get_db)):
    """创建新图集。"""
    atlas = Atlas(name=atlas_data.name, description=atlas_data.description)
    db.add(atlas)
    db.commit()
    db.refresh(atlas)
    return atlas


@router.get("/{atlas_id}", response_model=AtlasResponse)
async def get_atlas(atlas_id: int, db: Session = Depends(get_db)):
    """获取图集详情。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")
    return atlas


@router.put("/{atlas_id}", response_model=AtlasResponse)
async def update_atlas(
    atlas_id: int,
    atlas_data: AtlasUpdate,
    db: Session = Depends(get_db)
):
    """更新图集。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    if atlas_data.name is not None:
        atlas.name = atlas_data.name
    if atlas_data.description is not None:
        atlas.description = atlas_data.description

    db.commit()
    db.refresh(atlas)
    return atlas


@router.delete("/{atlas_id}", status_code=204)
async def delete_atlas(atlas_id: int, db: Session = Depends(get_db)):
    """删除图集。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    db.delete(atlas)
    db.commit()
    return None


@router.get("/{atlas_id}/images")
async def list_atlas_images(atlas_id: int, db: Session = Depends(get_db)):
    """获取图集图片列表。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    images = db.query(Image).filter(Image.atlas_id == atlas_id).all()
    return images


@router.post("/{atlas_id}/images", status_code=201)
async def upload_images(
    atlas_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """上传图片到图集（占位，后续实现文件存储）。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # TODO: 实现文件存储逻辑
    return {"message": f"收到 {len(files)} 个文件，待实现存储逻辑"}
