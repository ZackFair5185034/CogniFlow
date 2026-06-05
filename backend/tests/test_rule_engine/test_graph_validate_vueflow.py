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
