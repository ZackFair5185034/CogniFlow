# 规则引擎数据模型文档

> 文档版本：v1.0  
> 基于调研：canvas-editor-research-2026-05-06.md  
> 创建时间：2026-05-06

---

## 1. 概述

本文档定义 CogniFlow 规则引擎的核心数据模型，包括数据库 Schema、JSON 图结构、Pydantic 校验模型。设计参考调研报告第 3 章（节点数据结构）和第 4 章（数据库设计）。

---

## 2. 数据库 Schema

### 2.1 规则图表（RuleGraph）

```sql
CREATE TABLE rule_graphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    nodes_json TEXT NOT NULL DEFAULT '{}',
    edges_json TEXT NOT NULL DEFAULT '[]',
    variables_json TEXT NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    trigger_type VARCHAR(50) NOT NULL DEFAULT 'manual',
    trigger_config TEXT NOT NULL DEFAULT '{}',
    thumbnail TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | VARCHAR(255) | 规则图名称 |
| description | TEXT | 规则图描述 |
| nodes_json | TEXT | 节点字典（JSON 字符串），格式见 3.1 |
| edges_json | TEXT | 边列表（JSON 字符串），格式见 3.2 |
| variables_json | TEXT | 变量字典（JSON 字符串），格式见 3.3 |
| is_active | BOOLEAN | 是否激活（定时执行等） |
| trigger_type | VARCHAR(50) | 触发类型：manual / timer / webhook |
| trigger_config | TEXT | 触发器配置（JSON 字符串） |
| thumbnail | TEXT | Base64 缩略图 |
| version | INTEGER | 版本号 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**trigger_config 格式示例：**

```json
// timer 类型
{"interval_seconds": 60}

// webhook 类型
{"secret": "my_webhook_secret"}
```

---

### 2.2 执行记录表（ExecutionHistory）

```sql
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graph_id INTEGER NOT NULL,
    trigger_type VARCHAR(50) NOT NULL DEFAULT 'manual',
    trigger_data TEXT NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_time_ms INTEGER,
    error_message TEXT,
    result_data TEXT,
    FOREIGN KEY (graph_id) REFERENCES rule_graphs(id)
);
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| graph_id | INTEGER | 关联的规则图 ID |
| trigger_type | VARCHAR(50) | 触发类型 |
| trigger_data | TEXT | 触发时携带的数据（JSON） |
| status | VARCHAR(50) | 状态：pending / running / completed / failed / cancelled |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |
| total_time_ms | INTEGER | 总执行耗时（毫秒） |
| error_message | TEXT | 错误信息 |
| result_data | TEXT | 执行结果（JSON 字符串） |

---

### 2.3 节点执行日志表（NodeExecutionLog）

```sql
CREATE TABLE node_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_ms INTEGER,
    input_data_json TEXT,
    output_data_json TEXT,
    error_message TEXT,
    FOREIGN KEY (execution_id) REFERENCES execution_history(id)
);
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| execution_id | INTEGER | 关联的执行记录 ID |
| node_id | VARCHAR(255) | 节点 ID |
| node_type | VARCHAR(255) | 节点类型 |
| status | VARCHAR(50) | 状态 |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |
| execution_time_ms | INTEGER | 执行耗时 |
| input_data_json | TEXT | 输入数据（JSON） |
| output_data_json | TEXT | 输出数据（JSON） |
| error_message | TEXT | 错误信息 |

---

## 3. 图数据 JSON 结构

### 3.1 节点结构（Node）

参考调研报告 3.1 ComfyUI 节点格式：

```json
{
  "id": "node_001",
  "type": "ImageCapture",
  "position": {"x": 100, "y": 200},
  "data": {
    "label": "摄像头输入",
    "params": {
      "source": "video0",
      "fps": 30
    }
  },
  "inputs": {
    "trigger": {
      "node_id": null,
      "output": null,
      "value": null
    }
  },
  "outputs": {
    "image": {
      "type": "IMAGE"
    }
  }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 节点唯一标识（前端生成，如 `node_xxx`） |
| type | string | 节点类型，对应 NodeDefinition.type |
| position | {x, y} | 画布坐标（像素） |
| data.label | string | 节点显示名称（用户可编辑） |
| data.params | dict | 节点参数值，key 对应 NodeDefinition.inputs |
| inputs | dict | 输入端口配置 |
| inputs[key].node_id | string? | 连接的源节点 ID，null 表示未连接 |
| inputs[key].output | string? | 连接的源端口名 |
| inputs[key].value | any | 未连接时的默认值 |
| outputs | dict | 输出端口配置，value 为端口类型信息 |

---

### 3.2 边结构（Edge）

参考调研报告 3.2 边格式：

```json
{
  "id": "edge_001",
  "source": "node_001",
  "source_handle": "image",
  "target": "node_002",
  "target_handle": "image",
  "type": "IMAGE"
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 边唯一标识 |
| source | string | 源节点 ID |
| source_handle | string | 源端口名 |
| target | string | 目标节点 ID |
| target_handle | string | 目标端口名 |
| type | string | 连接数据类型（IMAGE/BBOX/TRIGGER 等） |

---

### 3.3 变量结构（Variable）

```json
{
  "CONF_THRESHOLD": {
    "type": "float",
    "default": 0.5,
    "description": "检测置信度阈值"
  },
  "TARGET_CLASS": {
    "type": "string",
    "default": "person",
    "description": "目标类别名称"
  },
  "MAX_TRACKS": {
    "type": "int",
    "default": 10,
    "description": "最大跟踪目标数"
  }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 变量类型：string / int / float / bool |
| default | any | 默认值 |
| description | string | 变量描述 |

---

### 3.4 完整规则图结构示例

```json
{
  "id": 1,
  "name": "目标检测与跟踪",
  "description": "使用 YOLO 进行目标检测并跟踪",
  "nodes": {
    "node_001": {
      "id": "node_001",
      "type": "ImageCapture",
      "position": {"x": 50, "y": 200},
      "data": {
        "label": "视频输入",
        "params": {"source": "video0", "fps": 30}
      },
      "inputs": {},
      "outputs": {"image": {"type": "IMAGE"}}
    },
    "node_002": {
      "id": "node_002",
      "type": "YOLOModel",
      "position": {"x": 300, "y": 200},
      "data": {
        "label": "YOLO 检测",
        "params": {"confidence": 0.5, "model_id": 1}
      },
      "inputs": {
        "image": {"node_id": "node_001", "output": "image"},
        "confidence": {"value": 0.5}
      },
      "outputs": {
        "bboxes": {"type": "BBOX"},
        "scores": {"type": "SCORES"},
        "class_ids": {"type": "CLASS_IDS"}
      }
    },
    "node_003": {
      "id": "node_003",
      "type": "CategoryEncode",
      "position": {"x": 550, "y": 200},
      "data": {
        "label": "类别过滤",
        "params": {"target_class": "person"}
      },
      "inputs": {
        "bboxes": {"node_id": "node_002", "output": "bboxes"},
        "class_ids": {"node_id": "node_002", "output": "class_ids"}
      },
      "outputs": {
        "filtered_bboxes": {"type": "BBOX"}
      }
    },
    "node_004": {
      "id": "node_004",
      "type": "MouseClick",
      "position": {"x": 800, "y": 200},
      "data": {
        "label": "鼠标点击",
        "params": {"button": "left", "action": "click"}
      },
      "inputs": {
        "trigger": {"node_id": "node_003", "output": "filtered_bboxes"},
        "x": {"value": 100},
        "y": {"value": 200}
      },
      "outputs": {}
    }
  },
  "edges": [
    {"id": "edge_001", "source": "node_001", "source_handle": "image", "target": "node_002", "target_handle": "image", "type": "IMAGE"},
    {"id": "edge_002", "source": "node_002", "source_handle": "bboxes", "target": "node_003", "target_handle": "bboxes", "type": "BBOX"},
    {"id": "edge_003", "source": "node_002", "source_handle": "class_ids", "target": "node_003", "target_handle": "class_ids", "type": "CLASS_IDS"},
    {"id": "edge_004", "source": "node_003", "source_handle": "filtered_bboxes", "target": "node_004", "target_handle": "trigger", "type": "BBOX"}
  ],
  "variables": {
    "DEFAULT_CONFIDENCE": {"type": "float", "default": 0.5, "description": "默认置信度"}
  }
}
```

---

## 4. Pydantic 数据模型

### 4.1 请求/响应模型

```python
# 节点定义（来自 registry）
class PortDefinition(BaseModel):
    """端口定义"""
    name: str
    type: str  # IMAGE, BBOX, TRIGGER, etc.
    required: bool = True
    default: Any = None
    description: str = ""


class NodeDefinition(BaseModel):
    """节点类型定义"""
    type: str
    category: str  # input, detection, processing, action, logic, output
    display_name: str
    description: str
    icon: str
    color: str  # hex color
    inputs: Dict[str, PortDefinition]
    outputs: Dict[str, PortDefinition]


class NodeDefinitionsResponse(BaseModel):
    """节点定义响应"""
    nodes: List[NodeDefinition]
    categories: List[dict]  # {name, display_name, color, icon}


# 规则图 CRUD
class RuleGraphCreate(BaseModel):
    """创建规则图"""
    name: str
    description: str = ""
    nodes_json: str = "{}"  # JSON string
    edges_json: str = "[]"
    variables_json: str = "{}"
    version: int = 1


class RuleGraphUpdate(BaseModel):
    """更新规则图"""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes_json: Optional[str] = None
    edges_json: Optional[str] = None
    variables_json: Optional[str] = None
    is_active: Optional[bool] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[str] = None
    thumbnail: Optional[str] = None


class RuleGraphResponse(BaseModel):
    """规则图响应"""
    id: int
    name: str
    description: str
    is_active: bool
    trigger_type: str
    thumbnail: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime


class RuleGraphDetailResponse(BaseModel):
    """规则图详情（含解析后数据）"""
    id: int
    name: str
    description: str
    is_active: bool
    nodes: Dict[str, Any]  # 解析后的节点字典
    edges: List[Dict[str, Any]]
    variables: Dict[str, Any]


# 执行
class ExecutionTrigger(BaseModel):
    """执行触发请求"""
    graph_id: int
    trigger_type: str = "manual"  # manual, timer, webhook
    trigger_data: Dict[str, Any] = {}


class ExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: int
    status: str
    result: Dict[str, Any]


class ExecutionHistoryResponse(BaseModel):
    """执行历史记录"""
    id: int
    graph_id: int
    trigger_type: str
    trigger_data: Dict[str, Any]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_time_ms: Optional[int]
    error_message: Optional[str]


class NodeExecutionLogResponse(BaseModel):
    """节点执行日志"""
    node_id: str
    node_type: str
    status: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error_message: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
```

---

## 5. 节点执行上下文

### 5.1 ExecutionContext

```python
class ExecutionContext:
    """规则图执行时的上下文，在整个执行期间共享"""

    def __init__(self, execution_id: int, trigger_type: str, trigger_data: Dict[str, Any]):
        self.execution_id = execution_id
        self.trigger_type = trigger_type
        self.trigger_data = trigger_data

        # 节点执行结果缓存：node_id -> output_data
        self.node_results: Dict[str, Dict[str, Any]] = {}

        # 节点状态：node_id -> status
        self.node_status: Dict[str, str] = {}

        # 规则变量
        self.variables: Dict[str, Any] = {}

        # 执行配置
        self.config: Dict[str, Any] = {}

        # 是否取消
        self.cancelled = False

    def get_node_result(self, node_id: str, output_name: str) -> Any:
        """获取指定节点的输出数据"""
        return self.node_results.get(node_id, {}).get(output_name)

    def set_node_result(self, node_id: str, outputs: Dict[str, Any]):
        """设置节点输出数据"""
        self.node_results[node_id] = outputs

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self.cancelled

    def cancel(self):
        """请求取消执行"""
        self.cancelled = True
```

---

## 6. 节点类型定义

### 6.1 类型兼容性矩阵

参考调研报告 3.5 和 8.5：

```python
# 类型兼容性：源类型 -> 可连接的目标类型
TYPE_COMPATIBILITY = {
    "IMAGE": ["IMAGE", "MASK"],
    "BBOX": ["BBOX"],
    "MASK": ["MASK"],
    "SCORES": ["SCORES"],
    "CLASS_IDS": ["CLASS_IDS"],
    "TRIGGER": ["TRIGGER", "BBOX", "IMAGE", "MASK", "SCORES", "CLASS_IDS", "CONTROL"],
    "CONTROL": ["CONTROL"],
    "MODEL": ["MODEL"],
    "ANY": ["IMAGE", "BBOX", "MASK", "SCORES", "CLASS_IDS", "TRIGGER", "CONTROL", "MODEL", "ANY"],
}


def can_connect(source_type: str, target_type: str) -> bool:
    """检查两个类型是否可以连接"""
    compatible_types = TYPE_COMPATIBILITY.get(source_type, [])
    return target_type in compatible_types or source_type == "ANY"
```

---

## 7. 拓扑排序数据结构

### 7.1 Kahn 算法输入/输出

```python
from collections import defaultdict, deque
from typing import List, Dict, Set, Tuple


def build_dependency_graph(
    nodes: Dict[str, Node],
    edges: List[Edge]
) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    """
    从节点和边构建依赖图

    Returns:
        graph: Dict[str, List[str]] - 邻接表，graph[target] = [sources...]
        in_degree: Dict[str, int] - 入度表
    """
    graph = defaultdict(list)
    in_degree = defaultdict(int)

    # 初始化所有节点的入度
    for node_id in nodes:
        in_degree[node_id] = 0

    # 从边构建依赖关系
    for edge in edges:
        # target 依赖 source
        graph[edge["target"]].append(edge["source"])
        in_degree[edge["target"]] += 1

    return dict(graph), dict(in_degree)


def topological_sort_levels(
    nodes: Dict[str, Node],
    edges: List[Edge]
) -> List[List[str]]:
    """
    Kahn 算法拓扑排序，返回按层级分组的节点列表

    Returns:
        List of levels, each level is a list of node IDs
        e.g., [["node_001"], ["node_002", "node_003"], ["node_004"]]
        同层节点可以并行执行

    Raises:
        CycleError: 如果图中存在环
    """
    graph, in_degree = build_dependency_graph(nodes, edges)

    # 收集所有节点
    all_nodes = set(nodes.keys())

    # Kahn 算法
    queue = deque([n for n in all_nodes if in_degree.get(n, 0) == 0])
    levels = []

    while queue:
        level_nodes = list(queue)
        levels.append(level_nodes)
        queue.clear()

        for node_id in level_nodes:
            for dependent in graph.get(node_id, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    # 检查是否有环
    processed = set()
    for level in levels:
        processed.update(level)

    unprocessed = all_nodes - processed
    if unprocessed:
        # 找出环中的节点
        cycle_nodes = find_cycle_nodes(graph, unprocessed)
        raise CycleError(f"规则图存在循环依赖: {' -> '.join(cycle_nodes)}", cycle_nodes)

    return levels


def find_cycle_nodes(graph: Dict[str, List[str]], remaining: Set[str]) -> List[str]:
    """找出环中的节点（简单实现）"""
    # 简化：返回未处理的节点作为环节点
    return list(remaining)
```

---

## 8. 序列化格式对比

### 8.1 ComfyUI 格式 vs CogniFlow 格式

| 方面 | ComfyUI | CogniFlow |
|------|---------|-----------|
| 节点存储 | `nodes: Dict` | `nodes: Dict`（一致） |
| 边存储 | `links: Dict` | `edges: List[Edge]`（简化） |
| 位置 | `pos: [x, y]` | `position: {x, y}`（语义更清晰） |
| 参数 | `widgets_values: []` | `data.params: Dict`（类型化） |
| 连接引用 | `[node_id, output_index]` | `{node_id, output}`（具名引用） |

**CogniFlow 选择 `edges: List[Edge]` 而非 `links: Dict` 的原因：**
- List 结构更直观，前端 Vue Flow 原生支持
- 避免 link_id 的额外管理工作
- 简化序列化/反序列化逻辑

### 8.2 节点引用格式对比

**ComfyUI（数组索引）：**
```json
"inputs": {
  "model": ["checkpoint_loader", 0]
}
```

**CogniFlow（具名引用）：**
```json
"inputs": {
  "image": {"node_id": "node_001", "output": "image"}
}
```

**CogniFlow 选择具名引用的原因：**
- 更易读和调试
- 支持重命名节点后更新引用
- 便于前端校验连接有效性
