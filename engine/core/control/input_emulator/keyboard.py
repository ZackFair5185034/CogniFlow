"""CogniFlow 键盘模拟器模块 - 使用 PyAutoGUI 模拟键盘输入。"""

from typing import List, Optional
import time

try:
    import pyautogui
    PYAUtoGUI_AVAILABLE = True
except ImportError:
    try:
        import pyautogui
        PYAUtoGUI_AVAILABLE = True
    except ImportError:
        PYAUtoGUI_AVAILABLE = False


class KeyboardEmulator:
    """使用 PyAutoGUI 的键盘输入模拟器。

    提供功能：
    - 按键按下和释放
    - 组合键
    - 可配置的时间控制
    """

    def __init__(
        self,
        key_press_duration: float = 0.05,
        key_release_delay: float = 0.01,
        safety_delay: float = 0.5,
    ):
        """初始化键盘模拟器。

        Args:
            key_press_duration: 按键保持时间（秒）。
            key_release_delay: 按键释放和下一个操作之间的延迟。
            safety_delay: 初始延迟以防止意外操作。
        """
        if not PYAUtoGUI_AVAILABLE:
            raise ImportError("需要安装 PyAutoGUI。安装命令: pip install pyautogui")

        self.key_press_duration = key_press_duration
        self.key_release_delay = key_release_delay
        self.safety_delay = safety_delay

        # 禁用安全保护以获得更平滑的操作
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

    def key_down(self, key: str) -> None:
        """按下并保持按键。

        Args:
            key: 按键名称（例如 'a', 'space', 'enter'）。
        """
        pyautogui.keyDown(key)
        time.sleep(self.key_press_duration)

    def key_up(self, key: str) -> None:
        """释放按键。

        Args:
            key: 按键名称。
        """
        pyautogui.keyUp(key)
        time.sleep(self.key_release_delay)

    def press(self, key: str) -> None:
        """按下并释放按键。

        Args:
            key: 按键名称。
        """
        self.key_down(key)
        self.key_up(key)

    def type(self, text: str, interval: float = 0.05) -> None:
        """输入字符串文本。

        Args:
            text: 要输入的文本。
            interval: 按键之间的间隔。
        """
        pyautogui.write(text, interval=interval)

    def hotkey(self, *keys: str) -> None:
        """按下组合键（例如 Ctrl+C）。

        Args:
            keys: 同时按下的按键列表。
        """
        # 按下所有按键
        for key in keys:
            pyautogui.keyDown(key)
        time.sleep(self.key_press_duration)
        # 反向顺序释放
        for key in reversed(keys):
            pyautogui.keyUp(key)
        time.sleep(self.key_release_delay)

    def combo(self, keys: List[str]) -> None:
        """执行一系列按键操作。

        Args:
            keys: 按顺序按下的按键列表。
        """
        for key in keys:
            self.press(key)

    def wait(self, duration: float) -> None:
        """等待指定时间。

        Args:
            duration: 等待时间（秒）。
        """
        time.sleep(duration)
