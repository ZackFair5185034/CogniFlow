# -*- coding: utf-8 -*-
"""模型启动路由。

提供模型加载和执行控制功能。
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

# 模型加载状态
_model_loaded = False
_model_info = {}


@router.post("/load")
async def load_model(model_id: int):
    """加载模型。"""
    global _model_loaded, _model_info

    # TODO: 实际加载模型逻辑
    _model_loaded = True
    _model_info = {"model_id": model_id, "status": "loaded"}

    return {
        "message": "模型加载成功",
        "model_id": model_id,
        "status": "loaded"
    }


@router.post("/start")
async def start_inference():
    """开始执行推理。"""
    global _model_loaded

    if not _model_loaded:
        raise HTTPException(status_code=400, detail="模型未加载")

    # TODO: 实际开始推理
    return {"message": "推理已开始"}


@router.post("/stop")
async def stop_inference():
    """停止执行推理。"""
    global _model_loaded

    if not _model_loaded:
        raise HTTPException(status_code=400, detail="模型未加载")

    # TODO: 实际停止推理
    return {"message": "推理已停止"}


@router.get("/status")
async def get_launch_status():
    """获取模型执行状态。"""
    return {
        "loaded": _model_loaded,
        "info": _model_info
    }
