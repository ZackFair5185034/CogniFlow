# CogniFlow 项目分析文档

> 分析日期：2026-05-05
> 分支：feature/project-analysis-2026
> 用途：记录现状和迭代计划，供后续讨论

---

## 一、项目现状总览

### 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | FastAPI + SQLAlchemy | Python 3.x |
| 前端 | Vue3 + TypeScript + Vite | UnoCSS 原子化 CSS |
| 深度学习 | Ultralytics YOLO (v8) | PyTorch 训练/推理 |
| 数据库 | SQLite | 轻量嵌入式 |
| 规则引擎 | 自研异步图执行器 | 节点化设计 |

### 项目结构

```
CogniFlow/
├── backend/
│   ├── routers/
│   │   ├── inference.py       # 图片/视频检测
│   │   ├── training.py        # 训练任务管理
│   │   ├── model.py           # 模型管理
│   │   ├── atlas.py          # 图集管理
│   │   ├── category.py       # 类别管理
│   │   ├── rule_engine.py    # 规则引擎 API
│   │   └── ws_stream.py      # 视频流 WebSocket
│   ├── services/rule_engine/
│   │   ├── nodes/
│   │   │   ├── triggers.py   # 触发器节点
│   │   │   ├── conditions.py # 条件节点
│   │   │   ├── actions.py    # 动作节点
│   │   │   └── logic.py      # 逻辑控制节点
│   │   ├── executor.py       # 图执行器
│   │   ├── graph_manager.py  # 图 CRUD
│   │   └── registry.py       # 节点注册表
│   └── database.py           # SQLAlchemy 模型
├── webui/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Launch.vue    # 推理启动页
│   │   │   ├── Training.vue  # 训练页
│   │   │   ├── RuleList.vue  # 规则列表
│   │   │   ├── Annotate.vue  # 标注页
│   │   │   └── ...
│   │   └── style/index.scss  # 深色主题设计系统
│   └── COGNIFLOW_DESIGN.md  # 设计规范
├── engine/                   # 核心视觉感知包（未完全集成）
│   └── core/
│       ├── vision/          # 目标检测/特征提取
│       ├── rl/              # 强化学习
│       └── control/         # 输入模拟（键盘/鼠标）
└── data/                    # 数据目录
    ├── checkpoints/         # 模型权重
    ├── inference_output/   # 推理结果
    ├── datasets/            # 训练数据集
    └── runs/               # YOLO 训练输出
```

### 已实现功能 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| **图集管理** | ✅ 完整 | 上传/标注/导出 YOLO 格式 |
| **模型训练** | ✅ 基本可用 | YOLO 训练 + ckpt 解析填充 metrics |
| **模型推理** | ✅ 基本可用 | 图片/视频检测，前端 SVG 绘制检测框 |
| **规则引擎** | ⚠️ 骨架完整 | CRUD + 节点系统已完成，核心未连通 |
| **WebUI** | ✅ 基本可用 | 深色主题 UI，UnoCSS 原子化样式 |
| **WebSocket** | ✅ 基本可用 | 视频流推送 + 训练进度推送 |

### 待完善功能 ⚠️

| 模块 | 问题 |
|------|------|
| **GPU 训练** | device 参数未暴露给前端，无 GPU 选择入口 |
| **GPU 推理** | inference 不传 device，硬编码 CPU |
| **规则引擎** | YOLO 触发器未对接推理服务，键盘/鼠标动作未对接 engine 模块 |
| **画布编辑器** | 前端 RuleList 只有列表，无可视化编辑器 |
| **多格式支持** | 只支持 .pt (YOLO ckpt)，无 ONNX/TensorRT 等 |

---

## 二、规则引擎现状与迭代计划

### 2.1 现状分析

#### 已实现组件

```
backend/services/rule_engine/
├── nodes/
│   ├── triggers.py          # YOLO触发器(框架)/定时器/手动触发
│   ├── conditions.py        # 目标存在/置信度阈值/变量条件
│   ├── actions.py          # 键盘⚠️/鼠标⚠️(均TODO)/HTTP请求/日志
│   └── logic.py            # 分支/并行分支/循环/延迟/设置变量
├── executor.py              # 异步图遍历执行器
├── graph_manager.py         # 图 CRUD + 验证
└── registry.py            # 节点类型注册表
```

#### 连通性问题

| 节点类型 | 状态 | 说明 |
|----------|------|------|
| `YOLOTriggerNode` | ⚠️ 框架完成 | 读取 `context.trigger_data`，未对接实际推理 |
| `TimerTriggerNode` | ⚠️ 框架完成 | 每次都触发，未记录上次触发时间 |
| `KeyboardActionNode` | ⚠️ TODO | 有 `engine.core.control.input_emulator` 接口但未对接 |
| `MouseActionNode` | ⚠️ TODO | 同上 |
| `HttpRequestActionNode` | ✅ 可用 | 完整实现 |
| `LogActionNode` | ✅ 可用 | 完整实现 |
| `BranchNode` | ✅ 可用 | 完整实现 |
| `LoopNode` | ⚠️ 框架完成 | 执行器未处理迭代逻辑 |

#### 前端现状

- `RuleList.vue`：规则图列表页，包含创建/删除/激活/停用
- 无画布编辑器（VueFlow / ReactFlow 尚未集成）
- 无节点配置面板

### 2.2 迭代计划

#### Phase 1：核心连通（让规则引擎真正跑起来）

**目标**：实现一个完整场景 —— "检测到金币 → 按空格键"

| 任务 | 说明 | 工作量 |
|------|------|--------|
| YOLO 触发器对接推理服务 | `YOLOTriggerNode._execute` 调用 `inference_yolo()` 或推理 API | 中 |
| 键盘动作对接 `engine/input_emulator` | 将 `KeyboardActionNode` 的 TODO 改为真实调用 | 中 |
| 鼠标动作对接 `engine/input_emulator` | 同上 | 中 |
| 推理结果传递给触发器 | `trigger_data` 格式定义和传递 | 小 |
| 触发器配置项完善 | `class_names`/`min_confidence` 从配置读取 | 小 |

**触发器 → 动作的典型流程**：

```
用户手动触发（或定时触发）
    ↓
YOLOTriggerNode 执行：
  1. 读取配置的 model_id、class_names、min_confidence
  2. 调用推理服务获取 detections
  3. 过滤符合条件的检测结果
  4. 如果有匹配 → triggered=True，存入 context
    ↓
ObjectExistsConditionNode 执行：
  1. 读取 detections
  2. 检查 class_names、min_count
  3. 输出 true/false 到分支
    ↓
BranchNode 执行：
  1. 根据条件选择分支
    ↓
KeyboardActionNode 执行：
  1. 读取 keys 配置
  2. 调用 input_emulator.press(key)
```

#### Phase 2：画布编辑器

| 任务 | 说明 | 工作量 |
|------|------|--------|
| VueFlow 集成 | 拖拽节点、缩放、画布操作 | 大 |
| 节点面板 | 显示所有节点类型，支持拖入画布 | 中 |
| 节点配置面板 | 点击节点显示配置项 | 中 |
| 连线操作 | 拖拽连接点建立边 | 中 |
| 保存/部署 | 实时保存图配置到后端 | 小 |
| 执行预览 | 从画布触发一次执行并高亮路径 | 中 |

#### Phase 3：功能完善

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 执行历史 | 每次执行记录到数据库，可回放 | 中 |
| 节点日志 | 每个节点的输入/输出/耗时记录 | 小 |
| 变量系统增强 | 跨节点传递复杂数据（检测结果等） | 中 |
| 并行执行 | ParallelBranchNode 真正并行运行 | 中 |
| 定时器完善 | 记录上次触发时间，支持 cron 表达式 | 小 |
| 循环执行 | LoopNode 迭代逻辑落地 | 中 |

---

## 三、GPU 相关问题

### 3.1 训练 GPU 支持

#### 当前问题

- `check_gpu_available()` 只检查 `torch.cuda.is_available()`，返回设备信息
- 训练配置 `config` 有 `device` 字段，但**前端没有暴露 GPU 选择 UI**
- 用户无法选择用 CPU 还是 GPU 训练

#### 需要改动

**前端 (Training.vue)**：
- 调用 `/api/training/device-info` 获取可用设备列表
- 添加设备选择器（Dropdown/Radio）
- 将 `device` 参数传给 `/api/training/start`

**后端 (yolo_training.py)**：
- `train_yolo()` 已经支持 `device` 参数 ✅
- `check_gpu_available()` 返回 GPU 列表，支持多卡 ✅

### 3.2 推理 GPU 支持

#### 当前问题

```python
# backend/routers/inference.py 第53行
detector = load_yolo_model(model.file_path)  # 硬编码，无 device 参数
```

`inference_yolo()` 不传 device，默认用 CPU。

#### 需要改动

```python
# inference.py
detector = load_yolo_model(model.file_path)
result = inference_yolo(detector, str(file_path), conf_threshold)
# 需要支持：
# 1. 根据模型设备自适应（模型在 GPU 还是 CPU）
# 2. 显式指定 device 参数
# 3. 推理时使用 half=True 加速
```

---

## 四、推理加速问题

### 当前状态

`inference_yolo()` 无任何加速配置，默认全精度 CPU 推理。

### 加速方向

| 方向 | 方法 | 预期效果 |
|------|------|----------|
| **半精度 (FP16)** | `model(image, half=True)` | 显存减半，速度↑ 30-50% |
| **TensorRT** | 导出 `.engine` + `device='cuda:0'` | 速度↑ 2-5x，显存↓ |
| **批量推理** | 多图合并一次推理 | 吞吐量↑ |
| **动态分辨率** | 降低 `imgsz` | 速度↑，精度略↓ |
| **ONNX + ONNXRuntime** | 导出 ONNX + `providers=['CUDAExecutionProvider']` | 速度↑ 2-3x |

### 优先级建议

1. **FP16 半精度** — 改动最小，效果明显
2. **ONNX 导出 + 推理** — 同时解决多格式支持问题
3. **TensorRT** — 效果最大，但需要 CUDA 环境 + 导出流程

---

## 五、模型格式支持问题

### 当前状态

只支持 `.pt`（YOLO checkpoint），由 `load_yolo_model()` 实现。

### 需要支持的格式

| 格式 | 典型用途 | 支持难度 |
|------|----------|----------|
| **ONNX** | 跨平台部署、ONNXRuntime 推理 | 中 |
| **TensorRT (.engine)** | 高性能推理（NVIDIA GPU） | 高（需导出+编译） |
| **TFLite** | 移动端/嵌入式 | 高（需量化） |
| **CoreML** | iOS/macOS | 高（需导出） |
| **OpenVINO** | Intel 硬件加速 | 中 |

### 架构建议：工厂模式

不要在 `load_yolo_model` 里硬编码，改成可扩展的工厂模式：

```python
# backend/ml_models/model_factory.py

class ModelLoader:
    """模型加载工厂"""

    @staticmethod
    def load(model_path: str, device: str = "cpu", half: bool = False):
        """根据文件扩展名加载对应模型"""
        ext = Path(model_path).suffix.lower()

        if ext == ".pt":
            return YOLOModel(model_path, device=device, half=half)
        elif ext == ".onnx":
            return ONNXModel(model_path, device=device)
        elif ext == ".engine":
            return TensorRTModel(model_path, device=device)
        else:
            raise ValueError(f"不支持的模型格式: {ext}")

    @staticmethod
    def export_to_onnx(pt_path: str, output_path: str):
        """YOLO → ONNX 导出"""
        model = YOLOModel(pt_path)
        model.export(format="onnx", save_path=output_path)
```

### 数据集格式扩展

当前只导出 YOLO 格式，考虑支持：

| 格式 | 说明 |
|------|------|
| **COCO JSON** | 通用目标检测标准格式 |
| **VOC XML** | Pascal VOC 传统格式 |
| **YOLO TXT** | 当前格式，归一化 bbox |

---

## 六、其他待讨论问题

### 6.1 engine 模块集成

`engine/` 目录下有完整的视觉感知和 RL 代码，但目前未与 FastAPI 后端连通：
- `engine/core/vision/` — CNN 编码器、游戏目标检测
- `engine/core/rl/` — PPO/SAC 强化学习算法
- `engine/core/control/` — 键盘/鼠标输入模拟

**问题**：engine 是独立包还是应该作为 CogniFlow 的一部分？是否需要将 engine 功能通过 API 暴露？

### 6.2 数据持久化

- 当前 SQLite 数据库文件路径？
- Docker 部署时 data 目录的 volume 映射？
- 模型缓存目录 `data/model_cache` 是否需要清理机制？

### 6.3 前端技术栈选择

当前使用 **UnoCSS**（原子化 CSS），但项目根目录 CLAUDE.md 写的是 **Element Plus**。

实际项目中：
- 样式主要靠 UnoCSS 原子类 + `index.scss` CSS 变量
- 少量组件用 Element Plus（对话框、按钮等）

**建议**：明确技术栈，减少维护负担。

---

## 七、优先级建议（供讨论）

基于改动难度和收益，建议讨论顺序：

| 优先级 | 事项 | 理由 |
|--------|------|------|
| **P0** | GPU 训练入口 | 前端加设备选择，后端无需改动 |
| **P0** | 规则引擎 Phase 1 | 核心功能连通，YOLO 触发 + 键盘动作 |
| **P1** | 推理 GPU 支持 + FP16 | 改动小，效果明显 |
| **P1** | ONNX 格式支持 | 统一推理加速 + 多格式支持 |
| **P1** | 规则引擎画布编辑器 | 前端工作量较大，尽早启动 |
| **P2** | TensorRT 支持 | 需要 CUDA 环境，效果最大 |
| **P2** | engine 模块集成 | 长期目标，短期先维持现状 |
