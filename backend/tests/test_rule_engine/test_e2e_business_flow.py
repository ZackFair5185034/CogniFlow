# -*- coding: utf-8 -*-
"""端到端业务闭环测试 - 规则图真的能跑出业务结果。

背景: 2026-10-24 实测发现规则引擎存在「四层静默失败」, 其中最上层是
顶层执行状态恒为 `{"status": "completed"}` —— 无论有多少节点失败都报成功。
数据库里唯一一条执行记录(2026-06-04)的 merged 为 []、count 为 0,
即「完成但零输出」, 正是谎报状态掩盖了全崩溃。

本文件锁定:
1. 顶层 status 由节点真实结果推导;
2. 一条 触发器 -> 检测 -> 动作 的链路, 动作节点真的拿到了上游数据。
"""
from unittest.mock import MagicMock, patch

import pytest

from backend.services.rule_engine.executor import RuleGraphExecutor


def _make_fake_executor(node_type: str, outputs: dict | None = None):
    """构造一个最小可用执行器替身。

    Args:
        node_type: 节点类型标识
        outputs: 该节点执行后写入 node_results 的输出字典(键为输出端口名)
    """
    payload = outputs if outputs is not None else {"result": {"node": node_type, "value": 1}}

    class FakeExecutor:
        def __init__(self, node_id=None, config=None):
            self.node_id = node_id
            self.config = config or {}

        def get_definition(self):
            """_validate_graph_connections 需要端口定义来校验连线类型。"""
            from backend.services.rule_engine.models import (
                NodeDefinition,
                PortDefinition,
            )

            return NodeDefinition(
                type=node_type,
                category="test",
                display_name=node_type,
                inputs={"image": PortDefinition(name="图像", type="ANY")},
                outputs={"result": PortDefinition(name="结果", type="ANY")},
            )

        def validate_inputs(self, inputs):
            return True, None

        async def execute(self, inputs, context):
            return payload

    return FakeExecutor


class TestTopLevelStatus:
    """顶层执行状态必须由节点真实结果推导。"""

    @pytest.mark.asyncio
    async def test_status_is_failed_when_a_node_failed(self):
        """有节点失败时顶层状态必须是 failed, 不能恒为 completed。"""
        executor = RuleGraphExecutor()
        graph_data = {
            "nodes": {
                "n1": {"id": "n1", "type": "manual_trigger", "data": {"type": "manual_trigger"}},
                "n2": {"id": "n2", "type": "log_action", "data": {"type": "log_action"}},
            },
            "edges": [{
                "source": "n1", "target": "n2",
                "source_handle": "result", "target_handle": "trigger",
            }],
            "variables": {},
        }

        async def fake_execute_node(self, node_id, context, *args, **kwargs):
            # 第一个参数是 self: 用 patch.object(..., new=fn) 替换类方法时,
            # 普通函数会按描述符协议绑定 self, 签名必须带上。
            context.set_node_status(node_id, "failed" if node_id == "n2" else "completed")
            return None

        with patch.object(RuleGraphExecutor, "_execute_node", new=fake_execute_node):
            result = await executor.execute(graph_data=graph_data, execution_id=999001)

        assert result["status"] == "failed"
        assert "n2" in result["failed_nodes"]

    @pytest.mark.asyncio
    async def test_status_is_completed_when_all_succeeded(self):
        """全部成功时状态为 completed。"""
        executor = RuleGraphExecutor()
        graph_data = {
            "nodes": {
                "n1": {"id": "n1", "type": "manual_trigger", "data": {"type": "manual_trigger"}},
            },
            "edges": [],
            "variables": {},
        }

        async def fake_execute_node(self, node_id, context, *args, **kwargs):
            context.set_node_status(node_id, "completed")
            return None

        with patch.object(RuleGraphExecutor, "_execute_node", new=fake_execute_node):
            result = await executor.execute(graph_data=graph_data, execution_id=999002)

        assert result["status"] == "completed"
        assert result["failed_nodes"] == []

    @pytest.mark.asyncio
    async def test_timeout_node_counts_as_failed(self):
        """超时的节点也算失败(下游继续执行, 但顶层不能报成功)。"""
        executor = RuleGraphExecutor()
        graph_data = {
            "nodes": {
                "n1": {"id": "n1", "type": "manual_trigger", "data": {"type": "manual_trigger"}},
            },
            "edges": [],
            "variables": {},
        }

        async def fake_execute_node(self, node_id, context, *args, **kwargs):
            context.set_node_status(node_id, "timeout")
            return None

        with patch.object(RuleGraphExecutor, "_execute_node", new=fake_execute_node):
            result = await executor.execute(graph_data=graph_data, execution_id=999004)

        assert result["status"] == "failed"
        assert "n1" in result["failed_nodes"]
        assert result["error"]


class TestBusinessFlowE2E:
    """真实链路: 触发器 -> 检测 -> 动作, 动作必须拿到上游真实数据。"""

    @pytest.mark.asyncio
    async def test_action_node_receives_upstream_data(self):
        """动作节点必须拿到上游节点的真实输出(核心闭环断言)。"""
        from backend.services.rule_engine.registry import init_builtin_executors

        init_builtin_executors()
        executor = RuleGraphExecutor()

        graph_data = {
            "nodes": {
                "n_trigger": {
                    "id": "n_trigger",
                    "type": "manual_trigger",
                    "data": {"type": "manual_trigger", "connections": {}},
                },
                "n_yolo": {
                    "id": "n_yolo",
                    "type": "yolo_model",
                    "data": {
                        "type": "yolo_model",
                        "config": {"model_id": 1},
                        "connections": {},
                    },
                },
                "n_log": {
                    "id": "n_log",
                    "type": "log_action",
                    "data": {
                        "type": "log_action",
                        "config": {"message": "检测到目标"},
                        "connections": {
                            "trigger": {"node_id": "n_yolo", "output": "detections"}
                        },
                    },
                },
            },
            "edges": [
                {"source": "n_trigger", "target": "n_yolo",
                 "source_handle": "result", "target_handle": "image"},
                {"source": "n_yolo", "target": "n_log",
                 "source_handle": "detections", "target_handle": "trigger"},
            ],
            "variables": {},
        }

        captured: dict = {}

        class SpyLogAction:
            """替身 log_action, 记录收到的输入。"""

            node_type = "log_action"

            def __init__(self, node_id=None, config=None):
                self.node_id = node_id
                self.config = config or {}

            def get_definition(self):
                """_validate_graph_connections 需要端口定义来校验连线类型。"""
                from backend.services.rule_engine.models import (
                    NodeDefinition,
                    PortDefinition,
                )

                return NodeDefinition(
                    type="log_action",
                    category="action",
                    display_name="日志",
                    inputs={"trigger": PortDefinition(name="触发", type="ANY")},
                    outputs={},
                )

            def validate_inputs(self, inputs):
                return True, None

            async def execute(self, inputs, context):
                captured.update(inputs)
                return {"logged": True, "received": inputs}

        # 每个节点类型的输出端口名必须与图里的连线一致:
        #   n_trigger.result -> n_yolo.image
        #   n_yolo.detections -> n_log.trigger
        node_outputs = {
            "manual_trigger": {"result": {"triggered": True}},
            "yolo_model": {"detections": [{"cls": "cat", "conf": 0.94}]},
        }

        with patch(
            "backend.services.rule_engine.executor.get_registry"
        ) as mock_registry:
            # 必须 patch executor 模块里的名字: executor.py 用
            # `from .registry import get_registry` 直接绑定了引用,
            # patch 源模块 registry.get_registry 不会生效。
            registry = MagicMock()
            # registry.get 返回**类**(供 _validate_graph_connections 拿端口定义)
            registry.get.side_effect = lambda t: _make_fake_executor(t)
            # registry.create_node 返回**实例**(供执行器真正调用 execute)
            registry.create_node.side_effect = (
                lambda node_type, node_id=None, config=None:
                    SpyLogAction(node_id, config)
                    if node_type == "log_action"
                    else _make_fake_executor(
                        node_type, node_outputs.get(node_type)
                    )(node_id, config)
            )
            mock_registry.return_value = registry

            result = await executor.execute(graph_data=graph_data, execution_id=999003)

        assert result["status"] == "completed", result
        assert result["failed_nodes"] == []
        # 核心断言: 动作节点收到了上游节点的输出, 而不是 None
        assert "trigger" in captured
        assert captured["trigger"] is not None, "动作节点没有收到上游数据"
        assert captured["trigger"] == [{"cls": "cat", "conf": 0.94}]


class TestValidateApi:
    """/validate 必须返回结构化错误, 前端才能显示真实原因。"""

    @pytest.fixture
    def graph_id(self):
        """创建一个缺触发器的规则图(校验必然失败), 测试结束后删除。"""
        from backend.database import RuleGraph, SessionLocal, init_db

        init_db()
        db = SessionLocal()
        graph = RuleGraph(
            name="cf_validate_test_graph",
            description="校验接口测试用规则图",
            nodes_json='[{"id": "n1", "type": "log_action", "data": {"type": "log_action"}}]',
            edges_json="[]",
        )
        db.add(graph)
        db.commit()
        db.refresh(graph)
        gid = graph.id
        yield gid
        db.query(RuleGraph).filter(RuleGraph.id == gid).delete()
        db.commit()
        db.close()

    def test_invalid_graph_returns_errors_list(self, graph_id):
        """校验失败时 errors 是非空字符串数组, 且 error 字段向后兼容。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app

        client = TestClient(fastapi_app)
        resp = client.post(f"/api/rule-engine/graphs/{graph_id}/validate")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["valid"] is False
        assert isinstance(body["errors"], list)
        assert len(body["errors"]) > 0
        assert all(isinstance(e, str) and e for e in body["errors"])
        assert body["error"] == body["errors"][0]
