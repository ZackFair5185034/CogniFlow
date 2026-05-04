# -*- coding: utf-8 -*-
"""CogniFlow 系统托盘模块。

提供 Windows 系统托盘功能：
- 托盘图标显示
- 右键菜单（打开浏览器、退出）
- 双击托盘打开浏览器
"""

from .tray_manager import TrayManager
from .browser import open_browser

__all__ = ["TrayManager", "open_browser"]
