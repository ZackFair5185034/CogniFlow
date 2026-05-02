# -*- coding: utf-8 -*-
"""WebSocket 流推理端点 - 实时推送推理帧给前端。

路由：WS /ws/inference/stream/{job_id}
"""

import asyncio
import base64
import json
import threading
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from utils.frame_buffer import stream_job_manager, FrameBuffer

router = APIRouter()


class StreamConnectionManager:
    """流式推理 WebSocket 连接管理器。"""

    def __init__(self):
        # job_id -> WebSocket 连接
        self._connections: dict[str, WebSocket] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pusher_tasks: dict[str, asyncio.Task] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop):
        """设置事件循环（需在应用启动时调用）。"""
        self._loop = loop

    async def connect(self, job_id: str, websocket: WebSocket):
        """接受 WebSocket 连接。"""
        await websocket.accept()
        self._connections[job_id] = websocket
        if job_id not in self._locks:
            self._locks[job_id] = asyncio.Lock()

    def disconnect(self, job_id: str):
        """断开连接。"""
        # 取消推送任务
        if job_id in self._pusher_tasks:
            self._pusher_tasks[job_id].cancel()
            del self._pusher_tasks[job_id]
        if job_id in self._connections:
            del self._connections[job_id]
        if job_id in self._locks:
            del self._locks[job_id]

    async def send_json(self, job_id: str, data: dict):
        """发送 JSON 数据。"""
        if job_id in self._connections:
            try:
                await self._connections[job_id].send_json(data)
            except Exception:
                self.disconnect(job_id)

    def start_pusher(self, job_id: str, frame_buffer: FrameBuffer):
        """启动帧推送协程。"""
        if self._loop is None:
            return
        task = self._loop.create_task(self._push_frames(job_id, frame_buffer))
        self._pusher_tasks[job_id] = task

    async def _push_frames(self, job_id: str, frame_buffer: FrameBuffer):
        """从帧缓冲队列取帧并推送。"""
        target_fps = 24
        frame_interval = 1.0 / target_fps

        while True:
            frame = frame_buffer.get(timeout=0.5)

            if frame is None:
                # 超时，检查任务是否结束
                job = stream_job_manager.get_job(job_id)
                if job is None or job["status"] in ("completed", "failed", "stopped"):
                    # 推送结束消息
                    await self.send_json(job_id, {
                        "type": "complete" if job and job["status"] == "completed" else "stopped",
                        "total_frames": job["current_frame"] if job else 0,
                        "total_detections": job["total_detections"] if job else 0,
                    })
                    break
                continue

            # 构建帧消息
            msg = {
                "type": "frame",
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "image": frame.image_base64,
                "detections": frame.detections,
                "stats": {
                    "inference_ms": frame.inference_ms,
                    "total_detections": len(frame.detections),
                }
            }

            try:
                await self.send_json(job_id, msg)
            except Exception:
                break

            # 控制推送节奏（尽量接近 target_fps）
            await asyncio.sleep(frame_interval)


# 全局连接管理器
stream_conn_manager = StreamConnectionManager()


@router.websocket("/inference/stream/{job_id}")
async def ws_inference_stream(websocket: WebSocket, job_id: str):
    """WebSocket 流式推理端点。

    前端连接此端点接收实时推理帧。
    """
    await stream_conn_manager.connect(job_id, websocket)

    try:
        # 获取帧缓冲
        frame_buffer = stream_job_manager.get_job_frame_buffer(job_id)
        if frame_buffer is None:
            await websocket.send_json({"type": "error", "error": "任务不存在"})
            stream_conn_manager.disconnect(job_id)
            return

        # 启动推送协程
        stream_conn_manager.start_pusher(job_id, frame_buffer)

        # 保持连接，处理前端消息
        while True:
            try:
                # 等待前端消息（目前主要处理 ping）
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # 发送心跳
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
    finally:
        stream_conn_manager.disconnect(job_id)
