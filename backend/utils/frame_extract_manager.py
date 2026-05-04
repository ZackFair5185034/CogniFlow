# -*- coding: utf-8 -*-
"""帧提取任务管理器 - 管理视频帧提取的异步任务。

功能：
- 提交帧提取任务，立即返回 job_id
- 后台线程执行提取，实时更新进度
- 前端轮询 job_id 获取状态
"""

import threading
import time
import uuid
from typing import Optional

# 任务状态常量
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class FrameExtractJobManager:
    """帧提取异步任务管理器。"""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def submit_job(
        self,
        atlas_id: int,
        video_path: str,
        extract_count: int,
        total_frames: int,
    ) -> str:
        """提交一个新任务，立即返回 job_id。

        Args:
            atlas_id: 图集 ID
            video_path: 视频文件路径
            extract_count: 需要提取的帧数
            total_frames: 视频总帧数

        Returns:
            job_id 字符串
        """
        job_id = str(uuid.uuid4())[:8]

        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": STATUS_PENDING,
                "progress": 0.0,
                "current_frame": 0,
                "extracted_count": 0,
                "total_frames": total_frames,
                "extract_count": extract_count,
                "atlas_id": atlas_id,
                "video_path": video_path,
                "directory": f"video_{job_id}",  # 使用 job_id 作为子目录名
                "error": None,
                "created_at": time.time(),
                "completed_at": None,
            }

        return job_id

    def get_job(self, job_id: str) -> Optional[dict]:
        """获取任务状态（只读拷贝）。"""
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def update_progress(self, job_id: str, current_frame: int, extracted_count: int):
        """更新任务进度（后台线程调用）。"""
        with self._lock:
            if job_id not in self._jobs:
                return
            job = self._jobs[job_id]
            job["current_frame"] = current_frame
            job["extracted_count"] = extracted_count
            job["progress"] = round(extracted_count / job["extract_count"], 4) if job["extract_count"] > 0 else 0
            job["status"] = STATUS_PROCESSING

    def complete_job(self, job_id: str):
        """标记任务完成（后台线程调用）。"""
        with self._lock:
            if job_id not in self._jobs:
                return
            job = self._jobs[job_id]
            job["status"] = STATUS_COMPLETED
            job["progress"] = 1.0
            job["completed_at"] = time.time()

    def fail_job(self, job_id: str, error: str):
        """标记任务失败（后台线程调用）。"""
        with self._lock:
            if job_id not in self._jobs:
                return
            job = self._jobs[job_id]
            job["status"] = STATUS_FAILED
            job["error"] = error
            job["completed_at"] = time.time()

    def set_status(self, job_id: str, status: str):
        """设置任务状态。"""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status


# 全局单例
frame_extract_manager = FrameExtractJobManager()