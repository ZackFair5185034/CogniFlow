# -*- coding: utf-8 -*-
"""VisionGame WebUI - FastAPI 主入口。

提供：
- REST API
- WebSocket 实时通信
- Vue3 前端静态文件托管
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

from database import init_db
from routers import atlas, image, annotation, category, model, training, launch

# 创建 FastAPI 应用
app = FastAPI(
    title="VisionGame WebUI",
    description="VisionGame 训练图集管理、模型管理、数据标注",
    version="0.1.0",
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


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库。"""
    init_db()


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
