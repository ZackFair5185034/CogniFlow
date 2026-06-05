# -*- coding: utf-8 -*-
"""执行日志 API 格式测试。

GET /api/rule-engine/executions/{id}/logs 应返回节点执行日志列表（List[dict]），
而非 {execution: {...}, node_logs: [...]} 包装对象。

Bug 历史：原实现返回包装对象，前端若按 List 解析会失败。
REST 约定："某资源的日志" → 直接返回日志数组。
"""
import json
import pytest
import sys
sys.path.insert(0, '/home/coding/PRIVATE_WORKSPACE/CogniFlow')

from backend.database import (
    ExecutionHistory, NodeExecutionLog, SessionLocal, init_db
)


@pytest.fixture
def db_with_execution():
    """创建一个带 2 条节点日志的执行记录，测试后清理。"""
    init_db()
    db = SessionLocal()
    from datetime import datetime
    exec_record = ExecutionHistory(
        graph_id=999,  # 测试用 graph，不存在也没关系
        status="completed",
        trigger_type="manual",
    )
    db.add(exec_record)
    db.commit()
    db.refresh(exec_record)
    eid = exec_record.id

    log1 = NodeExecutionLog(
        execution_id=eid,
        node_id="n1",
        node_type="manual_trigger",
        status="completed",
        start_time=datetime.now(),
        end_time=datetime.now(),
    )
    log2 = NodeExecutionLog(
        execution_id=eid,
        node_id="n2",
        node_type="log_action",
        status="completed",
        start_time=datetime.now(),
        end_time=datetime.now(),
    )
    db.add_all([log1, log2])
    db.commit()
    yield db, eid
    db.query(NodeExecutionLog).filter(NodeExecutionLog.execution_id == eid).delete()
    db.query(ExecutionHistory).filter(ExecutionHistory.id == eid).delete()
    db.commit()
    db.close()


class TestExecutionLogsAPI:
    """/executions/{id}/logs 应返回 List[dict]，每项包含节点日志字段。"""

    def test_returns_list_not_object(self, db_with_execution):
        """响应必须是 list（直接数组），不能用 {execution, node_logs} 包装。"""
        from fastapi.testclient import TestClient
        from app import app
        db, eid = db_with_execution
        client = TestClient(app)
        resp = client.get(f"/api/rule-engine/executions/{eid}/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list), f"应返回 list，实际: {type(data).__name__}"
        assert len(data) == 2

    def test_each_log_has_node_fields(self, db_with_execution):
        """每条日志必须包含 node_id / node_type / status / start_time / end_time。"""
        from fastapi.testclient import TestClient
        from app import app
        db, eid = db_with_execution
        client = TestClient(app)
        resp = client.get(f"/api/rule-engine/executions/{eid}/logs")
        data = resp.json()
        required = {"node_id", "node_type", "status", "start_time", "end_time"}
        for log in data:
            assert required.issubset(log.keys()), f"日志字段缺失: {required - log.keys()}"

    def test_404_for_missing_execution(self, db_with_execution):
        """不存在的 execution_id 返回 404。"""
        from fastapi.testclient import TestClient
        from app import app
        client = TestClient(app)
        resp = client.get("/api/rule-engine/executions/999999/logs")
        assert resp.status_code == 404

    def test_empty_list_for_execution_without_logs(self, db_with_execution):
        """执行记录存在但无节点日志时，返回空 list。"""
        from fastapi.testclient import TestClient
        from app import app
        db, _ = db_with_execution
        # 创建无日志的执行
        from backend.database import ExecutionHistory
        empty = ExecutionHistory(graph_id=999, status="pending", trigger_type="manual")
        db.add(empty)
        db.commit()
        db.refresh(empty)
        try:
            client = TestClient(app)
            resp = client.get(f"/api/rule-engine/executions/{empty.id}/logs")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            db.delete(empty)
            db.commit()
            db.close()
