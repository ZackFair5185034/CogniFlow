"""SAC (Soft Actor-Critic) 软Actor-Critic算法实现。"""

from typing import Tuple, Optional, Dict, Any
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal


class SACActor(nn.Module):
    """SAC Actor 网络。"""

    def __init__(self, observation_dim: int, action_dim: int, hidden_dim: int = 256):
        """初始化 SAC Actor。

        Args:
            observation_dim: 观测维度。
            action_dim: 动作维度。
            hidden_dim: 隐藏层维度。
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(observation_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.mean = nn.Linear(hidden_dim, action_dim)
        self.log_std = nn.Linear(hidden_dim, action_dim)

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """获取动作分布。"""
        h = self.net(obs)
        mean = self.mean(h)
        log_std = self.log_std(h).clamp(-20, 2)
        return mean, log_std

    def sample(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """使用重参数化技巧采样动作。"""
        mean, log_std = self.forward(obs)
        std = log_std.exp()
        normal = Normal(mean, std)
        x_t = normal.rsample()
        action = torch.tanh(x_t)
        # 计算 tanh 修正的对数概率
        log_prob = (normal.log_prob(x_t) - torch.log(1 - action.pow(2) + 1e-6)).sum(-1, keepdim=True)
        return action, log_prob


class SACCritic(nn.Module):
    """SAC Critic 网络 (Q函数)。"""

    def __init__(self, observation_dim: int, action_dim: int, hidden_dim: int = 256):
        """初始化 SAC Critic。

        Args:
            observation_dim: 观测维度。
            action_dim: 动作维度。
            hidden_dim: 隐藏层维度。
        """
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(observation_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, obs: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        """计算状态-动作对的 Q 值。"""
        return self.net(torch.cat([obs, action], dim=-1))


class SAC:
    """SAC (软Actor-Critic) 算法。

    论文: https://arxiv.org/abs/1801.01290
    """

    def __init__(
        self,
        observation_dim: int,
        action_dim: int,
        lr: float = 3e-4,
        gamma: float = 0.99,
        tau: float = 0.005,
        alpha: float = 0.2,
        device: str = "cuda",
    ):
        """初始化 SAC。

        Args:
            observation_dim: 观测维度。
            action_dim: 动作维度。
            lr: 学习率。
            gamma: 折扣因子。
            tau: 软更新系数。
            alpha: 熵温度参数。
            device: 使用的设备。
        """
        self.gamma = gamma
        self.tau = tau
        self.alpha = alpha
        self.device = torch.device(device)

        # Actor
        self.actor = SACActor(observation_dim, action_dim).to(self.device)
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)

        # Critics (双 Q 网络)
        self.critic1 = SACCritic(observation_dim, action_dim).to(self.device)
        self.critic2 = SACCritic(observation_dim, action_dim).to(self.device)
        self.critic1_optimizer = optim.Adam(self.critic1.parameters(), lr=lr)
        self.critic2_optimizer = optim.Adam(self.critic2.parameters(), lr=lr)

        # 目标 Critics
        self.target_critic1 = SACCritic(observation_dim, action_dim).to(self.device)
        self.target_critic2 = SACCritic(observation_dim, action_dim).to(self.device)
        self.target_critic1.load_state_dict(self.critic1.state_dict())
        self.target_critic2.load_state_dict(self.critic2.state_dict())

        # 缓冲区
        self.buffer = []
        self.buffer_size = 100000
        self.training_steps = 0

    def select_action(
        self,
        observation: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        """选择环境交互的动作。"""
        with torch.no_grad():
            obs_tensor = torch.FloatTensor(observation).to(self.device).unsqueeze(0)
            if deterministic:
                mean, _ = self.actor(obs_tensor)
                return torch.tanh(mean).cpu().numpy()[0]
            else:
                action, _ = self.actor.sample(obs_tensor)
                return action.cpu().numpy()[0]

    def store_transition(
        self,
        observation: np.ndarray,
        action: np.ndarray,
        reward: float,
        done: bool,
        next_observation: np.ndarray,
    ):
        """将转换存储到回放缓冲区。"""
        self.buffer.append((observation, action, reward, done, next_observation))
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)

    def update(self, batch_size: int = 256) -> Dict[str, float]:
        """使用批次数据更新网络。"""
        if len(self.buffer) < batch_size:
            return {}

        # 采样批次
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]

        observations = torch.FloatTensor(np.array([b[0] for b in batch])).to(self.device)
        actions = torch.FloatTensor(np.array([b[1] for b in batch])).to(self.device)
        rewards = torch.FloatTensor(np.array([b[2] for b in batch])).to(self.device)
        dones = torch.FloatTensor(np.array([b[3] for b in batch])).to(self.device)
        next_observations = torch.FloatTensor(np.array([b[4] for b in batch])).to(self.device)

        # 计算目标 Q
        with torch.no_grad():
            next_actions, next_log_probs = self.actor.sample(next_observations)
            target_q1 = self.target_critic1(next_observations, next_actions)
            target_q2 = self.target_critic2(next_observations, next_actions)
            target_q = torch.min(target_q1, target_q2)
            target_q = rewards.unsqueeze(1) + self.gamma * (1 - dones.unsqueeze(1)) * (target_q - self.alpha * next_log_probs)

        # 更新 Critics
        current_q1 = self.critic1(observations, actions)
        current_q2 = self.critic2(observations, actions)
        critic1_loss = nn.functional.mse_loss(current_q1, target_q)
        critic2_loss = nn.functional.mse_loss(current_q2, target_q)

        self.critic1_optimizer.zero_grad()
        critic1_loss.backward()
        self.critic1_optimizer.step()

        self.critic2_optimizer.zero_grad()
        critic2_loss.backward()
        self.critic2_optimizer.step()

        # 更新 Actor
        new_actions, log_probs = self.actor.sample(observations)
        q1_new = self.critic1(observations, new_actions)
        q2_new = self.critic2(observations, new_actions)
        q_new = torch.min(q1_new, q2_new)
        actor_loss = (self.alpha * log_probs - q_new).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        # 软更新目标网络
        for target, source in [
            (self.target_critic1, self.critic1),
            (self.target_critic2, self.critic2),
        ]:
            for target_param, source_param in zip(target.parameters(), source.parameters()):
                target_param.data.copy_(
                    self.tau * source_param.data + (1 - self.tau) * target_param.data
                )

        self.training_steps += 1

        return {
            "actor_loss": actor_loss.item(),
            "critic1_loss": critic1_loss.item(),
            "critic2_loss": critic2_loss.item(),
        }

    def save(self, path: str):
        """保存模型检查点。"""
        torch.save({
            "actor_state_dict": self.actor.state_dict(),
            "critic1_state_dict": self.critic1.state_dict(),
            "critic2_state_dict": self.critic2.state_dict(),
            "target_critic1_state_dict": self.target_critic1.state_dict(),
            "target_critic2_state_dict": self.target_critic2.state_dict(),
            "actor_optimizer_state_dict": self.actor_optimizer.state_dict(),
            "critic1_optimizer_state_dict": self.critic1_optimizer.state_dict(),
            "critic2_optimizer_state_dict": self.critic2_optimizer.state_dict(),
            "training_steps": self.training_steps,
        }, path)

    def load(self, path: str):
        """加载模型检查点。"""
        checkpoint = torch.load(path, map_location=self.device)
        self.actor.load_state_dict(checkpoint["actor_state_dict"])
        self.critic1.load_state_dict(checkpoint["critic1_state_dict"])
        self.critic2.load_state_dict(checkpoint["critic2_state_dict"])
        self.target_critic1.load_state_dict(checkpoint["target_critic1_state_dict"])
        self.target_critic2.load_state_dict(checkpoint["target_critic2_state_dict"])
        self.actor_optimizer.load_state_dict(checkpoint["actor_optimizer_state_dict"])
        self.critic1_optimizer.load_state_dict(checkpoint["critic1_optimizer_state_dict"])
        self.critic2_optimizer.load_state_dict(checkpoint["critic2_optimizer_state_dict"])
        self.training_steps = checkpoint["training_steps"]
