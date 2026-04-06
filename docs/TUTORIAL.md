# VisionGame 使用教程

## 目录

1. [项目简介](#1-项目简介)
2. [安装指南](#2-安装指南)
3. [快速开始](#3-快速开始)
4. [核心模块详解](#4-核心模块详解)
5. [API 参考](#5-api-参考)
6. [示例代码](#6-示例代码)
7. [配置说明](#7-配置说明)
8. [常见问题](#8-常见问题)

---

## 1. 项目简介

VisionGame 是一个基于强化学习的通用视觉控制游戏框架，支持：

- **屏幕/视频采集**：实时采集屏幕画面或读取视频文件
- **视觉特征提取**：支持多种 CNN 骨干网络（ResNet、MobileNet、EfficientNet）
- **强化学习训练**：支持 PPO 和 SAC 两种主流算法
- **游戏控制输入模拟**：键盘和鼠标输入的自动模拟
- **数据标注工具**：支持 COCO 和 YOLO 格式的标注导出

### 主要特性

- 模块化设计，易于扩展
- 支持 GPU 加速训练
- 丰富的预训练模型支持
- 完整的训练日志和可视化
- 紧急停止功能，保障安全

---

## 2. 安装指南

### 系统要求

- Python 3.8+
- PyTorch 2.0+
- Windows/Linux/macOS

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/your-repo/visiongame.git
cd visiongame

# 安装依赖
pip install -e .

# 可选依赖（增强视频解码和窗口管理）
pip install ffmpeg-python pygetwindow
```

### 验证安装

```python
from visiongame import __version__
print(f"VisionGame version: {__version__}")
```

---

## 3. 快速开始

### 3.1 屏幕采集

```python
from visiongame import ScreenCapture

# 创建屏幕采集器
with ScreenCapture(fps=30) as capture:
    # 采集单帧
    frame = capture.capture()
    print(f"采集帧尺寸: {frame.shape}")

    # 获取屏幕尺寸
    width, height = capture.get_screen_size()
    print(f"屏幕尺寸: {width}x{height}")
```

### 3.2 视频读取

```python
from visiongame import VideoReader

# 读取视频文件
with VideoReader("gameplay.mp4") as reader:
    print(f"视频信息: {reader.fps} FPS, {reader.frame_count} 帧")
    print(f"分辨率: {reader.resolution}")

    # 逐帧读取
    for frame in reader:
        print(f"帧尺寸: {frame.shape}")
```

### 3.3 特征提取

```python
import torch
from visiongame import CNNEncoder

# 创建编码器（使用 ResNet18 骨干）
encoder = CNNEncoder(backbone="resnet18", pretrained=True)

# 提取特征
frames = torch.randn(1, 3, 224, 224)  # B, C, H, W
features = encoder.extract(frames)
print(f"特征维度: {features.shape}")  # [1, 512]
```

### 3.4 RL 训练

```bash
# 运行训练示例
python examples/train_example.py
```

### 3.5 推理控制

```bash
# 运行推理示例
python examples/inference_example.py
```

---

## 4. 核心模块详解

### 4.1 数据输入模块 (`visiongame.core.data_input`)

#### ScreenCapture - 屏幕采集

```python
from visiongame import ScreenCapture

# 基本用法
capture = ScreenCapture(fps=30)
frame = capture.capture()
capture.release()

# 区域采集
capture = ScreenCapture(
    fps=30,
    capture_region=(0, 0, 800, 600)  # x, y, width, height
)

# 多显示器支持
capture = ScreenCapture(monitor_index=1)

# 使用上下文管理器
with ScreenCapture(fps=60) as capture:
    frame = capture.capture()
```

#### VideoReader - 视频读取

```python
from visiongame import VideoReader

# 基本用法
reader = VideoReader("video.mp4")
for frame in reader:
    process(frame)
reader.release()

# 指定帧率播放
reader = VideoReader("video.mp4", target_fps=15)

# 跳转和搜索
reader.seek(100)  # 跳转到第100帧
reader.seek_to_time(5.0)  # 跳转到5秒处

# 获取特定帧
frame = reader.get_frame_at(50)
```

#### DatasetManager - 数据集管理

```python
from visiongame import DatasetManager
from pathlib import Path

# 创建管理器
manager = DatasetManager(root_dir="./data")

# 添加样本
manager.add_sample(
    sample_id="img_001",
    image_path=Path("images/frame_001.png"),
    annotation_path=Path("annotations/frame_001.json"),
    metadata={"timestamp": 1.5},
    split="train"
)

# 获取样本
sample = manager.get_sample("img_001")

# 划分数据集
train, val, test = manager.split_dataset(
    train_ratio=0.8,
    val_ratio=0.1,
    test_ratio=0.1
)

# 导出标注
manager.export_annotations(Path("coco.json"), format="coco")
```

### 4.2 视觉处理模块 (`visiongame.core.vision`)

#### ImagePreprocessor - 图像预处理

```python
from visiongame import ImagePreprocessor
import numpy as np

# 创建预处理器
preprocessor = ImagePreprocessor(
    image_size=(224, 224),
    normalize=True,
    augmentation=True  # 启用数据增强
)

# 预处理单张图像
image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
tensor = preprocessor(image)  # 返回 torch.Tensor

# 预处理批量图像
images = [image, image]
batch = preprocessor.preprocess_batch(images)

# 反归一化
original = preprocessor.denormalize(tensor)
```

#### CNNEncoder - CNN 特征编码

```python
from visiongame import CNNEncoder

# 支持的骨干网络
print(CNNEncoder.list_backbones())
# ['resnet18', 'resnet34', 'resnet50', 'mobilenet_v2',
#  'mobilenet_v3_small', 'mobilenet_v3_large', 'efficientnet_b0']

# 创建编码器
encoder = CNNEncoder(
    backbone="resnet18",
    pretrained=True,
    feature_dim=512,
    freeze_backbone=False
)

# 提取特征
import torch
features = encoder.extract(torch.randn(4, 3, 224, 224))

# 保存和加载模型
encoder.save_weights("encoder_weights.pt")
encoder.load_weights("encoder_weights.pt")
```

#### UIDetector - UI 元素检测

```python
from visiongame import UIDetector
import torch

# 创建检测器
detector = UIDetector(
    num_classes=80,
    backbone="resnet18",
    pretrained=True,
    score_thresh=0.5,
    nms_thresh=0.4
)

# 检测
images = torch.randn(2, 3, 224, 224)
detections = detector.detect(images)

for img_detections in detections:
    for det in img_detections:
        print(f"类别: {det.label_name}, 置信度: {det.score:.2f}")
        print(f"边界框: {det.bbox}")
```

### 4.3 强化学习模块 (`visiongame.core.rl`)

#### PPO 算法

```python
from visiongame import PPO
import numpy as np

# 创建 PPO 智能体
agent = PPO(
    observation_dim=512,
    action_dim=4,
    lr=3e-4,
    gamma=0.99,
    lam=0.95,
    clip_eps=0.2,
    ent_coef=0.01,
    vf_coef=0.5,
    ppo_epochs=10,
    batch_size=64,
    device="cuda"
)

# 选择动作
observation = np.random.randn(512).astype(np.float32)
action, value = agent.select_action(observation)

# 确定性动作
action, value = agent.select_action(observation, deterministic=True)

# 存储转换
agent.store_transition(
    observation=torch.FloatTensor(observation),
    action=torch.FloatTensor(action),
    reward=1.0,
    done=False,
    log_prob=torch.FloatTensor([0.5]),
    value=value
)

# 更新策略
stats = agent.update()

# 保存和加载
agent.save("ppo_model.pt")
agent.load("ppo_model.pt")
```

#### SAC 算法

```python
from visiongame import SAC
import numpy as np

# 创建 SAC 智能体
agent = SAC(
    observation_dim=512,
    action_dim=4,
    lr=3e-4,
    gamma=0.99,
    tau=0.005,
    alpha=0.2,
    device="cuda"
)

# 选择动作
observation = np.random.randn(512).astype(np.float32)
action = agent.select_action(observation)

# 存储转换
agent.store_transition(
    observation=observation,
    action=action,
    reward=1.0,
    done=False,
    next_observation=observation
)

# 更新
stats = agent.update(batch_size=256)
```

#### GameEnv - 游戏环境

```python
from visiongame import GameEnv, GameAdapter

# 定义游戏适配器
class MyGameAdapter(GameAdapter):
    def get_state(self, frame):
        # 从游戏画面提取状态
        return frame.flatten().astype(np.float32)

    def get_action_space(self):
        from gymnasium import spaces
        return spaces.Box(low=-1, high=1, shape=(4,), dtype=np.float32)

    def map_action(self, action):
        # 将 RL 动作映射到游戏输入
        return action

    def compute_reward(self, old_state, new_state, action):
        # 计算奖励
        return 1.0

    def reset(self):
        return np.zeros((224, 224, 3), dtype=np.uint8)

# 创建环境
adapter = MyGameAdapter()
env = GameEnv(adapter=adapter, frame_stack=4, max_episode_steps=10000)

# 训练循环
observation, info = env.reset()
for step in range(1000):
    action = agent.select_action(observation)
    observation, reward, terminated, truncated, info = env.step(action)

    if terminated or truncated:
        observation, info = env.reset()
```

#### Trainer - 训练器

```python
from visiongame import Trainer

# 创建训练器
trainer = Trainer(
    agent=agent,
    env=env,
    config={
        "total_timesteps": 1_000_000,
        "eval_freq": 10000,
        "save_freq": 50000,
        "log_freq": 1000,
        "buffer_size": 2048,
    },
    log_dir="./logs",
    checkpoint_dir="./checkpoints",
    device="cuda"
)

# 开始训练
trainer.train()

# 评估
eval_stats = trainer.evaluate(num_episodes=10)
print(f"平均奖励: {eval_stats['mean_reward']:.2f}")

# 保存检查点
trainer.save_checkpoint()

# 加载检查点
trainer.load_checkpoint("./checkpoints/checkpoint_500000.pt")

# 关闭训练器
trainer.close()
```

### 4.4 控制模块 (`visiongame.core.control`)

#### KeyboardEmulator - 键盘模拟

```python
from visiongame import KeyboardEmulator

# 创建键盘模拟器
keyboard = KeyboardEmulator(
    key_press_duration=0.05,
    key_release_delay=0.01
)

# 按键操作
keyboard.press("a")           # 按下并释放
keyboard.key_down("space")    # 按下
keyboard.key_up("space")      # 释放

# 输入文本
keyboard.type("hello world", interval=0.1)

# 组合键
keyboard.hotkey("ctrl", "c")  # Ctrl+C
keyboard.hotkey("ctrl", "shift", "esc")

# 序列按键
keyboard.combo(["a", "b", "c"])
```

#### MouseEmulator - 鼠标模拟

```python
from visiongame import MouseEmulator

# 创建鼠标模拟器
mouse = MouseEmulator(
    move_duration=0.1,
    click_duration=0.05
)

# 移动鼠标
mouse.move_to(100, 200)        # 移动到绝对位置
mouse.move_rel(50, -30)       # 相对移动

# 点击操作
mouse.click(x=100, y=200)      # 点击指定位置
mouse.double_click(x=100, y=200)  # 双击
mouse.right_click(x=100, y=200)   # 右键点击

# 拖拽操作
mouse.drag_to(300, 400, duration=0.5)
mouse.drag_rel(-50, 100)

# 滚动
mouse.scroll(y=-3)  # 向下滚
mouse.scroll(y=3)   # 向上滚

# 获取位置
x, y = mouse.get_position()
```

#### GameController - 游戏控制器

```python
from visiongame import GameController, ActionMapper

# 创建动作映射器
mapper = ActionMapper()

# 注册动作
mapper.register_key_action("move_left", "a")
mapper.register_key_action("move_right", "d")
mapper.register_key_action("move_up", "w")
mapper.register_key_action("move_down", "s")
mapper.register_key_action("jump", "space")
mapper.register_combo_action("special", ["ctrl", "k"])

# 创建控制器
controller = GameController(
    action_mapper=mapper,
    action_delay=0.1,
    safety_check=True,
    emergency_stop_key="f12"
)

# 启动控制器
controller.start()

# 执行动作
controller.execute_named_action("move_left")
controller.execute_named_action("jump")

# 使用数组执行动作（用于 RL）
import numpy as np
action = np.array([1, 0, 0, 0])  # one-hot 编码的动作
controller.execute_action(action)

# 停止控制器
controller.stop()

# 紧急停止
controller.emergency_stop()
```

### 4.5 标注工具 (`visiongame.annotation`)

#### BoundingBoxAnnotator - 边界框标注

```python
from visiongame import BoundingBoxAnnotator, BoundingBox
import numpy as np

# 创建标注器
annotator = BoundingBoxAnnotator(labels=["player", "enemy", "item"])

# 添加框
box = BoundingBox(x1=100, y1=100, x2=200, y2=200, label="player", label_id=0)
annotator.add_box(box)

# 绘制标注
image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
annotated = annotator.draw_boxes(image)

# 鼠标事件处理
def on_mouse(event, x, y, flags, param):
    result = annotator.on_mouse_event(event, x, y, flags)
    if result:
        print(f"事件: {result}")

# 导出
coco_annotations = annotator.export_coco(image_id=1)
yolo_lines = annotator.export_yolo(img_width=640, img_height=480)

# 清除
annotator.clear()
```

### 4.6 标注工具 GUI (`visiongame.annotation.tools.label_tool`)

图形界面版标注工具，支持鼠标交互式标注。

#### LabelTool - 标注工具 GUI

```bash
# 启动标注工具
python -m visiongame.annotation.tools.label_tool

# 或在 Python 中运行
from visiongame.annotation.tools import LabelTool
tool = LabelTool(
    labels=["player", "enemy", "item", "npc", "ui"],
    output_dir="./annotations",
    output_format="coco"
)
tool.run()
```

#### 快捷键说明

| 快捷键 | 功能 |
|-------|------|
| 1-9 | 选择类别 |
| o | 打开图片文件夹 |
| s | 保存标注 |
| c | 清除当前标注 |
| z | 撤销上一个框 |
| space | 下一张图片 |
| 左箭头 | 上一张图片 |
| q | 退出 |

#### 命令行参数

```bash
# 指定类别标签
python -m visiongame.annotation.tools.label_tool --labels player enemy item npc

# 指定输出目录
python -m visiongame.annotation.tools.label_tool --output-dir ./my_annotations

# 指定输出格式
python -m visiongame.annotation.tools.label_tool --format yolo
```

---

## 5. API 参考

### 5.1 数据输入

| 类/函数 | 说明 |
|---------|------|
| `ScreenCapture` | 屏幕采集类 |
| `VideoReader` | 视频文件读取类 |
| `DatasetManager` | 数据集管理器 |
| `FrameBuffer` | 帧缓冲区 |

### 5.2 视觉处理

| 类/函数 | 说明 |
|---------|------|
| `ImagePreprocessor` | 图像预处理器 |
| `CNNEncoder` | CNN 特征编码器 |
| `UIDetector` | UI 元素检测器 |

### 5.3 强化学习

| 类/函数 | 说明 |
|---------|------|
| `PPO` | PPO 算法实现 |
| `SAC` | SAC 算法实现 |
| `GameEnv` | 游戏环境封装 |
| `GameAdapter` | 游戏适配器基类 |
| `Trainer` | 训练器 |

### 5.4 控制模块

| 类/函数 | 说明 |
|---------|------|
| `KeyboardEmulator` | 键盘模拟器 |
| `MouseEmulator` | 鼠标模拟器 |
| `GameController` | 游戏控制器 |
| `ActionMapper` | 动作映射器 |

### 5.5 标注工具

| 类/函数 | 说明 |
|---------|------|
| `BoundingBox` | 边界框数据类 |
| `BoundingBoxAnnotator` | 边界框标注工具（程序化） |
| `LabelTool` | 图形界面标注工具 |

---

## 6. 示例代码

### 6.1 完整训练流程

```python
"""完整训练流程示例"""
import numpy as np
import torch
from visiongame import (
    Config, RLConfig, VisionConfig,
    PPO, GameEnv, GameAdapter, Trainer
)
from gymnasium import spaces

class MyGame(GameAdapter):
    """自定义游戏适配器"""

    def __init__(self):
        super().__init__()
        self.frame = np.zeros((224, 224, 3), dtype=np.uint8)
        self.step_count = 0

    def get_state(self, frame):
        return frame.flatten().astype(np.float32) / 255.0

    def get_action_space(self):
        return spaces.Box(low=-1, high=1, shape=(4,), dtype=np.float32)

    def map_action(self, action):
        return action

    def compute_reward(self, old_state, new_state, action):
        return np.random.randn()

    def reset(self):
        self.step_count = 0
        return self.frame.copy()

    def capture_frame(self):
        self.step_count += 1
        return self.frame.copy()

    def is_done(self):
        return self.step_count > 100

# 配置
config = Config()
config.rl.learning_rate = 3e-4
config.rl.gamma = 0.99
config.training.device = "cuda" if torch.cuda.is_available() else "cpu"

# 环境
env = GameEnv(MyGame(), frame_stack=1, max_episode_steps=1000)

# 智能体
agent = PPO(
    observation_dim=224*224*3,
    action_dim=4,
    lr=config.rl.learning_rate,
    gamma=config.rl.gamma,
    device=config.training.device
)

# 训练器
trainer = Trainer(
    agent=agent,
    env=env,
    config={
        "total_timesteps": 50000,
        "log_freq": 1000,
        "save_freq": 10000,
    }
)

# 训练
trainer.train()

# 保存模型
agent.save("trained_model.pt")

# 评估
stats = trainer.evaluate(num_episodes=10)
print(f"评估结果: {stats}")

trainer.close()
```

### 6.2 屏幕采集与处理流程

```python
"""屏幕采集与处理流程"""
import torch
from visiongame import ScreenCapture, ImagePreprocessor, CNNEncoder

# 初始化
capture = ScreenCapture(fps=30)
preprocessor = ImagePreprocessor(image_size=(224, 224))
encoder = CNNEncoder(backbone="resnet18", pretrained=True)

# 采集和处理
frame = capture.capture()
tensor = preprocessor(frame)
features = encoder.extract(tensor.unsqueeze(0))

print(f"特征尺寸: {features.shape}")

capture.release()
```

### 6.3 自定义游戏控制器

```python
"""自定义游戏控制器"""
import numpy as np
from visiongame import (
    GameController, ActionMapper,
    KeyboardEmulator, MouseEmulator
)

# 创建动作映射
mapper = ActionMapper()
mapper.register_key_action("left", "a")
mapper.register_key_action("right", "d")
mapper.register_key_action("attack", "j")
mapper.register_mouse_action("click_ui", (640, 400))
mapper.register_combo_action("special", ["k", "l", "j"])

# 创建控制器
controller = GameController(
    action_mapper=mapper,
    action_delay=0.1,
    safety_check=True
)

# 启动
controller.start()

# 执行动作
while True:
    # ... 游戏逻辑 ...

    # 执行键盘动作
    controller.execute_named_action("left")
    controller.execute_named_action("attack")

    # 执行鼠标动作
    controller.execute_named_action("click_ui")

    # 执行组合动作
    controller.execute_named_action("special")

# 停止
controller.stop()
```

---

## 7. 配置说明

### 7.1 默认配置

配置文件位于 `visiongame/config/default.yaml`：

```yaml
# 数据输入配置
data_input:
  capture_fps: 30           # 采集帧率
  buffer_size: 100          # 缓冲区大小
  screenshot_format: png    # 截图格式
  video_decoder: ffmpeg     # 视频解码器

# 视觉处理配置
vision:
  image_size: [224, 224]    # 图像尺寸
  backbone: resnet18         # CNN 骨干网络
  feature_dim: 512           # 特征维度
  use_pretrained: true       # 使用预训练权重

# 强化学习配置
rl:
  algorithm: ppo              # 算法选择 (ppo/sac)
  gamma: 0.99                # 折扣因子
  learning_rate: 0.0003      # 学习率
  ppo_epochs: 10             # PPO 更新轮数
  batch_size: 64              # 批次大小

# 控制配置
control:
  action_delay: 0.1           # 动作间隔（秒）
  safety_check: true         # 安全检查
  emergency_stop_key: f12    # 紧急停止键

# 训练配置
training:
  total_timesteps: 1000000   # 总时间步
  save_freq: 50000           # 保存频率
  log_freq: 1000             # 日志频率
  device: cuda               # 计算设备
```

### 7.2 自定义配置

```python
from visiongame import Config, RLConfig, VisionConfig

# 方式1：修改默认配置
config = Config()
config.rl.algorithm = "sac"
config.rl.learning_rate = 1e-4
config.vision.backbone = "resnet50"

# 方式2：从 YAML 加载
config = Config.from_yaml("custom_config.yaml")

# 方式3：使用 dataclass
config = Config(
    rl=RLConfig(algorithm="sac", gamma=0.95),
    vision=VisionConfig(backbone="efficientnet_b0")
)

# 保存配置
config.save_yaml("my_config.yaml")
```

---

## 8. 常见问题

### Q1: 安装时出现依赖错误怎么办？

```bash
# 确保 Python 版本 >= 3.8
python --version

# 单独安装 PyTorch（推荐从官网选择合适的版本）
pip install torch torchvision

# 然后安装 VisionGame
pip install -e .
```

### Q2: 屏幕采集失败？

```python
# 检查是否安装了屏幕采集依赖
try:
    import mss
    import pyautogui
    print("依赖正常")
except ImportError:
    # 重新安装
    pip install mss pyautogui
```

### Q3: GPU 不可用？

```python
# 检查 CUDA
import torch
print(f"CUDA 可用: {torch.cuda.is_available()}")
print(f"CUDA 版本: {torch.version.cuda}")

# 使用 CPU 作为备选
device = "cuda" if torch.cuda.is_available() else "cpu"
agent = PPO(..., device=device)
```

### Q4: 如何实现自定义游戏适配器？

```python
from visiongame import GameAdapter
import numpy as np

class MyGame(GameAdapter):
    def get_state(self, frame):
        # 将游戏画面转换为 RL 状态
        return frame.flatten().astype(np.float32) / 255.0

    def get_action_space(self):
        from gymnasium import spaces
        return spaces.Discrete(5)  # 5 个离散动作

    def map_action(self, action):
        # 将 RL 动作转换为游戏输入
        if action == 0:
            return "left"
        elif action == 1:
            return "right"
        # ...

    def compute_reward(self, old_state, new_state, action):
        # 设计奖励函数
        return 1.0 if success else -0.1

    def reset(self):
        # 重置游戏状态
        return initial_frame

    def is_done(self):
        # 判断回合是否结束
        return game_over
```

### Q5: 如何导出训练好的模型？

```python
# PPO 模型保存
agent.save("ppo_agent.pt")

# 加载模型
agent.load("ppo_agent.pt")

# 仅保存智能体部分
torch.save({
    "agent_state_dict": agent.agent.state_dict(),
    "training_steps": agent.training_steps,
}, "ppo_agent_state.pt")
```

---

## 附录

### A. 支持的 CNN 骨干网络

| 骨干网络 | 特征维度 | 预训练支持 |
|---------|---------|-----------|
| ResNet18 | 512 | 是 |
| ResNet34 | 512 | 是 |
| ResNet50 | 2048 | 是 |
| MobileNetV2 | 1280 | 是 |
| MobileNetV3-Small | 576 | 是 |
| MobileNetV3-Large | 960 | 是 |
| EfficientNet-B0 | 1280 | 是 |

### B. 快捷键说明

| 快捷键 | 功能 |
|-------|------|
| F12 | 紧急停止 |
| Ctrl+C | 中断推理 |

### C. 联系与支持

- 问题反馈：https://github.com/your-repo/visiongame/issues
- 文档更新：https://github.com/your-repo/visiongame/wiki
