# -*- coding: utf-8 -*-
"""浏览器打开模块。

提供跨平台浏览器打开功能。
"""
import webbrowser
import threading

# CogniFlow WebUI 默认地址
DEFAULT_URL = "http://localhost:8000"


def open_browser(url: str = DEFAULT_URL) -> bool:
    """打开默认浏览器访问指定 URL。

    Args:
        url: 要打开的 URL 地址

    Returns:
        是否成功打开浏览器
    """
    try:
        # 在新线程中打开浏览器，避免阻塞主线程
        browser_thread = threading.Thread(target=_open_browser_thread, args=(url,))
        browser_thread.daemon = True
        browser_thread.start()
        return True
    except Exception:
        return False


def _open_browser_thread(url: str) -> None:
    """在独立线程中打开浏览器。"""
    try:
        webbrowser.open(url)
    except Exception:
        pass
