# -*- coding: utf-8 -*-
"""类别管理路由。

提供类别的 CRUD 操作。
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Category
from schemas import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
async def list_categories(db: Session = Depends(get_db)):
    """获取类别列表。"""
    return db.query(Category).all()


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """创建新类别。"""
    cat = Category(name=data.name, color=data.color)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """更新类别。"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    if data.name is not None:
        cat.name = data.name
    if data.color is not None:
        cat.color = data.color

    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除类别。"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    db.delete(cat)
    db.commit()
    return None
