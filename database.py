# -*- coding: utf-8 -*-
"""数据库模型 - SQLAlchemy ORM 定义。

使用 SQLite 数据库，单用户场景足够。
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class Atlas(Base):
    """图集模型 - 管理训练图片分组。"""
    __tablename__ = "atlas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = relationship("Image", back_populates="atlas", cascade="all, delete-orphan")


class Image(Base):
    """图片模型 - 存储图片元数据。"""
    __tablename__ = "image"

    id = Column(Integer, primary_key=True, autoincrement=True)
    atlas_id = Column(Integer, ForeignKey("atlas.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    directory = Column(String(255), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    annotated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    atlas = relationship("Atlas", back_populates="images")
    annotations = relationship("Annotation", back_populates="image", cascade="all, delete-orphan")


class Category(Base):
    """标注类别模型。"""
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), default="#FF0000")

    annotations = relationship("Annotation", back_populates="category")


class Annotation(Base):
    """标注模型 - COCO Bounding Box 格式。"""
    __tablename__ = "annotation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("image.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id", ondelete="CASCADE"), nullable=False)
    bbox = Column(Text, nullable=False)  # JSON: [x, y, w, h]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    image = relationship("Image", back_populates="annotations")
    category = relationship("Category", back_populates="annotations")


class Model(Base):
    """模型元数据模型。"""
    __tablename__ = "model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    file_path = Column(String(500), nullable=True)
    atlas_id = Column(Integer, ForeignKey("atlas.id", ondelete="SET NULL"), nullable=True)
    metrics = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    is_best = Column(Boolean, default=False)

    atlas = relationship("Atlas", back_populates=None)


class TrainingJob(Base):
    """训练任务模型。"""
    __tablename__ = "training_job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model.id", ondelete="CASCADE"), nullable=False)
    atlas_id = Column(Integer, ForeignKey("atlas.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    config = Column(Text, nullable=True)  # JSON
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=True)
    metrics = Column(Text, nullable=True)  # JSON
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    model = relationship("Model")
    atlas = relationship("Atlas")


# 数据库引擎和会话
DATABASE_URL = "sqlite:///./visiongame.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """获取数据库会话的依赖函数。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表。"""
    Base.metadata.create_all(bind=engine)
