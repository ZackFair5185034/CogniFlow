"""VisionGame 鼠标模拟器模块 - 使用 PyAutoGUI 模拟鼠标输入。"""

from typing import Tuple, Optional
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


class MouseEmulator:
    """使用 PyAutoGUI 的鼠标输入模拟器。

    提供功能：
    - 鼠标移动
    - 点击（左键、右键、中键）
    - 拖拽操作
    - 可配置的时间控制
    """

    def __init__(
        self,
        move_duration: float = 0.1,
        click_duration: float = 0.05,
        scroll_delay: float = 0.1,
    ):
        """初始化鼠标模拟器。

        Args:
            move_duration: 鼠标移动时间（秒）。
            click_duration: 点击保持时间（秒）。
            scroll_delay: 滚动后的延迟。
        """
        if not PYAUtoGUI_AVAILABLE:
            raise ImportError("需要安装 PyAutoGUI。安装命令: pip install pyautogui")

        self.move_duration = move_duration
        self.click_duration = click_duration
        self.scroll_delay = scroll_delay

        # 禁用安全保护以获得更平滑的操作
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

    def move_to(self, x: int, y: int, duration: Optional[float] = None) -> None:
        """移动鼠标到绝对位置。

        Args:
            x: X 坐标。
            y: Y 坐标。
            duration: 移动时间（None = 使用默认值）。
        """
        duration = duration if duration is not None else self.move_duration
        pyautogui.moveTo(x, y, duration=duration)

    def move_rel(self, x: int, y: int, duration: Optional[float] = None) -> None:
        """相对于当前位置移动鼠标。

        Args:
            x: X 偏移量。
            y: Y 偏移量。
            duration: 移动时间。
        """
        duration = duration if duration is not None else self.move_duration
        pyautogui.move(x, y, duration=duration)

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
    ) -> None:
        """在指定位置点击。

        Args:
            x: X 坐标（None = 当前位置）。
            y: Y 坐标（None = 当前位置）。
            button: 鼠标按钮（'left', 'right', 'middle'）。
            clicks: 点击次数。
        """
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)
        time.sleep(self.click_duration)

    def double_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
    ) -> None:
        """在指定位置双击。

        Args:
            x: X 坐标。
            y: Y 坐标。
            button: 鼠标按钮。
        """
        self.click(x, y, button=button, clicks=2)

    def right_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> None:
        """在指定位置右键点击。

        Args:
            x: X 坐标。
            y: Y 坐标。
        """
        self.click(x, y, button="right")

    def middle_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> None:
        """在指定位置中键点击。

        Args:
            x: X 坐标。
            y: Y 坐标。
        """
        self.click(x, y, button="middle")

    def down(self, button: str = "left") -> None:
        """按下鼠标按钮。

        Args:
            button: 鼠标按钮。
        """
        pyautogui.mouseDown(button=button)
        time.sleep(self.click_duration)

    def up(self, button: str = "left") -> None:
        """释放鼠标按钮。

        Args:
            button: 鼠标按钮。
        """
        pyautogui.mouseUp(button=button)
        time.sleep(self.click_duration)

    def scroll(self, x: int = 0, y: int = 0) -> None:
        """滚动鼠标滚轮。

        Args:
            x: 水平滚动量。
            y: 垂直滚动量（正数 = 向上，负数 = 向下）。
        """
        pyautogui.scroll(y, x=x)
        time.sleep(self.scroll_delay)

    def drag_to(
        self,
        x: int,
        y: int,
        button: str = "left",
        duration: Optional[float] = None,
    ) -> None:
        """拖拽鼠标到指定位置。

        Args:
            x: 目标 X 坐标。
            y: 目标 Y 坐标。
            button: 鼠标按钮。
            duration: 拖拽时间。
        """
        duration = duration if duration is not None else self.move_duration
        pyautogui.dragTo(x, y, duration=duration, button=button)

    def drag_rel(
        self,
        x: int,
        y: int,
        button: str = "left",
        duration: Optional[float] = None,
    ) -> None:
        """相对于当前位置拖拽鼠标。

        Args:
            x: X 偏移量。
            y: Y 偏移量。
            button: 鼠标按钮。
            duration: 拖拽时间。
        """
        duration = duration if duration is not None else self.move_duration
        pyautogui.drag(x, y, duration=duration, button=button)

    def get_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置。

        Returns:
            (x, y) 元组。
        """
        return pyautogui.position()
