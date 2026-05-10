# CogniFlow 项目分析文档

> 分析日期：2026-05-10
> 分支：develop
> 用途：记录现状和迭代计划，供后续讨论

---

## 一、项目现状总览

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | FastAPI + SQLAlchemy | Python 3.x |
| 前端 | Vue3 + TypeScript + Vite | UnoCSS 原子化 CSS + Element Plus |
| 深度学习 | Ultralytics YOLO (v8) | PyTorch 训练/推理 |
| 数据库 | SQLite | 轻量嵌入式 |
| 规则引擎 | 自研 Kahn 拓扑排序执行器 | 节点化设计 + WebSocket 推送 |
| 视频处理 | OpenCV + ffmpeg-python | 视频流处理 |

### 项目结构

```
CogniFlow/
├── backend/
│   ├── app.py                   # 应用入口
│   ├── database.py              # SQLAlchemy ORM + SQLite
│   ├── schemas.py               # Pydantic 模型
│   ├── websocket_manager.py     # 通用 WebSocket 管理
│   ├── core/
│   │   ├── backends/           # 推理设备自动检测
│   │   ├── formats/            # 多格式处理器 (YOLO/ONNX/OpenVINO)
│   │   └── export/             # 模型导出器
│   ├── routers/
│   │   ├── atlas.py            # 图集管理
│   │   ├── image.py            # 图片上传/管理
│   │   ├── annotation.py       # 标注 CRUD
│   │   ├── category.py         # 类别树管理
│   │   ├── model.py            # 模型元数据 + 多格式文件管理
│   │   ├── training.py         # YOLO 训练启动/停止/进度
│   │   ├── yolo_training.py    # YOLO 训练核心逻辑
│   │   ├── inference.py        # 图片/视频推理（双线程流水线）
│   │   ├── ws_stream.py       # 视频流 WebSocket 推送
│   │   ├── launch.py           # 模型加载（⚠️仅模拟）
│   │   ├── rule_engine.py      # 规则图 CRUD + 执行 API
│   │   ├── websocket.py        # 通用 WebSocket
│   │   ├── simple_detector.py  # 简单检测器
│   │   └── detection_dataset.py # 检测数据集
│   └── services/
│       └── rule_engine/
│           ├── executor.py       # Kahn 拓扑排序 + 层内并行执行
│           ├── graph_manager.py  # 图 CRUD + 验证
│           ├── registry.py       # 节点注册表
│           ├── scheduler.py      # Cron 定时调度器
│           ├── websocket_manager.py # 规则执行 WS 推送
│           └── nodes/
│               ├── base.py        # 基类
│               ├── triggers.py    # Manual/Timer/YOLO/Webhook 触发器
│               ├── conditions.py  # ObjectExists/ConfidenceThreshold/VariableCondition
│               ├── actions.py      # Log/HttpRequest/Delay 动作
│               ├── logic.py       # Branch/ParallelBranch/Loop/VariableSet
│               ├── detection_nodes.py # ImageInput/VideoInput/YOLODetect
│               ├── input_nodes.py
│               ├── output_nodes.py
│               └── processing_nodes.py
├── webui/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue        # 控制台
│   │   │   ├── AtlasList.vue   # 图集列表
│   │   │   ├── AtlasDetail.vue # 图集详情
│   │   │   ├── Annotate.vue    # 标注页面
│   │   │   ├── ModelList.vue   # 模型列表
│   │   │   ├── Training.vue    # 训练页面
│   │   │   ├── Launch.vue      # 推理启动页
│   │   │   ├── RuleList.vue    # 规则列表
│   │   │   └── RuleCanvas.vue  # ⚠️ 规则画布（空壳）
│   │   ├── api/
│   │   ├── stores/
│   │   ├── router/
│   │   └── style/              # 深色主题设计系统
│   └── COGNIFLOW_DESIGN.md   # 设计规范
├── engine/                     # 核心视觉感知包
│   ├── core/
│   │   ├── data_input/        # ScreenCapture/VideoReader/DatasetManager
│   │   ├── vision/            # ImagePreprocessor/CNNEncoder/UIDetector
│   │   ├── rl/                # PPO/SAC/GameEnv/Trainer（⚠️未集成）
│   │   └── control/           # KeyboardEmulator/MouseEmulator
│   └── annotation/            # BoundingBoxAnnotator/LabelTool
└── data/                      # 统一数据目录（2026-05 重构）
    ├── datasets/              # 训练数据集
    ├── checkpoints/           # 模型权重
    ├── model_cache/           # 模型缓存
    ├── inference_output/      # 推理结果
    └── runs/                  # YOLO 训练输出
```

### 已实现功能 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| **图集管理** | ✅ 完整 | 上传/标注/目录管理/YOLO 格式导出 |
| **类别管理** | ✅ 完整 | 树形目录结构，支持嵌套 |
| **标注管理** | ✅ 完整 | 边界框标注 CRUD |
| **模型训练** | ✅ 完整 | YOLO 训练 + ckpt 解析 + mAP 指标记录 |
| **模型推理** | ✅ 完整 | 图片/视频检测，流水线架构 |
| **视频流 WebSocket** | ✅ 完整 | 双线程流水线 + 动态 JPEG 压缩 |
| **训练进度 WebSocket** | ✅ 完整 | 实时推送 loss/mAP 指标 |
| **规则图 CRUD** | ✅ 完整 | 创建/编辑/验证/激活/停用 |
| **规则引擎执行器** | ✅ 完整 | Kahn 拓扑排序 + 层内并行执行 |
| **规则引擎节点系统** | ✅ 17+ 节点 | 触发器/条件/动作/逻辑/检测节点 |
| **节点注册表** | ✅ 完整 | @register 装饰器 |
| **Cron 定时调度** | ✅ 完整 | APScheduler 集成 |
| **Webhook 触发** | ✅ 完整 | 外部系统可 POST 触发 |
| **多格式模型管理** | ✅ 完整 | YOLO/ONNX/OpenVINO handler |
| **模型导出** | ✅ 完整 | onnx/openvino/tensorrt 格式 |
| **设备自动检测** | ✅ 完整 | 推理设备自动选择 |
| **DATA_DIR 统一数据** | ✅ 完整 | 2026-05 重构 |
| **深色主题 UI** | ✅ 完整 | UnoCSS + CSS 变量设计系统 |
| **WebUI 路由进度条** | ✅ 完整 | nprogress 集成 |

### 待完善功能 ⚠️

| 模块 | 问题 | 优先级 |
|------|------|--------|
| **GPU 训练** | device 参数未暴露给前端 | P0 |
| **GPU 推理** | inference 不传 device，硬编码 CPU | P0 |
| **画布编辑器** | RuleCanvas.vue 是空壳，无 VueFlow 集成 | P0 |
| **规则引擎节点连通** | YOLO触发/键盘/鼠标节点未与 engine 层打通 | P0 |
| **执行状态 WebSocket 高亮** | 规则执行时画布节点高亮未实现 | P1 |
| **LoopNode 迭代逻辑** | 执行器未处理循环迭代 | P1 |
| **Launch 实时采集** | ScreenCapture 存在但未对接 launch.py | P2 |
| **强化学习模块** | engine/rl 完整但无 API/前端/文档 | P2 |
| **系统托盘** | 有设计文档但无实现 | P3 |

---

## 二、架构亮点

### 2.1 多格式模型处理架构

`backend/core/formats/` 实现了工厂模式的多格式处理器：

```
backend/core/formats/
├── base.py          # FormatHandler 基类
├── yolo_handler.py  # YOLO .pt 格式
├── onnx_handler.py  # ONNX 格式
└── openvino_handler.py # OpenVINO 格式
```

特性：
- 运行时自动选择最优格式
- 统一接口 `FormatHandler`
- 支持格式转换和导出

### 2.2 推理流水线架构

`inference.py` 中的双线程流水线：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  _inference_worker │ → │ _encode_worker    │ → │ WebSocket 推送   │
│  (推理线程)       │     │ (JPEG 编码线程)   │     │ (前端渲染)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

优化特性：
- 推理与编码分离，避免阻塞
- 动态 JPEG 压缩质量自适应
- 视频抽帧策略
- 实时 FPS 显示

### 2.3 规则引擎执行器

`executor.py` 实现的执行模型：

```python
# Kahn 拓扑排序：确保依赖节点先执行
sorted_nodes = topological_sort(nodes, edges)

# 层内并行执行：同一层的节点可以并发
for layer in layers:
    await asyncio.gather(*[execute_node(n) for n in layer])
```

端口类型兼容性矩阵：
- `ANY` — 接受任何类型
- `IMAGE/BBOX/MASK/SCORES` — 图像相关
- `TRIGGER/CONTROL` — 控制流
- `MODEL/INT/FLOAT/BOOLEAN/STRING/ARRAY/OBJECT` — 数据类型

### 2.4 统一数据目录

2026-05 重构将所有数据统一到 `data/` 目录：

```
data/
├── datasets/           # 训练数据集 (YOLO 格式)
├── checkpoints/        # 模型权重文件
├── model_cache/        # 模型缓存
├── inference_output/  # 推理结果图片
├── runs/              # YOLO 训练输出
│   └── detect/        # 推理结果
│   └── train/         # 训练输出
└── database/          # SQLite 数据库
```

---

## 三、规则引擎详细分析

### 3.1 节点分类（17+ 节点）

| 分类 | 节点 | 状态 |
|------|------|------|
| **触发器** | ManualTrigger | ✅ 可用 |
| | TimerTrigger | ⚠️ 框架完成，未记录上次触发时间 |
| | YOLOTrigger | ⚠️ 未对接推理服务 |
| | WebhookTrigger | ✅ 可用 |
| **条件** | ObjectExistsCondition | ✅ 可用 |
| | ConfidenceThreshold | ✅ 可用 |
| | VariableCondition | ✅ 可用 |
| | CountCondition | ✅ 可用 |
| **动作** | LogAction | ✅ 可用 |
| | HttpRequestAction | ✅ 可用 |
| | DelayAction | ✅ 可用 |
| | KeyboardAction | ⚠️ 未对接 engine 模块 |
| | MouseAction | ⚠️ 未对接 engine 模块 |
| **逻辑** | BranchNode | ✅ 可用 |
| | ParallelBranch | ⚠️ 框架完成 |
| | LoopNode | ⚠️ 执行器未处理迭代 |
| | VariableSet/GetVariable | ✅ 可用 |
| **检测** | ImageInput | ✅ 可用 |
| | VideoInput | ✅ 可用 |
| | ScreenCapture | ⚠️ 未集成 |
| | YOLODetect | ⚠️ 未对接 |
| **输出** | DisplayResult | ✅ 可用 |
| | SaveResult | ✅ 可用 |
| **处理** | ImagePreprocess | ⚠️ 框架完成 |
| | DrawBBox | ⚠️ 框架完成 |
| | CountObjects | ⚠️ 框架完成 |

### 3.2 前端现状

- `RuleList.vue`：规则图列表页，包含创建/删除/激活/停用
- `RuleCanvas.vue`：空壳组件，无 VueFlow/ReactFlow 集成
- 无节点面板（节点搜索/拖放）
- 无属性配置面板

### 3.3 连通性缺失的典型场景

**目标场景**："检测到金币 → 按空格键"

```
用户手动触发
    ↓
YOLOTriggerNode（⚠️ 未对接推理）
    ↓
ObjectExistsConditionNode（✅ 可用）
    ↓
KeyboardActionNode（⚠️ 未对接 engine）
```

---

## 四、GPU 相关问题

### 4.1 训练 GPU 支持

**现状**：
- `check_gpu_available()` 返回 GPU 列表，支持多卡 ✅
- 训练 API `/api/training/device-info` 返回设备信息 ✅
- `yolo_training.py` 的 `train_yolo()` 支持 `device` 参数 ✅
- **前端没有暴露 GPU 选择 UI** ❌

**需要改动**：
- Training.vue 添加设备选择器
- 将 `device` 参数传给 `/api/training/start`

### 4.2 推理 GPU 支持

**现状**：
- `inference_yolo()` 不传 device，默认 CPU
- `backend/core/backends/auto_detector.py` 已有设备检测

**需要改动**：
- inference.py 添加 device 参数
- 前端暴露设备选择

---

## 五、engine 模块分析

### 5.1 已实现但未集成的模块

| 模块 | 文件 | 说明 |
|------|------|------|
| **ScreenCapture** | `engine/core/data_input/capture/screen_capture.py` | 屏幕采集，未对接 launch.py |
| **强化学习** | `engine/core/rl/ppo.py, sac.py, game_env.py, trainer.py` | 完整实现，无 API/前端 |
| **输入模拟** | `engine/core/control/input_emulator/` | Keyboard/Mouse Emulator，规则引擎未对接 |
| **标注工具** | `engine/annotation/bounding_box.py` | 独立实现，后端未使用 |

### 5.2 集成建议

1. **短期**：优先打通规则引擎与 engine 的连通
2. **中期**：集成 ScreenCapture 到 Launch 页面
3. **长期**：暴露 RL 功能通过 API

---

## 六、迭代计划

### Phase 0: 连通性补全（当前最优先）

| 任务 | 说明 | 状态 |
|------|------|------|
| YOLO 触发器对接推理服务 | 调用 inference API | ⚠️ 待做 |
| 键盘/鼠标动作对接 engine | input_emulator 集成 | ⚠️ 待做 |
| WebSocket 实时状态推送 | 节点执行时前端高亮 | ⚠️ 待做 |
| GPU 训练入口 | 前端设备选择器 | ⚠️ 待做 |

### Phase 1: 画布编辑器

| 任务 | 说明 | 状态 |
|------|------|------|
| VueFlow 集成 | 画布渲染 | ⚠️ 待做 |
| 节点面板 | 节点搜索/拖放 | ⚠️ 待做 |
| 属性配置面板 | 节点参数配置 | ⚠️ 待做 |

### Phase 2: 调试能力

| 任务 | 说明 |
|------|------|
| 断点设置 | 节点级别断点 |
| 单步执行 | next/continue |
| 变量监视 | context.variables 当前值 |

### Phase 3: 类型安全

| 任务 | 说明 |
|------|------|
| 端口类型化 | 类型不匹配禁止连接 |
| Field 批量处理 | detections 数组批量过滤/映射 |

---

## 七、文档体系

| 目录 | 说明 |
|------|------|
| `guides/` | 活跃文档：教程、项目分析 |
| `plans/` | 进行中计划 |
| `archives/` | 已完成归档：设计文档、已实现方案 |
| `research/` | 技术研究：画布编辑器、规则引擎调研 |

---

## 八、优先级总结

| 优先级 | 事项 | 理由 |
|--------|------|------|
| **P0** | 规则引擎节点连通性 | 核心不连通，规则引擎无法实际工作 |
| **P0** | GPU 训练入口 | 前端加设备选择，后端已支持 |
| **P0** | 画布编辑器 | 前端工作量较大，尽早启动 |
| **P1** | GPU 推理支持 | inference 添加 device 参数 |
| **P1** | WebSocket 执行高亮 | 调试体验关键 |
| **P2** | LoopNode 迭代逻辑 | 复杂规则需要 |
| **P2** | ScreenCapture 集成 | Launch 页面的"实时采集" |
| **P3** | 强化学习模块 | 长期目标 |
