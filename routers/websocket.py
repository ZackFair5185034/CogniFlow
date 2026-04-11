# -*- coding: utf-8 -*-
"""WebSocket 路由。

提供训练状态和模型执行状态的实时通信。
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/training/{job_id}")
async def websocket_training(websocket: WebSocket, job_id: int):
    """训练状态 WebSocket 连接。

    客户端连接后接收该任务的实时训练状态更新。
    """
    await ws_manager.connect_training(websocket, job_id)
    try:
        while True:
            # 保持连接，等待断开
            data = await websocket.receive_text()
            # 可以处理客户端消息（如请求特定数据）
    except WebSocketDisconnect:
        ws_manager.disconnect_training(websocket, job_id)


@router.websocket("/launch")
async def websocket_launch(websocket: WebSocket):
    """模型执行状态 WebSocket 连接。

    客户端连接后接收模型执行状态的实时更新。
    """
    await ws_manager.connect_launch(websocket)
    try:
        while True:
            # 保持连接，等待断开
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_launch(websocket)
