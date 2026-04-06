# VisionGame

A通用视觉控制游戏框架，基于强化学习实现游戏自动化控制。

## 特性

- **通用性**：非游戏专用，设计为适配任何游戏的框架
- **数据训练入口**：图片库上传、视频上传、人工标注功能
- **技术栈**：Python + PyTorch + 强化学习
- **输入源**：视频流/截图采集

## 安装

```bash
pip install -e .
```

## 快速开始

### 1. 屏幕采集

```python
from visiongame import ScreenCapture

with ScreenCapture(fps=30) as capture:
    frame = capture.capture()
    print(f"Captured frame: {frame.shape}")
```

### 2. 视频读取

```python
from visiongame import VideoReader

with VideoReader("gameplay.mp4") as reader:
    for frame in reader:
        print(f"Frame: {frame.shape}")
```

### 3. 特征提取

```python
from visiongame import CNNEncoder
import torch

encoder = CNNEncoder(backbone="resnet18", pretrained=True)
frames = torch.randn(1, 3, 224, 224)
features = encoder.extract(frames)
print(f"Features shape: {features.shape}")
```

### 4. RL训练

```bash
python examples/train_example.py
```

## 项目结构

```
visiongame/
├── visiongame/                    # 主包
│   ├── config/                     # 配置
│   ├── core/                       # 核心模块
│   │   ├── data_input/             # 数据输入
│   │   ├── vision/                 # 视觉处理
│   │   ├── rl/                     # 强化学习
│   │   └── control/                # 控制接口
│   └── annotation/                 # 标注工具
├── examples/                        # 示例
├── tests/                          # 测试
└── docs/                           # 文档
```

## 核心模块

### Data Input Pipeline

- `ScreenCapture`: 屏幕采集 (MSS/PyAutoGUI)
- `VideoReader`: 视频文件读取 (OpenCV)
- `DatasetManager`: 数据集管理 (SQLite)

### Vision Processor

- `ImagePreprocessor`: 图像预处理
- `CNNEncoder`: CNN特征编码器
- `UIDetector`: UI元素检测

### RL Training Engine

- `PPO`: Proximal Policy Optimization
- `SAC`: Soft Actor-Critic
- `GameEnv`: Gymnasium风格环境封装
- `Trainer`: 训练循环

### Game Control Interface

- `KeyboardEmulator`: 键盘模拟
- `MouseEmulator`: 鼠标模拟
- `GameController`: 游戏控制主逻辑

## 配置

配置文件位于 `visiongame/config/default.yaml`:

```yaml
data_input:
  capture_fps: 30
  buffer_size: 100

vision:
  image_size: [224, 224]
  backbone: resnet18
  feature_dim: 512

rl:
  algorithm: ppo
  gamma: 0.99
  learning_rate: 0.0003

control:
  action_delay: 0.1
  safety_check: true
```

## 许可证

MIT License
