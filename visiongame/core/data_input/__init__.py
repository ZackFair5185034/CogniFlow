"""Data input module for VisionGame."""

from visiongame.core.data_input.capture import ScreenCapture, VideoReader, FrameBuffer
from visiongame.core.data_input.storage.dataset_manager import DatasetManager

__all__ = [
    "ScreenCapture",
    "VideoReader",
    "FrameBuffer",
    "DatasetManager",
]
