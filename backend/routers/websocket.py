# -*- coding: utf-8 -*-
"""WebSocket 路由。

提供训练状态、模型执行状态和系统状态的实时通信。
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.websocket_manager import ws_manager
from backend.services.rule_engine.websocket_manager import rule_ws_manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])


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

    客户端连接后接收系统状态的实时更新（CPU、内存、磁盘、GPU）。
    """
    await ws_manager.connect_system(websocket)
    try:
        while True:
            # 保持连接，等待断开
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_system(websocket)


@router.websocket("/export/{export_id}")
async def websocket_export(websocket: WebSocket, export_id: str):
    """导出进度 WebSocket 连接。

    客户端连接后接收模型导出任务的实时进度更新。
    """
    await ws_manager.connect_export(websocket, export_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_export(websocket, export_id)


@router.websocket("/rule-execution")
async def websocket_rule_execution(websocket: WebSocket):
    """规则执行状态 WebSocket 连接。

    客户端连接后可订阅特定 execution_id 的执行进度更新。

    客户端发送订阅消息:
    {
        "action": "subscribe",
        "execution_id": 123
    }

    取消订阅:
    {
        "action": "unsubscribe",
        "execution_id": 123
    }
    """
    await rule_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            import json
            msg = json.loads(data)
            action = msg.get("action")
            execution_id = msg.get("execution_id")

            if action == "subscribe" and execution_id:
                # 用 subscribe_with_replay: 订阅建立之前产生的消息在无订阅者时被
                # 存入回放缓冲, 这里补发给客户端, 消除「先触发执行再连 WS」的竞态。
                await rule_ws_manager.subscribe_with_replay(websocket, execution_id)
            elif action == "unsubscribe" and execution_id:
                await rule_ws_manager.unsubscribe(websocket, execution_id)
    except WebSocketDisconnect:
        await rule_ws_manager.disconnect(websocket)
    except Exception:
        await rule_ws_manager.disconnect(websocket)
