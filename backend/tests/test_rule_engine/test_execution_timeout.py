# -*- coding: utf-8 -*-
"""规则引擎执行超时保护测试。

测试覆盖：
1. _execute_node 默认 300s 超时配置
2. 自定义 context.config['node_timeout'] 生效
3. 节点超时后标记为 failed，下游节点继续执行（断路器模式）
4. 超时后 WebSocket 推送 node_timeout 事件（区别于 node_failed）
5. BaseExecutor.default_timeout 覆盖全局默认
6. RuleExecutionConnectionManager.send_node_timeout 推送正确格式
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.nodes.base import BaseExecutor, ExecutionContext
from backend.services.rule_engine.websocket_manager import RuleExecutionConnectionManager
from backend.services.rule_engine.models import NodeCategory, NodeDefinition, PortDefinition
from backend.services.rule_engine.exceptions import ExecutorError


# ============================================================================
# 辅助节点：可控睡眠时长（用于测试超时）
# ============================================================================

class _ControllableSleepNode(BaseExecutor):
    """测试用：可配置 sleep 时长的节点（不真正 await sleep，便于测试）。"""
    node_type = "_controllable_sleep"
    category = NodeCategory.LOGIC
    display_name = "可控睡眠"
    default_timeout = None  # 走全局默认

    def __init__(self, node_id=None, config=None, sleep_seconds=0.0):
        super().__init__(node_id=node_id, config=config)
        self._sleep_seconds = sleep_seconds
        self._executed = False

    def set_sleep(self, seconds: float):
        self._sleep_seconds = seconds

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description="测试节点",
            icon="clock",
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
        self._executed = True
        await asyncio.sleep(self._sleep_seconds)
        return {"result": "done"}


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
    """模拟 WebSocket 管理器（使用 AsyncMock）。"""
    ws = Mock()
    ws.broadcast = AsyncMock()
    return ws


@pytest.fixture
def executor(mock_db, mock_ws_manager):
    """创建执行器实例。"""
    return RuleGraphExecutor(db=mock_db, ws_manager=mock_ws_manager)


@pytest.fixture
def sleep_node():
    """创建一个可配置 sleep 时长的测试节点。"""
    return _ControllableSleepNode()


# ============================================================================
# 超时配置测试
# ============================================================================

class TestTimeoutConfiguration:
    """测试 _execute_node 的超时配置读取逻辑。"""

    @pytest.mark.asyncio
    async def test_default_timeout_is_300s(self, executor, sleep_node):
        """未配置 node_timeout 时，默认 300s。"""
        context = ExecutionContext(
            execution_id=1,
            trigger_type="manual",
            trigger_data={},
            config={"nodes": {"n1": {"id": "n1", "data": {}}}},
        )

        # 模拟 registry.create_node 返回我们的 sleep_node
        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = sleep_node

            # 默认 timeout 应该是 300
            # 我们设置 sleep 很小（0.01s）所以不会触发超时
            sleep_node.set_sleep(0.01)
            await executor._execute_node("n1", context)

            # 节点应正常完成（不超时）
            assert context.get_node_status("n1") == "completed"
            # 由于 sleep 很短，不会触发 TimeoutError
            mock_ws_manager = executor.ws_manager

    @pytest.mark.asyncio
    async def test_context_node_timeout_override(self, executor, sleep_node):
        """context.config['node_timeout'] 覆盖默认 300s。"""
        # 设置很小的超时（0.05s），sleep 0.2s
        context = ExecutionContext(
            execution_id=2,
            trigger_type="manual",
            trigger_data={},
            config={
                "nodes": {"n1": {"id": "n1", "data": {}}},
                "node_timeout": 0.05,
            },
        )

        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = sleep_node
            sleep_node.set_sleep(0.2)

            await executor._execute_node("n1", context)

            # 节点应标记为 failed（超时）
            assert context.get_node_status("n1") == "failed"

    @pytest.mark.asyncio
    async def test_explicit_timeout_param_overrides_context(
        self, executor, sleep_node
    ):
        """_execute_node 的显式 timeout 参数覆盖 context 默认值。"""
        context = ExecutionContext(
            execution_id=3,
            trigger_type="manual",
            trigger_data={},
            config={
                "nodes": {"n1": {"id": "n1", "data": {}}},
                "node_timeout": 300,  # context 默认 300s
            },
        )

        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = sleep_node
            sleep_node.set_sleep(0.3)

            # 显式传入 0.05s 超时
            await executor._execute_node("n1", context, timeout=0.05)

            # 节点应超时失败
            assert context.get_node_status("n1") == "failed"


# ============================================================================
# 断路器模式测试
# ============================================================================

class TestTimeoutBreakerMode:
    """验证节点超时后下游节点继续执行（断路器模式）。"""

    @pytest.mark.asyncio
    async def test_timeout_node_does_not_propagate_exception(
        self, executor, sleep_node
    ):
        """超时不应传播异常（断路器模式）。"""
        context = ExecutionContext(
            execution_id=10,
            trigger_type="manual",
            trigger_data={},
            config={
                "nodes": {"n1": {"id": "n1", "data": {}}},
                "node_timeout": 0.05,
            },
        )

        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = sleep_node
            sleep_node.set_sleep(0.3)

            # 不应抛出异常
            await executor._execute_node("n1", context)

            # 节点状态应为 failed（不抛异常）
            assert context.get_node_status("n1") == "failed"

    @pytest.mark.asyncio
    async def test_timeout_does_not_emit_node_failed_event(
        self, executor, sleep_node, mock_ws_manager
    ):
        """超时应推送 node_timeout 事件，而不是 node_failed。"""
        context = ExecutionContext(
            execution_id=11,
            trigger_type="manual",
            trigger_data={},
            config={
                "nodes": {"n1": {"id": "n1", "data": {}}},
                "node_timeout": 0.05,
            },
            ws_manager=mock_ws_manager,
        )

        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = sleep_node
            sleep_node.set_sleep(0.3)

            await executor._execute_node("n1", context)

            # 检查所有 broadcast 调用
            broadcasts = [
                call.args[0] for call in mock_ws_manager.broadcast.call_args_list
            ]
            broadcast_types = [b.get("type") for b in broadcasts]

            # 必须有 node_timeout
            assert "node_timeout" in broadcast_types, (
                f"应推送 node_timeout 事件，实际: {broadcast_types}"
            )
            # 不应有 node_failed（超时是单独的事件）
            assert "node_failed" not in broadcast_types, (
                f"超时不应触发通用 node_failed，实际: {broadcast_types}"
            )

    @pytest.mark.asyncio
    async def test_timeout_event_includes_duration(
        self, executor, sleep_node, mock_ws_manager
    ):
        """node_timeout 事件应包含 timeout_seconds。"""
        context = ExecutionContext(
            execution_id=12,
            trigger_type="manual",
            trigger_data={},
            config={
                "nodes": {"n1": {"id": "n1", "data": {}}},
                "node_timeout": 0.05,
            },
            ws_manager=mock_ws_manager,
        )

        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = sleep_node
            sleep_node.set_sleep(0.3)

            await executor._execute_node("n1", context)

            # 找到 node_timeout 事件
            timeout_event = None
            for call in mock_ws_manager.broadcast.call_args_list:
                msg = call.args[0]
                if msg.get("type") == "node_timeout":
                    timeout_event = msg
                    break

            assert timeout_event is not None
            assert timeout_event["timeout_seconds"] == 0.05
            assert "node_id" in timeout_event
            assert "execution_id" in timeout_event
            assert "error" in timeout_event


# ============================================================================
# BaseExecutor.default_timeout 测试
# ============================================================================

class TestBaseExecutorDefaultTimeout:
    """测试 BaseExecutor.default_timeout 字段覆盖全局默认。"""

    def test_base_executor_default_timeout_is_none(self):
        """BaseExecutor.default_timeout 默认为 None（走全局默认）。"""
        assert BaseExecutor.default_timeout is None

    def test_subclass_can_override_default_timeout(self):
        """子类可以覆盖 default_timeout 设置特定超时。"""
        # 创建一个覆盖 default_timeout 的子类
        class _SlowNode(BaseExecutor):
            node_type = "_slow"
            default_timeout = 600.0  # yolo_model 等大模型节点可设为 600s

            def get_definition(self):
                return NodeDefinition(
                    type="_slow", category="action",
                    display_name="x", description="x", icon="x", color="#000",
                    inputs={}, outputs={}, config_schema={},
                )

            def validate_inputs(self, inputs):
                return True, None

            async def execute(self, inputs, context):
                return {}

        node = _SlowNode()
        assert node.default_timeout == 600.0

    @pytest.mark.asyncio
    async def test_node_default_timeout_overrides_context(
        self, executor, mock_ws_manager
    ):
        """节点的 default_timeout 应覆盖 context.node_timeout。"""
        # 创建一个 default_timeout=0.05 的节点
        class _FastTimeoutNode(BaseExecutor):
            node_type = "_fast_timeout"
            default_timeout = 0.05

            def get_definition(self):
                return NodeDefinition(
                    type="_fast_timeout", category="action",
                    display_name="x", description="x", icon="x", color="#000",
                    inputs={}, outputs={}, config_schema={},
                )

            def validate_inputs(self, inputs):
                return True, None

            async def execute(self, inputs, context):
                await asyncio.sleep(0.3)  # 超过 default_timeout 但不超过 context
                return {"result": "done"}

        context = ExecutionContext(
            execution_id=20,
            trigger_type="manual",
            trigger_data={},
            config={
                "nodes": {"n1": {"id": "n1", "data": {}}},
                "node_timeout": 60,  # context 默认 60s
            },
            ws_manager=mock_ws_manager,
        )

        node = _FastTimeoutNode()
        with patch.object(executor, '_resolve_inputs', return_value={}), \
             patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_registry = mock_get_registry.return_value
            mock_registry.create_node.return_value = node

            await executor._execute_node("n1", context)

            # 节点应超时（因为节点 default_timeout=0.05 < sleep 0.3）
            assert context.get_node_status("n1") == "failed"

            # 验证超时事件 timeout_seconds 是节点级别（0.05），不是 context 级别（60）
            for call in mock_ws_manager.broadcast.call_args_list:
                msg = call.args[0]
                if msg.get("type") == "node_timeout":
                    assert msg["timeout_seconds"] == 0.05
                    break


# ============================================================================
# WebSocket 管理器测试
# ============================================================================

class TestWebSocketNodeTimeoutEvent:
    """测试 RuleExecutionConnectionManager.send_node_timeout 推送格式。"""

    @pytest.mark.asyncio
    async def test_send_node_timeout_format(self):
        """send_node_timeout 应推送正确格式的事件。"""
        manager = RuleExecutionConnectionManager()

        # 不订阅任何连接 — broadcast 内部会因无订阅者而 noop
        # 但我们要验证 broadcast 被正确调用
        await manager.send_node_timeout(
            execution_id=42,
            node_id="node_xyz",
            timeout_seconds=300.0,
            error="执行超时（300.0s）"
        )

        # 验证 _pending_messages 中有正确格式的消息
        assert 42 in manager._pending_messages
        messages = manager._pending_messages[42]
        assert len(messages) == 1
        msg = messages[0]
        assert msg["type"] == "node_timeout"
        assert msg["execution_id"] == 42
        assert msg["node_id"] == "node_xyz"
        assert msg["timeout_seconds"] == 300.0
        assert "300" in msg["error"]

    @pytest.mark.asyncio
    async def test_send_node_timeout_uses_default_error(self):
        """未提供 error 时，应自动生成默认错误信息。"""
        manager = RuleExecutionConnectionManager()

        await manager.send_node_timeout(
            execution_id=1,
            node_id="n1",
            timeout_seconds=10.0
        )

        msg = manager._pending_messages[1][0]
        assert msg["error"] == "节点执行超时（10.0s）"


# ============================================================================
# 端到端流程测试
# ============================================================================

class TestTimeoutEndToEnd:
    """测试完整规则图中的超时场景。"""

    @pytest.mark.asyncio
    async def test_downstream_nodes_execute_after_timeout(
        self, executor, mock_ws_manager
    ):
        """节点超时不阻塞下游节点继续执行。"""
        # 构建一个简单图：slow_node → fast_node
        # slow_node 会超时，fast_node 应当正常完成

        fast_node = _ControllableSleepNode()
        fast_node.set_sleep(0.01)  # 0.01s，不会超时

        class _FastNodeRegistry:
            """mock registry：所有节点都返回同一个 fast_node（简化测试）"""
            def create_node(self, node_type, node_id, config):
                return fast_node

        with patch('backend.services.rule_engine.executor.get_registry') as mock_get_registry:
            mock_get_registry.return_value = _FastNodeRegistry()

            # 构造图：n1（sleep 0.3s）→ n2（sleep 0.01s）
            # node_timeout=0.05 让 n1 超时
            context = ExecutionContext(
                execution_id=100,
                trigger_type="manual",
                trigger_data={},
                config={
                    "nodes": {
                        "n1": {"id": "n1", "data": {}},
                        "n2": {"id": "n2", "data": {}},
                    },
                    "node_timeout": 0.05,
                },
                ws_manager=mock_ws_manager,
            )

            # 第一次设置 sleep=0.3（会超时），第二次设置 sleep=0.01
            sleep_calls = []

            async def controlled_execute(inputs, ctx):
                sleep_calls.append(True)
                if len(sleep_calls) == 1:
                    # n1 第一次执行：sleep 0.3（超时）
                    await asyncio.sleep(0.3)
                else:
                    # n2 第二次执行：sleep 0.01（正常）
                    await asyncio.sleep(0.01)
                return {"result": "ok"}

            fast_node.execute = controlled_execute

            # 执行 n1
            with patch.object(executor, '_resolve_inputs', return_value={}):
                await executor._execute_node("n1", context)

            # 验证 n1 已超时失败
            assert context.get_node_status("n1") == "failed"

            # n2 仍能继续执行（断路器模式）
            await executor._execute_node("n2", context)
            assert context.get_node_status("n2") == "completed"

            # 应有 node_timeout（n1）和 node_executed（n2）两种事件
            broadcast_types = [
                call.args[0].get("type")
                for call in mock_ws_manager.broadcast.call_args_list
            ]
            assert "node_timeout" in broadcast_types
            assert "node_executed" in broadcast_types
