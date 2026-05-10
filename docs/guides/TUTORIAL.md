# CogniFlow 使用教程

## 1. 项目概述

CogniFlow 是一个通用视觉感知处理框架，集模型训练、模型测试、模型推理、规则引擎于一体，核心流程：

```
图集管理 → 图片标注 → YOLO训练 → 模型推理 → 规则引擎 → 自动控制
```

**主要功能：**
- 📁 **图集管理** — 上传、管理训练图片
- 🏷️ **数据标注** — YOLO 格式目标检测标注
- 🏋️ **模型训练** — YOLO 模型训练
- 🚀 **模型推理** — 实时目标检测（图片/视频/实时流）
- 🔧 **规则引擎** — 可视化流程编排，基于检测结果触发动作

---

## 2. 快速开始

### 2.1 启动服务

```bash
# 启动后端 (FastAPI)
cd backend
pip install -r requirements.txt  # 如有需要
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
   - **上传视频** 进行视频检测
   - **实时采集** 连接屏幕进行实时检测

### 2.6 规则引擎

进入 **规则引擎** 页面：

1. **创建规则图**：点击新建，输入名称描述
2. **拖拽节点**：从左侧面板拖拽到画布
3. **配置节点**：点击节点，右侧面板设置参数
4. **连接节点**：从输出端口拖拽到输入端口
5. **执行规则**：保存后点击 **执行**

---

## 3. 目录结构

```
CogniFlow/
├── backend/                 # FastAPI 后端
│   ├── app.py              # 主入口
│   ├── database.py         # SQLAlchemy 模型
│   ├── schemas.py          # Pydantic 模型
│   ├── routers/            # API 路由
│   │   ├── atlas.py        # 图集管理
│   │   ├── image.py        # 图片管理
│   │   ├── annotation.py   # 标注管理
│   │   ├── category.py     # 类别管理
│   │   ├── model.py        # 模型管理
│   │   ├── training.py     # 训练管理
│   │   ├── yolo_training.py # YOLO 训练
│   │   ├── inference.py    # 推理
│   │   ├── launch.py       # 启动/推理
│   │   ├── rule_engine.py  # 规则引擎
│   │   ├── websocket.py    # WebSocket
│   │   └── ws_stream.py    # 视频流 WebSocket
│   └── services/
│       └── rule_engine/    # 规则引擎核心
│           ├── executor.py     # 执行器
│           ├── graph_manager.py # 图管理
│           ├── registry.py     # 节点注册
│           └── nodes/          # 节点实现
│               ├── base.py
│               ├── triggers.py
│               ├── conditions.py
│               ├── actions.py
│               └── logic.py
├── webui/                  # Vue3 前端
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   │   ├── AtlasList.vue
│   │   │   ├── AtlasDetail.vue
│   │   │   ├── Annotate.vue
│   │   │   ├── ModelList.vue
│   │   │   ├── Training.vue
│   │   │   ├── Launch.vue
│   │   │   ├── RuleList.vue   # 规则列表
│   │   │   └── RuleCanvas.vue # 规则编辑
│   │   ├── api/
│   │   │   └── index.ts    # API 调用
│   │   └── router/
│   └── package.json
├── engine/             # Python 核心包
│   ├── core/
│   │   ├── data_input/     # 数据输入
│   │   │   ├── capture/    # 屏幕/视频采集
│   │   │   └── storage/    # 数据集管理
│   │   ├── vision/         # 视觉处理
│   │   │   ├── detector/   # YOLO 检测器
│   │   │   ├── features/   # 特征提取
│   │   │   └── preprocessor/
│   │   ├── rl/             # 强化学习
│   │   │   ├── algorithms/ # PPO/SAC
│   │   │   ├── environment/
│   │   │   └── trainer/
│   │   └── control/        # 输入控制
│   │       ├── input_emulator/ # 键盘/鼠标
│   │       └── controller/
│   ├── annotation/         # 标注工具
│   └── config/             # 配置管理
├── docs/
│   ├── TUTORIAL.md          # 使用教程
│   ├── project-analysis-2026.md  # 项目分析文档
│   ├── plans/               # 进行中的开发计划
│   ├── archives/            # 已完成的计划/设计文档
│   └── research/            # 规则引擎研发文档
└── tests/
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

### 4.6 规则引擎

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
GET    /api/rule-engine/executions/:id      # 获取执行详情
```

---

## 5. 常见问题

### Q: 训练中断后能继续吗？
A: 可以，训练任务支持断点续传，重新开始训练会自动加载已有进度。

### Q: 支持哪些 YOLO 版本？
A: 当前使用 Ultralytics YOLO v8 格式。

### Q: 规则引擎支持循环吗？
A: 支持，使用 **循环** 节点，可设置最大迭代次数。

### Q: 如何实现实时检测？
A: 在 **模型启动** 页面，选择 **实时采集** 模式连接屏幕。

### Q: 规则引擎能同时触发多个动作吗？
A: 可以，使用 **并行分支** 节点可同时执行多个分支。

### Q: 如何选择 GPU 训练？
A: 在 **模型训练** 页面，点击设备选择器选择 GPU 设备。

---

## 6. 更新日志

| 版本 | 日期 | 说明 |
|-----|------|------|
| 0.2.0 | 2026-05-06 | 更新目录结构；添加 GPU 训练、实时流推理说明 |
| 0.1.0 | 2026-04 | 初始版本，包含图集管理、标注、YOLO训练、规则引擎 |
