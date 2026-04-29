# -*- coding: utf-8 -*-
"""图片管理路由。

提供图片的读取、删除和目录修改功能。
"""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, Image

router = APIRouter()


class BatchUpdateDirectoryRequest(BaseModel):
    """批量修改目录请求体"""
    image_ids: list[int]
    directory: str


class BatchDeleteRequest(BaseModel):
    """批量删除请求体"""
    image_ids: list[int]


@router.get("/", response_model=list)
async def list_images(db: Session = Depends(get_db)):
    """获取所有图片列表（用于统计）。"""
    images = db.query(Image).all()
    # 返回图片ID列表（用于统计）
    return [{"id": img.id, "atlas_id": img.atlas_id} for img in images]


@router.get("/{image_id}")
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """获取图片详情。"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    return image


@router.get("/{image_id}/file")
async def get_image_file(image_id: int, db: Session = Depends(get_db)):
    """获取图片文件。"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    if not image.file_path or not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")

    return FileResponse(image.file_path)


@router.put("/{image_id}/directory")
async def update_image_directory(image_id: int, directory: str, db: Session = Depends(get_db)):
    """修改图片所属目录。

    Args:
        image_id: 图片 ID
        directory: 目标目录名，传空字符串表示移回根目录
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 空字符串视为移回根目录
    new_directory = directory if directory else None
    old_directory = image.directory

    image.directory = new_directory
    db.commit()

    print(f"[图片] 修改目录: image_id={image_id}, {old_directory} -> {new_directory}")

    return {
        "message": "目录已更新",
        "image_id": image_id,
        "directory": new_directory,
    }


@router.delete("/{image_id}", status_code=204)
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    """删除图片。"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 删除物理文件
    if image.file_path and os.path.exists(image.file_path):
        try:
            os.remove(image.file_path)
        except Exception:
            pass

    # 删除数据库记录
    db.delete(image)
    db.commit()
    return None


@router.post("/batch-update-directory")
async def batch_update_directory(
    req: BatchUpdateDirectoryRequest,
    db: Session = Depends(get_db)
):
    """批量修改图片目录。

    Args:
        req: 请求体，包含 image_ids 和 directory
    """
    if not req.image_ids:
        raise HTTPException(status_code=400, detail="图片ID列表不能为空")

    # 空字符串视为移回根目录
    new_directory = req.directory if req.directory else None

    # 查询所有图片
    images = db.query(Image).filter(Image.id.in_(req.image_ids)).all()
    if len(images) != len(req.image_ids):
        found_ids = {img.id for img in images}
        missing_ids = set(req.image_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"部分图片不存在，缺失ID: {missing_ids}")

    # 批量更新
    for image in images:
        old_directory = image.directory
        image.directory = new_directory
        print(f"[图片] 批量修改目录: image_id={image.id}, {old_directory} -> {new_directory}")

    db.commit()

    return {
        "message": f"成功修改 {len(images)} 张图片的目录",
        "image_ids": req.image_ids,
        "directory": new_directory,
    }


@router.post("/batch-delete")
async def batch_delete_images(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """批量删除图片。

    Args:
        req: 请求体，包含 image_ids
    """
    if not req.image_ids:
        raise HTTPException(status_code=400, detail="图片ID列表不能为空")

    # 查询所有图片
    images = db.query(Image).filter(Image.id.in_(req.image_ids)).all()
    if len(images) != len(req.image_ids):
        found_ids = {img.id for img in images}
        missing_ids = set(req.image_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"部分图片不存在，缺失ID: {missing_ids}")

    deleted_count = 0
    for image in images:
        # 删除物理文件
        if image.file_path and os.path.exists(image.file_path):
            try:
                os.remove(image.file_path)
                deleted_count += 1
            except Exception:
                pass
        # 删除数据库记录
        db.delete(image)

    db.commit()

    return {
        "message": f"成功删除 {len(images)} 张图片",
        "deleted_count": len(images),
        "deleted_file_count": deleted_count,
    }
