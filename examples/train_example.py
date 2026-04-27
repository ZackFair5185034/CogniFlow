"""CogniFlow 训练示例脚本。"""

import numpy as np
import torch
from engine.config import Config, RLConfig, VisionConfig
from engine.core.rl.algorithms.ppo import PPO
from engine.core.rl.environment.game_env import GameEnv, GameAdapter
from engine.core.rl.trainer import Trainer


class DummyGameAdapter(GameAdapter):
    """用于测试的虚拟游戏适配器。"""

    def __init__(self):
        super().__init__()
        self._frame = np.zeros((224, 224, 3), dtype=np.uint8)
        self._step_count = 0

    def get_state(self, frame):
        # 为 RL 智能体展平帧
        return frame.flatten().astype(np.float32)

    def get_action_space(self):
        from gymnasium import spaces
        return spaces.Box(low=-1, high=1, shape=(4,), dtype=np.float32)

    def map_action(self, action):
        return action

    def compute_reward(self, old_state, new_state, action):
        # 虚拟奖励 - 移动为正
        return np.random.randn()

    def reset(self):
        self._step_count = 0
        # 返回原始帧 - GameEnv 会通过 get_state 处理
        return self._frame.copy()

    def capture_frame(self):
        # 模拟从游戏获取新帧（动作后）
        self._step_count += 1
        return self._frame.copy()

    def is_done(self):
        return self._step_count > 10  # 演示用更短的回合


def main():
    """主训练函数。"""
    print("CogniFlow 训练示例")
    print("=" * 40)

    # 创建配置
    config = Config()
    config.rl = RLConfig(
        algorithm="ppo",
        gamma=0.99,
        learning_rate=3e-4,
        ppo_epochs=10,
        batch_size=64,
    )
    config.vision = VisionConfig(
        image_size=(224, 224),
        backbone="resnet18",
        feature_dim=512,
    )
    config.training.device = "cuda" if torch.cuda.is_available() else "cpu"
    config.training.total_timesteps = 5000
    config.training.log_freq = 1000

    print(f"使用设备: {config.training.device}")
    print(f"总时间步: {config.training.total_timesteps}")

    # 创建虚拟游戏适配器和环境
    adapter = DummyGameAdapter()
    env = GameEnv(adapter=adapter, frame_stack=1, max_episode_steps=200)

    # 获取观测和动作维度
    obs_dim = 224 * 224 * 3  # 简化
    action_dim = 4

    # 创建 PPO 智能体
    agent = PPO(
        observation_dim=obs_dim,
        action_dim=action_dim,
        lr=config.rl.learning_rate,
        gamma=config.rl.gamma,
        lam=config.rl.lam,
        clip_eps=config.rl.clip_eps,
        ent_coef=config.rl.ent_coef,
        vf_coef=config.rl.vf_coef,
        max_grad_norm=config.rl.max_grad_norm,
        ppo_epochs=config.rl.ppo_epochs,
        batch_size=config.rl.batch_size,
        device=config.training.device,
    )

    print(f"创建 PPO 智能体，obs_dim={obs_dim}, action_dim={action_dim}")

    # 创建训练器
    trainer = Trainer(
        agent=agent,
        env=env,
        config={
            "total_timesteps": config.training.total_timesteps,
            "log_freq": config.training.log_freq,
            "save_freq": config.training.save_freq,
            "eval_freq": config.training.eval_freq,
            "buffer_size": config.rl.buffer_size,
        },
        log_dir=config.training.log_dir,
        checkpoint_dir=config.training.checkpoint_dir,
        device=config.training.device,
    )

    # 开始训练
    print("\n开始训练...")
    print(f"配置: total_timesteps={config.training.total_timesteps}, buffer_size={config.rl.buffer_size}, batch_size={config.rl.batch_size}")
    import time
    start = time.time()
    trainer.train()
    elapsed = time.time() - start
    print(f"\n训练完成，耗时 {elapsed:.1f} 秒！")
    print(f"回合数: {trainer.episode_count}")
    print(f"最终时间步: {trainer.current_timestep}")

    # 保存最终模型
    agent.save("final_model.pt")
    print("\n训练完成！模型已保存到 final_model.pt")

    trainer.close()


if __name__ == "__main__":
    main()
