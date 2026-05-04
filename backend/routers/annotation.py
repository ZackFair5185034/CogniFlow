# -*- coding: utf-8 -*-
"""标注管理路由。

提供标注的 CRUD 操作。
"""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Annotation, Image
from backend.schemas import AnnotationCreate, AnnotationUpdate, AnnotationResponse

router = APIRouter()


@router.get("/image/{image_id}", response_model=List[AnnotationResponse])
async def get_image_annotations(image_id: int, db: Session = Depends(get_db)):
    """获取图片的所有标注。"""
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    annotations = db.query(Annotation).filter(Annotation.image_id == image_id).all()
    results = []
    for ann in annotations:
        results.append(AnnotationResponse(
            id=ann.id,
            image_id=ann.image_id,
            category_id=ann.category_id,
            bbox=json.loads(ann.bbox),
            created_at=ann.created_at,
            updated_at=ann.updated_at,
        ))
    return results


@router.post("", response_model=AnnotationResponse, status_code=201)
async def create_annotation(data: AnnotationCreate, db: Session = Depends(get_db)):
    """创建新标注。"""
    image = db.query(Image).filter(Image.id == data.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    annotation = Annotation(
        image_id=data.image_id,
        category_id=data.category_id,
        bbox=json.dumps(data.bbox),
    )
    db.add(annotation)

    # 标记图片已标注
    image.annotated = True

    db.commit()
    db.refresh(annotation)
    return AnnotationResponse(
        id=annotation.id,
        image_id=annotation.image_id,
        category_id=annotation.category_id,
        bbox=json.loads(annotation.bbox),
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: int,
    data: AnnotationUpdate,
    db: Session = Depends(get_db)
):
    """更新标注。"""
    ann = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="标注不存在")

    if data.category_id is not None:
        ann.category_id = data.category_id
    if data.bbox is not None:
        ann.bbox = json.dumps(data.bbox)

    db.commit()
    db.refresh(ann)
    return AnnotationResponse(
        id=ann.id,
        image_id=ann.image_id,
        category_id=ann.category_id,
        bbox=json.loads(ann.bbox),
        created_at=ann.created_at,
        updated_at=ann.updated_at,
    )


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    """删除标注。"""
    ann = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="标注不存在")

    image_id = ann.image_id
    db.delete(ann)

    # 检查图片是否还有其他标注，没有则取消 annotated 标记
    remaining = db.query(Annotation).filter(Annotation.image_id == image_id).count()
    if remaining == 0:
        image = db.query(Image).filter(Image.id == image_id).first()
        if image:
            image.annotated = False

    db.commit()
    return None
