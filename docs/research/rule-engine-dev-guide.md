# 规则引擎开发规范

> 文档版本：v1.0  
> 基于调研：canvas-editor-research-2026-05-06.md  
> 创建时间：2026-05-06

---

## 1. 概述

本文档定义 CogniFlow 规则引擎的开发规范，包括目录结构、代码风格、节点注册机制、执行器开发模板、测试要求。开发规范基于项目现有 CLAUDE.md，补充规则引擎特定内容。

---

## 2. 目录结构

### 2.1 后端目录结构

```
backend/services/rule_engine/
    ├── __init__.py
    ├── registry.py          # 节点注册表核心
    ├── models.py            # Pydantic 数据模型
    ├── executor.py          # 执行引擎（Phase 2）
    ├── graph_manager.py    # 规则图 CRUD 管理
    ├── validators.py        # 输入校验工具
    ├── exceptions.py        # 自定义异常
    │
    └── executors/           # 节点执行器目录
        ├── __init__.py
        ├── base.py          # BaseExecutor 基类
        ├── input_nodes.py   # 输入类节点
        ├── detection_nodes.py  # 检测类节点
        ├── processing_nodes.py # 处理类节点
        ├── action_nodes.py  # 动作类节点
        ├── logic_nodes.py   # 逻辑类节点
        └── output_nodes.py  # 输出类节点
```

**说明：**
- 所有执行器放在 `executors/` 子目录，按类别分组
- 新增节点只需注册到 `registry.py`，无需修改其他代码
- 每个文件内的节点数量建议不超过 10 个（保持单一职责）

### 2.2 前端目录结构

```
webui/src/
    ├── components/rule-canvas/
    │   ├── nodes/              # 自定义节点组件
    │   │   ├── InputNode.vue   # 输入节点
    │   │   ├── DetectionNode.vue
    │   │   ├── ProcessingNode.vue
    │   │   ├── ActionNode.vue
    │   │   ├── LogicNode.vue
    │   │   └── OutputNode.vue
    │   ├── NodePalette.vue     # 左侧节点面板
    │   ├── PropertyPanel.vue   # 右侧属性面板
    │   ├── CanvasToolbar.vue   # 工具栏
    │   └── types.ts            # 前端类型定义
    │
    ├── stores/
    │   ├── ruleCanvas.ts       # 画布状态管理
    │   └── ruleEngineWS.ts    # WebSocket 客户端
    │
    └── views/
        └── RuleCanvas.vue      # 主画布页面（已存在）
```

---

## 3. 代码风格

### 3.1 Python 代码风格

**遵循项目规范（CLAUDE.md）：**
- 所有注释使用中文
- 使用 4 空格缩进
- 最大行长度 100 字符
- 使用类型注解
- 类名 PascalCase，函数名 snake_case

**规则引擎特定规范：**

```python
# -*- coding: utf-8 -*-
"""规则引擎注册表 - 节点定义和执行器注册中心。

本模块是规则引擎的核心，负责：
1. 管理所有可用节点类型的定义
2. 注册节点执行器
3. 提供节点定义查询接口

使用示例：
    registry = init_builtin_executors()
    definitions = registry.get_definitions()
    executor = registry.get_executor("YOLOModel")
"""

from typing import Dict, List, Optional, Any
from backend.services.rule_engine.executors.base import BaseExecutor


class NodeRegistry:
    """节点注册表 - 统一管理所有节点定义和执行器。"""

    def __init__(self):
        # 节点定义字典：type -> NodeDefinition
        self._definitions: Dict[str, NodeDefinition] = {}
        # 节点执行器字典：type -> BaseExecutor
        self._executors: Dict[str, BaseExecutor] = {}

    def register(self, definition: NodeDefinition, executor: BaseExecutor) -> None:
        """注册节点定义和执行器。

        Args:
            definition: 节点定义对象
            executor: 节点执行器实例

        Raises:
            ValueError: 如果节点类型已存在
        """
        if definition.type in self._definitions:
            raise ValueError(f"节点类型 '{definition.type}' 已注册")
        self._definitions[definition.type] = definition
        self._executors[definition.type] = executor

    def get_definition(self, node_type: str) -> Optional[NodeDefinition]:
        """获取指定类型的节点定义。"""
        return self._definitions.get(node_type)

    def get_definitions(self) -> List[NodeDefinition]:
        """获取所有节点定义（按 category 分组）。"""
        return list(self._definitions.values())

    def get_executor(self, node_type: str) -> Optional[BaseExecutor]:
        """获取指定类型的执行器。"""
        return self._executors.get(node_type)

    def get_by_category(self, category: str) -> List[NodeDefinition]:
        """获取指定类别的所有节点定义。"""
        return [
            d for d in self._definitions.values()
            if d.category == category
        ]
```

### 3.2 Vue/TypeScript 代码风格

**遵循项目规范（CLAUDE.md）：**
- 使用 `<script setup lang="ts">` 语法
- Props 使用 TypeScript 类型定义
- 组件名 PascalCase，事件名 camelCase
- CSS 类名 kebab-case

**前端类型定义：**

```typescript
// webui/src/components/rule-canvas/types.ts

// 节点定义（来自后端）
export interface NodeDefinition {
  type: string
  category: 'input' | 'detection' | 'processing' | 'action' | 'logic' | 'output'
  display_name: string
  description: string
  icon: string
  color: string
  inputs: Record<string, PortDefinition>
  outputs: Record<string, PortDefinition>
}

export interface PortDefinition {
  name: string
  type: string
  required: boolean
  default: any
  description: string
}

// Vue Flow 节点
export interface CanvasNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: {
    label: string
    params: Record<string, any>
    inputs: Record<string, { node_id: string | null; output: string | null; value: any }>
    outputs: Record<string, { type: string }>
  }
}

// Vue Flow 边
export interface CanvasEdge {
  id: string
  source: string
  sourceHandle: string
  target: string
  targetHandle: string
  type: string
}

// 规则图完整结构
export interface RuleGraph {
  id: number
  name: string
  description: string
  nodes: Record<string, CanvasNode>
  edges: CanvasEdge[]
  variables: Record<string, VariableDefinition>
}

// 节点执行状态
export type NodeStatus = 'idle' | 'pending' | 'running' | 'completed' | 'failed'
```

---

## 4. 节点执行器开发规范

### 4.1 BaseExecutor 基类

所有节点执行器必须继承 `BaseExecutor`：

```python
# backend/services/rule_engine/executors/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.services.rule_engine.models import (
    NodeDefinition,
    PortDefinition,
    ExecutionContext
)


class BaseExecutor(ABC):
    """节点执行器基类。

    所有节点执行器必须继承此类并实现：
    1. get_definition() - 返回节点定义
    2. validate_inputs() - 校验输入参数
    3. execute() - 执行节点逻辑

    使用示例：
        class MyNodeExecutor(BaseExecutor):
            def get_definition(self) -> NodeDefinition:
                return NodeDefinition(...)

            def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
                return "required_param" in inputs

            async def execute(
                self,
                inputs: Dict[str, Any],
                context: ExecutionContext
            ) -> Dict[str, Any]:
                return {"output": process(inputs)}
    """

    @abstractmethod
    def get_definition(self) -> NodeDefinition:
        """返回节点的完整定义。"""
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """校验输入参数。

        Returns:
            (is_valid, error_message)
        """
        pass

    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """执行节点逻辑。

        Args:
            inputs: 节点输入数据（已解析变量引用）
            context: 执行上下文

        Returns:
            节点输出数据字典

        Raises:
            ExecutorError: 执行失败时抛出
        """
        pass

    def get_required_inputs(self) -> List[str]:
        """返回必需输入端口名称列表。"""
        definition = self.get_definition()
        return [
            name for name, port in definition.inputs.items()
            if port.required
        ]
```

### 4.2 节点执行器开发模板

```python
# backend/services/rule_engine/executors/detection_nodes.py

"""检测类节点执行器 - YOLOModel 等检测节点。"""

from typing import Any, Dict, Optional
from .base import BaseExecutor
from ..models import NodeDefinition, PortDefinition, ExecutionContext
from ..exceptions import ExecutorError


class YOLOModelExecutor(BaseExecutor):
    """YOLO 目标检测执行器。"""

    def get_definition(self) -> NodeDefinition:
        """返回 YOLOModel 节点定义。"""
        return NodeDefinition(
            type="YOLOModel",
            category="detection",
            display_name="YOLO 检测模型",
            description="使用 YOLO 模型进行目标检测，支持多目标追踪",
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
                    description="检测到的目标框列表"
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

    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """校验输入参数。"""
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
        """执行 YOLO 目标检测。"""
        # 获取输入
        image = inputs["image"]
        confidence = inputs.get("confidence", 0.5)
        model_id = inputs["model_id"]

        try:
            # 调用检测逻辑
            results = await self._run_detection(image, model_id, confidence)

            # 过滤低置信度结果
            valid_indices = [
                i for i, score in enumerate(results["scores"])
                if score >= confidence
            ]

            return {
                "bboxes": [results["bboxes"][i] for i in valid_indices],
                "scores": [results["scores"][i] for i in valid_indices],
                "class_ids": [results["class_ids"][i] for i in valid_indices]
            }

        except Exception as e:
            raise ExecutorError(f"YOLO 检测失败: {str(e)}") from e

    async def _run_detection(
        self,
        image: Any,
        model_id: int,
        confidence: float
    ) -> Dict[str, Any]:
        """实际执行检测（内部方法）。"""
        # TODO: 调用现有的 inference 模块
        raise NotImplementedError("等待对接 inference 模块")
```

### 4.3 节点注册流程

```python
# backend/services/rule_engine/registry.py

from .executors.input_nodes import ImageCaptureExecutor, VideoCaptureExecutor
from .executors.detection_nodes import YOLOModelExecutor, ObjectDetectorExecutor
from .executors.processing_nodes import CategoryEncodeExecutor, FilterExecutor
from .executors.action_nodes import MouseClickExecutor, KeyPressExecutor
from .executors.logic_nodes import ConditionExecutor, TimerExecutor
from .executors.output_nodes import ActionOutputExecutor, SaveResultExecutor


def init_builtin_executors() -> NodeRegistry:
    """初始化内置节点执行器。

    Returns:
        已注册所有内置节点的注册表实例

    使用示例：
        registry = init_builtin_executors()
        definitions = registry.get_definitions()
    """
    registry = NodeRegistry()

    # 按类别注册节点
    # 输入类
    registry.register(ImageCaptureExecutor().get_definition(), ImageCaptureExecutor())
    registry.register(VideoCaptureExecutor().get_definition(), VideoCaptureExecutor())

    # 检测类
    registry.register(YOLOModelExecutor().get_definition(), YOLOModelExecutor())
    registry.register(ObjectDetectorExecutor().get_definition(), ObjectDetectorExecutor())

    # 处理类
    registry.register(CategoryEncodeExecutor().get_definition(), CategoryEncodeExecutor())
    registry.register(FilterExecutor().get_definition(), FilterExecutor())

    # 动作类
    registry.register(MouseClickExecutor().get_definition(), MouseClickExecutor())
    registry.register(KeyPressExecutor().get_definition(), KeyPressExecutor())

    # 逻辑类
    registry.register(ConditionExecutor().get_definition(), ConditionExecutor())
    registry.register(TimerExecutor().get_definition(), TimerExecutor())

    # 输出类
    registry.register(ActionOutputExecutor().get_definition(), ActionOutputExecutor())
    registry.register(SaveResultExecutor().get_definition(), SaveResultExecutor())

    return registry
```

### 4.4 新增节点检查清单

新增节点时，必须完成以下步骤：

1. **创建执行器类**
   - 继承 `BaseExecutor`
   - 实现 `get_definition()`
   - 实现 `validate_inputs()`
   - 实现 `execute()`

2. **注册到 registry.py**
   ```python
   registry.register(MyExecutor().get_definition(), MyExecutor())
   ```

3. **前端节点组件（如需自定义渲染）**
   - 在 `components/rule-canvas/nodes/` 创建 `.vue` 文件
   - 在 `ruleCanvas.ts` 的 `nodeTypes` 中注册

4. **添加单元测试**
   - 测试 `validate_inputs()` 各种输入情况
   - 测试 `execute()` 正常执行
   - 测试 `execute()` 异常处理

---

## 5. 异常处理规范

### 5.1 规则引擎异常类

```python
# backend/services/rule_engine/exceptions.py

"""规则引擎自定义异常。"""


class RuleEngineError(Exception):
    """规则引擎基础异常类。"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CycleError(RuleEngineError):
    """规则图存在循环依赖。"""

    def __init__(self, message: str, cycle_nodes: list = None):
        super().__init__(message)
        self.cycle_nodes = cycle_nodes or []


class ValidationError(RuleEngineError):
    """规则图校验失败。"""

    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class ExecutorError(RuleEngineError):
    """节点执行失败。"""

    def __init__(self, message: str, node_id: str = None, node_type: str = None):
        super().__init__(message)
        self.node_id = node_id
        self.node_type = node_type


class ConnectionTypeError(RuleEngineError):
    """节点连接类型不匹配。"""

    def __init__(self, source_type: str, target_type: str):
        message = f"类型不匹配：无法将 {source_type} 连接到 {target_type}"
        super().__init__(message)
        self.source_type = source_type
        self.target_type = target_type
```

### 5.2 异常处理原则

| 场景 | 处理方式 |
|------|---------|
| 输入校验失败 | 返回 (False, error_message)，不抛异常 |
| 执行逻辑失败 | 抛 `ExecutorError`，记录节点 ID 和类型 |
| 环回检测 | 抛 `CycleError`，包含环节点列表 |
| 连接类型不匹配 | 抛 `ConnectionTypeError` |
| 规则图校验失败 | 抛 `ValidationError`，包含错误列表 |

---

## 6. 测试规范

### 6.1 测试文件结构

```
tests/
    └── test_rule_engine/
        ├── __init__.py
        ├── test_registry.py       # 注册表测试
        ├── test_executor_base.py   # 基类测试
        ├── test_executors/        # 执行器测试
        │   ├── __init__.py
        │   ├── test_detection_nodes.py
        │   └── test_action_nodes.py
        ├── test_executor_engine.py # 执行引擎测试
        └── test_validators.py     # 校验器测试
```

### 6.2 测试覆盖要求

| 模块 | 最低覆盖率 | 测试重点 |
|------|-----------|---------|
| registry.py | 80% | 注册、查询、分类过滤 |
| executors/ | 80% | validate_inputs、execute、异常处理 |
| executor.py | 70% | 拓扑排序、并行执行、环检测、取消 |
| validators.py | 80% | 类型检查、连接验证 |

### 6.3 测试示例

```python
# tests/test_rule_engine/test_executors/test_detection_nodes.py

"""YOLOModel 执行器测试。"""

import pytest
from backend.services.rule_engine.executors.detection_nodes import YOLOModelExecutor
from backend.services.rule_engine.models import ExecutionContext
from backend.services.rule_engine.exceptions import ExecutorError


class TestYOLOModelExecutor:
    """YOLOModel 执行器测试类。"""

    @pytest.fixture
    def executor(self):
        """创建执行器实例。"""
        return YOLOModelExecutor()

    @pytest.fixture
    def context(self):
        """创建执行上下文。"""
        return ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={}
        )

    def test_get_definition(self, executor):
        """测试获取节点定义。"""
        definition = executor.get_definition()

        assert definition.type == "YOLOModel"
        assert definition.category == "detection"
        assert "image" in definition.inputs
        assert "bboxes" in definition.outputs

    def test_validate_inputs_missing_image(self, executor):
        """测试输入校验 - 缺少图片。"""
        is_valid, error = executor.validate_inputs({
            "model_id": 1
        })

        assert is_valid is False
        assert "图片输入不能为空" in error

    def test_validate_inputs_missing_model(self, executor):
        """测试输入校验 - 缺少模型。"""
        is_valid, error = executor.validate_inputs({
            "image": {"data": "..."}
        })

        assert is_valid is False
        assert "必须选择 YOLO 模型" in error

    def test_validate_inputs_valid(self, executor):
        """测试输入校验 - 有效输入。"""
        is_valid, error = executor.validate_inputs({
            "image": {"data": "..."},
            "model_id": 1,
            "confidence": 0.5
        })

        assert is_valid is True
        assert error is None
```

---

## 7. 前端开发规范

### 7.1 Vue Flow 节点组件规范

每个节点组件必须：

1. **接收 `data` prop**
2. **定义 `output` 拖拽源**
3. **定义 `input` 拖拽目标区域**
4. **支持选中状态样式**

```vue
<!-- webui/src/components/rule-canvas/nodes/DetectionNode.vue -->

<template>
  <div
    class="canvas-node detection-node"
    :class="{ selected: data.selected, running: data.state === 'running' }"
    :style="{ borderColor: nodeColor }"
  >
    <!-- 节点头部 -->
    <div class="node-header" :style="{ backgroundColor: nodeColor }">
      <span class="node-title">{{ data.label || '检测节点' }}</span>
    </div>

    <!-- 输入端口 -->
    <div class="node-ports">
      <div
        v-for="(port, key) in data.inputs"
        :key="'input-' + key"
        class="port input-port"
        :class="{ connected: port.node_id }"
        @dragover.prevent
        @drop="$emit('connect', { target: key, ...$event })"
      >
        <Handle type="target" :position="Position.Left" :id="key" />
        <span class="port-label">{{ port.name || key }}</span>
      </div>
    </div>

    <!-- 节点内容 -->
    <div class="node-body">
      <div class="node-type">{{ nodeType }}</div>
    </div>

    <!-- 输出端口 -->
    <div class="node-ports">
      <div
        v-for="(port, key) in data.outputs"
        :key="'output-' + key"
        class="port output-port"
      >
        <Handle type="source" :position="Position.Right" :id="key" />
        <span class="port-label">{{ port.name || key }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

interface Props {
  id: string
  type: string
  data: {
    label: string
    params: Record<string, any>
    inputs: Record<string, any>
    outputs: Record<string, any>
    selected?: boolean
    state?: 'idle' | 'running' | 'completed' | 'error'
  }
}

const props = defineProps<Props>()

// 节点颜色（从类型定义获取）
const nodeColor = computed(() => {
  const colors: Record<string, string> = {
    input: '#4CFF4C',
    detection: '#00f0FF',
    processing: '#FFFF4C',
    action: '#FF7F4C',
    logic: '#DC4FDC',
    output: '#FF4C4C'
  }
  return colors[props.type] || '#7D7D7D'
})

const nodeType = computed(() => {
  return props.type
})
</script>

<style scoped>
.canvas-node {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  min-width: 150px;
  font-size: 12px;
}

.canvas-node.selected {
  border-width: 2px;
  box-shadow: 0 0 0 2px var(--accent-cyan);
}

.canvas-node.running {
  animation: pulse 1s infinite;
}

.node-header {
  padding: 6px 10px;
  border-radius: 7px 7px 0 0;
  color: #000;
  font-weight: 500;
}

.node-ports {
  padding: 8px;
}

.port {
  display: flex;
  align-items: center;
  margin: 4px 0;
}

.port-label {
  margin-left: 8px;
  color: var(--text-secondary);
}
</style>
```

### 7.2 WebSocket 客户端规范

```typescript
// webui/src/stores/ruleEngineWS.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type WSMessageType =
  | 'connected'
  | 'node_started'
  | 'node_executed'
  | 'execution_progress'
  | 'execution_complete'
  | 'execution_log'

export interface WSMessage {
  type: WSMessageType
  [key: string]: any
}

export const useRuleEngineWSStore = defineStore('ruleEngineWS', () => {
  // 状态
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const sessionId = ref<string | null>(null)
  const subscriptions = ref<Set<number>>(new Set())
  const messageHistory = ref<WSMessage[]>([])

  // 连接
  function connect(url: string) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      console.log('[WS] Connected')
    }

    ws.value.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        handleMessage(msg)
      } catch (e) {
        console.error('[WS] Failed to parse message:', e)
      }
    }

    ws.value.onclose = () => {
      connected.value = false
      sessionId.value = null
      console.log('[WS] Disconnected')
    }

    ws.value.onerror = (error) => {
      console.error('[WS] Error:', error)
    }
  }

  // 断开连接
  function disconnect() {
    ws.value?.close()
    ws.value = null
  }

  // 发送消息
  function send(message: object) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    }
  }

  // 订阅执行进度
  function subscribe(executionId: number) {
    subscriptions.value.add(executionId)
    send({ type: 'subscribe', execution_id: executionId })
  }

  // 取消订阅
  function unsubscribe(executionId: number) {
    subscriptions.value.delete(executionId)
    send({ type: 'unsubscribe', execution_id: executionId })
  }

  // 请求取消执行
  function cancelExecution(executionId: number) {
    send({ type: 'cancel', execution_id: executionId })
  }

  // 处理消息
  function handleMessage(msg: WSMessage) {
    messageHistory.value.push(msg)

    switch (msg.type) {
      case 'connected':
        sessionId.value = msg.session_id
        break
      case 'node_executed':
        // 更新节点状态
        console.log(`[WS] Node ${msg.node_id} executed:`, msg.status)
        break
      case 'execution_complete':
        // 执行完成处理
        console.log(`[WS] Execution complete:`, msg.status)
        break
    }
  }

  return {
    // 状态
    connected,
    sessionId,
    subscriptions,
    messageHistory,
    // 方法
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    cancelExecution
  }
})
```

---

## 8. Git 提交规范

### 8.1 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 8.2 Type 类型

| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 bug |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构 |
| test | 测试相关 |
| chore | 构建/工具相关 |

### 8.3 Scope 值（规则引擎相关）

| Scope | 说明 |
|-------|------|
| rule-engine | 规则引擎核心 |
| rule-engine/executor | 节点执行器 |
| rule-engine/api | API 接口 |
| webui/canvas | 前端画布 |
| webui/node | 节点组件 |

### 8.4 提交示例

```
feat(rule-engine/executor): 添加 YOLOModel 节点执行器

- 实现 YOLOModelExecutor 类，继承 BaseExecutor
- 支持置信度阈值参数配置
- 对接现有 inference 模块

Closes #45
```

```
refactor(webui/canvas): 重构 RuleCanvas.vue 布局

- 分离工具栏、节点面板、画布、属性面板组件
- 提取 nodeTypes 配置到单独文件
- 优化 Vue Flow 初始化逻辑

Closes #50
```

---

## 9. 代码审查检查清单

提交代码前，确认以下项目：

### 9.1 功能性
- [ ] 新增节点执行器已注册到 registry
- [ ] validate_inputs() 处理了所有边界情况
- [ ] execute() 有异常处理，不会裸抛 Exception
- [ ] 单元测试覆盖新增代码

### 9.2 代码质量
- [ ] 所有注释使用中文
- [ ] 函数/方法有 docstring
- [ ] 没有 TODO 未完成（除非标注了明确的 ticket）
- [ ] 没有 debug print 语句

### 9.3 前端特定
- [ ] 节点组件正确使用 Handle 组件
- [ ] 颜色使用 CSS 变量或主题色
- [ ] 支持选中状态和运行状态样式
