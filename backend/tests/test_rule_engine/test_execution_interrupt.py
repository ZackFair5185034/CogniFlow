# -*- coding: utf-8 -*-
"""规则引擎执行中断（取消）集成测试。

测试执行引擎的取消机制：
1. cancel_execution() 正确设置取消状态
2. 取消后执行返回 cancelled 状态
3. WebSocket 广播 cancellation 消息
4. 数据库状态正确更新
5. 正在执行的节点能感知到取消信号
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '/root/coding/CogniFlow/backend')

from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.nodes.base import ExecutionContext
from backend.services.rule_engine.models import NodeCategory


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """创建模拟数据库会话。"""
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def mock_ws_manager():
    """创建模拟 WebSocket 管理器。"""
    ws = Mock()
    ws.broadcast = AsyncMock()
    return ws


@pytest.fixture
def mock_context():
    """创建模拟执行上下文。"""
    ctx = Mock()
    ctx.execution_id = 1
    ctx.trigger_type = "manual"
    ctx.trigger_data = {}
    ctx.node_results = {}
    ctx.node_status = {}
    ctx.variables = {"counter": 0}
    ctx.config = {}
    ctx.cancelled = False
    ctx.ws_manager = None
    return ctx


@pytest.fixture
def executor(mock_db, mock_ws_manager):
    """创建执行器实例。"""
    return RuleGraphExecutor(db=mock_db, ws_manager=mock_ws_manager)


@pytest.fixture
def sample_graph_data():
    """创建示例图数据（用于取消测试）。注意：nodes 是 Dict[str, Dict] 格式。"""
    return {
        "nodes": {
            "node_1": {
                "id": "node_1",
                "type": "ImageCapture",
                "data": {"params": {"path": "/test.jpg"}}
            },
            "node_2": {
                "id": "node_2",
                "type": "Delay",
                "data": {"params": {"delay_seconds": 0.5}}
            },
            "node_3": {
                "id": "node_3",
                "type": "LogAction",
                "data": {"params": {"message": "done"}}
            }
        },
        "edges": [
            {"source": "node_1", "target": "node_2", "sourceHandle": "result", "targetHandle": "input"},
            {"source": "node_2", "target": "node_3", "sourceHandle": "result", "targetHandle": "input"}
        ],
        "variables": {"counter": 0}
    }


# ============================================================================
# ExecutionContext 取消状态测试
# ============================================================================

class TestExecutionContextCancellation:
    """测试 ExecutionContext 的取消机制。"""

    def test_initial_state_not_cancelled(self):
        """初始状态不应该是取消状态。"""
        ctx = ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={}
        )
        assert ctx.is_cancelled() is False

    def test_request_cancel_sets_flag(self):
        """request_cancel() 应该设置取消标志。"""
        ctx = ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={}
        )
        ctx.request_cancel()
        assert ctx.is_cancelled() is True

    def test_is_cancelled_after_multiple_requests(self):
        """多次请求取消也应该返回 True。"""
        ctx = ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={}
        )
        ctx.request_cancel()
        ctx.request_cancel()
        assert ctx.is_cancelled() is True


# ============================================================================
# RuleGraphExecutor 取消 API 测试
# ============================================================================

class TestExecutorCancelAPI:
    """测试执行器的取消 API。"""

    def test_cancel_execution_not_found(self):
        """取消不存在的执行应返回 False。"""
        executor = RuleGraphExecutor()
        result = executor.cancel_execution(99999)
        assert result is False

    def test_cancel_execution_sets_context_flag(self):
        """取消执行应设置上下文的取消标志。"""
        executor = RuleGraphExecutor()

        # 创建执行上下文
        context = ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={}
        )

        # 注册执行
        RuleGraphExecutor.register_execution(1, context)

        # 取消执行
        result = executor.cancel_execution(1)
        assert result is True
        assert context.is_cancelled() is True

        # 清理
        RuleGraphExecutor.unregister_execution(1)

    def test_unregister_execution(self):
        """注销执行后取消应失败。"""
        executor = RuleGraphExecutor()

        context = ExecutionContext(
            execution_id=2,
            trigger_type="manual",
            trigger_data={}
        )

        RuleGraphExecutor.register_execution(2, context)
        RuleGraphExecutor.unregister_execution(2)

        result = executor.cancel_execution(2)
        assert result is False


# ============================================================================
# 取消后执行流程测试
# ============================================================================

class TestCancellationDuringExecution:
    """测试执行过程中的取消行为。"""

    @pytest.mark.asyncio
    async def test_cancellation_returns_cancelled_status(self, executor, sample_graph_data, mock_ws_manager):
        """取消后执行应返回 cancelled 状态。"""
        # 模拟图数据，只有两个快速节点
        graph_data = {
            "nodes": {
                "node_1": {
                    "id": "node_1",
                    "type": "ImageCapture",
                    "data": {"params": {"path": "/test.jpg"}}
                }
            },
            "edges": [],
            "variables": {}
        }

        # 创建执行记录
        execution_id = 100

        # 直接测试取消机制：在执行开始后、节点执行中请求取消
        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type="manual",
            trigger_data={},
            node_results={},
            node_status={},
            variables={},
            config={"nodes": graph_data["nodes"]},
            cancelled=False,
            ws_manager=mock_ws_manager
        )

        RuleGraphExecutor.register_execution(execution_id, context)

        # 在节点执行前请求取消
        context.request_cancel()

        # 模拟执行返回取消状态（实际由 execute() 方法处理）
        result = await executor.execute(graph_data, execution_id)

        # 验证返回取消状态
        assert result["status"] == "cancelled"

        RuleGraphExecutor.unregister_execution(execution_id)

    @pytest.mark.asyncio
    async def test_cancellation_broadcasts_ws_message(self, executor, sample_graph_data, mock_ws_manager):
        """取消应广播 WebSocket 消息。"""
        execution_id = 101

        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type="manual",
            trigger_data={},
            node_results={},
            node_status={},
            variables={},
            config={"nodes": sample_graph_data["nodes"]},
            cancelled=False,
            ws_manager=mock_ws_manager
        )

        RuleGraphExecutor.register_execution(execution_id, context)
        context.request_cancel()

        # 执行（会返回 cancelled）
        await executor.execute(sample_graph_data, execution_id)

        # 验证广播被调用
        mock_ws_manager.broadcast.assert_called()

        # 检查广播内容包含 cancelled 状态
        calls = mock_ws_manager.broadcast.call_args_list
        cancelled_broadcasts = [
            call for call in calls
            if call[0][0].get("status") == "cancelled"
        ]
        assert len(cancelled_broadcasts) > 0

        RuleGraphExecutor.unregister_execution(execution_id)

    @pytest.mark.asyncio
    async def test_cancellation_updates_db_status(self, executor, sample_graph_data, mock_db):
        """取消应更新数据库状态为 cancelled。"""
        execution_id = 102

        # 模拟数据库记录
        mock_record = Mock()
        mock_record.status = "running"
        mock_record.start_time = datetime.now()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_record

        # 创建执行上下文
        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type="manual",
            trigger_data={},
            node_results={},
            node_status={},
            variables={},
            config={"nodes": sample_graph_data["nodes"]},
            cancelled=False,
            ws_manager=None
        )

        RuleGraphExecutor.register_execution(execution_id, context)
        context.request_cancel()

        # 执行
        await executor.execute(sample_graph_data, execution_id)

        # 验证数据库状态更新
        assert mock_db.commit.called

        RuleGraphExecutor.unregister_execution(execution_id)


# ============================================================================
# 节点级别取消感知测试
# ============================================================================

class TestNodeCancellationAwareness:
    """测试节点对取消信号的感知。"""

    @pytest.mark.asyncio
    async def test_long_running_node_respects_cancellation(self, mock_context):
        """长时间运行的节点应该检查取消信号。"""
        from backend.services.rule_engine.nodes.logic import DelayNode

        node = DelayNode()
        node.config = {"delay_seconds": 10}  # 模拟长时间等待

        # 模拟取消：在执行开始后立即取消
        mock_context.cancelled = True

        result = await node.execute({}, mock_context)

        # 节点应该返回 cancelled 相关的结果
        assert isinstance(result, dict)
        # cancelled 节点返回 error 或 cancelled 状态
        assert result.get("status") == "cancelled" or "error" in result

    @pytest.mark.asyncio
    async def test_delay_node_cancelled_does_not_wait(self, mock_context):
        """取消的 Delay 节点不应等待完成。"""
        from backend.services.rule_engine.nodes.logic import DelayNode

        node = DelayNode()
        node.config = {"delay_seconds": 10}

        # 模拟取消上下文
        mock_context.cancelled = True

        # 执行（应该快速返回，不等待 10 秒）
        import time
        start = time.time()
        result = await node.execute({}, mock_context)
        elapsed = time.time() - start

        # 应该快速返回（< 1 秒），而不是等待完整的 10 秒
        assert elapsed < 1.0
        assert result.get("status") == "cancelled"


# ============================================================================
# 取消与进度广播测试
# ============================================================================

class TestCancellationProgressBroadcast:
    """测试取消时的进度广播。"""

    @pytest.mark.asyncio
    async def test_cancellation_includes_completed_nodes(
        self, executor, sample_graph_data, mock_ws_manager
    ):
        """取消时应报告已完成节点数量。"""
        execution_id = 103

        # 修改图数据，使第一个节点快速完成
        graph_data = {
            "nodes": {
                "fast_node": {
                    "id": "fast_node",
                    "type": "ImageCapture",
                    "data": {"params": {"path": "/test.jpg"}}
                }
            },
            "edges": [],
            "variables": {}
        }

        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type="manual",
            trigger_data={},
            node_results={},
            node_status={},
            variables={},
            config={"nodes": graph_data["nodes"]},
            cancelled=False,
            ws_manager=mock_ws_manager
        )

        RuleGraphExecutor.register_execution(execution_id, context)

        # 请求取消执行
        context.request_cancel()

        # 取消执行
        result = await executor.execute(graph_data, execution_id)

        assert result["status"] == "cancelled"
        assert "completed_nodes" in result
        assert "total_nodes" in result

        RuleGraphExecutor.unregister_execution(execution_id)

    @pytest.mark.asyncio
    async def test_multiple_rapid_cancellations(self, executor, sample_graph_data):
        """快速多次取消应该只生效一次。"""
        execution_id = 104

        context = ExecutionContext(
            execution_id=execution_id,
            trigger_type="manual",
            trigger_data={},
            node_results={},
            node_status={},
            variables={},
            config={"nodes": sample_graph_data["nodes"]},
            cancelled=False,
            ws_manager=None
        )

        RuleGraphExecutor.register_execution(execution_id, context)

        # 多次取消
        executor.cancel_execution(execution_id)
        executor.cancel_execution(execution_id)
        executor.cancel_execution(execution_id)

        # 上下文应该仍然在取消状态
        assert context.is_cancelled() is True

        result = await executor.execute(sample_graph_data, execution_id)

        # 只返回一次 cancelled
        assert result["status"] == "cancelled"

        RuleGraphExecutor.unregister_execution(execution_id)
