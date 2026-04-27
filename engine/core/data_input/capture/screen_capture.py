"""CogniFlow 屏幕采集模块 - 支持全屏和区域屏幕采集。"""

from typing import Optional, Tuple, List
from pathlib import Path
import numpy as np
import time

try:
    import mss
    import pyautogui
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class ScreenCapture:
    """屏幕采集类，支持全屏采集、区域采集和多显示器。

    使用 MSS 或 PyAutoGUI 作为后端。
    """

    def __init__(
        self,
        fps: int = 30,
        capture_region: Optional[Tuple[int, int, int, int]] = None,
        monitor_index: int = 0,
    ):
        """初始化屏幕采集。

        Args:
            fps: 目标采集帧率。
            capture_region: 可选的采集区域 (x, y, width, height)。
            monitor_index: 多显示器设置下的显示器索引。
        """
        if not MSS_AVAILABLE:
            raise ImportError("需要安装 MSS 和 PyAutoGUI 进行屏幕采集。安装命令: pip install mss pyautogui")

        self.fps = fps
        self.capture_region = capture_region
        self.monitor_index = monitor_index
        self.frame_interval = 1.0 / fps

        self._sct = mss.mss()
        self._last_capture_time = 0.0

        # Get monitor info
        monitors = self._sct.monitors
        if monitor_index >= len(monitors):
            raise ValueError(f"显示器索引 {monitor_index} 超出范围。可用范围: {len(monitors)}")

        if capture_region is None:
            self._monitor = monitors[monitor_index]
        else:
            x, y, w, h = capture_region
            self._monitor = {"left": x, "top": y, "width": w, "height": h}

    def capture(self) -> np.ndarray:
        """采集单帧画面。

        Returns:
            RGB 图像 numpy 数组 (H, W, 3)。
        """
        # 帧率限制
        current_time = time.time()
        elapsed = current_time - self._last_capture_time
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)
        self._last_capture_time = time.time()

        # 采集屏幕
        screenshot = self._sct.grab(self._monitor)
        # 转换为 numpy 数组 (BGRA -> RGB)
        img = np.array(screenshot)
        img = img[:, :, :3]  # 移除 alpha 通道
        img = img[:, :, ::-1]  # BGR -> RGB
        return img

    def capture_to_file(self, filepath: Path) -> None:
        """采集一帧并保存到文件。

        Args:
            filepath: 输出文件路径。
        """
        img = self.capture()
        import cv2
        cv2.imwrite(str(filepath), img[:, :, ::-1])  # RGB -> BGR

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸（像素）。

        Returns:
            (宽度, 高度) 元组。
        """
        return self._monitor["width"], self._monitor["height"]

    def set_region(self, region: Tuple[int, int, int, int]) -> None:
        """设置采集区域。

        Args:
            region: (x, y, width, height) 元组。
        """
        x, y, w, h = region
        self.capture_region = region
        self._monitor = {"left": x, "top": y, "width": w, "height": h}

    def release(self) -> None:
        """释放资源。"""
        self._sct.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    @property
    def monitor_count(self) -> int:
        """获取显示器数量。"""
        return len(self._sct.monitors)

    @staticmethod
    def list_monitors() -> List[dict]:
        """列出所有显示器及其几何信息。

        Returns:
            显示器信息字典列表。
        """
        if not MSS_AVAILABLE:
            return []
        with mss.mss() as sct:
            return [
                {"index": i, **m}
                for i, m in enumerate(sct.monitors)
            ]


class FrameBuffer:
    """帧缓冲区 - 用于存储采集的帧的环形缓冲区。"""

    def __init__(self, max_size: int = 100):
        """初始化帧缓冲区。

        Args:
            max_size: 最大帧数。
        """
        self.max_size = max_size
        self._buffer = []
        self._timestamps = []

    def push(self, frame: np.ndarray, timestamp: Optional[float] = None) -> None:
        """添加帧到缓冲区。

        Args:
            frame: 图像数组。
            timestamp: 可选的时间戳。
        """
        if timestamp is None:
            timestamp = time.time()

        self._buffer.append(frame.copy())
        self._timestamps.append(timestamp)

        # 如果缓冲区满，移除最旧的帧
        while len(self._buffer) > self.max_size:
            self._buffer.pop(0)
            self._timestamps.pop(0)

    def get(self, index: int) -> Optional[np.ndarray]:
        """获取指定索引的帧 (0 = 最旧)。

        Args:
            index: 帧索引。

        Returns:
            帧数组，如果索引超出范围则返回 None。
        """
        if 0 <= index < len(self._buffer):
            return self._buffer[index]
        return None

    def get_latest(self, n: int = 1) -> List[np.ndarray]:
        """获取最近的 n 帧。

        Args:
            n: 要获取的帧数。

        Returns:
            最近帧的列表（最新帧在最后）。
        """
        n = min(n, len(self._buffer))
        return self._buffer[-n:]

    def clear(self) -> None:
        """清空缓冲区。"""
        self._buffer.clear()
        self._timestamps.clear()

    def __len__(self) -> int:
        return len(self._buffer)

    @property
    def timestamps(self) -> List[float]:
        """获取所有时间戳。"""
        return self._timestamps.copy()
