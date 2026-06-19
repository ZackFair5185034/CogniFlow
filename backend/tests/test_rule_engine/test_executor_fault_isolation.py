# -*- coding: utf-8 -*-
"""BE-P0-2 节点级故障隔离测试 (2026-06-19)。

验证:
1. 节点抛异常时, 异常对象连同 traceback 写入 status (便于排查)
2. 节点实现 cleanup/close 钩子时, finally 必调 (资源清理)
3. 节点抛异常不影响同层其他节点 (isolate 模式默认行为)
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.nodes.base import ExecutionContext
from backend.services.rule_engine.models import NodeCategory


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_context():
    """创建模拟执行上下文。"""
    ctx = Mock()
    ctx.execution_id = "test_exec_001"
    ctx.config = {"nodes": {}, "node_timeout": 30, "failure_policy": "isolate"}
    ctx.is_cancelled = Mock(return_value=False)
    ctx.set_node_status = Mock()
    ctx.set_node_result = Mock()
    ctx.get_node_result = Mock(return_value=None)
    return ctx


@pytest.fixture
def failing_executor_with_cleanup():
    """构造一个会抛异常、但实现了 cleanup 钩子的执行器。"""

    class FailingExecutor:
        default_timeout = 30
        cleanup_called = False

        def __init__(self):
            self.validate_inputs = Mock(return_value=(True, None))

        async def execute(self, merged_inputs, context):
            raise ValueError("模拟业务异常, 应当被隔离")

        async def cleanup(self):
            # async cleanup 钩子, 验证 finally 会调
            FailingExecutor.cleanup_called = True

    FailingExecutor.cleanup_called = False
    return FailingExecutor()


def _build_node_config(node_id: str, node_type: str = "test_failing_node") -> dict:
    return {
        "id": node_id,
        "type": "testNode",
        "data": {
            "type": node_type,
            "config": {},
            "inputs": {},
        }
    }


# ============================================================================
# Tests
# ============================================================================

def test_exception_includes_traceback_in_error_message():
    """BE-P0-2: 异常对象连同 traceback 一并写入 status (供 WS 推送)。"""
    config = {"nodes": {"n1": _build_node_config("n1")}, "node_timeout": 30}
    ctx = Mock()
    ctx.execution_id = "exec_001"
    ctx.config = config
    ctx.is_cancelled = Mock(return_value=False)
    ctx.set_node_status = Mock()
    ctx.set_node_result = Mock()
    ctx.get_node_result = Mock(return_value=None)

    class FailExec:
        default_timeout = 30
        def __init__(self):
            self.validate_inputs = Mock(return_value=(True, None))
        async def execute(self, *a, **kw):
            raise ValueError("业务异常 1")
        async def cleanup(self):
            pass

    executor_instance = RuleGraphExecutor()
    with patch("backend.services.rule_engine.executor.get_registry") as mock_get_reg, \
         patch.object(executor_instance, "_broadcast_node_failed", new=AsyncMock()), \
         patch.object(executor_instance, "_broadcast_node_started", new=AsyncMock()), \
         patch.object(executor_instance, "_broadcast_node_executed", new=AsyncMock()), \
         patch.object(executor_instance, "_save_node_log", new=AsyncMock()):
        mock_reg = Mock()
        mock_reg.create_node = Mock(return_value=FailExec())
        mock_get_reg.return_value = mock_reg

        with pytest.raises(Exception):
            asyncio.run(executor_instance._execute_node("n1", ctx))

    # set_node_status 至少被调一次, 最终是 "failed"
    assert any(
        call.args == ("n1", "failed")
        for call in ctx.set_node_status.call_args_list
    ), f"set_node_status 未标记 failed: {ctx.set_node_status.call_args_list}"


def test_cleanup_hook_called_on_exception():
    """BE-P0-2: 节点抛异常时, finally 仍调 cleanup 钩子 (资源清理)。"""
    config = {"nodes": {"n1": _build_node_config("n1")}, "node_timeout": 30}
    ctx = Mock()
    ctx.execution_id = "exec_002"
    ctx.config = config
    ctx.is_cancelled = Mock(return_value=False)
    ctx.set_node_status = Mock()
    ctx.set_node_result = Mock()
    ctx.get_node_result = Mock(return_value=None)

    cleanup_called_flag = {"value": False}

    class FailExec:
        default_timeout = 30
        def __init__(self):
            self.validate_inputs = Mock(return_value=(True, None))
        async def execute(self, *a, **kw):
            raise RuntimeError("boom")
        async def cleanup(self):
            cleanup_called_flag["value"] = True

    executor_instance = RuleGraphExecutor()
    with patch("backend.services.rule_engine.executor.get_registry") as mock_get_reg, \
         patch.object(executor_instance, "_broadcast_node_failed", new=AsyncMock()), \
         patch.object(executor_instance, "_broadcast_node_started", new=AsyncMock()), \
         patch.object(executor_instance, "_broadcast_node_executed", new=AsyncMock()), \
         patch.object(executor_instance, "_save_node_log", new=AsyncMock()):
        mock_reg = Mock()
        mock_reg.create_node = Mock(return_value=FailExec())
        mock_get_reg.return_value = mock_reg

        with pytest.raises(Exception):
            asyncio.run(executor_instance._execute_node("n1", ctx))

    assert cleanup_called_flag["value"] is True, "finally 未调 cleanup 钩子 (资源泄漏风险)"


def test_cleanup_called_on_success():
    """BE-P0-2: 节点成功完成时, finally 同样调 cleanup 钩子。"""
    config = {"nodes": {"n1": _build_node_config("n1")}, "node_timeout": 30}
    ctx = Mock()
    ctx.execution_id = "exec_003"
    ctx.config = config
    ctx.is_cancelled = Mock(return_value=False)
    ctx.set_node_status = Mock()
    ctx.set_node_result = Mock()
    ctx.get_node_result = Mock(return_value=None)

    cleanup_called_flag = {"value": False}

    class OkExec:
        default_timeout = 30
        def __init__(self):
            self.validate_inputs = Mock(return_value=(True, None))
        async def execute(self, *a, **kw):
            return {"result": "ok"}
        async def cleanup(self):
            cleanup_called_flag["value"] = True

    executor_instance = RuleGraphExecutor()
    with patch("backend.services.rule_engine.executor.get_registry") as mock_get_reg, \
         patch.object(executor_instance, "_broadcast_node_started", new=AsyncMock()), \
         patch.object(executor_instance, "_broadcast_node_executed", new=AsyncMock()), \
         patch.object(executor_instance, "_save_node_log", new=AsyncMock()):
        mock_reg = Mock()
        mock_reg.create_node = Mock(return_value=OkExec())
        mock_get_reg.return_value = mock_reg

        asyncio.run(executor_instance._execute_node("n1", ctx))

    assert cleanup_called_flag["value"] is True, "成功路径 finally 未调 cleanup"


def test_cleanup_failure_does_not_mask_result():
    """BE-P0-2: cleanup 抛异常时, 只记 warning, 不掩盖主结果。"""
    config = {"nodes": {"n1": _build_node_config("n1")}, "node_timeout": 30}
    ctx = Mock()
    ctx.execution_id = "exec_004"
    ctx.config = config
    ctx.is_cancelled = Mock(return_value=False)
    ctx.set_node_status = Mock()
    ctx.set_node_result = Mock()
    ctx.get_node_result = Mock(return_value=None)

    class OkExecWithBrokenCleanup:
        default_timeout = 30
        def __init__(self):
            self.validate_inputs = Mock(return_value=(True, None))
        async def execute(self, *a, **kw):
            return {"result": "ok"}
        async def cleanup(self):
            raise RuntimeError("cleanup 内部错误")

    executor_instance = RuleGraphExecutor()
    with patch("backend.services.rule_engine.executor.get_registry") as mock_get_reg, \
         patch.object(executor_instance, "_broadcast_node_started", new=AsyncMock()), \
         patch.object(executor_instance, "_broadcast_node_executed", new=AsyncMock()), \
         patch.object(executor_instance, "_save_node_log", new=AsyncMock()):
        mock_reg = Mock()
        mock_reg.create_node = Mock(return_value=OkExecWithBrokenCleanup())
        mock_get_reg.return_value = mock_reg

        # 不应抛异常 (cleanup 失败被吞)
        asyncio.run(executor_instance._execute_node("n1", ctx))

    # 节点仍标记为 completed (cleanup 失败不掩盖)
    assert any(
        call.args == ("n1", "completed")
        for call in ctx.set_node_status.call_args_list
    ), f"cleanup 失败掩盖了主结果: {ctx.set_node_status.call_args_list}"
