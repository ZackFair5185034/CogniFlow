# -*- coding: utf-8 -*-
"""帧缓冲管理器 - 支持生产者-消费者模式的环形队列。

用于视频推理场景：
- 推理线程（生产者）不断将推理结果放入队列
- WebSocket 推送线程（消费者）从队列取出数据推送给前端
- 支持流量控制：当推理快于推送时丢弃最新帧，当推理慢于推送时等待
"""

import threading
import time
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawFrameResult:
    """原始帧推理结果（编码前）。"""
    frame_id: int           # 帧序号
    timestamp: float        # 时间戳（秒）
    frame_bgr: np.ndarray   # BGR 原始帧数据（numpy 数组）
    detections: list        # 检测结果列表
    inference_ms: int       # 推理耗时（毫秒）


@dataclass
class FrameResult:
    """单帧推理结果（已编码）。"""
    frame_id: int           # 帧序号
    timestamp: float        # 时间戳（秒）
    image_bytes: bytes      # JPEG 压缩后的原始字节
    detections: list        # 检测结果列表
    inference_ms: int       # 推理耗时（毫秒）


class FrameBuffer:
    """线程安全的帧缓冲队列。"""

    def __init__(self, maxsize: int = 30):
        """初始化帧缓冲。

        Args:
            maxsize: 队列最大长度，超过此长度时丢弃最旧的帧
        """
        self._queue: deque[FrameResult] = deque(maxlen=maxsize)
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._total_frames = 0   # 已入队总帧数（用于统计）
        self._dropped_frames = 0 # 丢弃的帧数（统计用）

    def put(self, frame: FrameResult) -> bool:
        """放入一帧（生产者调用）。

        如果队列已满，丢弃最旧的帧。

        Args:
            frame: 帧推理结果

        Returns:
            True 表示正常入队，False 表示队列已满被丢弃
        """
        with self._lock:
            self._total_frames += 1
            # 计算是否需要丢弃（队列已满时 deque 会自动丢弃最旧的）
            was_full = len(self._queue) >= self._queue.maxlen
            self._queue.append(frame)
            if was_full:
                self._dropped_frames += 1
            self._not_empty.notify()
            return not was_full

    def get(self, timeout: float = 1.0) -> Optional[FrameResult]:
        """取出一帧（消费者调用）。

        Args:
            timeout: 等待超时时间（秒）

        Returns:
            帧数据，超时返回 None
        """
        with self._not_empty:
            # while 循环：处理 clear() notify_all 唤醒后队列仍为空的情况
            while not self._queue:
                if not self._not_empty.wait(timeout):
                    return None
            return self._queue.popleft()

    def clear(self):
        """清空队列并唤醒所有等待中的 get() 调用。"""
        with self._lock:
            self._queue.clear()
            self._not_empty.notify_all()

    @property
    def qsize(self) -> int:
        """当前队列长度。"""
        with self._lock:
            return len(self._queue)

    @property
    def total_frames(self) -> int:
        """已入队总帧数。"""
        return self._total_frames

    @property
    def dropped_frames(self) -> int:
        """因队列满而丢弃的帧数。"""
        return self._dropped_frames


class StreamJobManager:
    """流式推理任务管理器。"""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        # 任务状态常量
        self.STATUS_PENDING = "pending"
        self.STATUS_PROCESSING = "processing"
        self.STATUS_COMPLETED = "completed"
        self.STATUS_FAILED = "failed"
        self.STATUS_STOPPED = "stopped"

    def create_job(
        self,
        input_path: str,
        model_id: int,
        conf_threshold: float,
        categories: list,
        fps: float,
        total_frames: int,
    ) -> tuple[str, FrameBuffer]:
        """创建流式推理任务。

        Returns:
            (job_id, frame_buffer) 元组
        """
        import uuid
        job_id = str(uuid.uuid4())[:8]
        frame_buffer = FrameBuffer(maxsize=30)
        # 原始帧缓冲（编码前），用于推理→编码流水线
        raw_buffer = FrameBuffer(maxsize=10)

        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": self.STATUS_PENDING,
                "progress": 0,
                "current_frame": 0,
                "total_frames": total_frames,
                "input_path": input_path,
                "result_path": None,
                "error": None,
                "model_id": model_id,
                "conf_threshold": conf_threshold,
                "categories": categories,
                "fps": fps,
                "frame_buffer": frame_buffer,
                "raw_buffer": raw_buffer,
                "inference_done": False,
                "final_frame_count": 0,
                "final_total_detections": 0,
                "created_at": time.time(),
                "total_detections": 0,
                # 播放进度（前端当前显示的帧位置）
                "playback_frame": 0,
                # 缓存帧数（暂停期间累积）
                "buffered_frames": 0,
            }

        return job_id, frame_buffer

    def update_job(self, job_id: str, **kwargs):
        """更新任务状态。"""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)

    def get_job(self, job_id: str) -> Optional[dict]:
        """获取任务状态。"""
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def get_job_frame_buffer(self, job_id: str) -> Optional[FrameBuffer]:
        """获取任务的帧缓冲（用于消费者连接）。"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job["frame_buffer"] if job else None

    def get_job_raw_buffer(self, job_id: str) -> Optional[FrameBuffer]:
        """获取任务的原始帧缓冲（用于编码线程）。"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.get("raw_buffer") if job else None

    def stop_job(self, job_id: str):
        """停止任务并清空缓冲区，唤醒所有阻塞等待的线程。"""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = self.STATUS_STOPPED
                # 清空缓冲区，触发 notify_all 唤醒等待中的 get() 调用
                fb = self._jobs[job_id].get("frame_buffer")
                if fb:
                    fb.clear()
                rb = self._jobs[job_id].get("raw_buffer")
                if rb:
                    rb.clear()

    def is_job_stopped(self, job_id: str) -> bool:
        """检查任务是否已停止。"""
        job = self.get_job(job_id)
        return job is not None and job["status"] == self.STATUS_STOPPED


# 全局单例
stream_job_manager = StreamJobManager()
