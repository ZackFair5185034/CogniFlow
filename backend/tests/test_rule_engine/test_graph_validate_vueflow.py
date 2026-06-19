# -*- coding: utf-8 -*-
"""规则图验证测试 - VueFlow 格式兼容。

回归测试 Phase 13.4 验收漏掉的 VueFlow 节点 type="ruleNode" 场景：
前端 VueFlow 保存的图，节点顶层 type 是 VueFlow 节点种类（"ruleNode"），
实际业务类型在 data.type。前端建的图应通过 validate_graph。

Bug 历史：
- Phase 13.4 修复了 type="custom" 的白名单，但漏掉 "ruleNode"
- 表现：前端建的图 100% 报"没有起始触发器节点"或"孤立节点"
"""
import json
import pytest
import sys
sys.path.insert(0, '/home/coding/PRIVATE_WORKSPACE/CogniFlow')

from backend.services.rule_engine.graph_manager import GraphManager
from backend.database import RuleGraph, SessionLocal, init_db


@pytest.fixture
def db_session():
    """提供测试用的数据库会话，测试后清理数据。"""
    init_db()  # 确保表存在
    db = SessionLocal()
    yield db
    # 清理：删除本测试创建的图
    db.query(RuleGraph).filter(RuleGraph.name.like("test_validate_%")).delete()
    db.commit()
    db.close()


class TestVueFlowFormatValidation:
    """验证 VueFlow 格式的图能通过 validate_graph。"""

    def _save_graph(self, db, name, nodes, edges):
        """辅助方法：直接以 VueFlow 格式创建图。"""
        graph = RuleGraph(
            name=name,
            nodes_json=json.dumps(nodes),
            edges_json=json.dumps(edges),
            variables_json="{}",
        )
        db.add(graph)
        db.commit()
        db.refresh(graph)
        return graph.id


def _save_graph(db, name, nodes, edges):
    """模块级辅助：直接以 VueFlow 格式创建图（多个测试类共用）。"""
    graph = RuleGraph(
        name=name,
        nodes_json=json.dumps(nodes),
        edges_json=json.dumps(edges),
        variables_json="{}",
    )
    db.add(graph)
    db.commit()
    db.refresh(graph)
    return graph.id

    def test_manual_trigger_vueflow_format_validates(self, db_session):
        """VueFlow 格式的 manual_trigger（type=ruleNode）应通过验证。"""
        nodes = [{
            "id": "n1",
            "type": "ruleNode",  # VueFlow 节点种类
            "data": {"type": "manual_trigger", "config": {}}
        }]
        graph_id = self._save_graph(db_session, "test_validate_mt", nodes, [])

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"VueFlow 格式 manual_trigger 应通过验证，但报错: {err}"
        assert err is None

    def test_yolo_trigger_vueflow_format_validates(self, db_session):
        """VueFlow 格式的 yolo_trigger 单节点应通过验证（不视为孤立）。"""
        nodes = [{
            "id": "y1",
            "type": "ruleNode",
            "data": {"type": "yolo_trigger", "config": {"model_id": 1}}
        }]
        graph_id = self._save_graph(db_session, "test_validate_yt", nodes, [])

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"VueFlow 格式 yolo_trigger 应通过验证，但报错: {err}"

    def test_manual_to_yolo_trigger_with_edge_validates(self, db_session):
        """VueFlow 格式 manual → yolo_trigger 连边应通过验证。"""
        nodes = [
            {"id": "n1", "type": "ruleNode",
             "data": {"type": "manual_trigger", "config": {}}},
            {"id": "n2", "type": "ruleNode",
             "data": {"type": "yolo_trigger", "config": {"model_id": 1}}}
        ]
        edges = [{"id": "e1", "source": "n1", "target": "n2",
                  "source_handle": "trigger", "target_handle": "image"}]
        graph_id = self._save_graph(db_session, "test_validate_mt_yt", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"VueFlow 格式 manual→yolo_trigger 连边应通过验证，但报错: {err}"

    def test_backend_format_still_works(self, db_session):
        """后端直存格式（type 在顶层）仍应通过验证（向后兼容）。"""
        nodes = [{"id": "n1", "type": "manual_trigger", "data": {}}]
        graph_id = self._save_graph(db_session, "test_validate_bf", nodes, [])

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"后端格式 manual_trigger 应通过验证，但报错: {err}"

    def test_non_trigger_node_without_edges_still_isolated(self, db_session):
        """VueFlow 格式的 action 节点（无输入输出边）仍应报孤立。"""
        nodes = [{
            "id": "n1",
            "type": "ruleNode",
            "data": {"type": "log_action", "config": {}}
        }]
        graph_id = self._save_graph(db_session, "test_validate_isolated", nodes, [])

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert not valid, "无连接的 action 节点应报孤立"
        assert "孤立" in err

    def test_data_field_missing_falls_back_to_top_type(self, db_session):
        """data 字段完全缺失时，应回退到顶层 type 识别节点。

        回归保护：graph_manager 的 get_node_type 在 data 不存在时
        必须正确处理（防止后续重构时改成强制要求 data 字段）。
        """
        nodes = [{"id": "n1", "type": "manual_trigger"}]  # 无 data 字段
        graph_id = self._save_graph(db_session, "test_validate_no_data", nodes, [])

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"data 缺失时应回退到顶层 type，但报错: {err}"

    def test_data_field_none_falls_back_to_top_type(self, db_session):
        """data 字段显式 None 时，应回退到顶层 type 识别节点。"""
        nodes = [{"id": "n1", "type": "manual_trigger", "data": None}]
        graph_id = self._save_graph(db_session, "test_validate_none_data", nodes, [])

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"data=None 时应回退到顶层 type，但报错: {err}"


class TestEdgeStructuralValidation:
    """P0-1 (2026-06-19): 边的结构合法性校验。

    - 自循环边（source == target）应被拒绝
    - 重复边（同 source/target/handles）应被拒绝
    - 历史：之前没拒绝，导致 Kahn 拓扑误报"循环依赖"，下游被多次触发。
    """

    def test_self_loop_edge_rejected(self, db_session):
        """A→A 自循环边应被拒绝。"""
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
        ]
        edges = [{"id": "e_loop", "source": "n1", "target": "n1",
                  "source_handle": "trigger", "target_handle": "image"}]
        graph_id = _save_graph(db_session, "test_validate_selfloop", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert not valid, "自循环边应被拒绝"
        assert "自循环" in err
        assert "e_loop" in err

    def test_duplicate_edge_rejected(self, db_session):
        """重复边（同端点 + 同 handles）应被拒绝。"""
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
            {"id": "n2", "type": "yolo_trigger", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2",
             "source_handle": "trigger", "target_handle": "image"},
            {"id": "e2", "source": "n1", "target": "n2",
             "source_handle": "trigger", "target_handle": "image"},  # 重复
        ]
        graph_id = _save_graph(db_session, "test_validate_dup", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert not valid, "重复边应被拒绝"
        assert "重复" in err
        assert "e2" in err

    def test_different_handles_same_endpoints_allowed(self, db_session):
        """同 source/target 但不同 handle 的多条边允许（多端口分别连）。"""
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
            {"id": "n2", "type": "yolo_trigger", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2",
             "source_handle": "trigger", "target_handle": "image"},
            {"id": "e2", "source": "n1", "target": "n2",
             "source_handle": "extra", "target_handle": "extra"},  # 不同 handle
        ]
        graph_id = _save_graph(db_session, "test_validate_multihandle", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"不同 handle 的多条边应被允许，但报错: {err}"

    def test_duplicate_check_handles_camel_and_snake_case(self, db_session):
        """重复检测同时识别 source_handle (snake) 和 sourceHandle (camel) 两种字段。"""
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
            {"id": "n2", "type": "yolo_trigger", "data": {}},
        ]
        edges = [
            {"id": "e1", "source": "n1", "target": "n2",
             "source_handle": "trigger", "target_handle": "image"},
            {"id": "e2", "source": "n1", "target": "n2",
             "sourceHandle": "trigger", "targetHandle": "image"},  # 混用 camel
        ]
        graph_id = _save_graph(db_session, "test_validate_camel", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert not valid, "snake_case 与 camelCase 字段混用时也应识别为重复边"

    def test_required_input_unconnected_rejected(self, db_session):
        """P1-1: 必填输入端口未连接应被拒绝。

        yolo_trigger 有 required image 输入, 没连边 → 校验失败。
        """
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
            {"id": "n2", "type": "ruleNode",
             "data": {"type": "yolo_trigger", "config": {},
                      "inputs": [{"name": "image", "type": "IMAGE",
                                  "required": True, "label": "图像"}]}},
        ]
        # n1 → n2 的边只连到 trigger handle, 不连 image (故意少连)
        edges = [{"id": "e1", "source": "n1", "target": "n2",
                  "source_handle": "trigger", "target_handle": "trigger"}]
        graph_id = _save_graph(db_session, "test_validate_missing_req", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert not valid, "必填 image 输入未连应被拒绝"
        assert "必填" in err
        assert "n2.image" in err

    def test_required_input_connected_allowed(self, db_session):
        """P1-1: 必填输入端口已连接 → 通过。"""
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
            {"id": "n2", "type": "ruleNode",
             "data": {"type": "yolo_trigger", "config": {},
                      "inputs": [{"name": "image", "type": "IMAGE",
                                  "required": True, "label": "图像"}]}},
        ]
        edges = [{"id": "e1", "source": "n1", "target": "n2",
                  "source_handle": "trigger", "target_handle": "image"}]
        graph_id = _save_graph(db_session, "test_validate_req_ok", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"必填 image 已连应通过，但报错: {err}"

    def test_optional_input_unconnected_allowed(self, db_session):
        """P1-1: 可选输入端口未连接 → 通过（前提是其它必填端口已连/无必填端口）。"""
        nodes = [
            {"id": "n1", "type": "manual_trigger", "data": {}},
            {"id": "n2", "type": "ruleNode",
             "data": {"type": "log_action", "config": {},
                      "inputs": [
                          {"name": "trigger", "type": "TRIGGER",
                           "required": True, "label": "触发"},
                          {"name": "message", "type": "STRING",
                           "required": False, "label": "消息"},
                      ]}},
        ]
        # 只连 trigger (必填), message (可选) 不连
        edges = [{"id": "e1", "source": "n1", "target": "n2",
                  "source_handle": "trigger", "target_handle": "trigger"}]
        graph_id = _save_graph(db_session, "test_validate_opt_ok", nodes, edges)

        manager = GraphManager(db_session)
        valid, err = manager.validate_graph(graph_id)

        assert valid, f"可选 input 未连应通过，但报错: {err}"
