# CogniFlow

通用视觉感知处理框架，集模型训练、模型测试、模型推理、规则引擎于一体，提供完整的 WebUI 管理平台。

## 特性

- **通用性**：不限定特定场景，适用于各类视觉感知任务
- **模块化**：清晰的模块划分，易于扩展和定制
- **WebUI 管理平台**：图集管理、模型管理、标注工具、训练监控
- **数据训练入口**：图片库上传、人工标注、YOLO 模型训练
- **技术栈**：Python + PyTorch + FastAPI + Vue3
- **输入源**：图片/视频/屏幕采集
- **规则引擎**：可视化流程编排，基于检测结果触发动作
- **多种算法支持**：支持 YOLO 目标检测、PPO/SAC 强化学习算法

## 项目结构

```
CogniFlow/
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
│       ├── inference.py         # 推理
│       ├── rule_engine.py       # 规则引擎
│       └── websocket.py         # WebSocket
├── engine/                     # 核心视觉感知包
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

# 启动后端服务并自动打开浏览器（Windows 打包版本默认行为）
python app.py --browser
```

**启动参数：**

| 参数 | 说明 | 适用平台 |
|------|------|----------|
| `--browser` | 启动后自动打开浏览器 | 所有平台 |
| `DATA_DIR=path` | 数据存储目录 | 环境变量 |
| `WEBUI_DIST=path` | 前端静态文件目录 | 环境变量 |

**Windows 打包版本说明：**

使用 PyInstaller 打包的 `cogniflow.exe`（通过 `scripts/build.ps1` 构建）默认会启动浏览器。这是通过 `cogniflow.spec` 配置的 `argv=["--browser"]` 实现的。

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

## 构建与打包

### 环境要求

- Python 3.10+
- Node.js 18+ (前端构建)
- pnpm (推荐) / yarn / npm
- 磁盘空间 5GB+ (含虚拟环境和构建产物)

### 脚本构建 (`scripts/build.sh`)

项目提供统一的构建脚本，支持以下构建目标：

```bash
./scripts/build.sh <命令>
```

| 命令 | 说明 |
|------|------|
| `backend` | 构建后端（安装依赖、可选 Cython 编译） |
| `frontend` | 构建前端（生产环境） |
| `binary` | PyInstaller 原生二进制打包（Linux/macOS） |
| `all` | 后端 + 前端 |
| `docker` | Docker 镜像 |
| `clean` | 清理构建产物 |

**环境变量：**

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `USE_VENV=1` | 使用虚拟环境隔离依赖 | `1` |
| `CYTHONIZE=1` | 用 Cython 编译 `engine/` 为 `.so`（源码保护） | `0` |
| `VERSION=xxx` | Docker 镜像版本 | `latest` |

**示例：**

```bash
# 构建原生二进制（Linux 可执行文件）
./scripts/build.sh binary

# 使用 Cython 保护源码后打包
CYTHONIZE=1 ./scripts/build.sh binary

# 构建 Docker 镜像
./scripts/build.sh docker
```

### 构建产物

| 类型 | 路径 |
|------|------|
| 前端dist | `webui/dist/` |
| PyInstaller输出 | `dist/cogniflow/cogniflow` |
| Docker镜像 | `cogniflow/cogniflow:latest` |

### PyInstaller 打包详情

`cogniflow.spec` 文件配置了完整的隐藏导入，包括：

- **Web框架**: fastapi, uvicorn, starlette, python-multipart
- **数据库**: sqlalchemy, aiosqlite
- **图像处理**: pillow, numpy, opencv-python-headless
- **系统工具**: psutil, pyyaml, mss, pyautogui, pygetwindow
- **其他**: ffmpeg-python

打包时自动使用虚拟环境 `venv/` 安装所有依赖，确保二进制文件完整运行。

**Windows 打包版本行为：**

通过 `scripts/build.ps1` 打包的 `dist/cogniflow/cogniflow.exe` 默认会自动启动浏览器。这是因为 `cogniflow.spec` 中的 EXE 配置指定了 `argv=["--browser"]`。

如需修改此行为，请编辑 `cogniflow.spec` 文件中 EXE 的 `argv` 参数。

| 平台 | 执行方式 | 浏览器自动启动 |
|------|----------|---------------|
| Windows exe (PyInstaller) | `cogniflow.exe` | ✅ 默认启动 |
| Windows Python | `python app.py --browser` | 需要 `--browser` 参数 |
| Linux/macOS Python | `python app.py` | 不启动（无桌面环境） |
| Linux/macOS exe | `./cogniflow --browser` | 需要参数 |

## WebUI 功能

| 页面 | 功能 |
|------|------|
| 控制台 | 系统概览、统计卡片、训练进度 |
| 图集管理 | 创建图集、上传图片、目录管理 |
| 模型管理 | 注册模型、上传模型文件、设置最佳模型 |
| 训练监控 | 启动训练、停止训练、实时进度监控 |
| 模型测试 | 加载模型进行图片/视频推理检测 |
| 规则引擎 | 可视化流程编排，基于检测结果触发动作 |
| 标注工具 | 图片边界框标注、类别管理 |

## 核心模块

### 数据输入 (engine/core/data_input)

| 模块 | 说明 | 依赖 |
|------|------|------|
| `ScreenCapture` | 屏幕采集 | mss, pyautogui |
| `VideoReader` | 视频文件读取 | opencv |
| `DatasetManager` | 数据集管理 | sqlite3 |
| `FrameBuffer` | 帧缓冲区 | - |

### 视觉处理 (engine/core/vision)

| 模块 | 说明 | 依赖 |
|------|------|------|
| `ImagePreprocessor` | 图像预处理 | opencv, torchvision |
| `CNNEncoder` | CNN特征编码 | torchvision |
| `UIDetector` | UI元素检测 | torchvision |

### 目标检测与模型训练

| 模块 | 说明 |
|------|------|
| YOLO 检测 | 基于 Ultralytics YOLO 的目标检测 |
| 模型训练 | 支持 YOLO 模型训练及指标监控 |
| 模型推理 | 图片/视频/实时采集推理 |

### 强化学习 (engine/core/rl)

| 模块 | 说明 |
|------|------|
| `PPO` | 近端策略优化算法 |
| `SAC` | 软Actor-Critic算法 |
| `GameEnv` | Gymnasium风格环境封装 |
| `Trainer` | 训练循环 |

### 规则引擎 (backend/services/rule_engine)

| 模块 | 说明 |
|------|------|
| 可视化编排 | 拖拽式节点编辑器 |
| YOLO 触发器 | 检测到目标时触发 |
| 条件节点 | 目标存在、置信度阈值、变量条件 |
| 动作节点 | 键盘/鼠标模拟、HTTP请求、日志 |
| 逻辑节点 | 分支、并行、循环、变量设置 |

## 配置

配置文件位于 `engine/config/default.yaml`：

```yaml
data_input:
  capture_fps: 30
  buffer_size: 100

vision:
  image_size: [224, 224]
  backbone: resnet18
  feature_dim: 512

training:
  epochs: 100
  batch_size: 16
  device: cuda

control:
  action_delay: 0.1
  safety_check: true
  emergency_stop_key: f12
```

## 文档

详细教程请参考 [docs/](docs/)，包含：

- 完整的 API 参考
- 各模块详细使用示例
- 规则引擎设计文档
- 配置说明
- 常见问题解答

## 许可证

MIT License
