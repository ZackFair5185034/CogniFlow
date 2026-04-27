"""CogniFlow 环境封装模块 - 提供标准的 RL 环境接口。"""

from typing import Dict, Any, Optional, Tuple, List
from abc import ABC, abstractmethod
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
except ImportError:
    try:
        import gym
        from gym import spaces
        GYM_AVAILABLE = True
    except ImportError:
        GYM_AVAILABLE = False
        spaces = None


class GameAdapter(ABC):
    """游戏接口抽象适配器。

    该类定义了任何环境必须实现的接口，以便与 CogniFlow RL 框架配合使用。
    """

    @abstractmethod
    def get_state(self, frame: np.ndarray) -> np.ndarray:
        """从游戏画面中提取状态表示。

        Args:
            frame: 原始游戏画面 (H, W, C)。

        Returns:
            状态表示（观测）。
        """
        pass

    @abstractmethod
    def get_action_space(self) -> "spaces.Space":
        """获取动作空间。

        Returns:
            Gymnasium 动作空间。
        """
        pass

    @abstractmethod
    def map_action(self, action: np.ndarray) -> Any:
        """将 RL 动作映射到游戏输入。

        Args:
            action: 来自 RL 策略的动作。

        Returns:
            游戏输入事件。
        """
        pass

    @abstractmethod
    def compute_reward(
        self,
        old_state: np.ndarray,
        new_state: np.ndarray,
        action: np.ndarray,
    ) -> float:
        """计算状态转换的奖励。

        Args:
            old_state: 前一个状态。
            new_state: 当前状态。
            action: 执行的动作。

        Returns:
            奖励值。
        """
        pass

    def reset(self) -> np.ndarray:
        """重置游戏。

        Returns:
            初始观测。
        """
        return np.zeros((224, 224, 3), dtype=np.uint8)

    def is_done(self) -> bool:
        """检查回合是否结束。"""
        return False

    def get_info(self) -> Dict[str, Any]:
        """获取附加信息字典。"""
        return {}


class GameEnv(gym.Env if GYM_AVAILABLE else object):
    """游戏的 Gymnasium 风格环境封装。

    封装 GameAdapter 以提供标准的 RL 环境接口。
    """

    metadata = {"render_modes": ["rgb_array"]}

    def __init__(
        self,
        adapter: GameAdapter,
        frame_stack: int = 1,
        max_episode_steps: int = 10000,
    ):
        """初始化游戏环境。

        Args:
            adapter: GameAdapter 实例。
            frame_stack: 要堆叠的帧数。
            max_episode_steps: 每个回合的最大步数。
        """
        if not GYM_AVAILABLE:
            raise ImportError("需要安装 Gymnasium。安装命令: pip install gymnasium")

        super().__init__()
        self.adapter = adapter
        self.frame_stack = frame_stack
        self.max_episode_steps = max_episode_steps

        # 定义空间
        self.action_space = adapter.get_action_space()
        # 观测将由适配器设置
        self._empty_obs = np.zeros((224, 224, 3), dtype=np.uint8)
        self.observation_space = spaces.Box(
            low=0, high=255, shape=self._empty_obs.shape, dtype=np.uint8
        )

        # 回合跟踪
        self._current_step = 0
        self._frame_buffer: List[np.ndarray] = []

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """重置环境。

        Args:
            seed: 随机种子。
            options: 附加选项。

        Returns:
            (observation, info) 元组。
        """
        super().reset(seed=seed)
        self._current_step = 0
        self._frame_buffer.clear()

        frame = self.adapter.reset()
        obs = self.adapter.get_state(frame)

        # 帧堆叠
        for _ in range(self.frame_stack):
            self._frame_buffer.append(obs)

        return self._get_observation(), self.adapter.get_info()

    def step(
        self,
        action: np.ndarray,
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """执行动作。

        Args:
            action: 来自 RL 策略的动作。

        Returns:
            (observation, reward, terminated, truncated, info) 元组。
        """
        # 将动作映射到游戏输入
        game_action = self.adapter.map_action(action)

        # 在游戏中执行动作（假设游戏内部更新）
        # 在真实实现中，这会从游戏捕获下一帧
        # 对于虚拟适配器，我们通过获取新帧来模拟（这代表动作后的游戏状态）
        frame = self.adapter.capture_frame() if hasattr(self.adapter, 'capture_frame') else self.adapter.reset()
        new_obs = self.adapter.get_state(frame)

        # 更新帧缓冲区
        self._frame_buffer.append(new_obs)
        if len(self._frame_buffer) > self.frame_stack:
            self._frame_buffer.pop(0)

        # 计算奖励
        old_state = self._frame_buffer[-2] if len(self._frame_buffer) > 1 else new_obs
        reward = self.adapter.compute_reward(old_state, new_obs, action)

        # 检查完成条件
        self._current_step += 1
        terminated = self.adapter.is_done()
        truncated = self._current_step >= self.max_episode_steps

        return self._get_observation(), reward, terminated, truncated, self.adapter.get_info()

    def _get_observation(self) -> np.ndarray:
        """获取堆叠的观测。"""
        if len(self._frame_buffer) == 0:
            return self._empty_obs
        return np.concatenate(list(self._frame_buffer), axis=-1)

    def render(self, mode: str = "rgb_array"):
        """渲染环境。

        Args:
            mode: 渲染模式。
        """
        if mode == "rgb_array":
            return self._frame_buffer[-1] if self._frame_buffer else self._empty_obs

    def close(self):
        """清理资源。"""
        pass
