# -*- coding: utf-8 -*-
"""图片管理路由。

提供图片的读取和删除功能。
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Image

router = APIRouter()


@router.get("/{image_id}")
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """获取图片详情。"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    return image


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
