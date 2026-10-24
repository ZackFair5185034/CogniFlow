# -*- coding: utf-8 -*-
"""端口兼容矩阵测试 - 验证矩阵是前后端唯一事实源。

背景: 前端 `RuleCanvas.vue` 的 `isPortCompatible` 只实现了 4 条规则, 与后端执行器的
14 类矩阵漂移, 导致 `BOOLEAN -> TRIGGER` 的边被 VueFlow 在 `isValidConnection` 阶段
静默丢弃, 所有动作节点(输入端口均为 TRIGGER)事实上不可达。
"""
import pytest

from backend.services.rule_engine.port_types import (
    PORT_COMPATIBILITY,
    PORT_TYPES,
    get_compatibility_matrix,
    is_port_compatible,
)


class TestPortCompatibility:
    """端口兼容性判定。"""

    def test_boolean_to_trigger_is_compatible(self):
        """BOOLEAN -> TRIGGER 必须兼容(前端旧实现拒绝, 导致动作层不可达)。"""
        assert is_port_compatible("BOOLEAN", "TRIGGER") is True

    def test_same_type_is_compatible(self):
        """同类型恒兼容。"""
        for t in PORT_TYPES:
            assert is_port_compatible(t, t) is True

    def test_any_is_compatible_with_everything(self):
        """ANY 与任意类型双向兼容。"""
        for t in PORT_TYPES:
            assert is_port_compatible("ANY", t) is True
            assert is_port_compatible(t, "ANY") is True

    def test_incompatible_image_to_boolean_is_rejected(self):
        """IMAGE -> BOOLEAN 非法。"""
        assert is_port_compatible("IMAGE", "BOOLEAN") is False

    def test_empty_type_is_rejected(self):
        """空类型不兼容(fail-loud, 不静默放行)。"""
        assert is_port_compatible("", "IMAGE") is False
        assert is_port_compatible("IMAGE", "") is False
        assert is_port_compatible("IMAGE", None) is False

    def test_unknown_source_type_is_rejected(self):
        """未知源类型不兼容(前端会给出可读错误而非丢弃边)。"""
        assert is_port_compatible("NOT_A_TYPE", "IMAGE") is False

    def test_matrix_covers_every_port_type(self):
        """矩阵必须覆盖全部端口类型。"""
        for t in PORT_TYPES:
            assert t in PORT_COMPATIBILITY

    def test_get_compatibility_matrix_returns_copy(self):
        """下发的矩阵是深拷贝, 外部修改不影响后端常量。"""
        m = get_compatibility_matrix()
        m["IMAGE"].append("HACKED")
        assert "HACKED" not in PORT_COMPATIBILITY["IMAGE"]


class TestExecutorUsesSharedMatrix:
    """执行器必须复用同一张矩阵, 不允许再自带一份。"""

    def test_executor_matrix_is_the_shared_one(self):
        """RuleGraphExecutor.PORT_COMPATIBILITY 与 port_types 保持同一份定义。"""
        from backend.services.rule_engine.executor import RuleGraphExecutor

        assert RuleGraphExecutor.PORT_COMPATIBILITY is PORT_COMPATIBILITY
