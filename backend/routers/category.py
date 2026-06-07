# -*- coding: utf-8 -*-
"""类别管理路由 - 支持树形目录结构。

提供类别和目录的 CRUD 操作。
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Category
from backend.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryImportPayload, CategoryImportResult

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


@router.get("/export")
async def export_categories(db: Session = Depends(get_db)):
    """导出所有类别为树形 JSON 结构。"""
    all_items = db.query(Category).order_by(Category.parent_id.nullslast(), Category.name).all()

    def build_export(items: List[Category], parent_id: Optional[int] = None) -> list:
        nodes = []
        for item in items:
            if item.parent_id == parent_id:
                node = {
                    "name": item.name,
                    "color": item.color,
                    "is_directory": item.is_directory,
                    "children": build_export(items, item.id) if item.is_directory else [],
                }
                nodes.append(node)
        return nodes

    return {
        "version": 1,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "categories": build_export(all_items),
    }


@router.post("/import", response_model=CategoryImportResult)
async def import_categories(payload: CategoryImportPayload, db: Session = Depends(get_db)):
    """从 JSON 树结构导入类别。

    按名称 + 父级去重，已存在则跳过（幂等）。
    """
    result = CategoryImportResult()

    def import_recursive(nodes: list, parent_id: Optional[int] = None):
        for node in nodes:
            name = node.name.strip()
            if not name:
                result.errors.append("跳过空名称的条目")
                continue

            existing = (
                db.query(Category)
                .filter(Category.name == name, Category.parent_id == parent_id)
                .first()
            )

            if existing:
                needs_update = (
                    existing.is_directory != node.is_directory
                    or existing.color != node.color
                )
                if needs_update:
                    existing.is_directory = node.is_directory
                    existing.color = node.color
                    db.flush()
                result.skipped += 1
                if node.is_directory:
                    import_recursive(node.children, existing.id)
            else:
                cat = Category(
                    name=name,
                    color=node.color if not node.is_directory else "#888888",
                    is_directory=node.is_directory,
                    parent_id=parent_id,
                )
                db.add(cat)
                db.flush()
                result.created += 1
                if node.is_directory:
                    import_recursive(node.children, cat.id)

    try:
        import_recursive(payload.categories)
        db.commit()
    except Exception as e:
        db.rollback()
        result.errors.append(str(e))

    return result
