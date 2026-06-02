# -*- coding: utf-8 -*-
"""TemplateNode 模板渲染节点测试。

覆盖：
1. 基础文本插值 {{name}}
2. 嵌套 key {{user.name}}
3. 未定义变量 → 空字符串
4. 数字 / 布尔值的字符串化
5. parse_as=text / json 两种输出
6. 非法 JSON 模板 → 回退为字符串
7. 空模板 / 无变量
8. 变量优先级：inputs.data > context.variables > trigger_data
9. 触发数据访问 {{trigger.cron}}
"""
import asyncio
import sys

import pytest

sys.path.insert(0, '/mnt/e/coding-space/aiCode/CogniFlow')

from backend.services.rule_engine.nodes.processing_nodes import (
    TemplateNode,
    _interpolate_template,
    _resolve_scope_key,
)
from backend.services.rule_engine.nodes.base import ExecutionContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_context():
    """模拟执行上下文（带规则图变量与触发数据）。"""
    return ExecutionContext(
        execution_id=1,
        trigger_type='webhook',
        trigger_data={"cron": "0 * * * *", "user_id": 42},
        variables={"threshold": 0.85, "name": "rule_default"},
    )


# ============================================================================
# 1. 辅助函数单元测试
# ============================================================================

class TestResolveScopeKey:
    """_resolve_scope_key 嵌套 key 解析。"""

    def test_top_level_key(self):
        assert _resolve_scope_key({"a": 1}, "a") == 1

    def test_nested_key(self):
        assert _resolve_scope_key({"a": {"b": 2}}, "a.b") == 2

    def test_deep_nested_key(self):
        scope = {"a": {"b": {"c": {"d": "deep"}}}}
        assert _resolve_scope_key(scope, "a.b.c.d") == "deep"

    def test_missing_key_returns_none(self):
        assert _resolve_scope_key({"a": 1}, "b") is None

    def test_missing_nested_segment_returns_none(self):
        assert _resolve_scope_key({"a": {"b": 1}}, "a.c") is None

    def test_traverse_non_dict_returns_none(self):
        # 中间节点不是 dict 时返回 None
        assert _resolve_scope_key({"a": "string_value"}, "a.b") is None


class TestInterpolateTemplate:
    """_interpolate_template 模板插值。"""

    def test_empty_template(self):
        assert _interpolate_template("", {}) == ""

    def test_no_placeholders(self):
        assert _interpolate_template("hello world", {}) == "hello world"

    def test_simple_substitution(self):
        result = _interpolate_template("Hello {{name}}", {"name": "Alice"})
        assert result == "Hello Alice"

    def test_multiple_placeholders(self):
        result = _interpolate_template(
            "{{greeting}}, {{name}}!",
            {"greeting": "Hi", "name": "Bob"},
        )
        assert result == "Hi, Bob!"

    def test_nested_key(self):
        result = _interpolate_template(
            "{{user.name}} ({{user.age}})",
            {"user": {"name": "Carol", "age": 30}},
        )
        assert result == "Carol (30)"

    def test_undefined_variable_empty(self):
        # 未定义变量替换为空字符串，不抛异常
        assert _interpolate_template("{{missing}}", {}) == ""

    def test_number_value(self):
        assert _interpolate_template("{{x}}", {"x": 42}) == "42"

    def test_float_value(self):
        assert _interpolate_template("{{x}}", {"x": 0.85}) == "0.85"

    def test_boolean_value(self):
        assert _interpolate_template("{{x}}", {"x": True}) == "True"

    def test_whitespace_around_key(self):
        # {{ key }} 与 {{key}} 等价
        assert _interpolate_template("{{ key }}", {"key": "v"}) == "v"

    def test_partial_nested_missing(self):
        # 嵌套 key 部分缺失 → 整个 placeholder 为空
        assert _interpolate_template(
            "user={{user.name}}",
            {"user": {}},
        ) == "user="


# ============================================================================
# 2. TemplateNode.execute() 集成测试
# ============================================================================

class TestTemplateNode:
    """TemplateNode 端到端渲染行为。"""

    def _make_node(self, **params):
        node = TemplateNode()
        node.config = {"params": params}
        return node

    def test_text_render_simple(self, mock_context):
        """parse_as=text 模式下 result 为字符串。"""
        node = self._make_node(template="Hello {{name}}", parse_as="text")
        result = asyncio.run(node.execute({}, mock_context))
        # inputs.data 缺失，context.variables.name 生效
        assert result["result"] == "Hello rule_default"
        assert result["raw"] == "Hello rule_default"

    def test_text_render_with_upstream_data(self, mock_context):
        """inputs.data 优先于 context.variables。"""
        node = self._make_node(template="{{name}}", parse_as="text")
        result = asyncio.run(
            node.execute({"data": {"name": "from_upstream"}}, mock_context)
        )
        assert result["result"] == "from_upstream"

    def test_text_render_with_nested_data(self, mock_context):
        """嵌套 dict 数据可点号访问。"""
        node = self._make_node(template="{{user.name}}", parse_as="text")
        result = asyncio.run(
            node.execute({"data": {"user": {"name": "Alice"}}}, mock_context)
        )
        assert result["result"] == "Alice"

    def test_json_render_valid(self, mock_context):
        """parse_as=json 模式下 result 为解析后的对象。"""
        node = self._make_node(
            template='{"count": {{count}}, "name": "{{name}}"}',
            parse_as="json",
        )
        result = asyncio.run(
            node.execute({"data": {"count": 5, "name": "test"}}, mock_context)
        )
        assert result["result"] == {"count": 5, "name": "test"}
        assert isinstance(result["result"], dict)

    def test_json_render_invalid_falls_back_to_string(self, mock_context):
        """非法 JSON 模板回退为字符串，不抛异常。"""
        node = self._make_node(
            template="not valid json {{x}}",
            parse_as="json",
        )
        result = asyncio.run(
            node.execute({"data": {"x": 1}}, mock_context)
        )
        # result 回退为字符串
        assert isinstance(result["result"], str)
        assert result["result"] == "not valid json 1"

    def test_empty_template(self, mock_context):
        """空模板返回空字符串。"""
        node = self._make_node(template="", parse_as="text")
        result = asyncio.run(node.execute({}, mock_context))
        assert result["result"] == ""
        assert result["raw"] == ""

    def test_default_parse_as_is_text(self, mock_context):
        """parse_as 未指定时默认 text。"""
        node = TemplateNode()
        node.config = {"params": {"template": "{{name}}"}}
        result = asyncio.run(
            node.execute({"data": {"name": "x"}}, mock_context)
        )
        assert isinstance(result["result"], str)

    def test_undefined_variable_renders_empty(self, mock_context):
        """未定义变量渲染为空字符串，不阻塞。"""
        node = self._make_node(template="before-{{missing}}-after", parse_as="text")
        result = asyncio.run(node.execute({}, mock_context))
        assert result["result"] == "before--after"

    def test_trigger_data_accessible_via_trigger_prefix(self, mock_context):
        """触发数据通过 {{trigger.*}} 访问。"""
        node = self._make_node(template="cron: {{trigger.cron}}", parse_as="text")
        result = asyncio.run(node.execute({}, mock_context))
        assert result["result"] == "cron: 0 * * * *"

    def test_priority_inputs_over_variables(self, mock_context):
        """inputs.data 同名 key 覆盖 context.variables。"""
        node = self._make_node(template="{{name}}", parse_as="text")
        result = asyncio.run(
            node.execute(
                {"data": {"name": "upstream_wins"}},
                mock_context,  # variables.name = "rule_default"
            )
        )
        assert result["result"] == "upstream_wins"

    def test_priority_variables_over_trigger(self, mock_context):
        """context.variables 同名 key 覆盖 trigger_data。"""
        node = self._make_node(
            template="trigger={{trigger.threshold}}, var={{threshold}}",
            parse_as="text",
        )
        # variables.threshold = 0.85, trigger_data 没有 threshold
        result = asyncio.run(node.execute({}, mock_context))
        # trigger.threshold 为空（未在 trigger_data 中），variables.threshold = 0.85
        assert result["result"] == "trigger=, var=0.85"

    def test_no_data_no_variables_renders_empty(self):
        """无任何数据源时所有 placeholder 渲染为空。"""
        ctx = ExecutionContext(
            execution_id=1,
            trigger_type='manual',
            trigger_data={},
        )
        node = self._make_node(template="{{a}}-{{b}}", parse_as="text")
        result = asyncio.run(node.execute({}, ctx))
        assert result["result"] == "-"

    def test_numeric_value_in_template(self, mock_context):
        """数字在模板中被字符串化。"""
        node = self._make_node(template="count={{n}}", parse_as="text")
        result = asyncio.run(
            node.execute({"data": {"n": 42}}, mock_context)
        )
        assert result["result"] == "count=42"

    def test_validate_inputs_always_passes(self):
        """TemplateNode 不强制输入。"""
        node = TemplateNode()
        valid, err = node.validate_inputs({})
        assert valid is True
        assert err is None
