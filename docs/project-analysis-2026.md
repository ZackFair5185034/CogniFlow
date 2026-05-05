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

### 2.2 Unity/Blender 调研对标分析

> 参考日期：2026-05-05

#### Unity Visual Scripting 核心能力

| 特性 | 说明 | 对 CogniFlow 的启发 |
|------|------|---------------------|
| **事件驱动执行** | Start/Update/OnCollisionEnter 等生命周期事件触发图执行 | YOLO 触发器 = 游戏引擎的 Update 事件 |
| **Script Machine** | 每个对象可挂载独立规则图 | 当前设计：全局图 → 应支持每规则独立图 |
| **Subgraph 子图复用** | 用户封装节点组为可复用子图 | ❌ 当前缺失，需补充 |
| **变量作用域** | Object/Graph/Scene 三级变量 | ⚠️ 只有全局变量，需补充作用域 |
| **类型专化节点** | Transform/Rigidbody/Collider 等游戏对象绑定 | CogniFlow 应有：Model/Detection/Input 等领域节点 |
| **断点调试** | 断点+单步+变量监视 | ❌ 当前缺失，Phase 1 应补充 |
| **实时高亮** | 执行到哪个节点画布上高亮 | ❌ WebSocket 未实现，无法做到 |
| **代码转换** | Visual Script ↔ C# 互转 | 🟢 低优先级 |

#### Blender Geometry Nodes 核心能力

| 特性 | 说明 | 对 CogniFlow 的启发 |
|------|------|---------------------|
| **Socket 类型系统** | Geometry/Float/Vector/Color/Boolean，类型不匹配禁止连接 | 🔴 **当前缺失，应优先补充** |
| **Field 隐式并行** | 自动对每个点/面/边执行，无需显式循环 | detections 是数组，应支持批量过滤/映射 |
| **节点树嵌套** | Group Input/Output 封装子图 | ❌ 当前缺失 |
| **实时视口反馈** | 节点修改即时反映在视图 | 需要执行状态 WebSocket 推送 |
| **实例化** | 大规模场景高效处理 | 规则引擎中用于批量动作执行 |

#### 设计文档 vs 实际实现 对比

| 模块 | 设计文档 (rule-engine-design.md) | 实际实现 | 差距 |
|------|--------------------------------|---------|------|
| 节点数量 | 20+（规划到 Phase 4） | 16 节点 | ⚠️ 规划完整，实现 OK |
| 执行引擎 | DAG + 并发 + 缓存 | 异步 DFS 图遍历 | ✅ 基本骨架 OK |
| 节点注册 | `@register` 装饰器 | 同 | ✅ 一致 |
| ExecutionContext | 完整设计 | 同 | ✅ 一致 |
| WebSocket | 实时状态推送 | ❌ **未实现** | 🔴 缺失 |
| CogniFlow 集成 | engine.core.control 对接 | Keyboard/Mouse 有 TODO | 🔴 未连通 |
| 前端画布 | VueFlow + 完整编辑器 | RuleList + RuleCanvas 基础 | ⚠️ 缺节点面板 |
| YOLO 触发器 | 对接推理服务 | 只是框架，未调用推理 | 🔴 未连通 |
| Socket 类型系统 | ❌ 无 | ❌ 无 | 🔴 **与 Blender 差距核心** |
| 子图复用 | ❌ 无 | ❌ 无 | 🟡 Blender 强大的关键 |

### 2.3 当前架构合理性评估

#### ✅ 合理的部分

1. **DAG 执行模型** — 正确，规则引擎就是有向无环图
2. **节点注册装饰器** — 方便扩展，符合开闭原则
3. **ExecutionContext 携带 detections/variables** — 设计正确
4. **Phase 1-5 分阶段** — 务实路线图
5. **BaseNodeExecutor.execute() 接口** — 统一执行契约
6. **TypeScript 类型定义** — 文档完整，前端类型有据可查

#### ❌ 问题与风险

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **YOLO 触发器没有真正对接推理** | 🔴 P0 | 只是框架，detections 来源没打通 |
| **Keyboard/Mouse 节点有 TODO** | 🔴 P0 | engine.core.control 集成未做 |
| **WebSocket 未实现** | 🔴 P1 | 调试体验会很差，无法实时高亮 |
| **没有 Socket 类型系统** | 🔴 P1 | 任意端口可以互连，类型安全为零（Blender 核心特性） |
| **节点不支持子图/复用** | 🟡 P2 | 复杂规则无法封装复用 |
| **没有 Field 概念** | 🟡 P2 | detections 是数组，但所有节点都是标量处理 |
| **执行引擎没有断点/单步调试** | 🟡 P1 | 复杂规则无法调试 |
| **节点面板缺失** | 🟡 P1 | 前端 RuleCanvas 有画布但没有节点搜索/拖放面板 |
| **没有变量作用域** | 🟡 P2 | 只有全局变量，无 Object/Graph 变量概念 |

### 2.4 迭代计划（修订版）

#### Phase 0: 连通性补全（1-2周）⚠️ 最优先

**目标**：实现一个完整场景 —— "检测到金币 → 按空格键"

| 任务 | 说明 | 工作量 |
|------|------|--------|
| YOLO 触发器对接推理服务 | `YOLOTriggerNode._execute` 调用 `inference_yolo()` 或推理 API | 中 |
| 键盘动作对接 `engine/input_emulator` | 将 `KeyboardActionNode` 的 TODO 改为真实调用 | 中 |
| 鼠标动作对接 `engine/input_emulator` | 同上 | 中 |
| WebSocket 实时状态推送 | 节点执行时前端能高亮当前节点 | 中 |
| 节点面板 | 显示所有节点类型，支持拖入画布 | 中 |

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

#### Phase 1: 调试能力（1周）

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 断点设置 | 节点级别断点，执行到断点暂停 | 中 |
| 单步执行 | next/continue 操作 | 中 |
| 变量监视面板 | 显示 context.variables 当前值 | 中 |
| 执行历史日志查看 | 每次执行记录到数据库，可回放 | 小 |

#### Phase 2: 类型安全（1周）

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 端口类型化 | trigger/data/boolean/数值，类型不匹配禁止连接 | 中 |
| detections 字段补全 | bbox/confidence/label 等字段类型定义 | 小 |
| Field 批量处理 | 支持对 detections 数组批量过滤/映射 | 中 |

#### Phase 3: 高级节点（2周）

| 任务 | 说明 | 工作量 |
|------|------|--------|
| Loop 循环完整实现 | 执行器处理迭代逻辑 | 中 |
| ParallelBranch 并行执行 | 真正并发运行多个分支 | 中 |
| PythonCode 节点 | 安全沙箱执行用户代码 | 中 |
| Expression 表达式节点 | `detection.label == "coin" and detection.conf > 0.8` | 中 |
| Subgraph 子图复用 | 封装节点组为可复用子图 | 中 |

#### Phase 4: 生态扩展（长期）

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 截图/OCR/区域检测节点 | 更丰富的触发源 | 🔴 高 |
| 图像处理节点 | resize/crop/filter | 🟡 中 |
| 变量作用域完善 | Object/Graph 变量 | 🟡 中 |
| 规则导入/导出 | JSON/YAML 格式 | 🟢 低 |
| TensorRT 加速 | 高性能推理 | 🟡 中 |

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
| **P0** | 规则引擎 Phase 0 连通性 | YOLO触发+键盘鼠标+WebSocket，核心不连通规则引擎永远跑不起来 |
| **P0** | GPU 训练入口 | 前端加设备选择，后端无需改动 |
| **P1** | 推理 GPU 支持 + FP16 | 改动小，效果明显 |
| **P1** | Socket 类型系统 | Blender 强大的核心，当前完全缺失 |
| **P1** | ONNX 格式支持 | 统一推理加速 + 多格式支持 |
| **P1** | 规则引擎画布编辑器 | 前端工作量较大，尽早启动 |
| **P2** | TensorRT 支持 | 需要 CUDA 环境，效果最大 |
| **P2** | engine 模块集成 | 长期目标，短期先维持现状 |

---

## 八、设计文档修订建议

现有 `docs/rule-engine-design.md` (128KB) 存在以下问题，建议后续一并修订：

| 问题 | 说明 |
|------|------|
| **文档部分过时** | endpoint 描述有些与实际代码不符（如 `/node-types` 实际是 `/nodes/definitions`） |
| **Socket 类型缺失** | Blender 最核心的类型化 Socket 没有对应设计 |
| **Field 概念缺失** | detections 是数组，但所有节点都是标量处理逻辑 |
| **子图/复用没有** | 这是 Unity/Blender 强大的关键之一，文档没有规划 |
| **变量作用域** | 只有全局变量，没有 Object/Graph 变量概念 |
| **Phase 5 过于笼统** | "集成与完善"没有具体里程碑 |
