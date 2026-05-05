# -*- coding: utf-8 -*-
"""图集管理路由 - Atlas CRUD 操作。

提供图集的创建、读取、更新、删除功能。
"""
import io
import os
import shutil
import threading
import time
import zipfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image as PILImage

from backend.database import get_db, Atlas, Image
from backend.schemas import AtlasCreate, AtlasUpdate, AtlasResponse
from backend.utils.frame_extract_manager import frame_extract_manager

router = APIRouter()

# 统一数据目录（与 app.py 保持一致）
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
_DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)

# 图片存储根目录
IMAGE_STORAGE_DIR = os.path.join(_DATA_DIR, "uploads", "images")
# 视频存储根目录
VIDEO_STORAGE_DIR = os.path.join(_DATA_DIR, "uploads", "videos")


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
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """获取图集图片列表，支持按目录筛选和分页。

    Args:
        atlas_id: 图集 ID
        directory: 可选，按目录名筛选
        page: 页码，从 1 开始
        page_size: 每页数量，默认 50
    """
    import sys
    print(f"[DEBUG] list_atlas_images called with atlas_id={atlas_id}, directory={directory}, page={page}, page_size={page_size}", flush=True)

    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    query = db.query(Image).filter(Image.atlas_id == atlas_id)

    if directory is not None:
        query = query.filter(Image.directory == directory)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    offset = (page - 1) * page_size
    images = query.order_by(Image.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": images,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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


@router.delete("/{atlas_id}/directories", status_code=204)
async def delete_atlas_directory(
    atlas_id: int,
    directory: str,
    db: Session = Depends(get_db)
):
    """删除目录及其包含的所有图片。

    删除指定目录下的所有图片（物理文件和数据库记录），并移除物理目录。
    """
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 查询该目录下的所有图片
    images = db.query(Image).filter(
        Image.atlas_id == atlas_id,
        Image.directory == directory
    ).all()

    # 删除所有图片（物理文件 + 数据库记录，注解通过 cascade 自动删除）
    for image in images:
        if image.file_path and os.path.exists(image.file_path):
            try:
                os.remove(image.file_path)
            except Exception:
                pass
        db.delete(image)

    # 删除物理目录
    dir_path = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id), directory)
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
        except Exception:
            pass

    db.commit()

    return None


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


# ===== 视频导入 =====

@router.post("/{atlas_id}/video/upload", status_code=201)
async def upload_video(
    atlas_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传视频文件并返回元数据。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    # 验证视频格式
    allowed_exts = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"}
    ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式，支持：{', '.join(allowed_exts)}")

    # 保存视频到 uploads/videos/{atlas_id}/
    atlas_video_dir = os.path.join(VIDEO_STORAGE_DIR, str(atlas_id))
    os.makedirs(atlas_video_dir, exist_ok=True)

    # 避免文件名冲突
    filename = file.filename or f"video_{int(time.time())}.mp4"
    if os.path.exists(os.path.join(atlas_video_dir, filename)):
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"

    video_path = os.path.join(atlas_video_dir, filename)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 获取视频元数据
    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = round(total_frames / fps) if fps and fps > 0 else 0
    cap.release()

    return {
        "video_path": video_path,
        "metadata": {
            "fps": round(fps) if fps else 24,
            "total_frames": total_frames,
            "duration": duration
        }
    }


@router.post("/{atlas_id}/video/extract-frames", status_code=201)
async def extract_video_frames(
    atlas_id: int,
    video_path: str = Query(...),
    extract_count: int = Query(default=None),
    directory: str = Query(default="video"),
    db: Session = Depends(get_db)
):
    """从视频中均匀采样提取帧，存入图集。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="视频文件不存在")

    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    # 确定提取数量：默认 total_frames（即每帧都提取）
    if extract_count is None or extract_count <= 0:
        extract_count = total_frames
    extract_count = min(extract_count, total_frames) if total_frames > 0 else 1

    # 间隔计算
    interval = max(1, total_frames / extract_count) if total_frames > 0 else 1

    # 创建帧存储目录
    frames_dir = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id), directory)
    os.makedirs(frames_dir, exist_ok=True)

    # 重新打开视频读帧（顺序读取，避免 codec seek 不准导致乱序）
    cap = cv2.VideoCapture(video_path)
    extracted_images = []
    extracted_idx = 0
    video_frame_idx = 0

    while extracted_idx < extract_count:
        ret, frame = cap.read()
        if not ret:
            break

        # 仅在达到目标帧位置时保存
        if video_frame_idx >= int(extracted_idx * interval):
            output_filename = f"frame_{extracted_idx:04d}.jpg"
            output_path = os.path.join(frames_dir, output_filename)
            cv2.imwrite(output_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

            img_height, img_width = frame.shape[:2]

            image = Image(
                atlas_id=atlas_id,
                file_path=output_path,
                directory=directory,
                width=img_width,
                height=img_height,
            )
            db.add(image)
            extracted_images.append(image)
            extracted_idx += 1

        video_frame_idx += 1

    cap.release()
    db.commit()

    return {
        "success": True,
        "extracted_count": len(extracted_images),
        "images": [
            {"id": img.id, "file_path": img.file_path, "frame_index": idx}
            for idx, img in enumerate(extracted_images)
        ]
    }


# ===== 异步帧提取 =====

def _extract_frames_background(
    job_id: str,
    atlas_id: int,
    video_path: str,
    extract_count: int,
    total_frames: int,
):
    """后台线程执行帧提取（内部函数，供 threadPoolExecutor 调用）。"""
    import cv2
    from backend.database import SessionLocal

    db = SessionLocal()
    frames_dir = os.path.join(IMAGE_STORAGE_DIR, str(atlas_id), f"video_{job_id}")
    os.makedirs(frames_dir, exist_ok=True)

    interval = max(1, total_frames / extract_count) if total_frames > 0 else 1

    cap = cv2.VideoCapture(video_path)
    extracted_idx = 0
    video_frame_idx = 0
    frame_paths = []  # 收集所有帧路径，最后批量入库

    try:
        while extracted_idx < extract_count:
            # 检查任务是否被停止
            job = frame_extract_manager.get_job(job_id)
            if job and job["status"] == "stopped":
                break

            ret, frame = cap.read()
            if not ret:
                break

            # 仅在达到目标帧位置时保存
            if video_frame_idx >= int(extracted_idx * interval):
                output_filename = f"frame_{extracted_idx:04d}.jpg"
                output_path = os.path.join(frames_dir, output_filename)
                cv2.imwrite(output_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

                img_height, img_width = frame.shape[:2]
                frame_paths.append((output_path, img_width, img_height))

                extracted_idx += 1

                # 每提取 5 帧更新一次进度
                if extracted_idx % 5 == 0 or extracted_idx == extract_count:
                    frame_extract_manager.update_progress(job_id, video_frame_idx, extracted_idx)

            video_frame_idx += 1

        # 批量创建 Image 记录
        for idx, (file_path, img_width, img_height) in enumerate(frame_paths):
            image = Image(
                atlas_id=atlas_id,
                file_path=file_path,
                directory=f"video_{job_id}",
                width=img_width,
                height=img_height,
            )
            db.add(image)
        db.commit()

        frame_extract_manager.complete_job(job_id)
    except Exception as e:
        frame_extract_manager.fail_job(job_id, str(e))
        db.rollback()
    finally:
        cap.release()
        db.close()


@router.post("/{atlas_id}/video/extract-frames/async", status_code=201)
async def extract_video_frames_async(
    atlas_id: int,
    video_path: str = Query(...),
    extract_count: int = Query(default=None),
    db: Session = Depends(get_db)
):
    """异步提取视频帧，立即返回 job_id。

    前端通过 GET /{{atlas_id}}/video/extract-frames/{{job_id}}/status 轮询进度。
    """
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="视频文件不存在")

    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if extract_count is None or extract_count <= 0:
        extract_count = total_frames
    extract_count = min(extract_count, total_frames) if total_frames > 0 else 1

    job_id = frame_extract_manager.submit_job(
        atlas_id=atlas_id,
        video_path=video_path,
        extract_count=extract_count,
        total_frames=total_frames,
    )

    # 启动后台线程执行提取
    thread = threading.Thread(
        target=_extract_frames_background,
        args=(job_id, atlas_id, video_path, extract_count, total_frames),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "message": "任务已提交"}


@router.get("/{atlas_id}/video/extract-frames/{job_id}/status")
async def get_extract_job_status(
    atlas_id: int,
    job_id: str,
    db: Session = Depends(get_db)
):
    """轮询帧提取任务状态。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    job = frame_extract_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "status": job["status"],
        "progress": job["progress"],
        "extracted_count": job["extracted_count"],
        "total_frames": job["total_frames"],
        "directory": job["directory"],
        "error": job["error"],
    }


@router.delete("/{atlas_id}/video/extract-frames/{job_id}", status_code=204)
async def cancel_extract_job(
    atlas_id: int,
    job_id: str,
    db: Session = Depends(get_db)
):
    """取消进行中的帧提取任务。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    job = frame_extract_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    frame_extract_manager.set_status(job_id, "stopped")
    return None


@router.get("/{atlas_id}/images/download")
async def batch_download_images(
    atlas_id: int,
    image_ids: str = Query(..., description="图片ID列表，逗号分隔"),
    db: Session = Depends(get_db)
):
    """打包下载选中的图片为 ZIP 文件。"""
    atlas = db.query(Atlas).filter(Atlas.id == atlas_id).first()
    if not atlas:
        raise HTTPException(status_code=404, detail="图集不存在")

    image_id_list = [int(x.strip()) for x in image_ids.split(",") if x.strip().isdigit()]
    if not image_id_list:
        raise HTTPException(status_code=400, detail="没有指定要下载的图片")

    images = db.query(Image).filter(Image.id.in_(image_id_list)).all()
    if not images:
        raise HTTPException(status_code=404, detail="未找到指定的图片")

    # 创建内存 ZIP 文件
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for img in images:
            if img.file_path and os.path.exists(img.file_path):
                arcname = os.path.basename(img.file_path)
                zipf.write(img.file_path, arcname)

    zip_buffer.seek(0)
    # 使用 ASCII 文件名避免 Content-Disposition 编码问题
    filename = f"atlas_{atlas_id}_images.zip"

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
