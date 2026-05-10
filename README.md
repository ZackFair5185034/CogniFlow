# CogniFlow

通用视觉感知处理框架，集模型训练、模型测试、模型推理、规则引擎于一体，提供完整的 WebUI 管理平台。

## 特性

- **通用性**：不限定特定场景，适用于各类视觉感知任务
- **模块化**：清晰的模块划分，易于扩展和定制
- **WebUI 管理平台**：图集管理、模型管理、标注工具、训练监控
- **数据训练入口**：图片库上传、人工标注、YOLO 模型训练
- **技术栈**：Python + PyTorch + FastAPI + Vue3 + UnoCSS
- **多格式支持**：YOLO / ONNX / OpenVINO 模型
- **规则引擎**：可视化流程编排，Kahn 拓扑排序执行器
- **多种算法支持**：YOLO 目标检测、PPO/SAC 强化学习算法（engine 层）

## 项目结构

```
CogniFlow/
├── backend/                      # FastAPI 后端服务
│   ├── app.py                   # 应用入口
│   ├── database.py              # SQLAlchemy ORM + SQLite
│   ├── schemas.py               # Pydantic 模型
│   ├── websocket_manager.py     # 通用 WebSocket 管理
│   ├── core/
│   │   ├── backends/           # 推理设备自动检测
│   │   ├── formats/            # 多格式处理器 (YOLO/ONNX/OpenVINO)
│   │   └── export/             # 模型导出器
│   └── routers/                # API 路由
│       ├── atlas.py             # 图集管理
│       ├── image.py            # 图片管理
│       ├── annotation.py        # 标注管理
│       ├── category.py          # 类别管理（树形目录）
│       ├── model.py            # 模型管理 + 多格式文件
│       ├── training.py         # 训练管理 + 进度推送
│       ├── yolo_training.py    # YOLO 训练核心
│       ├── inference.py         # 图片/视频推理（双线程流水线）
│       ├── ws_stream.py        # 视频流 WebSocket 推送
│       ├── launch.py           # 模型启动（⚠️仅模拟）
│       ├── rule_engine.py      # 规则引擎 API
│       ├── websocket.py        # 通用 WebSocket
│       ├── simple_detector.py   # 简单检测器
│       └── detection_dataset.py # 检测数据集
│   └── services/
│       └── rule_engine/         # 规则引擎核心
│           ├── executor.py      # Kahn 拓扑排序 + 层内并行
│           ├── graph_manager.py # 图 CRUD + 验证
│           ├── registry.py      # 节点注册表
│           ├── scheduler.py     # Cron 定时调度
│           └── nodes/          # 17+ 节点实现
├── engine/                      # 核心视觉感知包
│   ├── core/
│   │   ├── data_input/        # ScreenCapture/VideoReader
│   │   ├── vision/            # ImagePreprocessor/CNNEncoder
│   │   ├── rl/                # ⚠️ PPO/SAC（未集成）
│   │   └── control/           # KeyboardEmulator/MouseEmulator
│   └── annotation/             # 标注工具
├── webui/                      # Vue3 前端
│   ├── src/
│   │   ├── api/              # API 调用封装
│   │   ├── components/       # 公共组件
│   │   ├── router/           # 路由配置
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── views/            # 页面组件
│   │   ├── style/            # 深色主题设计系统
│   │   ├── App.vue           # 根组件
│   │   └── main.ts           # 入口文件
│   ├── public/               # 静态资源
│   └── COGNIFLOW_DESIGN.md  # 设计规范
├── data/                       # 统一数据目录
│   ├── datasets/             # 训练数据集
│   ├── checkpoints/         # 模型权重
│   ├── model_cache/         # 模型缓存
│   ├── inference_output/    # 推理结果
│   ├── runs/                # YOLO 训练输出
│   └── database/            # SQLite 数据库
├── docs/                      # 文档
│   ├── guides/              # 教程、项目分析
│   ├── plans/               # 开发计划
│   ├── archives/            # 已完成归档
│   └── research/            # 技术研究
└── tests/                    # 单元测试
```

## 快速开始

### 后端服务

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 启动后端服务（端口 8000）
python app.py

# 或使用 uvicorn
uvicorn app:app --reload --port 8000
```

**环境变量：**

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATA_DIR` | 数据存储目录 | `./data` |
| `WEBUI_DIST` | 前端静态文件目录 | `./webui/dist` |

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
| `backend` | 构建后端（安装依赖） |
| `frontend` | 构建前端（生产环境） |
| `binary` | PyInstaller 原生二进制打包 |
| `all` | 后端 + 前端 |
| `docker` | Docker 镜像 |
| `clean` | 清理构建产物 |

### PyInstaller 打包

通过 `cogniflow.spec` 配置，支持：
- 隐藏导入：fastapi, uvicorn, sqlalchemy, opencv, ultralytics 等
- 自动启动浏览器（`argv=["--browser"]`）

## WebUI 功能

| 页面 | 功能 | 状态 |
|------|------|------|
| 控制台 | 系统概览、统计卡片、训练进度 | ✅ |
| 图集管理 | 创建图集、上传图片、目录管理 | ✅ |
| 标注工具 | 图片边界框标注、类别管理 | ✅ |
| 模型管理 | 注册模型、上传模型文件、设置最佳模型 | ✅ |
| 训练监控 | 启动训练、停止训练、实时进度监控 | ✅ |
| 模型测试 | 加载模型进行图片/视频推理检测 | ✅ |
| 模型启动 | 模型加载、图片/视频推理 | ✅ |
| 规则引擎 | 规则图管理、规则执行 | ⚠️ 画布编辑器开发中 |

## 核心模块

### 数据输入 (engine/core/data_input)

| 模块 | 说明 | 状态 |
|------|------|------|
| `ScreenCapture` | 屏幕采集 | ⚠️ 未集成 |
| `VideoReader` | 视频文件读取 | ✅ |
| `DatasetManager` | 数据集管理 | ✅ |
| `FrameBuffer` | 帧缓冲区 | ✅ |

### 视觉处理 (engine/core/vision)

| 模块 | 说明 |
|------|------|
| `ImagePreprocessor` | 图像预处理 |
| `CNNEncoder` | CNN 特征编码 |
| `UIDetector` | UI 元素检测 |

### 目标检测与模型训练

| 模块 | 说明 | 状态 |
|------|------|------|
| YOLO 检测 | 基于 Ultralytics YOLO 的目标检测 | ✅ |
| 模型训练 | 支持 YOLO 模型训练及指标监控 | ✅ |
| 模型推理 | 图片/视频推理，WebSocket 实时推送 | ✅ |
| 多格式支持 | YOLO / ONNX / OpenVINO | ✅ |
| GPU 训练 | GPU 设备选择 | ⚠️ 前端入口开发中 |

### 强化学习 (engine/core/rl)

| 模块 | 说明 | 状态 |
|------|------|------|
| `PPO` | 近端策略优化算法 | ⚠️ 未集成 |
| `SAC` | 软 Actor-Critic 算法 | ⚠️ 未集成 |
| `GameEnv` | Gymnasium 风格环境封装 | ⚠️ 未集成 |
| `Trainer` | 训练循环 | ⚠️ 未集成 |

### 规则引擎 (backend/services/rule_engine)

| 模块 | 说明 | 状态 |
|------|------|------|
| 规则图 CRUD | 创建/编辑/验证/激活/停用 | ✅ |
| Kahn 执行器 | 拓扑排序 + 层内并行执行 | ✅ |
| 节点系统 | 17+ 节点（触发器/条件/动作/逻辑） | ⚠️ 部分未连通 |
| Cron 调度 | APScheduler 定时触发 | ✅ |
| Webhook 触发 | 外部系统 POST 触发 | ✅ |
| WebSocket 推送 | 训练进度/推理流推送 | ✅ |
| 画布编辑器 | 可视化拖拽编排 | ⚠️ 开发中 |

### 多格式模型处理 (backend/core/formats)

| 模块 | 说明 |
|------|------|
| `YOLOHandler` | YOLO .pt 格式 |
| `ONNXHandler` | ONNX 格式 |
| `OpenVINOHandler` | OpenVINO 格式 |

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

详细文档请参考 [docs/](docs/)：

| 目录 | 说明 |
|------|------|
| `guides/TUTORIAL.md` | 快速开始教程和 API 参考 |
| `guides/project-analysis-2026.md` | 项目分析报告 |
| `plans/` | 进行中的开发计划 |
| `archives/` | 已完成的设计方案 |
| `research/` | 技术调研文档 |

## 许可证

MIT License
