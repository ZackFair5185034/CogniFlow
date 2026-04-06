# VisionGame

通用视觉控制游戏框架，基于强化学习实现游戏自动化控制。

## 特性

- **通用性**：非游戏专用，设计为适配任何游戏的框架
- **模块化**：清晰的模块划分，易于扩展和定制
- **数据训练入口**：图片库上传、视频上传、人工标注功能
- **技术栈**：Python + PyTorch + 强化学习
- **输入源**：视频流/截图采集
- **多种 RL 算法**：支持 PPO 和 SAC 主流算法

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
    print(f"采集帧尺寸: {frame.shape}")
```

### 2. 视频读取

```python
from visiongame import VideoReader

with VideoReader("gameplay.mp4") as reader:
    for frame in reader:
        print(f"帧尺寸: {frame.shape}")
```

### 3. 特征提取

```python
import torch
from visiongame import CNNEncoder

encoder = CNNEncoder(backbone="resnet18", pretrained=True)
frames = torch.randn(1, 3, 224, 224)
features = encoder.extract(frames)
print(f"特征维度: {features.shape}")
```

### 4. RL 训练

```bash
python examples/train_example.py
```

## 项目结构

```
visiongame/
├── visiongame/                    # 主包
│   ├── __init__.py               # 包初始化
│   ├── config/                   # 配置模块
│   │   ├── schema.py            # 配置数据类
│   │   └── default.yaml          # 默认配置
│   ├── core/                     # 核心模块
│   │   ├── data_input/           # 数据输入
│   │   │   ├── capture/          # 屏幕/视频采集
│   │   │   └── storage/          # 数据集管理
│   │   ├── vision/               # 视觉处理
│   │   │   ├── features/         # 特征提取
│   │   │   ├── detector/         # UI检测
│   │   │   └── preprocessor/     # 图像预处理
│   │   ├── rl/                   # 强化学习
│   │   │   ├── algorithms/        # PPO/SAC算法
│   │   │   ├── environment/       # 环境封装
│   │   │   └── trainer/          # 训练器
│   │   └── control/              # 控制接口
│   │       ├── input_emulator/    # 输入模拟
│   │       └── controller/        # 游戏控制器
│   └── annotation/                # 标注工具
├── examples/                     # 示例代码
├── tests/                       # 单元测试
├── docs/                        # 文档
│   └── TUTORIAL.md             # 详细教程
└── CLAUDE.md                   # 项目规范
```

## 核心模块

### 数据输入 (data_input)

| 模块 | 说明 | 依赖 |
|------|------|------|
| `ScreenCapture` | 屏幕采集 | mss, pyautogui |
| `VideoReader` | 视频文件读取 | opencv |
| `DatasetManager` | 数据集管理 | sqlite3 |
| `FrameBuffer` | 帧缓冲区 | - |

### 视觉处理 (vision)

| 模块 | 说明 | 依赖 |
|------|------|------|
| `ImagePreprocessor` | 图像预处理 | opencv, torchvision |
| `CNNEncoder` | CNN特征编码 | torchvision |
| `UIDetector` | UI元素检测 | torchvision |

### 强化学习 (rl)

| 模块 | 说明 |
|------|------|
| `PPO` | 近端策略优化算法 |
| `SAC` | 软Actor-Critic算法 |
| `GameEnv` | Gymnasium风格环境封装 |
| `Trainer` | 训练循环 |

### 游戏控制 (control)

| 模块 | 说明 |
|------|------|
| `KeyboardEmulator` | 键盘模拟 |
| `MouseEmulator` | 鼠标模拟 |
| `GameController` | 游戏控制主逻辑 |
| `ActionMapper` | RL动作到游戏输入的映射 |

### 标注工具 (annotation)

| 模块 | 说明 |
|------|------|
| `BoundingBoxAnnotator` | 边界框标注 |
| `BoundingBox` | 边界框数据结构 |

## 配置

配置文件位于 `visiongame/config/default.yaml`：

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
  emergency_stop_key: f12

training:
  total_timesteps: 1000000
  save_freq: 50000
  device: cuda
```

## 文档

详细教程请参考 [docs/TUTORIAL.md](docs/TUTORIAL.md)，包含：

- 完整的 API 参考
- 各模块详细使用示例
- 自定义游戏适配器指南
- 配置说明
- 常见问题解答

## 许可证

MIT License
