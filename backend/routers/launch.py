# -*- coding: utf-8 -*-
"""模型启动路由。

提供模型加载和执行控制功能。
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException

from backend.websocket_manager import ws_manager

router = APIRouter()

# 模型加载状态
_model_loaded = False
_model_info = {}
_inference_running = False
_inference_task: Optional[asyncio.Task] = None


async def _simulate_inference():
    """模拟推理过程。"""
    global _inference_running
    step = 0
    while _inference_running:
        step += 1
        fps = 30.0
        await ws_manager.send_launch_update({
            "inference_step": step,
            "fps": fps,
            "status": "running",
        })
        await asyncio.sleep(1)


@router.post("/load")
async def load_model(model_id: int):
    """加载模型。"""
    global _model_loaded, _model_info

    # TODO: 实际加载模型逻辑
    _model_loaded = True
    _model_info = {"model_id": model_id, "status": "loaded"}

    await ws_manager.send_launch_update({
        "event": "model_loaded",
        "model_id": model_id,
    })

    return {
        "message": "模型加载成功",
        "model_id": model_id,
        "status": "loaded"
    }


@router.post("/start")
async def start_inference():
    """开始执行推理。"""
    global _model_loaded, _inference_running, _inference_task

    if not _model_loaded:
        raise HTTPException(status_code=400, detail="模型未加载")

    _inference_running = True
    _inference_task = asyncio.create_task(_simulate_inference())

    await ws_manager.send_launch_update({
        "event": "inference_started",
        "status": "running",
    })

    return {"message": "推理已开始"}


@router.post("/stop")
async def stop_inference():
    """停止执行推理。"""
    global _inference_running, _inference_task

    if not _model_loaded:
        raise HTTPException(status_code=400, detail="模型未加载")

    _inference_running = False
    if _inference_task:
        _inference_task.cancel()
        _inference_task = None

    await ws_manager.send_launch_update({
        "event": "inference_stopped",
        "status": "stopped",
    })

    return {"message": "推理已停止"}


@router.get("/status")
async def get_launch_status():
    """获取模型执行状态。"""
    return {
        "loaded": _model_loaded,
        "info": _model_info,
        "inference_running": _inference_running,
    }
