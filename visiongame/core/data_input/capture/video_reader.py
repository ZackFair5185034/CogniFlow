"""VisionGame 视频读取模块 - 支持常见视频格式的读取。"""

from typing import Optional, Tuple, List
from pathlib import Path
import numpy as np
import time

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class VideoReader:
    """视频文件读取类，使用 OpenCV 作为后端。

    支持功能：
    - 常见视频格式 (mp4, avi, mkv 等)
    - 逐帧读取
    - 跳转和速度控制
    """

    def __init__(
        self,
        video_path: Path,
        buffer_size: int = 100,
        target_fps: Optional[float] = None,
    ):
        """初始化视频读取器。

        Args:
            video_path: 视频文件路径。
            buffer_size: 内部帧缓冲区大小。
            target_fps: 播放目标帧率 (None = 视频原生帧率)。
        """
        if not CV2_AVAILABLE:
            raise ImportError("需要安装 OpenCV 进行视频读取。安装命令: pip install opencv-python")

        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件未找到: {self.video_path}")

        self.buffer_size = buffer_size
        self.target_fps = target_fps

        # Open video capture
        self._cap = cv2.VideoCapture(str(self.video_path))
        if not self._cap.isOpened():
            raise IOError(f"无法打开视频: {self.video_path}")

        # Get video properties
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._codec = int(self._cap.get(cv2.CAP_PROP_FOURCC))

        # Calculate frame interval
        if target_fps is not None:
            self.frame_interval = 1.0 / target_fps
        else:
            self.frame_interval = 1.0 / self._fps

        self._current_frame = 0
        self._buffer: List[Tuple[int, np.ndarray]] = []
        self._last_read_time = 0.0

    @property
    def fps(self) -> float:
        """获取视频帧率。"""
        return self._fps

    @property
    def frame_count(self) -> int:
        """获取总帧数。"""
        return self._frame_count

    @property
    def duration(self) -> float:
        """获取视频时长（秒）。"""
        return self._frame_count / self._fps if self._fps > 0 else 0

    @property
    def resolution(self) -> Tuple[int, int]:
        """获取视频分辨率 (宽度, 高度)。"""
        return self._width, self._height

    @property
    def current_frame_num(self) -> int:
        """获取当前帧号（从0开始）。"""
        return self._current_frame

    def read(self) -> Optional[np.ndarray]:
        """读取下一帧。

        Returns:
            RGB 图像 numpy 数组 (H, W, 3)，如果视频结束则返回 None。
        """
        # 帧率限制
        current_time = time.time()
        elapsed = current_time - self._last_read_time
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)
        self._last_read_time = time.time()

        ret, frame = self._cap.read()
        if not ret:
            return None

        self._current_frame += 1

        # BGR 转 RGB
        frame = frame[:, :, ::-1]

        # 缓存到缓冲区
        self._buffer.append((self._current_frame, frame.copy()))
        if len(self._buffer) > self.buffer_size:
            self._buffer.pop(0)

        return frame

    def read_batch(self, n_frames: int) -> List[np.ndarray]:
        """读取多帧。

        Args:
            n_frames: 要读取的帧数。

        Returns:
            帧列表 (RGB)。
        """
        frames = []
        for _ in range(n_frames):
            frame = self.read()
            if frame is None:
                break
            frames.append(frame)
        return frames

    def seek(self, frame_num: int) -> bool:
        """跳转到指定帧。

        Args:
            frame_num: 目标帧号 (从0开始)。

        Returns:
            跳转是否成功。
        """
        if frame_num < 0 or frame_num >= self._frame_count:
            return False

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        self._current_frame = frame_num
        self._buffer.clear()
        return True

    def seek_to_time(self, seconds: float) -> bool:
        """跳转到指定时间。

        Args:
            seconds: 目标时间（秒）。

        Returns:
            跳转是否成功。
        """
        frame_num = int(seconds * self._fps)
        return self.seek(frame_num)

    def get_frame_at(self, frame_num: int) -> Optional[np.ndarray]:
        """获取指定帧（不改变当前位置）。

        Args:
            frame_num: 帧号 (从0开始)。

        Returns:
            帧 (RGB)，如果不可用则返回 None。
        """
        # 先检查缓冲区
        for cached_frame_num, frame in self._buffer:
            if cached_frame_num == frame_num:
                return frame

        # 跳转并读取
        if self.seek(frame_num):
            return self.read()
        return None

    def reset(self) -> None:
        """重置到开头。"""
        self.seek(0)

    def release(self) -> None:
        """释放视频资源。"""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def __len__(self) -> int:
        return self._frame_count

    def __iter__(self):
        self.reset()
        return self

    def __next__(self) -> np.ndarray:
        frame = self.read()
        if frame is None:
            raise StopIteration
        return frame
