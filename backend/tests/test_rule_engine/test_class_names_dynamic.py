# -*- coding: utf-8 -*-
"""yolo_trigger / ObjectExistsCondition class_names 动态化测试。

Bug 历史：class_names 硬编码 COCO 7 类（["person","car",...,"bus"]），
无法匹配用户训练的实际类别（如 ["猫","马里奥","金币数"]）。
后果：选了"person"或"cat"也永远 triggered=False，节点不可用。

修复：
- ConfigSchemaProperty 加 allow_create 字段
- yolo_trigger.class_names 设 enum=[]，allow_create=True
- ObjectExistsCondition.class_names 同上
- 前端 multiselect widget 尊重 allow_create：true 时启用 filterable + allow-create

后端层面：节点 execute() 不依赖 enum，只读取 config.class_names，
因此只要前端能写入正确的类别名，节点就会正常工作。
"""
import pytest
import sys
sys.path.insert(0, '/home/coding/PRIVATE_WORKSPACE/CogniFlow')

from backend.services.rule_engine.models import ConfigSchemaProperty
from backend.services.rule_engine.nodes.detection_nodes import YOLOTriggerNode
from backend.services.rule_engine.nodes.conditions import ObjectExistsConditionNode


class TestConfigSchemaPropertyAllowCreate:
    """ConfigSchemaProperty 新增 allow_create 字段，默认为 False。"""

    def test_default_allow_create_is_false(self):
        prop = ConfigSchemaProperty(type="string", title="x")
        assert prop.allow_create is False

    def test_explicit_allow_create_true(self):
        prop = ConfigSchemaProperty(type="array", title="x", allow_create=True)
        assert prop.allow_create is True


class TestYoloTriggerClassNamesSchema:
    """yolo_trigger.class_names 应使用动态类别（enum 空 + allow_create=True）。"""

    def test_yolo_trigger_class_names_has_no_hardcoded_enum(self):
        """不应再硬编码 COCO 7 类。"""
        node = YOLOTriggerNode()
        schema = node.get_config_schema()
        class_names = schema["class_names"]
        # 移除硬编码后 enum 应为空（或 None），让前端动态填充或允许用户输入
        assert not class_names.enum, f"yolo_trigger.class_names 不应硬编码 enum，但发现: {class_names.enum}"

    def test_yolo_trigger_class_names_allows_user_input(self):
        """应允许用户输入自定义类别（allow_create=True）。"""
        node = YOLOTriggerNode()
        schema = node.get_config_schema()
        assert schema["class_names"].allow_create is True


class TestObjectExistsConditionClassNamesSchema:
    """ObjectExistsCondition.class_names 同上。"""

    def test_object_exists_class_names_has_no_hardcoded_enum(self):
        node = ObjectExistsConditionNode()
        schema = node.get_config_schema()
        class_names = schema["class_names"]
        assert not class_names.enum, f"ObjectExistsCondition.class_names 不应硬编码 enum，但发现: {class_names.enum}"

    def test_object_exists_class_names_allows_user_input(self):
        node = ObjectExistsConditionNode()
        schema = node.get_config_schema()
        assert schema["class_names"].allow_create is True
