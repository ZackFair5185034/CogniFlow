# -*- coding: utf-8 -*-
"""规则引擎 WebSocket 连接管理器。

按 execution_id 订阅/广播执行进度消息。
"""
import asyncio
import json
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from datetime import datetime


class RuleExecutionConnectionManager:
    """规则执行 WebSocket 连接管理器。

    负责：
    1. 管理所有活跃的 WebSocket 连接
    2. 按 execution_id 订阅/取消订阅
    3. 向订阅的连接推送消息（带批处理机制）
    """

    # 批处理窗口大小（秒），约 60fps 一帧的时间
    BATCH_WINDOW_SEC: float = 0.016

    def __init__(self):
        # 所有活跃连接: websocket -> set of execution_ids
        self._connections: Dict[WebSocket, Set[int]] = {}

        # execution_id -> 已订阅的 WebSocket 集合
        self._subscriptions: Dict[int, Set[WebSocket]] = {}

        # 锁，保证线程安全
        self._lock = asyncio.Lock()

        # 批处理：待发送的消息缓冲，按 execution_id 分组
        self._pending_messages: Dict[int, List[dict]] = {}

        # 批处理刷新任务
        self._flush_task: Optional[asyncio.Task] = None

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
        """向消息中指定的 execution_id 广播消息（带批处理）。

        兼容 executor.py 的调用方式（message 中已含 execution_id）。
        消息会被缓冲一段时间后批量发送，减少网络往返次数。
        """
        execution_id = message.get("execution_id")
        if not execution_id:
            return

        # 添加时间戳
        message["timestamp"] = datetime.now().isoformat()

        async with self._lock:
            # 将消息加入待发送缓冲
            if execution_id not in self._pending_messages:
                self._pending_messages[execution_id] = []
            self._pending_messages[execution_id].append(message)

            # 如果没有正在运行的刷新任务，则创建一个
            if not self._flush_task or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._flush_messages())

    async def _flush_messages(self):
        """将缓冲的消息批量发送出去。

        在 BATCH_WINDOW_SEC 时间窗口结束后，将该时间段内收集的所有消息
        按 execution_id 分组合并后发送。
        """
        # 等待一个批处理窗口
        await asyncio.sleep(self.BATCH_WINDOW_SEC)

        async with self._lock:
            # 取出所有待发送的消息
            pending = self._pending_messages
            self._pending_messages = {}

        # 发送给各个 execution_id 的订阅者
        for execution_id, messages in pending.items():
            if not messages:
                continue

            # 获取订阅者
            async with self._lock:
                subscribers = self._subscriptions.get(execution_id, set()).copy()

            if not subscribers:
                continue

            # 合并消息为批量消息
            if len(messages) == 1:
                # 只有一条消息，直接发送原消息
                batch = messages[0]
            else:
                # 多条消息，包装为批量消息
                batch = {"type": "batch", "messages": messages}

            text = json.dumps(batch, ensure_ascii=False)

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

    async def send_node_executed(
        self,
        execution_id: int,
        node_id: str,
        status: str,
        outputs: dict,
        metrics: dict = None,
    ):
        """广播节点执行完成。

        Args:
            metrics: 节点输出指标（如 detections 数量、字节数等），可选。
                区别于 outputs 中的原始数据，metrics 是聚合后的统计信息，
                便于前端做轻量级展示而无需解析完整 outputs。
        """
        await self.broadcast({
            "execution_id": execution_id,
            "type": "node_executed",
            "node_id": node_id,
            "status": status,
            "outputs": outputs,
            "metrics": metrics,
        })

    async def send_node_failed(self, execution_id: int, node_id: str, error: str):
        """广播节点执行失败。"""
        await self.broadcast({
            "execution_id": execution_id,
            "type": "node_failed",
            "node_id": node_id,
            "error": error,
        })

    async def send_node_timeout(
        self,
        execution_id: int,
        node_id: str,
        timeout_seconds: float,
        error: str = None
    ):
        """广播节点执行超时。

        区别于通用的 node_failed，便于前端做差异化展示（黄色警告 vs 红色错误）。
        下游节点将继续执行（断路器模式）。
        """
        await self.broadcast({
            "execution_id": execution_id,
            "type": "node_timeout",
            "node_id": node_id,
            "timeout_seconds": timeout_seconds,
            "error": error or f"节点执行超时（{timeout_seconds}s）",
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
