# -*- coding: utf-8 -*-
"""规则引擎 WebSocket 连接管理器。

按 execution_id 订阅/广播执行进度消息。
"""
import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime


class RuleExecutionConnectionManager:
    """规则执行 WebSocket 连接管理器。

    负责：
    1. 管理所有活跃的 WebSocket 连接
    2. 按 execution_id 订阅/取消订阅
    3. 向订阅的连接推送消息
    """

    def __init__(self):
        # 所有活跃连接: websocket -> set of execution_ids
        self._connections: Dict[WebSocket, Set[int]] = {}

        # execution_id -> 已订阅的 WebSocket 集合
        self._subscriptions: Dict[int, Set[WebSocket]] = {}

        # 锁，保证线程安全
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, execution_ids: list[int] = None):
        """客户端连接并订阅执行ID列表。"""
        await websocket.accept()

        async with self._lock:
            self._connections[websocket] = set(execution_ids or [])

            for eid in execution_ids or []:
                if eid not in self._subscriptions:
                    self._subscriptions[eid] = set()
                self._subscriptions[eid].add(websocket)

    async def disconnect(self, websocket: WebSocket):
        """客户端断开连接。"""
        async with self._lock:
            execution_ids = self._connections.pop(websocket, set())

            for eid in execution_ids:
                if eid in self._subscriptions:
                    self._subscriptions[eid].discard(websocket)

    async def subscribe(self, websocket: WebSocket, execution_id: int):
        """订阅特定 execution_id 的执行更新。"""
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket].add(execution_id)

            if execution_id not in self._subscriptions:
                self._subscriptions[execution_id] = set()
            self._subscriptions[execution_id].add(websocket)

    async def unsubscribe(self, websocket: WebSocket, execution_id: int):
        """取消订阅。"""
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket].discard(execution_id)

            if execution_id in self._subscriptions:
                self._subscriptions[execution_id].discard(websocket)

    async def broadcast(self, message: dict):
        """向消息中指定的 execution_id 广播消息。

        兼容 executor.py 的调用方式（message 中已含 execution_id）。
        """
        execution_id = message.get("execution_id")
        if not execution_id:
            return

        async with self._lock:
            subscribers = self._subscriptions.get(execution_id, set()).copy()

        if not subscribers:
            return

        message["timestamp"] = datetime.now().isoformat()
        text = json.dumps(message, ensure_ascii=False)

        # 并发发送给所有订阅者
        async def send_to(ws: WebSocket):
            try:
                await ws.send_text(text)
            except Exception:
                pass  # 忽略发送失败的连接

        await asyncio.gather(*[send_to(ws) for ws in subscribers], return_exceptions=True)

    async def send_node_started(self, execution_id: int, node_id: str, node_type: str):
        """广播节点开始执行。"""
        await self.broadcast({
            "execution_id": execution_id,
            "type": "node_started",
            "node_id": node_id,
            "node_type": node_type,
        })

    async def send_node_executed(self, execution_id: int, node_id: str, status: str, outputs: dict):
        """广播节点执行完成。"""
        await self.broadcast({
            "execution_id": execution_id,
            "type": "node_executed",
            "node_id": node_id,
            "status": status,
            "outputs": outputs,
        })

    async def send_node_failed(self, execution_id: int, node_id: str, error: str):
        """广播节点执行失败。"""
        await self.broadcast({
            "execution_id": execution_id,
            "type": "node_failed",
            "node_id": node_id,
            "error": error,
        })

    async def send_progress(self, execution_id: int, progress: float, current_level: int,
                            total_levels: int, completed_nodes: int, total_nodes: int):
        """广播执行进度。"""
        await self.broadcast({
            "execution_id": execution_id,
            "type": "execution_progress",
            "progress": progress,
            "current_level": current_level,
            "total_levels": total_levels,
            "completed_nodes": completed_nodes,
            "total_nodes": total_nodes,
        })

    async def send_complete(self, execution_id: int, status: str, result: dict = None, error: str = None):
        """广播执行完成。"""
        msg = {
            "type": "execution_complete",
            "status": status,
        }
        if result:
            msg["result"] = result
        if error:
            msg["error"] = error
        await self.broadcast({"execution_id": execution_id, **msg})


# 全局单例
rule_ws_manager = RuleExecutionConnectionManager()
