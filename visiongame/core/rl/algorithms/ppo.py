"""PPO (Proximal Policy Optimization) 近端策略优化算法实现。"""

from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal


@dataclass
class PPOBuffer:
    """PPO 经验回放缓冲区。"""
    observations: List[torch.Tensor] = None
    actions: List[torch.Tensor] = None
    rewards: List[float] = None
    dones: List[bool] = None
    log_probs: List[torch.Tensor] = None
    values: List[torch.Tensor] = None

    def __post_init__(self):
        if self.observations is None:
            self.observations = []
        if self.actions is None:
            self.actions = []
        if self.rewards is None:
            self.rewards = []
        if self.dones is None:
            self.dones = []
        if self.log_probs is None:
            self.log_probs = []
        if self.values is None:
            self.values = []

    def __len__(self) -> int:
        return len(self.rewards)

    def clear(self):
        """清空缓冲区。"""
        self.observations.clear()
        self.actions.clear()
        self.rewards.clear()
        self.dones.clear()
        self.log_probs.clear()
        self.values.clear()


class PPOActorCritic(nn.Module):
    """PPO Actor-Critic 智能体。"""

    def __init__(
        self,
        observation_dim: int,
        action_dim: int,
        hidden_dim: int = 256,
        log_std_init: float = -0.5,
    ):
        """初始化 PPO 智能体。

        Args:
            observation_dim: 观测维度。
            action_dim: 动作维度。
            hidden_dim: 隐藏层维度。
            log_std_init: 初始 log 标准差。
        """
        super().__init__()

        self.observation_dim = observation_dim
        self.action_dim = action_dim

        # Actor 网络
        self.actor = nn.Sequential(
            nn.Linear(observation_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.log_std = nn.Parameter(torch.ones(action_dim) * log_std_init)

        # Critic 网络
        self.critic = nn.Sequential(
            nn.Linear(observation_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, observation: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """获取动作分布和价值。

        Args:
            observation: 观测张量 (obs_dim,) 或 (batch, obs_dim)。

        Returns:
            (action_mean, value) 元组。
        """
        # 确保输入是2D
        if observation.ndim == 1:
            observation = observation.unsqueeze(0)
        hidden = self.actor(observation)
        action_mean = hidden[:, :self.action_dim]
        value = self.critic(observation)
        return action_mean, value

    def get_action(
        self,
        observation: torch.Tensor,
        deterministic: bool = False,
    ) -> Tuple[np.ndarray, float, torch.Tensor]:
        """从策略中采样动作。

        Args:
            observation: 观测张量。
            deterministic: 如果为 True，返回均值动作。

        Returns:
            (action, value, log_prob) 元组。
        """
        original_1d = observation.ndim == 1
        action_mean, value = self.forward(observation)

        if deterministic:
            action = action_mean
            log_prob = None
        else:
            std = self.log_std.exp()
            dist = Normal(action_mean, std)
            action = dist.sample()
            log_prob = dist.log_prob(action).sum(dim=-1)

        # 如果输入是1D则压缩
        if original_1d:
            action = action.squeeze(0)
            if log_prob is not None:
                log_prob = log_prob.squeeze(0)

        return action.cpu().numpy(), value.item(), log_prob

    def evaluate_actions(
        self,
        observations: torch.Tensor,
        actions: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """评估当前策略下的动作。

        Args:
            observations: 观测批次。
            actions: 动作批次。

        Returns:
            (log_probs, values) 元组。
        """
        action_mean, values = self.forward(observations)
        std = self.log_std.exp()
        dist = Normal(action_mean, std)
        log_probs = dist.log_prob(actions).sum(dim=-1)
        return log_probs, values.squeeze(-1)


class PPO:
    """PPO (近端策略优化) 算法。

    论文: https://arxiv.org/abs/1707.06347
    """

    def __init__(
        self,
        observation_dim: int,
        action_dim: int,
        lr: float = 3e-4,
        gamma: float = 0.99,
        lam: float = 0.95,
        clip_eps: float = 0.2,
        ent_coef: float = 0.01,
        vf_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        ppo_epochs: int = 10,
        batch_size: int = 64,
        device: str = "cuda",
    ):
        """初始化 PPO。

        Args:
            observation_dim: 观测维度。
            action_dim: 动作维度。
            lr: 学习率。
            gamma: 折扣因子。
            lam: GAE lambda 参数。
            clip_eps: PPO 裁剪 epsilon。
            ent_coef: 熵系数。
            vf_coef: 价值函数系数。
            max_grad_norm: 最大梯度范数（裁剪用）。
            ppo_epochs: 每次更新的 epoch 数。
            batch_size: 训练批次大小。
            device: 使用的设备。
        """
        self.gamma = gamma
        self.lam = lam
        self.clip_eps = clip_eps
        self.ent_coef = ent_coef
        self.vf_coef = vf_coef
        self.max_grad_norm = max_grad_norm
        self.ppo_epochs = ppo_epochs
        self.batch_size = batch_size

        self.device = torch.device(device)

        # 创建智能体
        self.agent = PPOActorCritic(observation_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.agent.parameters(), lr=lr)

        # 缓冲区
        self.buffer = PPOBuffer()

        # 训练统计
        self.training_steps = 0

    def select_action(
        self,
        observation: np.ndarray,
        deterministic: bool = False,
    ) -> Tuple[np.ndarray, float]:
        """选择环境交互的动作。

        Args:
            observation: 观测数组。
            deterministic: 如果为 True，返回均值动作。

        Returns:
            (action, value estimate) 元组。
        """
        with torch.no_grad():
            obs_tensor = torch.FloatTensor(observation).to(self.device)
            action, value, _ = self.agent.get_action(obs_tensor, deterministic)
            return action, value

    def store_transition(
        self,
        observation: torch.Tensor,
        action: torch.Tensor,
        reward: float,
        done: bool,
        log_prob: torch.Tensor,
        value: float,
    ):
        """将转换存储到缓冲区。

        Args:
            observation: 观测张量。
            action: 动作张量。
            reward: 奖励值。
            done: 完成标志。
            log_prob: 动作的对数概率。
            value: 价值估计。
        """
        self.buffer.observations.append(observation.cpu())
        self.buffer.actions.append(action.cpu())
        self.buffer.rewards.append(reward)
        self.buffer.dones.append(done)
        self.buffer.log_probs.append(log_prob.cpu())
        self.buffer.values.append(torch.tensor(value))

    def compute_gae(
        self,
        rewards: List[float],
        values: List[float],
        dones: List[bool],
        last_value: float,
    ) -> Tuple[List[float], List[float]]:
        """计算广义优势估计 (GAE)。

        Args:
            rewards: 奖励列表。
            values: 价值估计列表。
            dones: 完成标志列表。
            last_value: 最终价值估计。

        Returns:
            (advantages, returns) 元组。
        """
        advantages = []
        returns = []
        gae = 0

        values = values + [last_value]

        for t in reversed(range(len(rewards))):
            delta = rewards[t] + self.gamma * values[t + 1] * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.lam * (1 - dones[t]) * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + values[t])

        return advantages, returns

    def update(self) -> Dict[str, float]:
        """使用 PPO 算法更新策略。

        Returns:
            训练统计信息字典。
        """
        if len(self.buffer) == 0:
            return {}

        # 将缓冲区转换为张量
        observations = torch.stack(self.buffer.observations).to(self.device)
        actions = torch.stack(self.buffer.actions).to(self.device)
        old_log_probs = torch.stack(self.buffer.log_probs).to(self.device)
        old_values = torch.stack(self.buffer.values).to(self.device)

        # 计算优势估计
        last_value = old_values[-1].item()
        advantages, returns = self.compute_gae(
            self.buffer.rewards,
            old_values.tolist(),
            self.buffer.dones,
            last_value,
        )
        advantages = torch.FloatTensor(advantages).to(self.device)
        returns = torch.FloatTensor(returns).to(self.device)

        # 优势归一化
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO 更新
        stats = {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        for _ in range(self.ppo_epochs):
            # 打乱索引
            indices = torch.randperm(len(observations))

            for start in range(0, len(observations), self.batch_size):
                end = start + self.batch_size
                batch_indices = indices[start:end]

                batch_obs = observations[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_advantages = advantages[batch_indices]
                batch_returns = returns[batch_indices]

                # 评估动作
                log_probs, values = self.agent.evaluate_actions(batch_obs, batch_actions)

                # 策略损失 (PPO 裁剪)
                ratio = (log_probs - batch_old_log_probs).exp()
                surr1 = ratio * batch_advantages
                surr2 = ratio.clamp(1 - self.clip_eps, 1 + self.clip_eps) * batch_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # 价值损失
                value_loss = nn.functional.mse_loss(values, batch_returns)

                # 熵奖励
                entropy = 0.5 * (1 + np.log(2 * np.pi) + 2 * self.agent.log_std).sum()

                # 总损失
                loss = policy_loss + self.vf_coef * value_loss - self.ent_coef * entropy

                # 优化
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.agent.parameters(), self.max_grad_norm)
                self.optimizer.step()

                # 累积统计
                stats["loss"] += loss.item()
                stats["policy_loss"] += policy_loss.item()
                stats["value_loss"] += value_loss.item()
                stats["entropy"] += entropy.item()

        # 平均统计
        num_updates = self.ppo_epochs * (len(observations) // self.batch_size + 1)
        for key in stats:
            stats[key] /= num_updates

        self.training_steps += 1
        self.buffer.clear()

        return stats

    def save(self, path: str):
        """保存模型检查点。"""
        torch.save({
            "agent_state_dict": self.agent.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "training_steps": self.training_steps,
        }, path)

    def load(self, path: str):
        """加载模型检查点。"""
        checkpoint = torch.load(path, map_location=self.device)
        self.agent.load_state_dict(checkpoint["agent_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.training_steps = checkpoint["training_steps"]
