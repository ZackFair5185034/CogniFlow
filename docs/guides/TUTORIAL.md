# CogniFlow 使用教程

## 1. 项目概述

CogniFlow 是一个通用视觉感知处理框架，集模型训练、模型测试、模型推理、规则引擎于一体，核心流程：

```
图集管理 → 图片标注 → YOLO训练 → 模型推理 → 规则引擎 → 自动控制
```

**主要功能：**

- 📁 **图集管理** — 上传、管理训练图片，支持目录组织
- 🏷️ **数据标注** — YOLO 格式目标检测标注，SVG 边界框绘制
- 🏋️ **模型训练** — YOLO 模型训练，支持 GPU，实时 mAP 指标
- 🚀 **模型推理** — 图片/视频检测，WebSocket 实时流推送
- 🔧 **规则引擎** — 可视化流程编排，Kahn 拓扑排序执行器

---

## 2. 快速开始

### 2.1 启动服务

```bash
# 启动后端 (FastAPI)
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# 启动前端 (新终端)
cd webui
pnpm install
pnpm dev
```

访问 `http://localhost:5173`

### 2.2 创建图集并上传图片

1. 点击左侧菜单 **图集管理**
2. 点击 **新建图集**，输入名称
3. 进入图集详情，点击 **上传图片** 按钮

### 2.3 标注数据

1. 在图集详情选中一张或多张图片
2. 点击 **开始标注**
3. 在标注页面：
   - 左侧选择或创建类别（支持树形目录）
   - 按住鼠标左键拖动绘制边界框
   - 快捷键：`A/D` 切换上一张/下一张，`W` 创建新类别

### 2.4 训练模型

1. 进入 **模型管理**
2. 点击 **新建模型**，选择绑定的图集
3. 进入 **模型训练** 页面，选中模型点击 **开始训练**
4. 训练过程中可查看 loss、mAP 等指标曲线
5. 训练完成后可 **设为最佳**

### 2.5 模型推理测试

1. 进入 **模型启动**
2. 选择训练好的模型，点击 **加载模型**
3. 可选择：
   - **上传图片** 进行图片检测
   - **上传视频** 进行视频检测（WebSocket 实时推送）

### 2.6 规则引擎

进入 **规则引擎** 页面：

1. **创建规则图**：点击新建，输入名称描述
2. **查看节点**：访问节点定义列表
3. **配置规则**：通过 API 或直接编辑 JSON
4. **执行规则**：保存后点击 **执行**

> ⚠️ 注意：画布可视化编辑器（拖拽节点、连接端口）正在开发中，当前通过 API 进行配置。

---

## 3. 目录结构

```
CogniFlow/
├── backend/                 # FastAPI 后端
│   ├── app.py              # 主入口
│   ├── database.py         # SQLAlchemy ORM + SQLite
│   ├── schemas.py          # Pydantic 模型
│   ├── websocket_manager.py # WebSocket 管理
│   ├── routers/            # API 路由
│   │   ├── atlas.py        # 图集管理
│   │   ├── image.py        # 图片管理
│   │   ├── annotation.py   # 标注管理
│   │   ├── category.py     # 类别管理（树形目录）
│   │   ├── model.py        # 模型管理 + 多格式文件
│   │   ├── training.py     # 训练管理 + 进度推送
│   │   ├── yolo_training.py # YOLO 训练核心
│   │   ├── inference.py    # 图片/视频推理（流水线）
│   │   ├── ws_stream.py   # 视频流 WebSocket
│   │   ├── launch.py      # 模型启动（⚠️仅模拟）
│   │   ├── rule_engine.py # 规则图 CRUD + 执行
│   │   ├── websocket.py    # 通用 WebSocket
│   │   ├── simple_detector.py # 简单检测器
│   │   └── detection_dataset.py # 检测数据集
│   ├── core/
│   │   ├── backends/      # 推理设备自动检测
│   │   ├── formats/       # 多格式处理器 (YOLO/ONNX/OpenVINO)
│   │   └── export/        # 模型导出器
│   └── services/
│       └── rule_engine/    # 规则引擎核心
│           ├── executor.py     # Kahn 拓扑排序执行器
│           ├── graph_manager.py # 图管理
│           ├── registry.py     # 节点注册
│           ├── scheduler.py   # Cron 调度器
│           ├── websocket_manager.py # 规则 WS 推送
│           └── nodes/        # 节点实现
│               ├── base.py
│               ├── triggers.py    # 触发器节点
│               ├── conditions.py  # 条件节点
│               ├── actions.py     # 动作节点
│               ├── logic.py      # 逻辑节点
│               ├── detection_nodes.py
│               ├── input_nodes.py
│               ├── output_nodes.py
│               └── processing_nodes.py
├── webui/                  # Vue3 前端
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   │   ├── Home.vue        # 控制台
│   │   │   ├── AtlasList.vue   # 图集列表
│   │   │   ├── AtlasDetail.vue # 图集详情
│   │   │   ├── Annotate.vue    # 标注页面
│   │   │   ├── ModelList.vue   # 模型列表
│   │   │   ├── Training.vue    # 训练页面
│   │   │   ├── Launch.vue      # 模型启动
│   │   │   ├── RuleList.vue    # 规则列表
│   │   │   └── RuleCanvas.vue  # ⚠️ 规则画布（开发中）
│   │   ├── api/           # API 调用封装
│   │   ├── stores/         # Pinia 状态管理
│   │   └── router/         # 路由配置
│   └── COGNIFLOW_DESIGN.md # 设计规范
├── engine/                 # Python 核心包
│   ├── core/
│   │   ├── data_input/    # 数据输入
│   │   │   ├── capture/  # 屏幕/视频采集
│   │   │   └── storage/  # 数据集管理
│   │   ├── vision/        # 视觉处理
│   │   │   ├── detector/ # YOLO 检测器
│   │   │   ├── features/ # 特征提取
│   │   │   └── preprocessor/
│   │   ├── rl/           # ⚠️ 强化学习（未集成）
│   │   │   ├── algorithms/ # PPO/SAC
│   │   │   ├── environment/
│   │   │   └── trainer/
│   │   └── control/      # 输入控制
│   │       └── input_emulator/ # 键盘/鼠标
│   ├── annotation/       # 标注工具
│   └── config/           # 配置管理
├── data/                  # 统一数据目录
│   ├── datasets/         # 训练数据集
│   ├── checkpoints/      # 模型权重
│   ├── model_cache/      # 模型缓存
│   ├── inference_output/ # 推理结果
│   ├── runs/            # YOLO 训练输出
│   └── database/        # SQLite 数据库
├── docs/                 # 文档
│   ├── guides/          # 活跃文档
│   ├── plans/           # 开发计划
│   ├── archives/        # 已完成归档
│   └── research/        # 技术研究
└── tests/               # 单元测试
```

---

## 4. API 参考

### 4.1 图集管理

```
GET    /api/atlas                 # 获取图集列表
POST   /api/atlas                 # 创建图集
GET    /api/atlas/:id             # 获取图集详情
PUT    /api/atlas/:id             # 更新图集
DELETE /api/atlas/:id             # 删除图集
GET    /api/atlas/:id/images      # 获取图片列表
POST   /api/atlas/:id/images      # 上传图片
POST   /api/atlas/:id/directories # 创建目录
DELETE /api/atlas/:id/images/:imageId # 删除图片
GET    /api/atlas/:id/export-yolo # 导出 YOLO 格式
```

### 4.2 类别管理

```
GET    /api/categories            # 获取类别列表
GET    /api/categories/tree       # 获取树形结构
POST   /api/categories            # 创建类别
PUT    /api/categories/:id        # 更新类别
DELETE /api/categories/:id        # 删除类别
```

### 4.3 标注管理

```
GET    /api/annotations/image/:id  # 获取图片的标注
POST   /api/annotations           # 创建标注
PUT    /api/annotations/:id       # 更新标注
DELETE /api/annotations/:id       # 删除标注
POST   /api/annotations/batch     # 批量创建标注
```

### 4.4 模型管理

```
GET    /api/models                 # 获取模型列表
POST   /api/models                 # 创建模型
GET    /api/models/:id             # 获取模型详情
PUT    /api/models/:id             # 更新模型
DELETE /api/models/:id            # 删除模型
POST   /api/models/:id/set-best   # 设为最佳
POST   /api/models/:id/upload     # 上传模型文件
GET    /api/models/:id/files      # 获取模型文件列表
POST   /api/models/:id/export     # 导出模型格式
GET    /api/models/formats        # 获取支持的格式列表
```

### 4.5 训练

```
GET    /api/training/jobs          # 获取训练任务列表
POST   /api/training/start         # 开始训练
POST   /api/training/stop         # 停止训练
DELETE /api/training/jobs/:id     # 删除任务
GET    /api/training/jobs/:id/metrics-history # 获取指标历史
GET    /api/training/device-info   # 获取可用 GPU 设备
```

### 4.6 推理

```
POST   /api/inference/image       # 图片推理
POST   /api/inference/video       # 视频推理
GET    /api/inference/jobs/:id    # 获取推理任务状态
WS     /ws/stream/:job_id        # 视频流 WebSocket
```

### 4.7 规则引擎

```
# 规则图管理
GET    /api/rule-engine/graphs              # 获取规则图列表
POST   /api/rule-engine/graphs              # 创建规则图
GET    /api/rule-engine/graphs/:id          # 获取规则图
PUT    /api/rule-engine/graphs/:id          # 更新规则图
DELETE /api/rule-engine/graphs/:id          # 删除规则图
POST   /api/rule-engine/graphs/:id/validate # 验证规则图
POST   /api/rule-engine/graphs/:id/activate # 激活规则图
POST   /api/rule-engine/graphs/:id/deactivate # 停用规则图

# 节点定义
GET    /api/rule-engine/nodes/definitions   # 获取所有节点类型定义

# 执行
POST   /api/rule-engine/execute             # 执行规则图
GET    /api/rule-engine/executions          # 获取执行历史
GET    /api/rule-engine/executions/:id     # 获取执行详情

# Webhook 触发
POST   /api/rule-engine/webhook/:graph_id  # Webhook 触发

# 定时调度
POST   /api/rule-engine/schedule           # 创建定时任务
GET    /api/rule-engine/schedule           # 获取定时任务列表
DELETE /api/rule-engine/schedule/:id      # 删除定时任务
```

### 4.8 通用 WebSocket

```
WS     /ws                              # 通用 WebSocket 连接
```

---

## 5. 常见问题

### Q: 训练中断后能继续吗？
A: 可以，训练任务支持断点续传，重新开始训练会自动加载已有进度。

### Q: 支持哪些模型格式？
A: 支持 YOLO (.pt)、ONNX (.onnx)、OpenVINO 三种格式。

### Q: 如何导出模型？
A: 在模型详情页点击导出按钮，选择目标格式（onnx/openvino/tensorrt）。

### Q: 规则引擎支持循环吗？
A: 支持，使用 **循环** 节点，可设置最大迭代次数。

### Q: 视频推理如何实时查看？
A: 视频推理通过 WebSocket 实时推送检测结果，浏览器自动更新画面。

### Q: 如何选择 GPU 训练？
A: 在 **模型训练** 页面，点击设备选择器选择 GPU 设备（⚠️ 前端入口开发中）。

### Q: 画布编辑器如何使用？
A: ⚠️ 可视化拖拽编辑器正在开发中，当前通过 API 进行规则配置。

---

## 6. 更新日志

| 版本 | 日期 | 说明 |
|-----|------|------|
| 0.3.0 | 2026-05-10 | 更新项目结构；修正 API 端点；标注开发中功能 |
| 0.2.0 | 2026-05-06 | 更新目录结构；添加 GPU 训练、实时流推理说明 |
| 0.1.0 | 2026-04 | 初始版本，包含图集管理、标注、YOLO训练、规则引擎 |
