# -*- coding: utf-8 -*-
"""规则引擎节点执行指标采集测试。

测试覆盖：
1. _compute_metrics 对各类型输出的指标计算
2. _save_node_log 写入 metrics_json 字段到数据库
3. WebSocketManager.send_node_executed payload 包含 metrics
4. _broadcast_node_executed payload 包含 metrics
5. 端到端：_execute_node 成功后，WebSocket payload 含 metrics
"""
import json
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

import pytest

sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.websocket_manager import RuleExecutionConnectionManager
from backend.services.rule_engine.models import NodeCategory, NodeDefinition, PortDefinition
from backend.services.rule_engine.nodes.base import BaseExecutor


# ============================================================================
# 辅助节点：返回固定 outputs，便于验证 _compute_metrics
# ============================================================================

class _MetricsNode(BaseExecutor):
    """测试用：返回固定 outputs 的节点（用于验证 metrics 计算）。"""
    node_type = "_metrics_node"
    category = NodeCategory.LOGIC
    display_name = "指标节点"

    def __init__(self, node_id=None, config=None, outputs=None):
        super().__init__(node_id=node_id, config=config)
        self._outputs = outputs or {}

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description="测试节点",
            icon="chart",
            color="#888",
            inputs={},
            outputs={
                "result": PortDefinition(
                    name="结果",
                    type="ANY",
                    description="结果",
                ),
            },
            config_schema={},
        )

    def validate_inputs(self, inputs):
        return True, None

    async def execute(self, inputs, context):
        return self._outputs


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """模拟数据库会话。"""
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def mock_ws_manager():
    """模拟 WebSocket 管理器。"""
    ws = Mock()
    ws.broadcast = AsyncMock()
    return ws


@pytest.fixture
def executor(mock_db, mock_ws_manager):
    """创建执行器实例。"""
    return RuleGraphExecutor(db=mock_db, ws_manager=mock_ws_manager)


@pytest.fixture
def ws_manager():
    """创建 WebSocketManager 实例，并 mock broadcast 以便观测。"""
    wm = RuleExecutionConnectionManager()
    wm.broadcast = AsyncMock()
    return wm


# ============================================================================
# 1. _compute_metrics 单元测试
# ============================================================================

def test_compute_metrics_list_outputs(executor):
    """list 输出：metrics[key] = len(list)。"""
    metrics = executor._compute_metrics({"detections": [{"bbox": 1}, {"bbox": 2}, {"bbox": 3}]})
    assert metrics == {"detections": 3}


def test_compute_metrics_dict_outputs(executor):
    """dict 输出：metrics[key] = len(dict)。"""
    metrics = executor._compute_metrics({"result": {"a": 1, "b": 2, "c": 3}})
    assert metrics == {"result": 3}


def test_compute_metrics_string_outputs(executor):
    """str 输出：metrics[key] = len(str)。"""
    metrics = executor._compute_metrics({"body": "hello world"})
    assert metrics == {"body": 11}


def test_compute_metrics_numeric_outputs(executor):
    """数字输出：metrics[key] = 1（标量记为 1）。"""
    metrics = executor._compute_metrics({"count": 42, "score": 0.95})
    assert metrics == {"count": 1, "score": 1}


def test_compute_metrics_none_outputs(executor):
    """None 输出：metrics[key] = 0。"""
    metrics = executor._compute_metrics({"empty": None})
    assert metrics == {"empty": 0}


def test_compute_metrics_empty_dict(executor):
    """空 outputs：返回空 dict。"""
    metrics = executor._compute_metrics({})
    assert metrics == {}


def test_compute_metrics_mixed_outputs(executor):
    """混合类型输出：每个 key 独立计算。"""
    metrics = executor._compute_metrics({
        "detections": [1, 2, 3, 4, 5],
        "status_code": 200,
        "body": "x" * 100,
        "config": {"a": 1, "b": 2},
    })
    assert metrics == {
        "detections": 5,
        "status_code": 1,
        "body": 100,
        "config": 2,
    }


# ============================================================================
# 2. _save_node_log 单元测试
# ============================================================================

@pytest.mark.asyncio
async def test_save_node_log_writes_metrics_json(executor, mock_db):
    """_save_node_log 应该把 metrics 序列化为 metrics_json 字段。"""
    metrics = {"detections": 5, "body": 100}
    await executor._save_node_log(
        execution_id=1,
        node_id="node-1",
        node_type="yolo_model",
        status="completed",
        duration_ms=150,
        error_message=None,
        metrics=metrics,
    )

    # 验证 db.add 被调用一次
    assert mock_db.add.call_count == 1
    # 验证 db.commit 被调用一次
    assert mock_db.commit.call_count == 1

    # 验证传入的 log 对象包含 metrics_json 字段
    log_obj = mock_db.add.call_args[0][0]
    assert log_obj.node_id == "node-1"
    assert log_obj.node_type == "yolo_model"
    assert log_obj.status == "completed"
    assert log_obj.duration_ms == 150
    assert log_obj.metrics_json is not None
    # 验证 metrics_json 是有效 JSON 且内容正确
    parsed = json.loads(log_obj.metrics_json)
    assert parsed == metrics


@pytest.mark.asyncio
async def test_save_node_log_handles_none_metrics(executor, mock_db):
    """_save_node_log 在 metrics=None 时，metrics_json 应为 None。"""
    await executor._save_node_log(
        execution_id=1,
        node_id="node-1",
        node_type="delay",
        status="completed",
        duration_ms=100,
        error_message=None,
        metrics=None,
    )
    log_obj = mock_db.add.call_args[0][0]
    assert log_obj.metrics_json is None


@pytest.mark.asyncio
async def test_save_node_log_swallows_exceptions(executor, mock_db):
    """_save_node_log 写库失败不应影响主流程。"""
    mock_db.add.side_effect = Exception("DB write failed")
    # 不应该抛异常
    await executor._save_node_log(
        execution_id=1,
        node_id="node-1",
        node_type="delay",
        status="completed",
        duration_ms=100,
    )
    # 不验证 commit 因为 add 已经抛异常


@pytest.mark.asyncio
async def test_save_node_log_no_db(executor):
    """无 DB 时 _save_node_log 应该直接返回（不抛异常）。"""
    executor.db = None
    # 不应该抛异常
    await executor._save_node_log(
        execution_id=1,
        node_id="node-1",
        node_type="delay",
        status="completed",
        duration_ms=100,
    )


# ============================================================================
# 3. WebSocketManager.send_node_executed 单元测试
# ============================================================================

@pytest.mark.asyncio
async def test_send_node_executed_includes_metrics(ws_manager):
    """send_node_executed payload 应包含 metrics 字段。"""
    metrics = {"detections": 5, "score": 0.95}
    await ws_manager.send_node_executed(
        execution_id=1,
        node_id="node-1",
        status="success",
        outputs={"detections": [1, 2, 3, 4, 5]},
        metrics=metrics,
    )

    # ws_manager.broadcast 应该被调用一次
    assert ws_manager.broadcast.call_count == 1
    payload = ws_manager.broadcast.call_args[0][0]
    assert payload["type"] == "node_executed"
    assert payload["node_id"] == "node-1"
    assert payload["status"] == "success"
    assert payload["metrics"] == metrics


@pytest.mark.asyncio
async def test_send_node_executed_metrics_optional(ws_manager):
    """send_node_executed 在 metrics=None 时，payload 中 metrics 应为 None。"""
    await ws_manager.send_node_executed(
        execution_id=1,
        node_id="node-1",
        status="success",
        outputs={},
    )
    payload = ws_manager.broadcast.call_args[0][0]
    assert payload["metrics"] is None


# ============================================================================
# 4. _broadcast_node_executed 单元测试
# ============================================================================

@pytest.mark.asyncio
async def test_broadcast_node_executed_passes_metrics(executor):
    """_broadcast_node_executed 应该把 metrics 传给 ws_manager.broadcast。"""
    metrics = {"detections": 3}
    await executor._broadcast_node_executed(
        execution_id=1,
        node_id="node-1",
        node_type="yolo_model",
        status="success",
        outputs={"detections": [1, 2, 3]},
        duration_ms=200,
        metrics=metrics,
    )
    payload = executor.ws_manager.broadcast.call_args[0][0]
    assert payload["type"] == "node_executed"
    assert payload["node_id"] == "node-1"
    assert payload["status"] == "success"
    assert payload["duration_ms"] == 200
    assert payload["metrics"] == metrics
    # node_type 必须带上 —— 前端日志面板按它标注来源节点 (2026-10-24 走查发现)
    assert payload["node_type"] == "yolo_model"


@pytest.mark.asyncio
async def test_broadcast_node_executed_no_ws_manager(executor):
    """无 ws_manager 时 _broadcast_node_executed 不应抛异常。"""
    executor.ws_manager = None
    # 不应该抛异常
    await executor._broadcast_node_executed(
        execution_id=1,
        node_id="node-1",
        node_type="yolo_model",
        status="success",
        outputs={},
    )


# ============================================================================
# 5. 端到端测试：_execute_node 成功 → metrics 流向 WS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_node_broadcasts_metrics_on_success(executor, mock_ws_manager, monkeypatch):
    """_execute_node 成功后，WebSocket payload 应包含 metrics。

    端到端集成：_execute_node 内部调用 _compute_metrics 生成 metrics，
    校验该 metrics 通过 _broadcast_node_executed 流向 WebSocket payload。
    _compute_metrics 自身逻辑已在 test_compute_metrics_* 中单测覆盖。
    """
    import backend.services.rule_engine.executor as executor_module

    # Patch _compute_metrics 返回固定值，验证 metrics 字段被正确序列化到 WS payload
    monkeypatch.setattr(
        executor_module.RuleGraphExecutor,
        "_compute_metrics",
        lambda self, outputs: {"detections": 3},
    )

    # 准备 context
    from backend.services.rule_engine.nodes.base import ExecutionContext
    from backend.services.rule_engine.registry import get_registry

    registry = get_registry()
    registry.register(_MetricsNode)

    try:
        context = ExecutionContext(
            execution_id=1,
            trigger_type='manual',
            trigger_data={},
            config={
                "nodes": {
                    "node-1": {
                        "id": "node-1",
                        "type": "_metrics_node",
                        "data": {
                            "type": "_metrics_node",
                            "config": {},
                        },
                    }
                }
            }
        )

        await executor._execute_node(
            node_id="node-1",
            context=context,
            timeout=10,
        )

        executed_calls = [
            call for call in mock_ws_manager.broadcast.call_args_list
            if call[0][0].get("type") == "node_executed"
        ]
        assert len(executed_calls) == 1, f"expected 1 node_executed, got {len(executed_calls)}"
        payload = executed_calls[0][0][0]
        assert "metrics" in payload
        assert payload["metrics"] == {"detections": 3}
    finally:
        # 清理注册（NodeRegistry 无 unregister API，直接操作内部 dict）
        registry._executors.pop("_metrics_node", None)


@pytest.mark.asyncio
async def test_execute_node_broadcasts_metrics_with_multiple_outputs(executor, mock_ws_manager, monkeypatch):
    """_execute_node 多个输出时，metrics 应包含每个 key 的统计。

    验证 _compute_metrics → _broadcast_node_executed 集成链路：
    当 _compute_metrics 返回多 key 指标时，WS payload 完整保留。
    """
    import backend.services.rule_engine.executor as executor_module

    # Patch _compute_metrics 返回多 key 指标
    monkeypatch.setattr(
        executor_module.RuleGraphExecutor,
        "_compute_metrics",
        lambda self, outputs: {"detections": 7, "summary": 12, "count": 1},
    )

    from backend.services.rule_engine.nodes.base import ExecutionContext
    from backend.services.rule_engine.registry import get_registry

    class _MixedOutputsNode(_MetricsNode):
        node_type = "_mixed_outputs"

    registry = get_registry()
    registry.register(_MixedOutputsNode)

    try:
        context = ExecutionContext(
            execution_id=1,
            trigger_type='manual',
            trigger_data={},
            config={
                "nodes": {
                    "node-1": {
                        "id": "node-1",
                        "type": "_mixed_outputs",
                        "data": {
                            "type": "_mixed_outputs",
                            "config": {},
                        },
                    }
                }
            }
        )

        await executor._execute_node(
            node_id="node-1",
            context=context,
            timeout=10,
        )

        executed_calls = [
            call for call in mock_ws_manager.broadcast.call_args_list
            if call[0][0].get("type") == "node_executed"
        ]
        assert len(executed_calls) == 1
        payload = executed_calls[0][0][0]
        assert payload["metrics"] == {
            "detections": 7,
            "summary": 12,
            "count": 1,
        }
    finally:
        registry._executors.pop("_mixed_outputs", None)
