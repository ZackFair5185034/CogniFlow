# -*- coding: utf-8 -*-
"""CogniFlow WebUI - FastAPI 主入口。

提供：
- REST API
- WebSocket 实时通信
- Vue3 前端静态文件托管
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from database import init_db
from routers import atlas, image, annotation, category, model, training, launch, websocket, inference, rule_engine, ws_stream

# 统一数据目录（所有持久化数据都放这里）
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

# 上传文件存储目录
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
MODEL_DIR = os.path.join(UPLOAD_DIR, "models")

# 推理输出目录
INFERENCE_OUTPUT_DIR = os.path.join(DATA_DIR, "inference_output")

# 日志目录
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# YOLO 训练输出目录（YOLO 默认 runs/detect/，我们统一放这里）
YOLO_RUNS_DIR = os.path.join(DATA_DIR, "runs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 确保所有数据目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, "images"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(INFERENCE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(YOLO_RUNS_DIR, exist_ok=True)

    init_db()
    # 设置事件循环给流式推理 WebSocket 管理器
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        ws_stream.stream_conn_manager.set_loop(loop)
    except RuntimeError:
        pass
    yield


# 创建 FastAPI 应用
app = FastAPI(
    title="CogniFlow WebUI",
    description="CogniFlow 训练图集管理、模型管理、数据标注、规则引擎",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(atlas.router, prefix="/api/atlas", tags=["图集管理"])
app.include_router(image.router, prefix="/api/images", tags=["图片管理"])
app.include_router(annotation.router, prefix="/api/annotations", tags=["标注管理"])
app.include_router(category.router, prefix="/api/categories", tags=["类别管理"])
app.include_router(model.router, prefix="/api/models", tags=["模型管理"])
app.include_router(training.router, prefix="/api/training", tags=["训练管理"])
app.include_router(launch.router, prefix="/api/launch", tags=["模型启动"])
app.include_router(inference.router, prefix="/api/inference", tags=["模型测试"])
app.include_router(rule_engine.router, tags=["规则引擎"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(ws_stream.router, prefix="/ws", tags=["流式推理WebSocket"])

# 挂载上传文件目录为静态文件服务
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 挂载推理输出目录为静态文件服务
os.makedirs(INFERENCE_OUTPUT_DIR, exist_ok=True)
app.mount("/inference_output", StaticFiles(directory=INFERENCE_OUTPUT_DIR), name="inference_output")


@app.get("/")
async def root():
    """根路径重定向到前端。"""
    return RedirectResponse(url="/index.html")


@app.get("/api/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
