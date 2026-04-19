# -*- coding: utf-8 -*-
"""图集管理路由 - Atlas CRUD 操作。

提供图集的创建、读取、更新、删除功能。
"""
import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from PIL import Image as PILImage

from database import get_db, Atlas, Image
from schemas import AtlasCreate, AtlasUpdate, AtlasResponse

router = APIRouter()

# 图片存储根目录
IMAGE_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "images")


def get_image_storage_path(atlas_id: int, filename: str) -> tuple[str, str]:
    """获取图片存储路径。

    Returns:
        (directory, file_path) - 目录路径和完整文件路径
    """
    atlas_dir = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id))
    file_path = os.path.join(atlas_dir, filename)
    return atlas_dir, file_path


@router.get("", response_model=List[AtlasResponse])
async def list_atlases(db: Session = Depends(get_db)):
    """获取图集列表。"""
    return db.query(Atlas).order_by(Atlas.created_at.desc()).all()


@router.post("", response_model=AtlasResponse, status_code=201)
async def create_atlas(atlas_data: AtlasCreate, db: Session = Depends(get_db)):
    """创建新图集。"""
    # 检查名称是否已存在
    existing = db.query(Atlas).filter(Atlas.name == atlas_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"图集名称 '{atlas_data.name}' 已存在")

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
async def list_atlas_images(
    atlas_id: int,
    directory: str = None,
    db: Session = Depends(get_db)
):
    """获取图集图片列表，支持按目录筛选。

    Args:
        atlas_id: 图集 ID
        directory: 可选，按目录名筛选
    """
    import sys
    print(f"[DEBUG] list_atlas_images called with atlas_id={atlas_id}, directory={directory}", flush=True)
    print(f"[DEBUG] directory type: {type(directory)}, repr: {repr(directory)}", flush=True)
    if directory:
        print(f"[DEBUG] directory encoding: {directory.encode('utf-8')}", flush=True)

    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    query = db.query(Image).filter(Image.atlas_id == atlas_id)

    # Debug: check what directories are stored
    all_images = query.all()
    print(f"[DEBUG] Total images for atlas {atlas_id}: {len(all_images)}", flush=True)

    if directory is not None:
        print(f"[DEBUG] Filtering by directory: '{directory}'", flush=True)
        # Try direct string comparison
        matching = [img for img in all_images if img.directory == directory]
        print(f"[DEBUG] Direct Python comparison matches: {len(matching)}", flush=True)

        query = query.filter(Image.directory == directory)

    images = query.all()
    print(f"[DEBUG] Final query result: {len(images)} images", flush=True)
    return images


@router.get("/{atlas_id}/directories")
async def list_atlas_directories(atlas_id: int, db: Session = Depends(get_db)):
    """获取图集中的所有目录分组（包括空目录）。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 获取已有图片的目录
    images = db.query(Image.directory).filter(
        Image.atlas_id == atlas_id,
        Image.directory.isnot(None)
    ).distinct().all()

    directories = [img.directory for img in images if img.directory]

    # 获取物理目录
    atlas_dir = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id))
    if os.path.exists(atlas_dir):
        for item in os.listdir(atlas_dir):
            item_path = os.path.join(atlas_dir, item)
            if os.path.isdir(item_path) and item not in directories:
                directories.append(item)

    return sorted(set(directories))


@router.post("/{atlas_id}/directories")
async def create_atlas_directory(
    atlas_id: int,
    directory: str,
    db: Session = Depends(get_db)
):
    """创建目录（不依赖图片上传）。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 创建物理目录
    dir_path = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id), directory)
    os.makedirs(dir_path, exist_ok=True)

    return {"message": f"目录 '{directory}' 已创建", "directory": directory}


@router.post("/{atlas_id}/images", status_code=201)
async def upload_images(
    atlas_id: int,
    files: List[UploadFile] = File(...),
    directory: str = None,
    db: Session = Depends(get_db)
):
    """上传图片到图集。

    Args:
        atlas_id: 图集 ID
        files: 图片文件列表
        directory: 可选，目录分组名称
    """
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 确定目标目录
    if directory:
        # 使用用户指定的目录名
        atlas_dir = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id), directory)
    else:
        atlas_dir = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id))
    os.makedirs(atlas_dir, exist_ok=True)

    uploaded_images = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        # 保持原始文件名（可加唯一前缀避免冲突）
        filename = file.filename
        file_path = os.path.join(atlas_dir, filename)

        # 如果文件已存在，添加时间戳前缀
        if os.path.exists(file_path):
            import time
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            file_path = os.path.join(atlas_dir, filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 提取图片元数据
        img_width, img_height = None, None
        try:
            with PILImage.open(file_path) as img:
                img_width, img_height = img.size
        except Exception:
            pass

        # 创建数据库记录
        image = Image(
            atlas_id=atlas_id,
            file_path=file_path,
            directory=directory if directory else None,
            width=img_width,
            height=img_height,
        )
        db.add(image)
        uploaded_images.append(filename)

    db.commit()
    return {"message": f"成功上传 {len(uploaded_images)} 个文件", "files": uploaded_images}
