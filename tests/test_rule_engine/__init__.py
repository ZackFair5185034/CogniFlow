# -*- coding: utf-8 -*-
"""规则引擎单元测试。"""
import pytest
import json
from backend.services.rule_engine.nodes.base import (
    NodeCategory, NodeResult, NodeStatus, ExecutionContext
)
from backend.services.rule_engine.registry import NodeRegistry, init_builtin_executors


class TestExecutionContext:
    """测试执行上下文。"""

    def test_set_and_get_var(self):
        """测试变量存取。"""
        ctx = ExecutionContext()
        ctx.set_var("name", "test")
        assert ctx.get_var("name") == "test"

    def test_get_var_default(self):
        """测试获取不存在的变量返回默认值。"""
        ctx = ExecutionContext()
        assert ctx.get_var("nonexistent", "default") == "default"


class TestNodeRegistry:
    """测试节点注册表。"""

    def test_singleton(self):
        """测试单例模式。"""
        registry1 = NodeRegistry()
        registry2 = NodeRegistry()
        assert registry1 is registry2

    def test_init_builtin_executors(self):
        """测试初始化内置节点。"""
        registry = init_builtin_executors()
        types = registry.list_types()

        # 验证各类节点已注册
        assert "yolo_trigger" in types
        assert "timer_trigger" in types
        assert "manual_trigger" in types
        assert "object_exists_condition" in types
        assert "confidence_threshold_condition" in types
        assert "variable_condition" in types
        assert "wait_action" in types
        assert "log_action" in types
        assert "branch" in types
        assert "set_variable" in types

    def test_create_node(self):
        """测试创建节点实例。"""
        registry = init_builtin_executors()
        node = registry.create_node("wait_action", "node1", {"duration": 0.1})
        assert node is not None
        assert node.node_id == "node1"
        assert node.config["duration"] == 0.1

    def test_create_unknown_node(self):
        """测试创建未知类型节点返回 None。"""
        registry = init_builtin_executors()
        node = registry.create_node("unknown_type", "node1")
        assert node is None

    def test_get_definitions(self):
        """测试获取节点定义。"""
        registry = init_builtin_executors()
        definitions = registry.get_definitions()

        assert len(definitions) > 0
        for definition in definitions:
            assert "type" in definition
            assert "category" in definition
            assert "label" in definition


class TestYOLOTriggerNode:
    """测试 YOLO 触发器节点。"""

    @pytest.mark.asyncio
    async def test_trigger_with_matching_detection(self):
        """测试检测到匹配目标时触发。"""
        node = YOLOTriggerNode("test", {"class_names": ["person"], "min_confidence": 0.5})
        ctx = ExecutionContext(trigger_data={
            "detections": [
                {"class": "person", "confidence": 0.9},
                {"class": "car", "confidence": 0.8},
            ]
        })

        result = await node.execute(ctx)

        assert result.status == NodeStatus.COMPLETED
        assert result.output_data["triggered"] is True
        assert len(result.output_data["detections"]) == 1

    @pytest.mark.asyncio
    async def test_trigger_without_matching_detection(self):
        """测试未检测到匹配目标时不触发。"""
        node = YOLOTriggerNode("test", {"class_names": ["person"], "min_confidence": 0.5})
        ctx = ExecutionContext(trigger_data={
            "detections": [
                {"class": "car", "confidence": 0.8},
            ]
        })

        result = await node.execute(ctx)

        assert result.status == NodeStatus.COMPLETED
        assert result.output_data["triggered"] is False


class TestObjectExistsConditionNode:
    """测试目标存在条件节点。"""

    @pytest.mark.asyncio
    async def test_condition_true(self):
        """测试条件成立。"""
        node = ObjectExistsConditionNode(
            "test",
            {"class_names": ["person"], "min_count": 1, "comparison": "gte"}
        )
        ctx = ExecutionContext()
        input_data = {
            "detections": [
                {"class": "person", "confidence": 0.9},
            ]
        }

        result = await node.execute(ctx, input_data)

        assert result.status == NodeStatus.COMPLETED
        assert result.output_data["result"] is True

    @pytest.mark.asyncio
    async def test_condition_false(self):
        """测试条件不成立。"""
        node = ObjectExistsConditionNode(
            "test",
            {"class_names": ["person"], "min_count": 3, "comparison": "gte"}
        )
        ctx = ExecutionContext()
        input_data = {
            "detections": [
                {"class": "person", "confidence": 0.9},
            ]
        }

        result = await node.execute(ctx, input_data)

        assert result.status == NodeStatus.COMPLETED
        assert result.output_data["result"] is False


class TestWaitActionNode:
    """测试等待动作节点。"""

    @pytest.mark.asyncio
    async def test_wait_action(self):
        """测试等待动作。"""
        import asyncio
        node = WaitActionNode("test", {"duration": 0.05})
        ctx = ExecutionContext()

        result = await node.execute(ctx)

        assert result.status == NodeStatus.COMPLETED
        assert result.output_data["waited_seconds"] == 0.05


class TestSetVariableNode:
    """测试设置变量节点。"""

    @pytest.mark.asyncio
    async def test_set_static_variable(self):
        """测试设置静态变量。"""
        node = SetVariableNode(
            "test",
            {"variable_name": "count", "value": "10", "value_type": "static"}
        )
        ctx = ExecutionContext()

        result = await node.execute(ctx)

        assert result.status == NodeStatus.COMPLETED
        assert ctx.get_var("count") == 10

    @pytest.mark.asyncio
    async def test_set_variable_no_name(self):
        """测试未提供变量名时失败。"""
        node = SetVariableNode("test", {"variable_name": "", "value": "10"})
        ctx = ExecutionContext()

        result = await node.execute(ctx)

        assert result.status == NodeStatus.FAILED


class TestLogActionNode:
    """测试日志动作节点。"""

    @pytest.mark.asyncio
    async def test_log_action(self):
        """测试日志记录。"""
        node = LogActionNode("test", {"message": "test message", "level": "info"})
        ctx = ExecutionContext()

        result = await node.execute(ctx)

        assert result.status == NodeStatus.COMPLETED
        assert len(ctx.logs) == 1
        assert ctx.logs[0]["message"] == "test message"


class TestManualTriggerNode:
    """测试手动触发器节点。"""

    @pytest.mark.asyncio
    async def test_manual_trigger(self):
        """测试手动触发总是返回 triggered=True。"""
        node = ManualTriggerNode("test")
        ctx = ExecutionContext()

        result = await node.execute(ctx)

        assert result.status == NodeStatus.COMPLETED
        assert result.output_data["triggered"] is True
