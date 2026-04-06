"""VisionGame 推理示例脚本。"""

import numpy as np
import torch
from pathlib import Path
from visiongame.config import Config
from visiongame.core.rl.algorithms.ppo import PPO
from visiongame.core.control.controller import GameController, ActionMapper


def main():
    """主推理函数。"""
    print("VisionGame 推理示例")
    print("=" * 40)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    # 配置
    action_dim = 4
    obs_dim = 224 * 224 * 3  # 简化

    # 创建智能体
    agent = PPO(
        observation_dim=obs_dim,
        action_dim=action_dim,
        device=device,
    )

    # 尝试加载模型（如果存在）
    model_path = Path("final_model.pt")
    if model_path.exists():
        agent.load(str(model_path))
        print(f"从 {model_path} 加载模型")
    else:
        print("未找到模型，使用随机权重")

    # 设置动作映射器
    action_mapper = ActionMapper()
    action_mapper.register_key_action("move_left", "a")
    action_mapper.register_key_action("move_right", "d")
    action_mapper.register_key_action("move_up", "w")
    action_mapper.register_key_action("move_down", "s")

    # 创建游戏控制器
    controller = GameController(
        action_mapper=action_mapper,
        action_delay=0.1,
        safety_check=True,
    )

    print("\n控制器设置:")
    print("  W - 向上移动")
    print("  A - 向左移动")
    print("  S - 向下移动")
    print("  D - 向右移动")
    print("\n以手动模式启动推理（按 Ctrl+C 退出）")

    # 启动控制器
    controller.start()

    try:
        # 手动模式 - 等待用户输入
        import time
        while True:
            # 生成虚拟观测
            obs = np.random.randn(obs_dim).astype(np.float32)

            # 从智能体获取动作
            with torch.no_grad():
                action, _ = agent.select_action(obs, deterministic=False)

            # 执行动作
            controller.execute_action(action)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n正在关闭...")
        controller.stop()
        print("完成")


if __name__ == "__main__":
    main()
