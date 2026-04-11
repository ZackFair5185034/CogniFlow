# -*- coding: utf-8 -*-
"""WebSocket 管理器 - 处理实时通信。

支持训练状态和模型执行状态的实时推送。
"""
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """WebSocket 连接管理器。"""

    def __init__(self):
        # 训练状态连接: job_id -> set of websockets
        self._training_connections: Dict[int, Set[WebSocket]] = {}
        # 模型执行状态连接
        self._launch_connections: Set[WebSocket] = set()

    async def connect_training(self, websocket: WebSocket, job_id: int):
        """连接训练状态 WebSocket。"""
        await websocket.accept()
        if job_id not in self._training_connections:
            self._training_connections[job_id] = set()
        self._training_connections[job_id].add(websocket)

    def disconnect_training(self, websocket: WebSocket, job_id: int):
        """断开训练状态 WebSocket。"""
        if job_id in self._training_connections:
            self._training_connections[job_id].discard(websocket)

    async def send_training_update(self, job_id: int, data: dict):
        """向所有连接的客户端发送训练更新。"""
        if job_id in self._training_connections:
            disconnected = set()
            for websocket in self._training_connections[job_id]:
                try:
                    await websocket.send_json({
                        "type": "training_update",
                        "data": data
                    })
                except Exception:
                    disconnected.add(websocket)
            # 清理断开的连接
            for ws in disconnected:
                self._training_connections[job_id].discard(ws)

    async def connect_launch(self, websocket: WebSocket):
        """连接模型执行状态 WebSocket。"""
        await websocket.accept()
        self._launch_connections.add(websocket)

    def disconnect_launch(self, websocket: WebSocket):
        """断开模型执行状态 WebSocket。"""
        self._launch_connections.discard(websocket)

    async def send_launch_update(self, data: dict):
        """向所有连接的客户端发送执行状态更新。"""
        disconnected = set()
        for websocket in self._launch_connections:
            try:
                await websocket.send_json({
                    "type": "launch_update",
                    "data": data
                })
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            self._launch_connections.discard(ws)


# 全局单例
ws_manager = WebSocketManager()
