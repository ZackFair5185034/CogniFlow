# 多模型格式与硬件加速支持 - 实施计划

> 基于分支 `feature/multi-format-hardware-accel` 开发
> 最后更新: 2026-05-09

## 状态总览

| 阶段 | 状态 | 备注 |
|------|------|------|
| 第一阶段：模型格式抽象层 | ✅ 完成 | ModelFormat 枚举、handler 注册表、YOLO/ONNX handler、导出器 |
| 第二阶段：硬件加速抽象层 | ✅ 完成 | HardwareInfo、DeviceDetector、Precision 枚举 |
| 第三阶段：API 和前端 UI | ✅ 完成 | 多格式导出、格式切换、推理设备/精度参数 |
| 第四阶段：engine 包桥接 | ⏸️ 搁置 | 低优先级，暂不处理 |

## Context

当前 CogniFlow **仅支持 YOLO `.pt` 格式**，推理**硬编码 CPU**，没有模型格式抽象层和硬件加速抽象层。本项目旨在建立统一的模型推理框架，支持多种模型格式（ONNX、OpenVINO、TensorRT）和硬件后端（CPU、CUDA、TensorRT、OpenVINO）。

## 已完成工作

### 第一阶段：模型格式抽象层（核心基础）

**目标**：建立工厂模式的模型格式抽象层，将推理逻辑与具体格式解耦。

#### 新的目录结构 ✅

```
backend/core/                          # 新增核心包
    __init__.py
    model_format.py                    # ModelFormat 枚举 + 扩展名检测
    model_registry.py                  # 工厂注册表
    interfaces.py                      # InferenceResult 数据类 + IModelHandler 协议
    formats/
        __init__.py
        base_handler.py                # BaseModelHandler 抽象基类
        yolo_handler.py                # YOLO .pt 处理器（封装 ultralytics.YOLO）
        onnx_handler.py                # ONNX 处理器（onnxruntime）
        openvino_handler.py            # OpenVINO 处理器
        tensorrt_handler.py            # TensorRT 处理器
    export/
        __init__.py
        yolo_exporter.py               # YOLO .pt → ONNX/OpenVINO/TensorRT 导出
```

#### 关键接口设计 ✅

```python
# backend/core/interfaces.py
@dataclass
class InferenceResult:
    detections: List[Dict]     # [{"bbox", "confidence", "class_id", "class_name"}, ...]
    num_detections: int
    inference_ms: float


# backend/core/formats/base_handler.py
class BaseModelHandler(ABC):
    format: ModelFormat
    device: str
    def load(self, model_path: str) -> None
    def infer(self, image: np.ndarray, conf: float) -> InferenceResult
    def infer_batch(self, images: List[np.ndarray], conf: float) -> List[InferenceResult]
    def unload(self) -> None
    def get_metadata(self) -> Dict


# backend/core/model_registry.py
ModelHandlerRegistry.register(ModelFormat.YOLO_PT, YoloModelHandler)
ModelHandlerRegistry.register(ModelFormat.ONNX, OnnxModelHandler)
handler = ModelHandlerRegistry.from_path(model_path, device="cpu")
```

### 第二阶段：硬件加速抽象层 ✅

**目标**：统一的推理后端接口，自动设备检测，精度选择。

#### 新的目录结构 ✅

```
backend/core/backends/
    __init__.py
    base.py                      # HardwareInfo dataclass + InferenceBackend ABC
    auto_detector.py             # 自动检测可用设备 + pick_best()
    precision.py                 # Precision 枚举 + 精度工具
```

### 第三阶段：多格式模型存储与推理切换 ✅

#### ModelFile 表

新增 `model_file` 表，支持一个模型关联多个格式文件：

```sql
CREATE TABLE model_file (
    id INTEGER PRIMARY KEY,
    model_id INTEGER REFERENCES model(id) ON DELETE CASCADE,
    format VARCHAR(20),        -- yolo_pt/onnx/openvino/tensorrt/pytorch
    file_path VARCHAR(500),
    file_size INTEGER,
    precision VARCHAR(10),     -- fp32/fp16/int8
    is_default BOOLEAN,
    created_at DATETIME
);
```

#### Model 表变化

- `available_formats` 字段改为从 `model_files` 表实时查询，不再存储 JSON
- `file_path` 和 `format` 保留用于向后兼容
- 新增 `device_preference`, `precision`, `input_shape` 字段

#### 后端 API

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/models` | 返回每个模型的 `files` 列表（含格式、路径、是否默认） |
| POST | `/api/models/{id}/upload` | 上传自动检测格式，创建 ModelFile 记录 |
| DELETE | `/api/models/{id}` | 级联删除所有 ModelFile 记录 |
| POST | `/api/models/{id}/files/{file_id}/set-default` | 设置默认推理格式 |
| DELETE | `/api/models/{id}/files/{file_id}` | 删除单个格式文件及物理文件 |
| GET | `/api/models/{id}/files` | 列出模型所有格式文件 |
| POST | `/api/models/{id}/export` | 异步导出（WebSocket 进度推送） |
| POST | `/api/models/{id}/export/sync` | 同步导出（无进度） |
| POST | `/api/inference/detect/image` | 增加 `format` 参数（可选，默认自动） |
| POST | `/api/inference/detect/video/stream` | 增加 `format` 参数（可选，默认自动） |

**自动选择逻辑**：按优先级 `tensorrt > openvino > onnx > yolo_pt`，同时检查文件是否真实存在于磁盘。

#### WebSocket 导出进度

| 端点 | 功能 |
|------|------|
| `/ws/export/{export_id}` | 实时接收导出进度（starting/loading/saving/completed/error） |

#### 前端 UI

| 文件 | 修改内容 |
|------|----------|
| `webui/src/api/index.ts` | 新增 exportAsync/export、model file CRUD；更新 inference API 添加 format/device/precision 参数 |
| `webui/src/views/ModelList.vue` | 模型列表格式 badge（显示前 3 种，折叠剩余）；导出对话框（格式选择 + 进度条 + WebSocket）；操作列下拉菜单 |
| `webui/src/views/Launch.vue` | 格式选择器（自动/指定格式）；推理结果展示实际使用的格式 |
| `webui/src/style/index.scss` | 新增 format-badge、export-progress、dialog 等样式 |

#### 分阶段实施计划

```
Phase 1 ──────────────────────── ✅ 完成
  ├── 1. model_format.py + interfaces.py
  ├── 2. base_handler.py + yolo_handler.py + onnx_handler.py
  ├── 3. model_registry.py
  ├── 4. yolo_exporter.py
  ├── 5. 数据库迁移 (Model 表新列 + ModelFile 表)
  ├── 6. schemas.py 更新
  ├── 7. 重构 model.py 上传解析 + 导出
  ├── 8. 重构 yolo_training.py
  └── 9. 重构 inference.py 全线替换

Phase 2 ──────────────────────── ✅ 完成
  ├── 10. backends/base.py + auto_detector.py + precision.py
  └── 11. 更新 check_gpu_available + device-info

Phase 3 ──────────────────────── ✅ 完成
  ├── 12. 后端：导出端点 + 扩展推理参数
  ├── 13. 前端：api 封装更新
  ├── 14. 前端：ModelList.vue 格式展示+导出UI
  └── 15. 前端：Launch.vue 格式/设备选择器

Phase 4 ──────────────────────── ⏸️ 搁置
  ├── 16. PytorchModelHandler + UIDetectorAdapter
  └── 17. FeatureExtractor + ConfigBridge
```

## 已知问题

1. **ONNX 推理检测不到目标**：使用导出的 ONNX 格式进行推理时，返回的检测结果为空（detections=[]）。.pt 格式推理正常。可能与 ONNX 后处理逻辑或输出格式解析有关，待排查。
2. **OpenVINO / TensorRT 处理器未完全集成到推理管线**：handler 已实现但未在 inference.py 的后处理中完全适配。

## 新增依赖

```
onnxruntime>=1.15.0              # ONNX 推理
onnx>=1.14.0                     # ONNX 导出
# OpenVINO 和 TensorRT 按需安装，不加入 requirements.txt
```

## 验证方案

1. ✅ 上传 `.pt` 模型 → 自动识别格式并存入 DB
2. ✅ 导出为 ONNX → 生成 `.onnx` 文件 + model_file 记录
3. ❌ 用 ONNX 模型推理图片 → 检测不到目标（待修复）
4. ✅ 后端模型列表返回 `files` 数组
5. ✅ 前端模型列表显示格式徽章
6. ✅ 推理页面格式选择器正常工作
7. ✅ 导出进度通过 WebSocket 实时推送
8. ✅ 同格式重复导出覆盖旧文件（不产生重复记录）
