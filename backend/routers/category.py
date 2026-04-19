# -*- coding: utf-8 -*-
"""类别管理路由 - 支持树形目录结构。

提供类别和目录的 CRUD 操作。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Category
from schemas import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
async def list_categories(db: Session = Depends(get_db)):
    """获取所有类别和目录（扁平列表）。"""
    return db.query(Category).order_by(Category.parent_id.nullslast(), Category.name).all()


@router.get("/tree", response_model=List[dict])
async def get_category_tree(db: Session = Depends(get_db)):
    """获取目录树结构。"""
    all_items = db.query(Category).order_by(Category.parent_id.nullslast(), Category.name).all()

    def build_tree(items: List[Category], parent_id: Optional[int] = None) -> List[dict]:
        tree = []
        for item in items:
            if item.parent_id == parent_id:
                node = {
                    "id": item.id,
                    "name": item.name,
                    "is_directory": item.is_directory,
                    "color": item.color,
                    "parent_id": item.parent_id,
                    "children": build_tree(items, item.id) if item.is_directory else []
                }
                tree.append(node)
        return tree

    return build_tree(all_items)


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """创建新类别或目录。"""
    # 标签必须有颜色，目录使用默认颜色
    color = data.color if not data.is_directory else "#888888"

    # 验证 parent_id 存在且是目录
    if data.parent_id is not None:
        parent = db.query(Category).filter(Category.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="父节点不存在")
        if not parent.is_directory:
            raise HTTPException(status_code=400, detail="父节点必须是目录")

    cat = Category(
        name=data.name,
        color=color,
        is_directory=data.is_directory,
        parent_id=data.parent_id
    )
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
    """更新类别或目录。"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    if data.name is not None:
        cat.name = data.name
    if data.color is not None:
        cat.color = data.color
    if data.is_directory is not None:
        cat.is_directory = data.is_directory
    if data.parent_id is not None:
        # 验证新父节点存在且是目录
        if data.parent_id == cat.id:
            raise HTTPException(status_code=400, detail="不能将自己设为父节点")
        parent = db.query(Category).filter(Category.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="父节点不存在")
        if not parent.is_directory:
            raise HTTPException(status_code=400, detail="父节点必须是目录")
        cat.parent_id = data.parent_id

    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除类别或目录（同时删除所有子节点）。"""
    def delete_recursive(cat_id: int):
        # 先递归删除子节点
        children = db.query(Category).filter(Category.parent_id == cat_id).all()
        for child in children:
            delete_recursive(child.id)
        # 再删除自己
        cat = db.query(Category).filter(Category.id == cat_id).first()
        if cat:
            db.delete(cat)

    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    delete_recursive(category_id)
    db.commit()
    return None
