# 多模型格式与硬件加速支持 - 实施计划

> 基于分支 `feature/multi-format-hardware-accel` 开发

## Context

当前 CogniFlow **仅支持 YOLO `.pt` 格式**，推理**硬编码 CPU**，没有模型格式抽象层和硬件加速抽象层。本项目旨在建立统一的模型推理框架，支持多种模型格式（ONNX、OpenVINO、TensorRT）和硬件后端（CPU、CUDA、TensorRT、OpenVINO）。

## 分阶段实施计划

---

### 第一阶段：模型格式抽象层（核心基础）

**目标**：建立工厂模式的模型格式抽象层，将推理逻辑与具体格式解耦。

#### 新的目录结构

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

#### 关键接口设计

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

#### 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `backend/database.py` | Model 表新增列：`format`, `available_formats`, `device_preference`, `precision`, `input_shape` |
| `backend/schemas.py` | ModelCreate/ModelResponse 添加 `format`, `device_preference`, `precision` 字段 |
| `backend/routers/model.py` | 重构 `upload_model_file()` 使用 `ModelHandlerRegistry` 解析元数据；新增 `POST /{id}/export` 导出端点 |
| `backend/routers/yolo_training.py` | 重构 `load_yolo_model()` → 委托给 `ModelHandlerRegistry`；`inference_yolo()` 适配 `BaseModelHandler` 接口 |
| `backend/routers/inference.py` | 全线替换 `load_yolo_model`+`inference_yolo` 为 `ModelHandlerRegistry.from_path().infer()`；添加 `device` 参数 |

#### yolo_training.py 重构要点（最小侵入）

```python
# 保持 train_yolo() 不变（依然生成 .pt）
# 仅重构 load/inference：

def load_yolo_model(model_path: str, device: str = "cpu"):
    """委托给新模型注册表，向后兼容。"""
    from backend.core.model_registry import ModelHandlerRegistry
    handler = ModelHandlerRegistry.from_path(model_path, device=device)
    handler.load(model_path)
    return handler  # 返回 BaseModelHandler，不再是原始 YOLO 实例

def inference_yolo(handler, image_path: str, conf: float = 0.25) -> Dict:
    """适配新接口。"""
    import cv2
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = handler.infer(image_rgb, conf)
    return {"image_path": image_path, "num_detections": result.num_detections,
            "detections": result.detections}
```

#### YOLO 导出流程（新 API）

```
POST /api/models/{id}/export  Body: {target_format: "onnx", half: false}
  → YoloExporter.export(model.file_path, target_format, output_dir, half=half)
    → ultralytics.YOLO(model_path).export(format=..., half=..., dynamic=True)
  → 更新 Model.available_formats（JSON 数组）
  → 注册导出版本文件路径
```

---

### 第二阶段：硬件加速抽象层

**目标**：统一的推理后端接口，自动设备检测，精度选择。

#### 新的目录结构

```
backend/core/backends/
    __init__.py
    base.py                      # HardwareInfo dataclass + InferenceBackend ABC
    auto_detector.py             # 自动检测可用设备 + pick_best()
    precision.py                 # Precision 枚举 + 精度工具
```

#### 设计要点

```python
# backend/core/backends/base.py
@dataclass
class HardwareInfo:
    device_type: str        # "cpu", "cuda", "openvino", "tensorrt"
    device_name: str
    memory_total_mb: int = 0
    supports_fp16: bool = False
    supports_int8: bool = False

# backend/core/backends/auto_detector.py
class DeviceDetector:
    @staticmethod
    def detect_all() -> Dict[str, HardwareInfo]:    # 检测所有可用后端
    @staticmethod
    def pick_best(preference: str = "auto") -> str:  # 自动选择最佳设备
```

#### 文件修改

| 文件 | 修改内容 |
|------|----------|
| `backend/routers/yolo_training.py` | 更新 `check_gpu_available()` 使用 `DeviceDetector`，返回更详细的设备列表 |
| `backend/routers/training.py` | 扩展 `/api/training/device-info` 端点，返回所有可用设备 |
| `backend/routers/inference.py` | 推理端点添加 `device` 和 `precision` Form 参数 |

---

### 第三阶段：API 和前端 UI 更新

**目标**：后端 API 和前端 UI 支持新的格式/设备选项。

#### 后端 API 变更

| 端点 | 变更 |
|------|------|
| `POST /api/models/{id}/export` | 新增：YOLO .pt → ONNX/OpenVINO/TensorRT 导出 |
| `GET /api/training/device-info` | 扩展：返回完整设备列表 `{"devices": {}}` |
| `POST /api/inference/detect/image` | 添加 `device`、`precision` Form 参数 |
| `POST /api/inference/detect/video/stream` | 添加 `device`、`precision` Form 参数 |

#### 前端 UI 变更

| 文件 | 修改内容 |
|------|----------|
| `webui/src/api/index.ts` | 新增 `modelApi.export()`, `modelApi.getAvailableFormats()`；更新 `inferenceApi.detectImage` 参数 |
| `webui/src/views/ModelList.vue` | 表格列添加"格式"徽章；操作列增加"导出"按钮及导出对话框（目标格式+精度选择） |
| `webui/src/views/Launch.vue` | 模型选择下方增加"推理后端"下拉（auto/cpu/cuda）和"精度"下拉（fp32/fp16） |
| `webui/src/views/Training.vue` | 训练设备选择器扩展为显示更详细的设备信息 |

---

### 第四阶段：engine 包桥接（可选增强）

**目标**：将 engine 包中的 `UIDetector`、`CNNEncoder` 接入统一推理框架。

#### 新增文件

```
backend/core/formats/pytorch_handler.py           # 通用 PyTorch nn.Module 包装器
backend/core/formats/adapters/
    __init__.py
    ui_detector_adapter.py                         # UIDetector → BaseModelHandler 适配器
backend/core/backends/feature_extractor.py         # CNNEncoder 特征提取封装
backend/core/config_bridge.py                      # engine/config/schema.py → 后端配置桥接
```

engine 包本身**不做任何修改**，仅添加适配器层。

---

## 实施顺序与依赖

```
Phase 1 ──────────────────────── 高优先级（基础能力）
  ├── 1. model_format.py + interfaces.py  (无依赖)
  ├── 2. base_handler.py + yolo_handler.py + onnx_handler.py (依赖 1)
  ├── 3. model_registry.py (依赖 2)
  ├── 4. yolo_exporter.py (依赖 1)
  ├── 5. 数据库迁移 (Model 表新列) (依赖 1)
  ├── 6. schemas.py 更新 (依赖 5)
  ├── 7. 重构 model.py 上传解析 (依赖 3)
  ├── 8. 重构 yolo_training.py (依赖 3)
  └── 9. 重构 inference.py 全线替换 (依赖 7, 8)

Phase 2 ──────────────────────── 中优先级
  ├── 10. backends/base.py + auto_detector.py + precision.py (无依赖)
  └── 11. 更新 check_gpu_available + device-info (依赖 10)

Phase 3 ──────────────────────── 中优先级
  ├── 12. 后端：导出端点 + 扩展推理参数 (依赖 4, 11)
  ├── 13. 前端：api 封装更新 (依赖 12)
  ├── 14. 前端：ModelList.vue 格式展示+导出UI (依赖 13)
  └── 15. 前端：Launch.vue 设备/精度选择器 (依赖 13)

Phase 4 ──────────────────────── 低优先级
  ├── 16. PytorchModelHandler + UIDetectorAdapter (依赖 2)
  └── 17. FeatureExtractor + ConfigBridge (依赖 16)
```

## 新增依赖

```
onnxruntime>=1.15.0              # ONNX 推理
onnx>=1.14.0                     # ONNX 导出
# OpenVINO 和 TensorRT 按需安装，不加入 requirements.txt
```

## 验证方案

1. **单元测试**：`tests/test_core/` 下测试 ModelFormat 枚举解析、注册表创建、各 handler 的基本方法（mock 外部依赖）
2. **集成测试**：使用 SQLite 内存数据库 + TestClient 测试导出 API 和上传解析
3. **手动验证**：
   - 上传 `.pt` 模型 → 确认自动识别格式并存入 DB
   - 导出为 ONNX → 确认生成 `.onnx` 文件 + available_formats 更新
   - 用 ONNX 模型推理图片 → 确认结果与 `.pt` 一致
   - CUDA 可用时设备选择自动识别
   - 前端模型列表显示格式徽章，推理页面设备/精度选择器正常工作
