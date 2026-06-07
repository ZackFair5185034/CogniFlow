"""CogniFlow 控制器模块 - 整合输入模拟和控制逻辑。"""

from typing import Dict, Any, Optional, Callable, Tuple
from pathlib import Path
import numpy as np
import time

from engine.core.control.input_emulator.keyboard import KeyboardEmulator
from engine.core.control.input_emulator.mouse import MouseEmulator


class ActionMapper:
    """RL 动作到游戏输入的映射器。"""

    def __init__(self):
        """初始化动作映射器。"""
        # 动作空间定义
        self._keyboard_actions: Dict[str, Callable] = {}
        self._mouse_actions: Dict[str, Callable] = {}
        self._combo_actions: Dict[str, list] = {}

    def register_key_action(self, action_name: str, key: str) -> None:
        """注册键盘动作。

        Args:
            action_name: 动作名称。
            key: 键盘按键。
        """
        self._keyboard_actions[action_name] = key

    def register_mouse_action(self, action_name: str, position: Tuple[int, int]) -> None:
        """注册鼠标动作。

        Args:
            action_name: 动作名称。
            position: (x, y) 位置。
        """
        self._mouse_actions[action_name] = position

    def register_combo_action(self, action_name: str, keys: list) -> None:
        """注册组合动作。

        Args:
            action_name: 动作名称。
            keys: 按键列表。
        """
        self._combo_actions[action_name] = keys

    def get_action_type(self, action_name: str) -> str:
        """获取动作类型。

        Args:
            action_name: 动作名称。

        Returns:
            'keyboard'、'mouse' 或 'combo'。
        """
        if action_name in self._keyboard_actions:
            return "keyboard"
        elif action_name in self._mouse_actions:
            return "mouse"
        elif action_name in self._combo_actions:
            return "combo"
        return "unknown"

    def get_key(self, action_name: str) -> Optional[str]:
        """获取动作对应的键盘按键。"""
        return self._keyboard_actions.get(action_name)

    def get_mouse_position(self, action_name: str) -> Optional[Tuple[int, int]]:
        """获取动作对应的鼠标位置。"""
        return self._mouse_actions.get(action_name)

    def get_combo_keys(self, action_name: str) -> Optional[list]:
        """获取动作对应的组合按键。"""
        return self._combo_actions.get(action_name)


class GameController:
    """整合输入模拟的主游戏控制器。

    提供功能：
    - 动作执行
    - 安全检查
    - 紧急停止
    """

    def __init__(
        self,
        action_mapper: Optional[ActionMapper] = None,
        action_delay: float = 0.1,
        safety_check: bool = True,
        emergency_stop_key: str = "f12",
    ):
        """初始化游戏控制器。

        Args:
            action_mapper: ActionMapper 实例。
            action_delay: 动作间隔时间。
            safety_check: 启用安全检查。
            emergency_stop_key: 紧急停止键。
        """
        self.keyboard = KeyboardEmulator()
        self.mouse = MouseEmulator()
        self.action_mapper = action_mapper or ActionMapper()
        self.action_delay = action_delay
        self.safety_check = safety_check
        self.emergency_stop_key = emergency_stop_key

        self._is_running = False
        self._action_count = 0

    def execute_action(self, action: np.ndarray) -> bool:
        """执行来自 RL 策略的动作。

        Args:
            action: 来自 RL 策略的动作数组。

        Returns:
            动作是否成功执行。
        """
        if not self._is_running:
            return False

        # Convert action to action name
        # This is a simplified implementation
        action_idx = int(np.argmax(action)) if action.ndim > 0 else int(action)
        action_names = list(self.action_mapper._keyboard_actions.keys())

        if action_idx >= len(action_names):
            return False

        action_name = action_names[action_idx]
        action_type = self.action_mapper.get_action_type(action_name)

        try:
            if action_type == "keyboard":
                key = self.action_mapper.get_key(action_name)
                if key:
                    self.keyboard.press(key)
            elif action_type == "mouse":
                pos = self.action_mapper.get_mouse_position(action_name)
                if pos:
                    self.mouse.click(pos[0], pos[1])
            elif action_type == "combo":
                keys = self.action_mapper.get_combo_keys(action_name)
                if keys:
                    self.keyboard.hotkey(*keys)

            self._action_count += 1
            time.sleep(self.action_delay)
            return True

        except Exception as e:
            print(f"执行动作 {action_name} 时出错: {e}")
            return False

    def execute_named_action(self, action_name: str) -> bool:
        """直接执行命名动作。

        Args:
            action_name: 动作名称。

        Returns:
            动作是否成功执行。
        """
        if not self._is_running:
            return False

        action_type = self.action_mapper.get_action_type(action_name)

        try:
            if action_type == "keyboard":
                key = self.action_mapper.get_key(action_name)
                if key:
                    self.keyboard.press(key)
            elif action_type == "mouse":
                pos = self.action_mapper.get_mouse_position(action_name)
                if pos:
                    self.mouse.click(pos[0], pos[1])
            elif action_type == "combo":
                keys = self.action_mapper.get_combo_keys(action_name)
                if keys:
                    self.keyboard.hotkey(*keys)
            else:
                return False

            self._action_count += 1
            time.sleep(self.action_delay)
            return True

        except Exception as e:
            print(f"执行动作 {action_name} 时出错: {e}")
            return False

    def start(self) -> None:
        """启动控制器。"""
        self._is_running = True
        print("游戏控制器已启动")

    def stop(self) -> None:
        """停止控制器。"""
        self._is_running = False
        print("游戏控制器已停止")

    def emergency_stop(self) -> None:
        """紧急停止 - 释放所有按键并停止。"""
        try:
            self.keyboard.key_up("all")
        except:
            pass
        self._is_running = False
        print("紧急停止")

    @property
    def is_running(self) -> bool:
        """检查控制器是否正在运行。"""
        return self._is_running

    @property
    def action_count(self) -> int:
        """获取总动作计数。"""
        return self._action_count

    def reset_action_count(self) -> None:
        """重置动作计数器。"""
        self._action_count = 0
