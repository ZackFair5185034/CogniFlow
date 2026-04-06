"""Capture module for data input."""

from visiongame.core.data_input.capture.screen_capture import ScreenCapture, FrameBuffer
from visiongame.core.data_input.capture.video_reader import VideoReader

__all__ = [
    "ScreenCapture",
    "FrameBuffer",
    "VideoReader",
]
