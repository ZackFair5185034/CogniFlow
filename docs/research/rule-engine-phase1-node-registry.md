# Phase 1 技术实现文档：节点类型系统（后端）
> ⚠️ **实现前审核状态：** 待老大评审
> 文档版本：v1.1
> 创建时间：2026-05-06
> **节点类型定义权威来源：** Phase 1 实现文档（`rule-engine-phase1-node-registry.md`）
> **执行器设计规范：** 所有 `BaseExecutor.execute()` 必须为 `async def`，同步 I/O 用 `asyncio.to_thread()` 封装

---

## 1. 阶段目标

**目标：** 建立统一的节点定义体系和执行器注册机制，后端能够返回完整的节点类型信息供前端渲染。

**验收标准：**
- [ ] `GET /api/rule-engine/nodes/definitions` 返回完整的 6 类节点定义
- [ ] 节点面板能够按类别分组展示（前端可验证）
- [ ] 每个节点执行器能独立执行并返回输出（单元测试覆盖）
- [ ] 新增节点只需注册到 `NodeRegistry`，无需修改其他代码

---

## 2. 核心架构

### 2.1 组件关系

```
┌─────────────────────────────────────────────────────────┐
│                    NodeRegistry                          │
│  ┌─────────────────┐    ┌─────────────────────────┐    │
│  │ _definitions    │    │ _executors              │    │
│  │ Dict[str, Node] │    │ Dict[str, BaseExecutor] │    │
│  └────────┬────────┘    └──────────┬────────────┘    │
│           │                          │                  │
│           │    ┌─────────────────────┘                  │
│           ▼    ▼                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │         get_definitions()                        │   │
│  │         返回所有节点定义（含 category）            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   API Router           │
              │   GET /nodes/definitions │
              └─────────────────────────┘
```

### 2.2 文件结构

```
backend/services/rule_engine/
    ├── __init__.py
    ├── registry.py           # 节点注册表核心
    ├── models.py             # Pydantic 数据模型
    ├── exceptions.py         # 自定义异常
    │
    └── executors/
        ├── __init__.py
        ├── base.py           # BaseExecutor 基类
        ├── input_nodes.py    # 输入类节点
        ├── detection_nodes.py
        ├── processing_nodes.py
        ├── action_nodes.py
        ├── logic_nodes.py
        └── output_nodes.py
```

---

## 3. 数据结构

### 3.1 Pydantic 模型

```python
# backend/services/rule_engine/models.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PortDefinition(BaseModel):
    """端口定义 - 描述节点的输入或输出端口。"""
    name: str = Field(..., description="端口显示名称")
    type: str = Field(..., description="数据类型：IMAGE/BBOX/MASK/SCORES/TRIGGER/CONTROL/MODEL/ANY")
    required: bool = Field(True, description="是否为必需端口")
    default: Any = Field(None, description="默认值（未连接时使用）")
    description: str = Field("", description="端口功能描述")


class NodeDefinition(BaseModel):
    """节点定义 - 描述节点类型的元信息。"""
    type: str = Field(..., description="节点类型标识，如 'YOLOModel'")
    category: str = Field(..., description="所属类别：input/detection/processing/action/logic/output")
    display_name: str = Field(..., description="前端显示名称")
    description: str = Field("", description="节点功能描述")
    icon: str = Field("circle", description="图标名称")
    color: str = Field("#7D7D7D", description="节点颜色（十六进制）")
    inputs: Dict[str, PortDefinition] = Field(default_factory=dict, description="输入端口定义")
    outputs: Dict[str, PortDefinition] = Field(default_factory=dict, description="输出端口定义")


class CategoryInfo(BaseModel):
    """节点类别信息。"""
    name: str
    display_name: str
    color: str
    icon: str


class NodeDefinitionsResponse(BaseModel):
    """节点定义响应（API 返回格式）。"""
    nodes: List[NodeDefinition]
    categories: List[CategoryInfo]
```

---

## 4. 节点注册表实现

### 4.1 NodeRegistry 核心代码

```python
# backend/services/rule_engine/registry.py

from typing import Dict, List, Optional, Type
from .models import NodeDefinition, CategoryInfo
from .executors.base import BaseExecutor


class NodeRegistry:
    """节点注册表 - 统一管理所有节点定义和执行器。

    这是规则引擎的核心组件，负责：
    1. 管理所有可用节点类型的定义（供前端渲染节点面板）
    2. 管理节点执行器实例（供执行引擎调用）
    3. 提供按类别查询节点的能力

    使用示例：
        registry = NodeRegistry()
        registry.register(MyNodeExecutor())

        # 获取所有定义
        definitions = registry.get_definitions()

        # 按类别查询
        detection_nodes = registry.get_by_category("detection")

        # 获取执行器
        executor = registry.get_executor("YOLOModel")
    """

    # 内置类别定义
    CATEGORIES: List[CategoryInfo] = [
        CategoryInfo(name="input", display_name="输入", color="#4CFF4C", icon="upload"),
        CategoryInfo(name="detection", display_name="检测", color="#00f0FF", icon="radar"),
        CategoryInfo(name="processing", display_name="处理", color="#FFFF4C", icon="process"),
        CategoryInfo(name="action", display_name="动作", color="#FF7F4C", icon="cursor"),
        CategoryInfo(name="logic", display_name="逻辑", color="#DC4FDC", icon="branch"),
        CategoryInfo(name="output", display_name="输出", color="#FF4C4C", icon="download"),
    ]

    def __init__(self):
        # 节点定义字典：type -> NodeDefinition
        self._definitions: Dict[str, NodeDefinition] = {}

        # 节点执行器字典：type -> BaseExecutor 实例
        self._executors: Dict[str, BaseExecutor] = {}

    def register(self, executor: BaseExecutor) -> None:
        """注册节点执行器（同时注册定义）。

        Args:
            executor: 节点执行器实例（必须继承 BaseExecutor）

        Raises:
            ValueError: 如果节点类型已存在
        """
        definition = executor.get_definition()
        node_type = definition.type

        if node_type in self._definitions:
            raise ValueError(f"节点类型 '{node_type}' 已注册")

        self._definitions[node_type] = definition
        self._executors[node_type] = executor

    def get_definition(self, node_type: str) -> Optional[NodeDefinition]:
        """获取指定类型的节点定义。"""
        return self._definitions.get(node_type)

    def get_definitions(self) -> List[NodeDefinition]:
        """获取所有节点定义。"""
        return list(self._definitions.values())

    def get_executor(self, node_type: str) -> Optional[BaseExecutor]:
        """获取指定类型的执行器实例。"""
        return self._executors.get(node_type)

    def get_by_category(self, category: str) -> List[NodeDefinition]:
        """获取指定类别的所有节点定义。"""
        return [
            d for d in self._definitions.values()
            if d.category == category
        ]

    def get_categories(self) -> List[CategoryInfo]:
        """获取所有类别定义。"""
        return self.CATEGORIES

    def to_response(self) -> Dict:
        """生成 API 响应格式。"""
        return {
            "nodes": [d.model_dump() for d in self._definitions.values()],
            "categories": [c.model_dump() for c in self.CATEGORIES]
        }
```

---

## 5. BaseExecutor 基类

### 5.1 完整实现

```python
# backend/services/rule_engine/executors/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from ..models import NodeDefinition, ExecutionContext
from ..exceptions import ExecutorError


class BaseExecutor(ABC):
    """节点执行器基类。

    所有节点执行器必须继承此类，并实现：
    1. get_definition() - 返回节点定义
    2. validate_inputs() - 校验输入参数
    3. execute() - 执行节点逻辑

    使用示例：
        class MyNodeExecutor(BaseExecutor):
            def get_definition(self) -> NodeDefinition:
                return NodeDefinition(...)

            def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
                if "data" not in inputs:
                    return False, "缺少必需参数 'data'"
                return True, None

            async def execute(self, inputs, context) -> Dict[str, Any]:
                return {"result": process(inputs["data"])}
    """

    @abstractmethod
    def get_definition(self) -> NodeDefinition:
        """返回节点的完整定义。

        Returns:
            NodeDefinition 对象，包含节点的所有元信息
        """
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """校验输入参数是否满足要求。

        在节点执行前调用，用于验证输入数据的合法性。
        不合法的输入应返回 (False, error_message)，而非抛异常。

        Args:
            inputs: 节点输入数据字典

        Returns:
            (is_valid, error_message) 元组
            - is_valid: 输入是否合法
            - error_message: 错误描述（如果非法）
        """
        pass

    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行节点逻辑。

        这是节点的核心执行方法，由执行引擎在拓扑排序后调用。

        Args:
            inputs: 节点输入数据（已解析变量引用）
            context: 执行上下文（包含变量、执行结果缓存等）

        Returns:
            节点输出数据字典，key 为输出端口名称

        Raises:
            ExecutorError: 执行失败时抛出（包含节点 ID 和类型信息）
        """
        pass

    def get_required_inputs(self) -> List[str]:
        """返回必需输入端口名称列表。"""
        definition = self.get_definition()
        return [
            name for name, port in definition.inputs.items()
            if port.required
        ]

    def get_optional_defaults(self) -> Dict[str, Any]:
        """返回有默认值的可选输入端口及其默认值。"""
        definition = self.get_definition()
        return {
            name: port.default
            for name, port in definition.inputs.items()
            if not port.required and port.default is not None
        }

    def merge_with_defaults(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """将可选输入与默认值合并。"""
        result = dict(inputs)
        for name, default in self.get_optional_defaults().items():
            if name not in result or result[name] is None:
                result[name] = default
        return result
```

---

## 6. 执行器实现模板

### 6.1 输入类节点

```python
# backend/services/rule_engine/executors/input_nodes.py

from typing import Any, Dict, Optional, Tuple
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class ImageCaptureExecutor(BaseExecutor):
    """图片采集节点 - 从文件或 URL 采集单张图片。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="ImageCapture",
            category="input",
            display_name="图片输入",
            description="从文件路径或 URL 采集单张图片",
            icon="image",
            color="#4CFF4C",
            inputs={},
            outputs={
                "image": PortDefinition(
                    name="图片",
                    type="IMAGE",
                    description="采集到的图片数据"
                ),
                "width": PortDefinition(
                    name="宽度",
                    type="INT",
                    description="图片宽度（像素）"
                ),
                "height": PortDefinition(
                    name="高度",
                    type="INT",
                    description="图片高度（像素）"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        # 输入类节点不需要输入校验
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        # 从节点参数获取图片路径或 URL
        params = context.config.get("params", {})
        source = params.get("source", "")

        if not source:
            raise ExecutorError("图片源不能为空", node_type="ImageCapture")

        try:
            # TODO: 实现实际的图片读取逻辑
            # image_data = load_image(source)
            image_data = {"path": source, "data": b"..."}  # 占位

            return {
                "image": image_data,
                "width": 1920,  # TODO: 从实际图片读取
                "height": 1080
            }
        except Exception as e:
            raise ExecutorError(f"图片读取失败: {str(e)}", node_type="ImageCapture") from e


class VideoCaptureExecutor(BaseExecutor):
    """视频流采集节点 - 从摄像头或视频文件采集帧。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="VideoCapture",
            category="input",
            display_name="视频输入",
            description="从摄像头或视频文件持续采集帧",
            icon="video",
            color="#4CFF4C",
            inputs={},
            outputs={
                "image": PortDefinition(name="帧图片", type="IMAGE"),
                "frame_id": PortDefinition(name="帧序号", type="INT"),
                "timestamp": PortDefinition(name="时间戳", type="FLOAT")
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        params = context.config.get("params", {})
        source = params.get("source", "video0")
        fps = params.get("fps", 30)

        # TODO: 实现实际的视频帧读取
        return {
            "image": {"source": source, "data": b"..."},
            "frame_id": context.node_results.get("_frame_count", 0),
            "timestamp": 0.0
        }
```

### 6.2 检测类节点

```python
# backend/services/rule_engine/executors/detection_nodes.py

from typing import Any, Dict, Optional, Tuple
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class YOLOModelExecutor(BaseExecutor):
    """YOLO 目标检测节点。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="YOLOModel",
            category="detection",
            display_name="YOLO 检测模型",
            description="使用 YOLO 模型进行目标检测",
            icon="radar",
            color="#00f0FF",
            inputs={
                "image": PortDefinition(
                    name="图片输入",
                    type="IMAGE",
                    required=True,
                    description="待检测的图片"
                ),
                "confidence": PortDefinition(
                    name="置信度阈值",
                    type="FLOAT",
                    required=False,
                    default=0.5,
                    description="检测置信度下限"
                ),
                "model_id": PortDefinition(
                    name="模型选择",
                    type="MODEL",
                    required=True,
                    description="已注册的 YOLO 模型"
                )
            },
            outputs={
                "bboxes": PortDefinition(
                    name="检测框",
                    type="BBOX",
                    description="检测到的目标框列表 [[x1,y1,x2,y2], ...]"
                ),
                "scores": PortDefinition(
                    name="置信度",
                    type="SCORES",
                    description="各检测框对应的置信度"
                ),
                "class_ids": PortDefinition(
                    name="类别ID",
                    type="CLASS_IDS",
                    description="各检测框对应的类别 ID"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "image" not in inputs or inputs["image"] is None:
            return False, "图片输入不能为空"
        if "model_id" not in inputs or inputs["model_id"] is None:
            return False, "必须选择 YOLO 模型"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        image = inputs["image"]
        confidence = inputs.get("confidence", 0.5)
        model_id = inputs["model_id"]

        try:
            # TODO: 对接现有的 inference 模块
            # results = await run_yolo_inference(image, model_id, confidence)

            # 占位返回
            results = {
                "bboxes": [[100, 100, 200, 200], [300, 150, 400, 350]],
                "scores": [0.95, 0.87],
                "class_ids": [0, 0]
            }

            # 过滤低置信度
            valid_mask = [s >= confidence for s in results["scores"]]
            return {
                "bboxes": [b for b, m in zip(results["bboxes"], valid_mask) if m],
                "scores": [s for s, m in zip(results["scores"], valid_mask) if m],
                "class_ids": [c for c, m in zip(results["class_ids"], valid_mask) if m]
            }

        except Exception as e:
            raise ExecutorError(
                f"YOLO 检测失败: {str(e)}",
                node_type="YOLOModel"
            ) from e
```

### 6.3 处理类节点

```python
# backend/services/rule_engine/executors/processing_nodes.py

from typing import Any, Dict, Optional, Tuple
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class CategoryEncodeExecutor(BaseExecutor):
    """类别过滤节点 - 按类别 ID 过滤检测框。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="CategoryEncode",
            category="processing",
            display_name="类别过滤",
            description="按类别 ID 或名称过滤检测框",
            icon="filter",
            color="#FFFF4C",
            inputs={
                "bboxes": PortDefinition(
                    name="检测框输入",
                    type="BBOX",
                    required=True,
                    description="待过滤的检测框"
                ),
                "class_ids": PortDefinition(
                    name="类别ID输入",
                    type="CLASS_IDS",
                    required=True,
                    description="对应的类别 ID"
                ),
                "target_class": PortDefinition(
                    name="目标类别",
                    type="STRING",
                    required=False,
                    default="person",
                    description="要保留的类别名称"
                )
            },
            outputs={
                "filtered_bboxes": PortDefinition(
                    name="过滤后检测框",
                    type="BBOX",
                    description="过滤后的检测框"
                ),
                "filtered_class_ids": PortDefinition(
                    name="过滤后类别ID",
                    type="CLASS_IDS",
                    description="过滤后的类别 ID"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "bboxes" not in inputs:
            return False, "检测框输入不能为空"
        if "class_ids" not in inputs:
            return False, "类别ID输入不能为空"
        if len(inputs["bboxes"]) != len(inputs["class_ids"]):
            return False, "检测框和类别ID数量不匹配"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        bboxes = inputs["bboxes"]
        class_ids = inputs["class_ids"]
        target_class = inputs.get("target_class", "person")

        # TODO: 从 context 获取类别映射表
        # category_map = context.variables.get("CATEGORY_MAP", {})
        # target_id = category_map.get(target_class)

        # 占位：假设 target_class = "person" 对应 class_id = 0
        target_id = 0

        filtered_bboxes = []
        filtered_class_ids = []

        for bbox, cls_id in zip(bboxes, class_ids):
            if cls_id == target_id:
                filtered_bboxes.append(bbox)
                filtered_class_ids.append(cls_id)

        return {
            "filtered_bboxes": filtered_bboxes,
            "filtered_class_ids": filtered_class_ids
        }


class FilterExecutor(BaseExecutor):
    """条件过滤节点 - 按自定义条件过滤数据。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="Filter",
            category="processing",
            display_name="条件过滤",
            description="根据条件表达式过滤数据",
            icon="funnel",
            color="#FFFF4C",
            inputs={
                "data": PortDefinition(
                    name="数据输入",
                    type="ANY",
                    required=True,
                    description="待过滤的数据"
                ),
                "condition": PortDefinition(
                    name="过滤条件",
                    type="STRING",
                    required=True,
                    description="过滤条件表达式，如 'score > 0.5'"
                )
            },
            outputs={
                "filtered": PortDefinition(
                    name="过滤结果",
                    type="ANY",
                    description="满足条件的数据"
                ),
                "count": PortDefinition(
                    name="结果数量",
                    type="INT",
                    description="满足条件的数量"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "data" not in inputs:
            return False, "数据输入不能为空"
        if "condition" not in inputs or not inputs["condition"]:
            return False, "过滤条件不能为空"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        data = inputs["data"]
        condition = inputs["condition"]

        # TODO: 实现表达式解析器
        # 简单实现：假设 condition 是 Python 表达式
        try:
            # 注意：实际使用时需要安全的表达式解析器
            filtered = [d for d in data if eval(condition, {"__builtins__": {}}, {"d": d})]

            return {
                "filtered": filtered,
                "count": len(filtered)
            }
        except Exception as e:
            raise ExecutorError(f"条件过滤失败: {str(e)}", node_type="Filter") from e
```

### 6.4 动作类节点

```python
# backend/services/rule_engine/executors/action_nodes.py

from typing import Any, Dict, Optional, Tuple
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class MouseClickExecutor(BaseExecutor):
    """鼠标点击节点 - 模拟鼠标点击操作。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="MouseClick",
            category="action",
            display_name="鼠标点击",
            description="模拟鼠标点击操作",
            icon="cursor",
            color="#FF7F4C",
            inputs={
                "trigger": PortDefinition(
                    name="触发信号",
                    type="TRIGGER",
                    required=False,
                    description="触发信号（可选，无触发时立即执行）"
                ),
                "x": PortDefinition(
                    name="X坐标",
                    type="INT",
                    required=True,
                    description="点击 X 坐标"
                ),
                "y": PortDefinition(
                    name="Y坐标",
                    type="INT",
                    required=True,
                    description="点击 Y 坐标"
                ),
                "button": PortDefinition(
                    name="鼠标按钮",
                    type="STRING",
                    required=False,
                    default="left",
                    description="按钮：left/right/middle"
                )
            },
            outputs={}
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "x" not in inputs or "y" not in inputs:
            return False, "X 和 Y 坐标必须提供"
        if inputs["x"] < 0 or inputs["y"] < 0:
            return False, "坐标不能为负数"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        x = inputs["x"]
        y = inputs["y"]
        button = inputs.get("button", "left")

        try:
            # TODO: 对接现有的控制模块
            # await pyautogui.click(x=x, y=y, button=button)
            return {}
        except Exception as e:
            raise ExecutorError(
                f"鼠标点击失败: {str(e)}",
                node_type="MouseClick"
            ) from e


class KeyPressExecutor(BaseExecutor):
    """键盘按键节点 - 模拟键盘按键操作。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="KeyPress",
            category="action",
            display_name="键盘按键",
            description="模拟键盘按键操作",
            icon="keyboard",
            color="#FF7F4C",
            inputs={
                "trigger": PortDefinition(
                    name="触发信号",
                    type="TRIGGER",
                    required=False,
                    description="触发信号"
                ),
                "key": PortDefinition(
                    name="按键",
                    type="STRING",
                    required=True,
                    description="按键名称，如 'enter', 'ctrl+c'"
                )
            },
            outputs={}
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "key" not in inputs or not inputs["key"]:
            return False, "按键名称不能为空"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        key = inputs["key"]

        try:
            # TODO: 对接现有的控制模块
            # await pyautogui.press(key)
            return {}
        except Exception as e:
            raise ExecutorError(
                f"键盘按键失败: {str(e)}",
                node_type="KeyPress"
            ) from e


class NotificationExecutor(BaseExecutor):
    """通知节点 - 发送系统通知。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="Notification",
            category="action",
            display_name="发送通知",
            description="发送系统通知或日志",
            icon="bell",
            color="#FF7F4C",
            inputs={
                "trigger": PortDefinition(
                    name="触发信号",
                    type="TRIGGER",
                    required=False,
                    description="触发信号"
                ),
                "message": PortDefinition(
                    name="消息内容",
                    type="STRING",
                    required=True,
                    description="通知内容"
                ),
                "level": PortDefinition(
                    name="级别",
                    type="STRING",
                    required=False,
                    default="info",
                    description="级别：info/warn/error"
                )
            },
            outputs={}
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "message" not in inputs or not inputs["message"]:
            return False, "通知内容不能为空"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        message = inputs["message"]
        level = inputs.get("level", "info")

        # TODO: 实现实际的通知发送逻辑
        return {}
```

### 6.5 逻辑类节点

```python
# backend/services/rule_engine/executors/logic_nodes.py

from typing import Any, Dict, Optional, Tuple
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class ConditionExecutor(BaseExecutor):
    """条件分支节点 - 根据条件选择执行分支。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="Condition",
            category="logic",
            display_name="条件分支",
            description="根据条件表达式选择执行分支",
            icon="branch",
            color="#DC4FDC",
            inputs={
                "data": PortDefinition(
                    name="数据输入",
                    type="ANY",
                    required=True,
                    description="用于判断的数据"
                ),
                "expression": PortDefinition(
                    name="条件表达式",
                    type="STRING",
                    required=True,
                    description="条件表达式，如 'count > 0'"
                )
            },
            outputs={
                "true": PortDefinition(
                    name="条件为真",
                    type="TRIGGER",
                    description="条件满足时触发"
                ),
                "false": PortDefinition(
                    name="条件为假",
                    type="TRIGGER",
                    description="条件不满足时触发"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "data" not in inputs:
            return False, "数据输入不能为空"
        if "expression" not in inputs or not inputs["expression"]:
            return False, "条件表达式不能为空"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        data = inputs["data"]
        expression = inputs["expression"]

        try:
            # 注意：实际使用时需要安全的表达式解析器
            result = eval(expression, {"__builtins__": {}}, {"d": data, "data": data})

            return {
                "true": result,
                "false": not result
            }
        except Exception as e:
            raise ExecutorError(
                f"条件判断失败: {str(e)}",
                node_type="Condition"
            ) from e


class TimerExecutor(BaseExecutor):
    """定时器节点 - 定时触发下游节点。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="Timer",
            category="logic",
            display_name="定时器",
            description="按固定间隔触发下游节点",
            icon="clock",
            color="#DC4FDC",
            inputs={
                "trigger": PortDefinition(
                    name="启动信号",
                    type="TRIGGER",
                    required=False,
                    description="启动定时器（可选）"
                ),
                "interval": PortDefinition(
                    name="间隔(秒)",
                    type="INT",
                    required=False,
                    default=1,
                    description="触发间隔（秒）"
                )
            },
            outputs={
                "tick": PortDefinition(
                    name="定时信号",
                    type="TRIGGER",
                    description="定时触发信号"
                ),
                "count": PortDefinition(
                    name="计数",
                    type="INT",
                    description="触发次数"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        interval = inputs.get("interval", 1)
        if interval <= 0:
            return False, "间隔必须大于 0"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        interval = inputs.get("interval", 1)
        count = context.node_results.get("_timer_count", 0) + 1

        # 注意：定时器的实际定时功能由执行引擎控制
        # 这里只返回当前计数
        return {
            "tick": True,
            "count": count
        }
```

### 6.6 输出类节点

```python
# backend/services/rule_engine/executors/output_nodes.py

from typing import Any, Dict, Optional, Tuple
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class ActionOutputExecutor(BaseExecutor):
    """动作输出节点 - 规则图的最终输出节点。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="ActionOutput",
            category="output",
            display_name="规则输出",
            description="规则图的最终输出节点，接收上游结果",
            icon="download",
            color="#FF4C4C",
            inputs={
                "trigger": PortDefinition(
                    name="触发信号",
                    type="TRIGGER",
                    required=False,
                    description="触发信号"
                ),
                "data": PortDefinition(
                    name="输出数据",
                    type="ANY",
                    required=False,
                    description="要输出的数据"
                )
            },
            outputs={}
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        # 输出节点通常不强制要求输入
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        # 输出节点不需要实际执行逻辑
        # 数据已经通过 context 传递给调用方
        return {}


class SaveResultExecutor(BaseExecutor):
    """保存结果节点 - 将数据保存到文件。"""

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type="SaveResult",
            category="output",
            display_name="保存结果",
            description="将数据保存到文件",
            icon="save",
            color="#FF4C4C",
            inputs={
                "data": PortDefinition(
                    name="数据输入",
                    type="ANY",
                    required=True,
                    description="要保存的数据"
                ),
                "path": PortDefinition(
                    name="保存路径",
                    type="STRING",
                    required=False,
                    default="/tmp/result.json",
                    description="保存文件路径"
                ),
                "format": PortDefinition(
                    name="格式",
                    type="STRING",
                    required=False,
                    default="json",
                    description="保存格式：json/csv/txt"
                )
            },
            outputs={
                "saved_path": PortDefinition(
                    name="保存路径",
                    type="STRING",
                    description="实际保存的文件路径"
                )
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "data" not in inputs:
            return False, "数据输入不能为空"
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        import json
        import os

        data = inputs["data"]
        path = inputs.get("path", "/tmp/result.json")
        format_ = inputs.get("format", "json")

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

            # 根据格式保存
            if format_ == "json":
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format_ == "txt":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(data))
            else:
                raise ValueError(f"不支持的格式: {format_}")

            return {"saved_path": path}

        except Exception as e:
            raise ExecutorError(
                f"保存结果失败: {str(e)}",
                node_type="SaveResult"
            ) from e
```

---

## 7. 注册初始化

### 7.1 统一注册入口

```python
# backend/services/rule_engine/__init__.py

from .registry import NodeRegistry
from .executors.input_nodes import ImageCaptureExecutor, VideoCaptureExecutor
from .executors.detection_nodes import YOLOModelExecutor
from .executors.processing_nodes import CategoryEncodeExecutor, FilterExecutor
from .executors.action_nodes import MouseClickExecutor, KeyPressExecutor, NotificationExecutor
from .executors.logic_nodes import ConditionExecutor, TimerExecutor
from .executors.output_nodes import ActionOutputExecutor, SaveResultExecutor


def init_builtin_executors() -> NodeRegistry:
    """初始化内置节点执行器。

    创建并初始化规则引擎的节点注册表，注册所有内置节点。
    此函数在应用启动时调用一次。

    Returns:
        已注册所有内置节点的注册表实例

    使用示例：
        registry = init_builtin_executors()
        definitions = registry.get_definitions()
    """
    registry = NodeRegistry()

    # 输入类
    registry.register(ImageCaptureExecutor())
    registry.register(VideoCaptureExecutor())

    # 检测类
    registry.register(YOLOModelExecutor())

    # 处理类
    registry.register(CategoryEncodeExecutor())
    registry.register(FilterExecutor())

    # 动作类
    registry.register(MouseClickExecutor())
    registry.register(KeyPressExecutor())
    registry.register(NotificationExecutor())

    # 逻辑类
    registry.register(ConditionExecutor())
    registry.register(TimerExecutor())

    # 输出类
    registry.register(ActionOutputExecutor())
    registry.register(SaveResultExecutor())

    return registry


# 全局注册表实例（延迟初始化）
_registry: NodeRegistry = None


def get_registry() -> NodeRegistry:
    """获取全局节点注册表实例（单例）。"""
    global _registry
    if _registry is None:
        _registry = init_builtin_executors()
    return _registry
```

---

## 8. API 路由

### 8.1 节点定义接口

```python
# backend/routers/rule_engine.py

from fastapi import APIRouter, Depends
from backend.services.rule_engine import get_registry

router = APIRouter(prefix="/api/rule-engine", tags=["规则引擎"])


@router.get("/nodes/definitions")
async def get_node_definitions():
    """获取所有可用节点定义 - 用于前端渲染节点面板。"""
    registry = get_registry()
    return registry.to_response()
```

---

## 9. 单元测试模板

### 9.1 测试结构

```python
# tests/test_rule_engine/test_executors/test_input_nodes.py

import pytest
from backend.services.rule_engine.executors.input_nodes import ImageCaptureExecutor
from backend.services.rule_engine.models import ExecutionContext


class TestImageCaptureExecutor:
    """ImageCaptureExecutor 测试类。"""

    @pytest.fixture
    def executor(self):
        return ImageCaptureExecutor()

    @pytest.fixture
    def context(self):
        return ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={}
        )

    def test_get_definition(self, executor):
        """测试获取节点定义。"""
        definition = executor.get_definition()

        assert definition.type == "ImageCapture"
        assert definition.category == "input"
        assert definition.color == "#4CFF4C"
        assert "image" in definition.outputs

    def test_validate_inputs(self, executor):
        """测试输入校验 - 输入节点不需要校验。"""
        is_valid, error = executor.validate_inputs({})
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_execute_without_source(self, executor, context):
        """测试执行 - 无图片源时应报错。"""
        context.config = {"params": {}}

        with pytest.raises(Exception):
            await executor.execute({}, context)

    @pytest.mark.asyncio
    async def test_execute_with_source(self, executor, context):
        """测试执行 - 有图片源时正常执行。"""
        context.config = {"params": {"source": "/tmp/test.jpg"}}

        result = await executor.execute({}, context)

        assert "image" in result
        assert "width" in result
        assert "height" in result
```

---

## 10. 验收检查清单

### 10.1 功能验收

- [ ] `GET /api/rule-engine/nodes/definitions` 返回 200
- [ ] 返回包含 `nodes` 和 `categories` 两个字段
- [ ] `categories` 包含全部 6 个类别（input/detection/processing/action/logic/output）
- [ ] `nodes` 包含全部 10+ 个节点定义
- [ ] 每个节点定义包含 `type`、`category`、`inputs`、`outputs`
- [ ] 每个节点执行器单元测试通过

### 10.2 可扩展性验收

- [ ] 新增节点只需：创建 Executor 类 + 调用 `registry.register()`
- [ ] 无需修改 API 路由代码
- [ ] 无需修改其他已有执行器代码

### 10.3 数据完整性验收

- [ ] 所有输入端口有正确的 `type` 和 `required` 标记
- [ ] 所有输出端口有正确的 `type` 标记
- [ ] 颜色值符合类别规范（见开发规范）
