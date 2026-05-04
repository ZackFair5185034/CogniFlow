# -*- coding: utf-8 -*-
"""系统托盘管理模块。

管理 Windows 系统托盘图标、菜单和事件处理。
"""
import os
import sys
import threading
from typing import Optional

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pystray
except ImportError:
    pystray = None

from .browser import open_browser, DEFAULT_URL


class TrayManager:
    """系统托盘管理器。"""

    def __init__(self, app_name: str = "CogniFlow", on_quit_callback=None):
        """初始化托盘管理器。

        Args:
            app_name: 应用名称，用于窗口标题等
            on_quit_callback: 退出时执行的回调函数
        """
        self.app_name = app_name
        self._icon: Optional[pystray.Icon] = None
        self._stop_event = threading.Event()
        self._on_quit_callback = on_quit_callback

    def _create_icon_image(self) -> Image.Image:
        """创建托盘图标图像。

        Returns:
            PIL Image 对象
        """
        if Image is None:
            raise RuntimeError("Pillow 未安装，请运行: pip install Pillow")

        # 创建一个简单的图标图像（32x32 蓝色方形）
        icon_size = 32
        img = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))

        # 绘制一个简单的圆形图标背景
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)

        # 蓝色圆形背景
        draw.ellipse([2, 2, icon_size - 2, icon_size - 2], fill=(0, 180, 216, 255))

        # 白色字母 C
        draw.text((icon_size // 2 - 4, icon_size // 2 - 6), "C", fill=(255, 255, 255, 255))

        return img

    def _create_menu(self) -> pystray.Menu:
        """创建托盘右键菜单。

        Returns:
            pystray.Menu 对象
        """
        return pystray.Menu(
            pystray.MenuItem("打开浏览器", self._on_open_browser),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def _on_open_browser(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """打开浏览器菜单项回调。"""
        open_browser(DEFAULT_URL)

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """退出菜单项回调。"""
        self._stop_event.set()
        if self._icon:
            self._icon.stop()
        # 执行退出回调，实际关闭应用
        if self._on_quit_callback:
            self._on_quit_callback()

    def _on_double_click(self, icon: pystray.Icon) -> None:
        """双击托盘图标回调。"""
        open_browser(DEFAULT_URL)

    def start(self) -> None:
        """启动系统托盘。"""
        if pystray is None:
            print("[警告] pystray 未安装，托盘功能不可用")
            return

        if Image is None:
            print("[警告] Pillow 未安装，托盘功能不可用")
            return

        # 创建图标图像
        icon_image = self._create_icon_image()

        # 创建托盘图标
        self._icon = pystray.Icon(
            self.app_name,
            icon_image,
            self.app_name,
            self._create_menu(),
        )

        # 设置双击回调
        self._icon.on_double_click = self._on_double_click

        # 运行托盘事件循环（阻塞）
        print(f"[CogniFlow] 系统托盘已启动")
        self._icon.run()

    def stop(self) -> None:
        """停止系统托盘。"""
        if self._icon:
            self._icon.stop()


def run_tray() -> None:
    """运行系统托盘（阻塞主线程）。"""
    manager = TrayManager()
    manager.start()
