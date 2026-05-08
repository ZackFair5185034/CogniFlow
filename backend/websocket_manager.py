# -*- coding: utf-8 -*-
"""WebSocket 管理器 - 处理实时通信。

支持训练状态、模型执行状态和系统状态的实时推送。
"""
import asyncio
import psutil
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """WebSocket 连接管理器。"""

    def __init__(self):
        # 训练状态连接: job_id -> set of websockets
        self._training_connections: Dict[int, Set[WebSocket]] = {}
        # 模型执行状态连接
        self._launch_connections: Set[WebSocket] = set()
        # 系统状态连接
        self._system_connections: Set[WebSocket] = set()
        # 系统状态推送任务
        self._system_push_task: asyncio.Task | None = None
        # 导出状态连接: export_id -> set of websockets
        self._export_connections: Dict[str, Set[WebSocket]] = {}

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
        # 发送给特定 job_id 的连接
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

        # 同时发送给全局频道（job_id=0）的连接
        if 0 in self._training_connections:
            disconnected = set()
            for websocket in self._training_connections[0]:
                try:
                    await websocket.send_json({
                        "type": "training_update",
                        "data": data
                    })
                except Exception:
                    disconnected.add(websocket)
            for ws in disconnected:
                self._training_connections[0].discard(ws)

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

    # ===== 导出进度 WebSocket =====
    async def connect_export(self, websocket: WebSocket, export_id: str):
        """连接导出进度 WebSocket。"""
        await websocket.accept()
        if export_id not in self._export_connections:
            self._export_connections[export_id] = set()
        self._export_connections[export_id].add(websocket)

    def disconnect_export(self, websocket: WebSocket, export_id: str):
        """断开导出进度 WebSocket。"""
        if export_id in self._export_connections:
            self._export_connections[export_id].discard(websocket)

    async def send_export_update(self, export_id: str, data: dict):
        """向导出任务连接的客户端发送进度更新。"""
        if export_id not in self._export_connections:
            return
        disconnected = set()
        for websocket in self._export_connections[export_id]:
            try:
                await websocket.send_json({
                    "type": "export_update",
                    "data": data
                })
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            self._export_connections[export_id].discard(ws)

    async def connect_system(self, websocket: WebSocket):
        """连接系统状态 WebSocket。"""
        await websocket.accept()
        self._system_connections.add(websocket)
        # 启动推送任务（如果还没启动）
        if self._system_push_task is None or self._system_push_task.done():
            self._system_push_task = asyncio.create_task(self._push_system_stats())

    def disconnect_system(self, websocket: WebSocket):
        """断开系统状态 WebSocket。"""
        self._system_connections.discard(websocket)

    async def _push_system_stats(self):
        """定期推送系统状态。"""
        while self._system_connections:
            try:
                stats = self._get_system_stats()
                disconnected = set()
                for websocket in self._system_connections:
                    try:
                        await websocket.send_json({
                            "type": "system_stats",
                            "data": stats
                        })
                    except Exception:
                        disconnected.add(websocket)
                for ws in disconnected:
                    self._system_connections.discard(ws)
                await asyncio.sleep(2)  # 每2秒推送一次
            except Exception:
                await asyncio.sleep(2)

    def _get_system_stats(self) -> dict:
        """获取系统状态。"""
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=None)

        # 内存信息
        memory = psutil.virtual_memory()
        memory_total = memory.total
        memory_used = memory.used
        memory_percent = memory.percent

        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = disk.percent

        return {
            "cpu": {
                "percent": cpu_percent,
                "status": "warning" if cpu_percent > 80 else "normal"
            },
            "memory": {
                "total": memory_total,
                "used": memory_used,
                "percent": memory_percent,
                "status": "warning" if memory_percent > 80 else "normal"
            },
            "disk": {
                "total": disk_total,
                "used": disk_used,
                "percent": disk_percent,
                "status": "warning" if disk_percent > 90 else "normal"
            }
        }


# 全局单例
ws_manager = WebSocketManager()
