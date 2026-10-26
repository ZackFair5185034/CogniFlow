# -*- coding: utf-8 -*-
"""P0 三件套集成测试。

覆盖范围:
- P0-A 节点配置强类型校验 (extra='forbid' 行为, 默认值应用, 必填字段)
- P0-B 图 schema_version 迁移框架 (no-op / 注册迁移 / 缺失链报错)
- P0-C 节点注册表重复检测 (dev 抛 ValueError, prod warn)
- P0-2 ObjectDetector 移除 ssd/detectron2 选项
"""
import logging

import pytest


# ============================================================
# P0-C 节点注册表重复检测
# ============================================================

class TestRegistryDuplication:
    """P0-C: 节点重复注册时 dev 抛 ValueError, prod 仅 warn 覆盖。"""

    def test_register_duplicate_raises_in_dev(self, monkeypatch):
        """开发环境下重复注册同名节点应抛 ValueError。"""
        import backend.services.rule_engine.registry as reg
        monkeypatch.setattr(reg, "_DEV_MODE", True)
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        # init_builtin_executors 是幂等的, 第二次调用直接返回已注册的 registry,
        # 因此手动调用 register 触发重复检测
        registry = reg.init_builtin_executors()
        with pytest.raises(ValueError, match="yolo_model"):
            registry.register(YOLOModelNode)

    def test_register_duplicate_warns_in_prod(self, monkeypatch, caplog):
        """生产环境下重复注册应 warning 日志而非抛异常。"""
        import backend.services.rule_engine.registry as reg
        monkeypatch.setattr(reg, "_DEV_MODE", False)
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        registry = reg.init_builtin_executors()
        with caplog.at_level(logging.WARNING):
            registry.register(YOLOModelNode)
        # 应至少有一条 WARN 日志说明被覆盖
        warning_logs = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_logs) >= 1, "生产模式应输出 WARN 日志"


# ============================================================
# P0-A 节点配置强类型校验
# ============================================================

class TestNodeConfigValidation:
    """P0-A: BaseExecutor.validate_config() 强类型校验。"""

    def test_validate_config_valid(self):
        """合法配置应通过校验, 返回应用默认值后的 sanitized_config。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        ok, err, sanitized = node.validate_config({"model_id": 1, "confidence": 0.7})
        assert ok is True
        assert err is None
        assert sanitized["model_id"] == 1
        assert sanitized["confidence"] == 0.7

    def test_validate_config_unknown_field_rejected(self):
        """extra='forbid' 必须捕获拼写错误的字段名。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        # 'confidenc' 是 'confidence' 的拼写错误
        ok, err, _ = node.validate_config({"model_id": 1, "confidenc": 0.7})
        assert ok is False
        assert "confidenc" in err

    def test_validate_config_defaults_applied(self):
        """校验后未提供的可选字段应填默认值。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        ok, err, sanitized = node.validate_config({"model_id": 1})
        assert ok is True
        assert err is None
        assert sanitized["confidence"] == 0.5
        assert sanitized["iou_threshold"] == 0.45
        assert sanitized["max_detections"] == 300
        assert sanitized["device"] == "auto"

    def test_validate_config_none_schema_passes(self):
        """ConfigSchema=None 的节点应直接放行 (向后兼容无配置节点)。"""
        from backend.services.rule_engine.nodes.actions import LogActionNode
        # LogActionNode 已声明 ConfigSchema, 改用无 schema 的 BranchNode
        from backend.services.rule_engine.nodes.logic import BranchNode
        node = BranchNode()
        ok, err, sanitized = node.validate_config({"any": "thing"})
        assert ok is True
        assert err is None

    def test_validate_config_enum_violation(self):
        """Literal 字段传入非法值应报错。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        ok, err, _ = node.validate_config({"model_id": 1, "device": "tpu"})
        assert ok is False
        assert "device" in err

    def test_validate_config_range_violation(self):
        """数值字段超出 ge/le 范围应报错。"""
        from backend.services.rule_engine.nodes.detection_nodes import YOLOModelNode
        node = YOLOModelNode()
        ok, err, _ = node.validate_config({"model_id": 1, "confidence": 1.5})
        assert ok is False
        assert "confidence" in err

    def test_all_34_nodes_have_schema_or_none(self):
        """34 个节点均应正常注册, 且至少有 ConfigSchema 属性。"""
        from backend.services.rule_engine.registry import init_builtin_executors
        from backend.services.rule_engine.models import NodeConfigSchema
        registry = init_builtin_executors()
        assert len(registry.list_types()) == 34, (
            f"期望 34 个节点, 实际 {len(registry.list_types())}"
        )
        for node_type in registry.list_types():
            executor_cls = registry.get(node_type)
            assert hasattr(executor_cls, "ConfigSchema"), (
                f"{node_type} 缺少 ConfigSchema 类属性"
            )
            assert executor_cls.ConfigSchema is None or issubclass(
                executor_cls.ConfigSchema, NodeConfigSchema
            ), f"{node_type}.ConfigSchema 应为 None 或 NodeConfigSchema 子类"


# ============================================================
# P0-B 图 schema_version 迁移框架
# ============================================================

class TestGraphMigration:
    """P0-B: 规则图 schema 迁移框架。"""

    def test_migrate_noop_when_current(self):
        """from_version == CURRENT_SCHEMA_VERSION 时不应用迁移。"""
        from backend.services.rule_engine.migrations import (
            CURRENT_SCHEMA_VERSION, migrate_graph_data,
        )
        nodes, edges, vars_, new_v = migrate_graph_data([], [], {}, CURRENT_SCHEMA_VERSION)
        assert new_v == CURRENT_SCHEMA_VERSION

    def test_migrate_with_function(self):
        """注册的迁移函数应被正确调用。"""
        import backend.services.rule_engine.migrations as mig_mod
        from backend.services.rule_engine.migrations import (
            migrate_graph_data, register_migration, _MIGRATIONS,
        )
        original = mig_mod.CURRENT_SCHEMA_VERSION
        mig_mod.CURRENT_SCHEMA_VERSION = 100
        try:
            @register_migration(99, 100)
            def _add_x(nodes, edges, variables):
                return nodes + [{"id": "x"}], edges, variables

            new_nodes, new_edges, new_vars, new_v = migrate_graph_data([], [], {}, 99)
            assert new_v == 100
            assert len(new_nodes) == 1
            assert new_nodes[0]["id"] == "x"
        finally:
            mig_mod.CURRENT_SCHEMA_VERSION = original
            _MIGRATIONS.pop((99, 100))

    def test_migrate_missing_chain_raises(self):
        """缺少中间迁移函数应抛 MigrationError。"""
        import backend.services.rule_engine.migrations as mig_mod
        from backend.services.rule_engine.migrations import (
            migrate_graph_data, MigrationError,
        )
        original = mig_mod.CURRENT_SCHEMA_VERSION
        mig_mod.CURRENT_SCHEMA_VERSION = 99
        try:
            with pytest.raises(MigrationError):
                migrate_graph_data([], [], {}, 95)
        finally:
            mig_mod.CURRENT_SCHEMA_VERSION = original

    def test_migrate_chain_v1_to_v3(self):
        """链式迁移 v1 -> v2 -> v3 应一次性完成。"""
        import backend.services.rule_engine.migrations as mig_mod
        from backend.services.rule_engine.migrations import (
            migrate_graph_data, register_migration, _MIGRATIONS,
        )
        original = mig_mod.CURRENT_SCHEMA_VERSION
        mig_mod.CURRENT_SCHEMA_VERSION = 3
        try:
            @register_migration(1, 2)
            def _m12(nodes, edges, variables):
                return nodes + [{"id": "v2"}], edges, variables

            @register_migration(2, 3)
            def _m23(nodes, edges, variables):
                return nodes + [{"id": "v3"}], edges, variables

            new_nodes, _, _, new_v = migrate_graph_data([], [], {}, 1)
            assert new_v == 3
            assert len(new_nodes) == 2
            assert new_nodes[0]["id"] == "v2"
            assert new_nodes[1]["id"] == "v3"
        finally:
            mig_mod.CURRENT_SCHEMA_VERSION = original
            _MIGRATIONS.pop((1, 2))
            _MIGRATIONS.pop((2, 3))


# ============================================================
# P0-2 ObjectDetector 移除 ssd/detectron2/mtcnn
# ============================================================

class TestObjectDetectorSchema:
    """P0-2: ObjectDetector 应仅保留 yolo 选项。"""

    def test_ssd_detectron2_removed(self):
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        schema = node.get_config_schema()
        model_type_prop = schema.get("model_type")
        assert model_type_prop is not None
        assert "ssd" not in model_type_prop.enum
        assert "detectron2" not in model_type_prop.enum
        assert "mtcnn" not in model_type_prop.enum
        assert "yolo" in model_type_prop.enum

    def test_object_detector_rejects_non_yolo_config(self):
        """ConfigSchema 应通过 Pydantic Literal 拒绝非 yolo 的 model_type。"""
        from backend.services.rule_engine.nodes.detection_nodes import ObjectDetectorNode
        node = ObjectDetectorNode()
        ok, err, _ = node.validate_config({"model_type": "ssd"})
        assert ok is False
        assert "model_type" in err


# ============================================================
# P0-A 注册清单 (启动期输出现已实现, 此处只做冒烟验证)
# ============================================================

class TestStartupNodeList:
    """P0-C: init_builtin_executors 应注册全部 34 个节点。"""

    def test_all_34_nodes_registered(self):
        from backend.services.rule_engine.registry import init_builtin_executors
        registry = init_builtin_executors()
        types = sorted(registry.list_types())
        assert len(types) == 34

        # 校验所有预期节点类型已注册
        expected = {
            # input (3)
            "image_capture", "video_capture", "screen_capture",
            # triggers (5)
            "manual_trigger", "timer_trigger", "cron_trigger",
            "webhook_trigger", "api_trigger",
            # detection (3)
            "yolo_model", "yolo_trigger", "object_detector",
            # processing (7)
            "category_encode", "filter", "tracker",
            "image_preprocessor", "template", "merge_detections", "roi_extract",
            # actions (5)
            "keyboard_action", "mouse_action", "wait_action",
            "http_request_action", "log_action",
            # logic (5)
            "branch", "parallel_branch", "delay",
            "set_variable", "counter",
            # conditions (3)
            "object_exists_condition", "confidence_threshold_condition",
            "variable_condition",
            # output (3)
            "save_result", "notification", "display",
        }
        assert set(types) == expected