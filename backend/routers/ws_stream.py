# -*- coding: utf-8 -*-
"""WebSocket 流推理端点 - 实时推送推理帧给前端。

服务端不做任何节流，帧就绪即推。
前端通过本地定时器按设置帧率消费缓存帧。

路由：WS /ws/inference/stream/{job_id}
"""

import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.utils.frame_buffer import stream_job_manager, FrameBuffer, FrameResult

router = APIRouter()


class StreamConnectionManager:
    """流式推理 WebSocket 连接管理器。"""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pusher_tasks: dict[str, asyncio.Task] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop):
        self._loop = loop

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[job_id] = websocket
        if job_id not in self._locks:
            self._locks[job_id] = asyncio.Lock()

    def disconnect(self, job_id: str):
        if job_id in self._pusher_tasks:
            self._pusher_tasks[job_id].cancel()
            del self._pusher_tasks[job_id]
        if job_id in self._connections:
            del self._connections[job_id]
        if job_id in self._locks:
            del self._locks[job_id]

    async def send_json(self, job_id: str, data: dict):
        if job_id in self._connections:
            try:
                await self._connections[job_id].send_json(data)
            except Exception:
                self.disconnect(job_id)

    async def send_bytes(self, job_id: str, data: bytes):
        if job_id in self._connections:
            try:
                await self._connections[job_id].send_bytes(data)
            except Exception:
                self.disconnect(job_id)

    def start_pusher(self, job_id: str, frame_buffer: FrameBuffer):
        if self._loop is None:
            return
        task = self._loop.create_task(self._push_frames(job_id, frame_buffer))
        self._pusher_tasks[job_id] = task

    async def _send_frame(self, job_id: str, frame: FrameResult):
        """发送单帧（元数据 + 二进制），附带推理进度信息。"""
        job = stream_job_manager.get_job(job_id)
        buffer_frame = job["current_frame"] if job else frame.frame_id
        total = job["total_frames"] if job else 0

        meta = {
            "type": "frame_meta",
            "frame_id": frame.frame_id,
            "timestamp": frame.timestamp,
            "detections": frame.detections,
            "stats": {
                "inference_ms": frame.inference_ms,
                "total_detections": len(frame.detections),
            },
            "progress": {
                "buffer_frame": buffer_frame,
                "total_frames": total,
                "buffer_pct": round((buffer_frame / max(total, 1)) * 100, 1),
            }
        }

        await self.send_json(job_id, meta)
        await self.send_bytes(job_id, frame.image_bytes)

    async def _send_complete(self, job_id: str, job: Optional[dict]):
        if not job:
            await self.send_json(job_id, {
                "type": "complete", "total_frames": 0, "total_detections": 0,
            })
            return
        is_complete = job["status"] == "completed"
        await self.send_json(job_id, {
            "type": "complete" if is_complete else "stopped",
            "total_frames": job.get("current_frame", 0),
            "total_detections": job.get("total_detections", 0),
        })

    async def _push_frames(self, job_id: str, frame_buffer: FrameBuffer):
        """从帧缓冲取帧并立即推送，不做节流——前端自行控制渲染帧率。"""
        while True:
            frame = frame_buffer.get(timeout=0.5)

            if frame is not None:
                await self._send_frame(job_id, frame)
                stream_job_manager.update_job(job_id, playback_frame=frame.frame_id)
            else:
                job = stream_job_manager.get_job(job_id)
                if job is None or job["status"] in ("completed", "failed", "stopped"):
                    await self._send_complete(job_id, job)
                    break
                await asyncio.sleep(0.1)

    async def handle_client_message(self, job_id: str, msg: dict):
        msg_type = msg.get("type", "")

        if msg_type == "ping":
            await self.send_json(job_id, {"type": "pong"})


stream_conn_manager = StreamConnectionManager()


@router.websocket("/inference/stream/{job_id}")
async def ws_inference_stream(websocket: WebSocket, job_id: str):
    await stream_conn_manager.connect(job_id, websocket)

    try:
        frame_buffer = stream_job_manager.get_job_frame_buffer(job_id)
        if frame_buffer is None:
            await websocket.send_json({"type": "error", "error": "任务不存在"})
            stream_conn_manager.disconnect(job_id)
            return

        stream_conn_manager.start_pusher(job_id, frame_buffer)

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=10)
                msg = json.loads(data)
                await stream_conn_manager.handle_client_message(job_id, msg)
            except asyncio.TimeoutError:
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
        stream_job_manager.stop_job(job_id)

        # 更新 DB 记录状态
        try:
            from backend.database import SessionLocal, InferenceJob
            db = SessionLocal()
            try:
                db.query(InferenceJob).filter(
                    InferenceJob.job_id == job_id,
                    InferenceJob.status == "processing"
                ).update({"status": "stopped"})
                db.commit()
            finally:
                db.close()
        except Exception:
            pass
