"""VisionGame 训练器模块 - RL 智能体的训练循环。"""

from typing import Dict, Any, Optional
from pathlib import Path
import time
import torch
from torch.utils.tensorboard import SummaryWriter

try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False


class Trainer:
    """RL 智能体训练器主类。"""

    def __init__(
        self,
        agent,
        env,
        config=None,
        log_dir: Path = Path("./logs"),
        checkpoint_dir: Path = Path("./checkpoints"),
        device: str = "cuda",
    ):
        """初始化训练器。

        Args:
            agent: 要训练的 RL 智能体。
            env: 训练环境。
            config: 训练配置。
            log_dir: 日志目录。
            checkpoint_dir: 检查点保存目录。
            device: 训练设备。
        """
        self.agent = agent
        self.env = env
        self.config = config or {}
        self.log_dir = Path(log_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        # 创建目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # TensorBoard 写入器
        self.writer = None
        if TENSORBOARD_AVAILABLE:
            self.writer = SummaryWriter(str(self.log_dir / f"run_{int(time.time())}"))

        # 训练状态
        self.total_timesteps = self.config.get("total_timesteps", 1_000_000)
        self.eval_freq = self.config.get("eval_freq", 10000)
        self.save_freq = self.config.get("save_freq", 50000)
        self.log_freq = self.config.get("log_freq", 1000)

        self.current_timestep = 0
        self.episode_count = 0
        self.training_start_time = time.time()

    def train(self) -> Dict[str, Any]:
        """运行训练循环。

        Returns:
            最终训练统计信息。
        """
        episode_rewards = []
        episode_lengths = []
        episode_reward = 0
        episode_length = 0

        obs, info = self.env.reset()
        stats = {}

        while self.current_timestep < self.total_timesteps:
            # Select action
            action, value = self.agent.select_action(obs)

            # Step environment
            next_obs, reward, terminated, truncated, info = self.env.step(action)

            # Store transition
            self.agent.store_transition(
                observation=torch.FloatTensor(obs),
                action=torch.FloatTensor(action),
                reward=reward,
                done=terminated or truncated,
                log_prob=torch.FloatTensor([0.0]),  # Placeholder
                value=value,
            )

            episode_reward += reward
            episode_length += 1
            obs = next_obs

            # Handle episode end
            if terminated or truncated:
                episode_rewards.append(episode_reward)
                episode_lengths.append(episode_length)
                self.episode_count += 1

                obs, info = self.env.reset()
                episode_reward = 0
                episode_length = 0

            # Update agent
            if len(self.agent.buffer) >= self.config.get("buffer_size", 64):
                stats = self.agent.update()

            # Logging
            if self.current_timestep % self.log_freq == 0:
                self._log_stats(stats, episode_rewards, episode_lengths)
                episode_rewards.clear()
                episode_lengths.clear()

            # Checkpointing
            if self.current_timestep % self.save_freq == 0 and self.current_timestep > 0:
                self.save_checkpoint()

            self.current_timestep += 1

        return stats

    def _log_stats(
        self,
        stats: Dict[str, float],
        episode_rewards: list,
        episode_lengths: list,
    ):
        """将统计信息记录到 TensorBoard。"""
        if self.writer is None:
            return

        # 记录 RL 统计
        for key, value in stats.items():
            self.writer.add_scalar(f"rl/{key}", value, self.current_timestep)

        # 记录回合统计
        if episode_rewards:
            mean_reward = sum(episode_rewards) / len(episode_rewards)
            mean_length = sum(episode_lengths) / len(episode_lengths) if episode_lengths else 0
            self.writer.add_scalar("episode/mean_reward", mean_reward, self.current_timestep)
            self.writer.add_scalar("episode/mean_length", mean_length, self.current_timestep)

        # 记录 FPS
        elapsed = time.time() - self.training_start_time
        fps = self.current_timestep / elapsed if elapsed > 0 else 0
        self.writer.add_scalar("training/fps", fps, self.current_timestep)

    def save_checkpoint(self, suffix: str = ""):
        """保存训练检查点。"""
        path = self.checkpoint_dir / f"checkpoint_{self.current_timestep}{suffix}.pt"
        self.agent.save(str(path))
        print(f"检查点已保存到 {path}")

    def load_checkpoint(self, path: str):
        """加载训练检查点。"""
        self.agent.load(path)
        print(f"检查点已从 {path} 加载")

    def evaluate(self, num_episodes: int = 10) -> Dict[str, float]:
        """评估智能体。

        Args:
            num_episodes: 运行的回合数。

        Returns:
            评估统计信息。
        """
        eval_rewards = []
        eval_lengths = []

        for _ in range(num_episodes):
            obs, info = self.env.reset()
            episode_reward = 0
            episode_length = 0
            done = False

            while not done:
                action, _ = self.agent.select_action(obs, deterministic=True)
                obs, reward, terminated, truncated, info = self.env.step(action)
                episode_reward += reward
                episode_length += 1
                done = terminated or truncated

            eval_rewards.append(episode_reward)
            eval_lengths.append(episode_length)

        return {
            "mean_reward": sum(eval_rewards) / len(eval_rewards),
            "mean_length": sum(eval_lengths) / len(eval_lengths),
        }

    def close(self):
        """清理资源。"""
        if self.writer is not None:
            self.writer.close()
