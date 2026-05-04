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
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, backref
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class Atlas(Base):
    """图集模型 - 管理训练图片分组。"""
    __tablename__ = "atlas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
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
    """标注类别模型 - 支持树形目录结构。

    - is_directory=True: 目录容器，可嵌套
    - is_directory=False: 实际标签，属于某个目录
    """
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#FF0000")
    is_directory = Column(Boolean, default=False)  # True=目录, False=标签
    parent_id = Column(Integer, ForeignKey("category.id"), nullable=True)  # 父节点，支持嵌套

    # 关系
    annotations = relationship("Annotation", back_populates="category")
    children = relationship("Category", backref=backref("parent", remote_side=[id]), cascade="all")


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
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_model_name_version'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=True)
    pretrained_model = Column(String(50), nullable=True, default='yolov8n.pt')  # 预训练模型
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


class RuleGraph(Base):
    """规则图模型 - 存储可视化规则配置。"""
    __tablename__ = "rule_graph"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    nodes_json = Column(Text, nullable=False)  # JSON 存储节点列表
    edges_json = Column(Text, nullable=False)  # JSON 存储连接列表
    variables_json = Column(Text, nullable=True)  # JSON 存储变量定义
    version = Column(String(50), default="1.0.0")
    is_active = Column(Boolean, default=False)
    thumbnail = Column(Text, nullable=True)  # Base64 缩略图快照
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = relationship("ExecutionHistory", back_populates="graph", cascade="all, delete-orphan")


class ExecutionHistory(Base):
    """执行历史模型 - 记录每次规则执行的详情。"""
    __tablename__ = "execution_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    graph_id = Column(Integer, ForeignKey("rule_graph.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)  # running/completed/failed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    trigger_type = Column(String(50), nullable=True)  # yolo/timer/manual/http
    trigger_data_json = Column(Text, nullable=True)  # 触发时的数据
    result_json = Column(Text, nullable=True)  # 执行结果
    logs_json = Column(Text, nullable=True)  # 执行日志

    graph = relationship("RuleGraph", back_populates="executions")
    node_logs = relationship("NodeExecutionLog", back_populates="execution", cascade="all, delete-orphan")


class NodeExecutionLog(Base):
    """节点执行记录模型 - 记录每个节点的执行详情。"""
    __tablename__ = "node_execution_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(Integer, ForeignKey("execution_history.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(255), nullable=False)
    node_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # running/completed/failed
    input_data_json = Column(Text, nullable=True)
    output_data_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    execution = relationship("ExecutionHistory", back_populates="node_logs")


# 数据库引擎和会话
import os

_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)
os.makedirs(os.path.join(DATA_DIR, "database"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads", "images"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads", "videos"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads", "models"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "inference_output"), exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'database', 'engine.db')}"

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
