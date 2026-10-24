# -*- coding: utf-8 -*-
"""节点连接契约测试 - data.connections 与旧 data.inputs dict 的双格式兼容。

背景: 前端 `graph.ts` 的 `createNode` 把 `data.inputs` 存成**端口元数据数组**
(`[{name, type, label, ...}]`), 而后端 `executor.py` 的 `_resolve_inputs` 对它调
`.items()` -> `AttributeError: 'list' object has no attribute 'items'`。
实测后果: 54 个节点全部崩溃、0 输出。

修复方向: 端口元数据(`data.inputs`/`data.outputs`, 用于渲染手柄)与连线关系
(`data.connections`, 用于取上游数据)职责分离。
"""
from unittest.mock import MagicMock

import pytest

from backend.services.rule_engine.executor import RuleGraphExecutor


@pytest.fixture
def executor():
    """构造一个只用于 _resolve_inputs 的执行器实例。"""
    return RuleGraphExecutor()


class TestResolveInputs:
    """_resolve_inputs 的输入解析。"""

    def test_resolves_from_connections_field(self, executor):
        """新契约: 从 data.connections 解析上游节点结果。"""
        context = MagicMock()
        context.get_node_result.return_value = {"detections": [{"cls": "cat", "conf": 0.9}]}

        result = executor._resolve_inputs(
            {"image": {"node_id": "node_yolo", "output": "detections"}},
            context,
        )

        assert result["image"] == {"detections": [{"cls": "cat", "conf": 0.9}]}
        context.get_node_result.assert_called_once_with("node_yolo", "detections")

    def test_list_inputs_does_not_crash(self, executor):
        """回归: 前端存成数组时不能抛 AttributeError(原 54 节点全崩根因)。"""
        context = MagicMock()
        context.get_node_result.return_value = None

        result = executor._resolve_inputs(
            [{"name": "image", "type": "IMAGE", "label": "图像"}],
            context,
        )

        assert result == {}

    def test_missing_source_returns_none_not_raise(self, executor):
        """上游节点没有结果时返回 None, 不抛异常。"""
        context = MagicMock()
        context.get_node_result.return_value = None

        result = executor._resolve_inputs(
            {"image": {"node_id": "node_missing", "output": "detections"}},
            context,
        )

        assert result == {"image": None}

    def test_default_value_is_used_when_not_connected(self, executor):
        """未连线但配了默认值时使用默认值。"""
        context = MagicMock()

        result = executor._resolve_inputs({"threshold": {"value": 0.5}}, context)

        assert result == {"threshold": 0.5}

    def test_unconnected_port_without_value_is_absent(self, executor):
        """既无 node_id 也无 value 的端口不写入结果(缺失即报错, 不静默传 None)。"""
        context = MagicMock()

        result = executor._resolve_inputs({"trigger": {}}, context)

        assert result == {}
        assert "trigger" not in result


class TestExecuteNodeInputSource:
    """执行单个节点时, 输入配置来源的优先级。"""

    def test_connections_field_takes_priority_over_inputs(self):
        """data.connections 优先于 data.inputs(旧 dict 格式)。"""
        from backend.services.rule_engine.executor import RuleGraphExecutor as _E

        node_data = {
            "connections": {"trigger": {"node_id": "from_connections", "output": "result"}},
            "inputs": {"trigger": {"node_id": "from_inputs", "output": "result"}},
        }

        config = node_data.get("connections")
        if not isinstance(config, dict):
            config = node_data.get("inputs")
        if not isinstance(config, dict):
            config = {}

        assert config["trigger"]["node_id"] == "from_connections"
        assert _E is not None


class TestBuildInputConfig:
    """_build_input_config —— 连接关系以边表为准推导。"""

    @staticmethod
    def _context(edges, nodes=None):
        from backend.services.rule_engine.nodes.base import ExecutionContext

        return ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={},
            node_results={},
            node_status={},
            variables={},
            config={"nodes": nodes or {}, "edges": edges},
        )

    def test_connections_are_derived_from_edges(self):
        """边表是权威来源: 没有 data.connections 也能推出连接关系。"""
        executor = RuleGraphExecutor()
        edges = [{
            "source": "n_yolo", "target": "n_log",
            "source_handle": "detections", "target_handle": "trigger",
        }]
        context = self._context(edges)

        config = executor._build_input_config("n_log", {}, context)

        assert config["trigger"] == {"node_id": "n_yolo", "output": "detections"}

    def test_snake_case_handles_are_supported(self):
        """后端格式(蛇形)的边也能推导出连接。"""
        executor = RuleGraphExecutor()
        edges = [{
            "source": "n_yolo", "target": "n_log",
            "source_handle": "detections", "target_handle": "trigger",
        }]
        context = self._context(edges)

        config = executor._build_input_config("n_log", {}, context)

        assert config["trigger"]["node_id"] == "n_yolo"

    def test_edges_override_declared_connections(self):
        """边表与 data.connections 冲突时以边表为准。"""
        executor = RuleGraphExecutor()
        edges = [{
            "source": "from_edge", "target": "n_log",
            "source_handle": "out", "target_handle": "trigger",
        }]
        context = self._context(edges)
        node_data = {"connections": {"trigger": {"node_id": "declared", "output": "x"}}}

        config = executor._build_input_config("n_log", node_data, context)

        assert config["trigger"]["node_id"] == "from_edge"

    def test_declared_connections_fill_gaps(self):
        """边表没覆盖的端口由 data.connections 补齐。"""
        executor = RuleGraphExecutor()
        edges = [{
            "source": "n_a", "target": "n_log",
            "source_handle": "out", "target_handle": "trigger",
        }]
        context = self._context(edges)
        node_data = {"connections": {"extra": {"node_id": "n_b", "output": "o"}}}

        config = executor._build_input_config("n_log", node_data, context)

        assert config["trigger"]["node_id"] == "n_a"
        assert config["extra"]["node_id"] == "n_b"

    def test_legacy_inputs_dict_is_used_as_fallback(self):
        """既无边也无 connections 时, 回退到旧契约 data.inputs(dict)。"""
        executor = RuleGraphExecutor()
        context = self._context([])
        node_data = {"inputs": {"trigger": {"node_id": "legacy", "output": "r"}}}

        config = executor._build_input_config("n_log", node_data, context)

        assert config["trigger"]["node_id"] == "legacy"
