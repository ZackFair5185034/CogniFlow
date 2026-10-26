# -*- coding: utf-8 -*-
"""
Branch 节点分流执行测试 (Phase 19.1)

覆盖场景:
1. Branch 节点 result="true" -> true 分支 completed, false 分支 skipped
2. Branch 节点 result="false" -> false 分支 completed, true 分支 skipped
3. Branch 节点没接 output 边 -> 不报错, 不影响执行
4. Branch 节点 result 字段异常 -> 保守: 不跳过, 两路都跑

策略: 通过 mock _save_node_log 拿到每个节点的实际 status 写入
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from backend.services.rule_engine.executor import RuleGraphExecutor


def make_node(node_id, node_type, category="logic", config=None, position=None, inputs=None):
    return {
        "id": node_id,
        "type": node_type,
        "category": category,
        "data": {
            "type": node_type,
            "category": category,
            "config": config or {},
            **({"inputs": inputs} if inputs else {}),
        },
        "position": position or {"x": 0, "y": 0},
    }


class _StatusRecorder:
    """记录 _save_node_log 调用, 按 (node_id, status) 索引"""
    def __init__(self):
        self.calls = []  # list of (node_id, status)

    async def __call__(self, execution_id, node_id, node_type, status, duration_ms, error_message=None, metrics=None):
        self.calls.append((node_id, status))
        return None


class TestBranchSkipBehavior:
    """Branch 节点分流到执行器的集成测试"""

    def setup_method(self):
        """每个测试前初始化 registry (Class-level singleton, 避免其他测试清空)"""
        from backend.services.rule_engine.registry import init_builtin_executors
        init_builtin_executors()

    def _setup(self, condition_value):
        """构造 graph: ManualTrigger -> SetVariable(score) -> VariableCondition(score>=60) -> Branch(true/false) -> Display"""
        score = 85 if condition_value else 30
        nodes = {
            "n1": make_node("n1", "manual_trigger", "input", position={"x": 0, "y": 0}),
            "n2": make_node("n2", "set_variable", "logic",
                           config={"variable_name": "score", "value": str(score), "value_type": "static"},
                           position={"x": 200, "y": 0}),
            "n3": make_node("n3", "variable_condition", "logic",
                           config={"variable_name": "score", "expected_value": "60", "comparison": "gte"},
                           position={"x": 400, "y": 0}),
            "n4": make_node("n4", "branch", "logic",
                           position={"x": 600, "y": 0},
                           inputs={"condition": {"node_id": "n3", "output": "result"}}),
            "n5": make_node("n5", "display", "output",
                           config={"title": "true 分支"},
                           position={"x": 800, "y": -100}),
            "n6": make_node("n6", "display", "output",
                           config={"title": "false 分支"},
                           position={"x": 800, "y": 100}),
        }
        edges = [
            {"source": "n1", "target": "n2", "sourceHandle": "triggered", "targetHandle": "trigger"},
            {"source": "n2", "target": "n3", "sourceHandle": "next", "targetHandle": None},
            {"source": "n3", "target": "n4", "sourceHandle": "result", "targetHandle": "condition"},
            {"source": "n4", "target": "n5", "sourceHandle": "true", "targetHandle": "data"},
            {"source": "n4", "target": "n6", "sourceHandle": "false", "targetHandle": "data"},
        ]
        variables = {"score": score}
        return nodes, edges, variables

    def _make_executor(self, recorder):
        mock_db = Mock()
        mock_ws = Mock()
        mock_ws.broadcast = AsyncMock()
        executor = RuleGraphExecutor(db=mock_db, ws_manager=mock_ws)
        # Mock 所有副作用
        executor._save_node_log = recorder  # 用 recorder 替换
        executor._update_execution_status = AsyncMock()
        executor._broadcast_node_started = AsyncMock()
        executor._broadcast_node_executed = AsyncMock()
        executor._broadcast_node_failed = AsyncMock()
        executor._broadcast_node_timeout = AsyncMock()
        executor._broadcast_progress = AsyncMock()
        executor._broadcast_complete = AsyncMock()
        # 清理 class-level _active_executions (test isolation)
        RuleGraphExecutor._active_executions.clear()
        return executor

    def _next_execution_id(self):
        """生成唯一 execution_id (避免 _active_executions class variable 串扰)"""
        if not hasattr(self, "_id_counter"):
            self._id_counter = 1000
        self._id_counter += 1
        return self._id_counter

    def _node_status_map(self, recorder):
        """从 recorder 提取每个 node_id 最终的 status (后写覆盖先写)"""
        m = {}
        for nid, status in recorder.calls:
            m[nid] = status
        return m

    @pytest.mark.asyncio
    async def test_branch_true_path_skip_false(self):
        """score=85 (gte) -> Branch result=true -> n5 completed, n6 skipped"""
        nodes, edges, variables = self._setup(condition_value=True)
        recorder = _StatusRecorder()
        executor = self._make_executor(recorder)

        result = await executor.execute(
            graph_data={"nodes": nodes, "edges": edges, "variables": variables},
            execution_id=self._next_execution_id(),
            trigger_type="manual",
            trigger_data={},
        )

        assert result["status"] == "completed"
        m = self._node_status_map(recorder)
        assert m.get("n5") == "completed", f"n5 (true 分支) 应 completed, 实际 status={m.get('n5')}, 全部={m}"
        assert m.get("n6") == "skipped", f"n6 (false 分支) 应 skipped, 实际 status={m.get('n6')}, 全部={m}"
        # Branch 节点 result 应是 "true"
        branch_result = result.get("node_results", {}).get("n4", {}).get("branch")
        assert branch_result == "true", f"Branch 应返回 'true', 实际 {branch_result}"

    @pytest.mark.asyncio
    async def test_branch_false_path_skip_true(self):
        """score=30 (gte 不成立) -> Branch result=false -> n6 completed, n5 skipped"""
        nodes, edges, variables = self._setup(condition_value=False)
        recorder = _StatusRecorder()
        executor = self._make_executor(recorder)

        result = await executor.execute(
            graph_data={"nodes": nodes, "edges": edges, "variables": variables},
            execution_id=self._next_execution_id(),
            trigger_type="manual",
            trigger_data={},
        )

        assert result["status"] == "completed"
        m = self._node_status_map(recorder)
        assert m.get("n5") == "skipped", f"n5 (true 分支) 应 skipped, 实际 status={m.get('n5')}, 全部={m}"
        assert m.get("n6") == "completed", f"n6 (false 分支) 应 completed, 实际 status={m.get('n6')}, 全部={m}"
        branch_result = result.get("node_results", {}).get("n4", {}).get("branch")
        assert branch_result == "false", f"Branch 应返回 'false', 实际 {branch_result}"

    @pytest.mark.asyncio
    async def test_branch_no_output_edges_runs_normally(self):
        """Branch 节点没接 output 边 -> 不应影响执行, 不报错"""
        nodes = {
            "n1": make_node("n1", "manual_trigger", "input", position={"x": 0, "y": 0}),
            "n2": make_node("n2", "branch", "logic", position={"x": 200, "y": 0}),
        }
        edges = [
            {"source": "n1", "target": "n2", "sourceHandle": "triggered", "targetHandle": None},
        ]
        variables = {}
        recorder = _StatusRecorder()
        executor = self._make_executor(recorder)

        result = await executor.execute(
            graph_data={"nodes": nodes, "edges": edges, "variables": variables},
            execution_id=self._next_execution_id(),
            trigger_type="manual",
            trigger_data={},
        )
        assert result["status"] == "completed"
        m = self._node_status_map(recorder)
        assert m.get("n1") == "completed"
        assert m.get("n2") == "completed"

    @pytest.mark.asyncio
    async def test_branch_with_chained_skip(self):
        """Branch -> Display1 (true) -> Display2 (链)
        当 Branch 走 true 时, Display1 应 completed, Display2 应 completed (链上),
        false 分支 (无) 应没有节点
        """
        # n4 Branch -> n5 (true) -> n6 (Display 接 n5 的 data)
        # 这里要避免 CONTROL/TRIGGER 不兼容, 用 Display.data 接 BOOLEAN
        nodes = {
            "n1": make_node("n1", "manual_trigger", "input", position={"x": 0, "y": 0}),
            "n2": make_node("n2", "set_variable", "logic",
                           config={"variable_name": "score", "value": "85", "value_type": "static"},
                           position={"x": 200, "y": 0}),
            "n3": make_node("n3", "variable_condition", "logic",
                           config={"variable_name": "score", "expected_value": "60", "comparison": "gte"},
                           position={"x": 400, "y": 0}),
            "n4": make_node("n4", "branch", "logic",
                           position={"x": 600, "y": 0},
                           inputs={"condition": {"node_id": "n3", "output": "result"}}),
            "n5": make_node("n5", "display", "output",
                           config={"title": "true 分支"},
                           position={"x": 800, "y": -100}),
            "n6": make_node("n6", "display", "output",
                           config={"title": "false 分支"},
                           position={"x": 800, "y": 100}),
            "n7": make_node("n7", "display", "output", config={"title": "链上节点"},
                           position={"x": 1000, "y": -100}),
        }
        edges = [
            {"source": "n1", "target": "n2", "sourceHandle": "triggered", "targetHandle": "trigger"},
            {"source": "n2", "target": "n3", "sourceHandle": "next", "targetHandle": None},
            {"source": "n3", "target": "n4", "sourceHandle": "result", "targetHandle": "condition"},
            {"source": "n4", "target": "n5", "sourceHandle": "true", "targetHandle": "data"},
            {"source": "n4", "target": "n6", "sourceHandle": "false", "targetHandle": "data"},
            # n5.output (displayed BOOLEAN) -> n7.data (ANY)
            {"source": "n5", "target": "n7", "sourceHandle": "displayed", "targetHandle": "data"},
        ]
        variables = {"score": 85}
        recorder = _StatusRecorder()
        executor = self._make_executor(recorder)

        result = await executor.execute(
            graph_data={"nodes": nodes, "edges": edges, "variables": variables},
            execution_id=self._next_execution_id(),
            trigger_type="manual",
            trigger_data={},
        )
        assert result["status"] == "completed"
        m = self._node_status_map(recorder)
        # n5 (true 分支) -> n7 链上, 都应 completed
        assert m.get("n5") == "completed", f"n5 应 completed, 实际 {m.get('n5')}, 全部={m}"
        assert m.get("n7") == "completed", f"n7 (链上) 应 completed, 实际 {m.get('n7')}, 全部={m}"
        # n6 (false 分支) 应 skipped
        assert m.get("n6") == "skipped", f"n6 应 skipped, 实际 {m.get('n6')}, 全部={m}"
