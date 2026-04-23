# -*- coding: utf-8 -*-
"""WebSocket 路由。

提供训练状态、模型执行状态和系统状态的实时通信。
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/training")
async def websocket_training_all(websocket: WebSocket):
    """全局训练状态 WebSocket 连接。

    客户端连接后接收所有训练任务的实时状态更新。
    """
    await websocket.accept()
    job_id = 0  # 全局频道不使用特定 job_id
    if job_id not in ws_manager._training_connections:
        ws_manager._training_connections[job_id] = set()
    ws_manager._training_connections[job_id].add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager._training_connections[job_id].discard(websocket)


@router.websocket("/training/{job_id}")
async def websocket_training(websocket: WebSocket, job_id: int):
    """特定任务训练状态 WebSocket 连接。

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


@router.websocket("/system")
async def websocket_system(websocket: WebSocket):
    """系统状态 WebSocket 连接。

    客户端连接后接收系统状态的实时更新（CPU、内存、磁盘）。
    """
    await ws_manager.connect_system(websocket)
    try:
        while True:
            # 保持连接，等待断开
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_system(websocket)
