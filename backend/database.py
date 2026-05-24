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
    Float,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
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

    # 多格式支持字段
    format = Column(String(20), default="yolo_pt")  # 当前注册格式
    available_formats = Column(Text, default="[]")  # JSON 数组，可用格式列表
    device_preference = Column(String(20), default="auto")  # 设备偏好: auto/cpu/cuda
    precision = Column(String(10), default="fp32")  # 推理精度: fp32/fp16/int8
    input_shape = Column(String(50), nullable=True)  # 输入尺寸，如 "640x640"

    atlas = relationship("Atlas", back_populates=None)
    inference_jobs = relationship("InferenceJob", back_populates="model", cascade="all, delete-orphan")
    files = relationship("ModelFile", back_populates="model", cascade="all, delete-orphan")


class ModelFile(Base):
    """模型文件模型 - 关联模型与其多种格式的文件。"""
    __tablename__ = "model_file"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)  # yolo_pt/onnx/openvino/tensorrt/pytorch
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    precision = Column(String(10), default="fp32")  # fp32/fp16/int8
    is_default = Column(Boolean, default=False)  # 推理默认格式
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("Model", back_populates="files")


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
    cron_expression = Column(String(100), nullable=True)  # 定时触发 Cron 表达式
    thumbnail = Column(Text, nullable=True)  # Base64 缩略图快照
    webhook_api_key = Column(String(64), nullable=True)  # Webhook API Key 认证
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = relationship("ExecutionHistory", back_populates="graph", cascade="all, delete-orphan")


class ExecutionHistory(Base):
    """执行历史模型 - 记录每次规则执行的详情。"""
    __tablename__ = "execution_history"
    __table_args__ = (
        Index('ix_execution_history_graph_id', 'graph_id'),
        Index('ix_execution_history_status', 'status'),
    )

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
    __table_args__ = (
        Index('ix_node_execution_log_execution_id', 'execution_id'),
    )

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
    duration_ms = Column(Integer, nullable=True)  # 执行耗时（毫秒）
    metrics_json = Column(Text, nullable=True)  # 指标数据（如检测数、数据量等）

    execution = relationship("ExecutionHistory", back_populates="node_logs")


class InferenceJob(Base):
    """推理记录模型 - 记录最近检测任务的元数据。"""
    __tablename__ = "inference_job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), nullable=False, unique=True)
    model_id = Column(Integer, ForeignKey("model.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)                   # "image" / "video"
    conf_threshold = Column(Float, default=0.25)
    device = Column(String(20), default="cpu")                        # 推理设备: auto/cpu/cuda
    precision = Column(String(10), default="fp32")                    # 推理精度: fp32/fp16
    used_format = Column(String(20), default="yolo_pt")               # 实际使用的模型格式
    status = Column(String(20), default="completed")                 # completed / processing / failed
    total_frames = Column(Integer, nullable=True)
    total_detections = Column(Integer, default=0)
    thumbnail = Column(Text, nullable=True)                           # 缩略图 Base64 JPEG
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    model = relationship("Model", back_populates="inference_jobs")


# 数据库引擎和会话
import os

# 统一数据目录（所有持久化数据都放项目根目录下的 data/）
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
    """初始化数据库，创建所有表并执行迁移。"""
    Base.metadata.create_all(bind=engine)

    # 迁移：为已有数据库添加新列（2026-05 添加 device/precision/used_format）
    _migrate_add_column("inference_job", "device", "VARCHAR(20) DEFAULT 'cpu'")
    _migrate_add_column("inference_job", "precision", "VARCHAR(10) DEFAULT 'fp32'")
    _migrate_add_column("inference_job", "used_format", "VARCHAR(20) DEFAULT 'yolo_pt'")

    # 迁移：rule_graph 表新增字段
    _migrate_add_column("rule_graph", "cron_expression", "VARCHAR(100)")
    _migrate_add_column("rule_graph", "thumbnail", "TEXT")
    _migrate_add_column("rule_graph", "webhook_api_key", "VARCHAR(64)")

    # 迁移：model 表新增字段（多格式支持）
    _migrate_add_column("model", "format", "VARCHAR(20) DEFAULT 'yolo_pt'")
    _migrate_add_column("model", "available_formats", "TEXT DEFAULT '[]'")
    _migrate_add_column("model", "device_preference", "VARCHAR(20) DEFAULT 'auto'")
    _migrate_add_column("model", "precision", "VARCHAR(10) DEFAULT 'fp32'")
    _migrate_add_column("model", "input_shape", "VARCHAR(50)")


def _migrate_add_column(table: str, column: str, column_def: str):
    """安全地向已有表添加列（SQLite 不支持 IF NOT EXISTS，忽略重复列错误）。"""
    import sqlite3
    try:
        db_path = engine.url.database
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
            conn.commit()
            conn.close()
    except Exception:
        pass  # 列已存在则忽略
