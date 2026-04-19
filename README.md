# VisionGame

通用视觉控制游戏框架，基于强化学习实现游戏自动化控制，同时提供完整的 WebUI 管理平台。

## 特性

- **通用性**：非游戏专用，设计为适配任何游戏的框架
- **模块化**：清晰的模块划分，易于扩展和定制
- **WebUI 管理平台**：图集管理、模型管理、标注工具、训练监控
- **数据训练入口**：图片库上传、人工标注功能
- **技术栈**：Python + PyTorch + FastAPI + Vue3
- **输入源**：视频流/截图采集
- **多种 RL 算法**：支持 PPO 和 SAC 主流算法

## 项目结构

```
visionGame/
├── backend/                      # FastAPI 后端服务
│   ├── app.py                   # 应用入口
│   ├── database.py              # 数据库配置
│   ├── schemas.py               # Pydantic 模型
│   ├── websocket_manager.py      # WebSocket 管理
│   └── routers/                 # API 路由
│       ├── atlas.py             # 图集管理
│       ├── image.py             # 图片管理
│       ├── annotation.py         # 标注管理
│       ├── category.py          # 类别管理
│       ├── model.py             # 模型管理
│       ├── training.py          # 训练管理
│       ├── launch.py            # 启动管理
│       └── websocket.py         # WebSocket
├── visiongame/                  # 核心 RL/Vision 包
│   ├── __init__.py             # 包初始化
│   ├── config/                 # 配置模块
│   │   ├── schema.py          # 配置数据类
│   │   ├── default.yaml        # 默认配置
│   │   └── __init__.py
│   ├── core/                   # 核心模块
│   │   ├── data_input/        # 数据输入
│   │   ├── vision/            # 视觉处理
│   │   ├── rl/                # 强化学习
│   │   └── control/           # 控制接口
│   └── annotation/             # 标注工具
├── webui/                       # Vue3 前端
│   ├── src/
│   │   ├── api/              # API 调用封装
│   │   ├── components/       # 公共组件
│   │   ├── router/           # 路由配置
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── utils/            # 工具函数
│   │   ├── views/            # 页面组件
│   │   ├── App.vue           # 根组件
│   │   └── main.ts           # 入口文件
│   ├── public/               # 静态资源
│   └── ...
├── uploads/                    # 上传文件存储
├── checkpoints/               # 模型检查点
├── logs/                     # 日志目录
├── examples/                 # 示例代码
├── tests/                    # 单元测试
└── docs/                     # 文档
```

## 快速开始

### 后端服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端服务（端口 8000）
cd backend
python app.py
```

### 前端服务

```bash
# 安装前端依赖
cd webui
pnpm install

# 启动开发服务器（端口 5173）
pnpm dev
```

### 访问 WebUI

打开浏览器访问 http://localhost:5173

## WebUI 功能

| 页面 | 功能 |
|------|------|
| 控制台 | 系统概览、统计卡片、训练进度 |
| 图集管理 | 创建图集、上传图片、目录管理 |
| 模型管理 | 注册模型、上传模型文件、设置最佳模型 |
| 训练监控 | 启动训练、停止训练、实时进度监控 |
| 模型启动 | 加载模型进行推理 |
| 标注工具 | 图片边界框标注、类别管理 |

## 核心模块

### 数据输入 (visiongame/core/data_input)

| 模块 | 说明 | 依赖 |
|------|------|------|
| `ScreenCapture` | 屏幕采集 | mss, pyautogui |
| `VideoReader` | 视频文件读取 | opencv |
| `DatasetManager` | 数据集管理 | sqlite3 |
| `FrameBuffer` | 帧缓冲区 | - |

### 视觉处理 (visiongame/core/vision)

| 模块 | 说明 | 依赖 |
|------|------|------|
| `ImagePreprocessor` | 图像预处理 | opencv, torchvision |
| `CNNEncoder` | CNN特征编码 | torchvision |
| `UIDetector` | UI元素检测 | torchvision |

### 强化学习 (visiongame/core/rl)

| 模块 | 说明 |
|------|------|
| `PPO` | 近端策略优化算法 |
| `SAC` | 软Actor-Critic算法 |
| `GameEnv` | Gymnasium风格环境封装 |
| `Trainer` | 训练循环 |

### 游戏控制 (visiongame/core/control)

| 模块 | 说明 |
|------|------|
| `KeyboardEmulator` | 键盘模拟 |
| `MouseEmulator` | 鼠标模拟 |
| `GameController` | 游戏控制主逻辑 |
| `ActionMapper` | RL动作到游戏输入的映射 |

### 标注工具 (visiongame/annotation)

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

## 示例代码

### 屏幕采集

```python
from visiongame import ScreenCapture

with ScreenCapture(fps=30) as capture:
    frame = capture.capture()
    print(f"采集帧尺寸: {frame.shape}")
```

### 视频读取

```python
from visiongame import VideoReader

with VideoReader("gameplay.mp4") as reader:
    for frame in reader:
        print(f"帧尺寸: {frame.shape}")
```

### 特征提取

```python
import torch
from visiongame import CNNEncoder

encoder = CNNEncoder(backbone="resnet18", pretrained=True)
frames = torch.randn(1, 3, 224, 224)
features = encoder.extract(frames)
print(f"特征维度: {features.shape}")
```

### RL 训练

```bash
python examples/train_example.py
```

## 文档

详细教程请参考 [docs/](docs/)，包含：

- 完整的 API 参考
- 各模块详细使用示例
- 自定义游戏适配器指南
- 配置说明
- 常见问题解答

## 许可证

MIT License
