# -*- coding: utf-8 -*-
"""WebSocket 回放与批处理消息测试。

背景: 2026-10-24 实测, 前端「先 POST 执行再连 WebSocket」存在竞态窗口;
后端 `websocket_manager._flush_messages` 在无订阅者时 `continue` 直接丢弃消息,
导致执行早期的节点事件永远收不到。后端还把多条消息包成 `{"type":"batch"}`,
而前端 `handleWsMessage` 的 switch 没有 batch 分支, 批处理窗口内的消息全部丢失。

本测试锁定:
1. 无订阅者时消息进入回放缓冲, 订阅后补发;
2. 回放一次后即清空, 不重复推送;
3. 批量消息格式正确且每条都带 type。
"""
import asyncio
import json

import pytest

from backend.services.rule_engine.websocket_manager import RuleExecutionConnectionManager


class FakeWebSocket:
    """最小 WebSocket 替身, 记录发送内容。"""

    def __init__(self):
        self.sent: list[str] = []

    async def accept(self):
        return None

    async def send_text(self, text: str):
        self.sent.append(text)

    async def close(self):
        return None


@pytest.fixture
def manager():
    return RuleExecutionConnectionManager()


class TestReplayBuffer:
    """无订阅者时的消息回放。"""

    @pytest.mark.asyncio
    async def test_messages_before_subscribe_are_replayed(self, manager):
        """订阅之前产生的消息在订阅后被回放。"""
        await manager.broadcast({"execution_id": 42, "type": "node_started", "node_id": "n1"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC + 0.05)

        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[42])
        await asyncio.sleep(0.05)

        assert len(ws.sent) == 1
        payload = json.loads(ws.sent[0])
        assert payload["type"] == "node_started"
        assert payload["node_id"] == "n1"

    @pytest.mark.asyncio
    async def test_replay_buffer_is_cleared_after_replay(self, manager):
        """回放一次后即清空, 不重复推送。"""
        await manager.broadcast({"execution_id": 42, "type": "node_started", "node_id": "n1"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC + 0.05)

        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[42])
        await asyncio.sleep(0.05)
        count_after_first = len(ws.sent)

        await manager.subscribe_with_replay(ws, 42)
        await asyncio.sleep(0.05)

        assert len(ws.sent) == count_after_first

    @pytest.mark.asyncio
    async def test_replay_buffer_is_bounded(self, manager):
        """回放缓冲有上限, 不会无限增长。"""
        assert manager.REPLAY_BUFFER_SIZE == 200

    @pytest.mark.asyncio
    async def test_subscribe_with_replay_returns_count(self, manager):
        """subscribe_with_replay 返回回放条数。"""
        await manager.broadcast({"execution_id": 7, "type": "node_started", "node_id": "a"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC + 0.05)

        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[])
        count = await manager.subscribe_with_replay(ws, 7)

        assert count == 1
        assert len(ws.sent) == 1

    @pytest.mark.asyncio
    async def test_replay_is_scoped_per_execution_id(self, manager):
        """回放缓冲按 execution_id 隔离, 不会串到别的执行。"""
        await manager.broadcast({"execution_id": 42, "type": "node_started", "node_id": "n1"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC + 0.05)

        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[99])
        await asyncio.sleep(0.05)

        assert len(ws.sent) == 0


class TestBatchMessage:
    """批量消息格式。"""

    @pytest.mark.asyncio
    async def test_multiple_messages_are_wrapped_in_batch(self, manager):
        """窗口内多条消息被包成 batch, 且每条都带 type。"""
        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[7])

        await manager.broadcast({"execution_id": 7, "type": "node_started", "node_id": "a"})
        await manager.broadcast({"execution_id": 7, "type": "node_started", "node_id": "b"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC + 0.05)

        payload = json.loads(ws.sent[0])
        assert payload["type"] == "batch"
        assert len(payload["messages"]) == 2
        assert all("type" in m for m in payload["messages"])


class TestDeferStartApi:
    """defer_start 接口契约 - 先登记再启动, 消除 WS 订阅竞态。"""

    @pytest.fixture
    def graph_id(self):
        """创建一个最小规则图, 测试结束后删除。"""
        from backend.database import RuleGraph, SessionLocal, init_db

        init_db()
        db = SessionLocal()
        graph = RuleGraph(
            name="cf_defer_start_test_graph",
            description="defer_start 测试用规则图",
            nodes_json="[]",
            edges_json="[]",
        )
        db.add(graph)
        db.commit()
        db.refresh(graph)
        gid = graph.id
        yield gid
        db.query(RuleGraph).filter(RuleGraph.id == gid).delete()
        db.commit()
        db.close()

    def test_execute_with_defer_start_registers_without_running(self, graph_id):
        """defer_start=True 时只登记执行记录, 状态为 pending, 不真正执行。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app

        client = TestClient(fastapi_app)
        resp = client.post(
            "/api/rule-engine/execute",
            json={"graph_id": graph_id, "trigger_type": "manual", "defer_start": True},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "pending"
        assert body["execution_id"] > 0

        # 登记的执行记录状态应为 pending(未被启动)
        from backend.database import ExecutionHistory, SessionLocal

        db = SessionLocal()
        rec = db.query(ExecutionHistory).filter(
            ExecutionHistory.id == body["execution_id"]
        ).first()
        assert rec is not None
        assert rec.status == "pending"
        db.query(ExecutionHistory).filter(
            ExecutionHistory.id == body["execution_id"]
        ).delete()
        db.commit()
        db.close()

    def test_start_execution_rejects_unknown_id(self):
        """对不存在的执行记录启动 -> 404。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app

        client = TestClient(fastapi_app)
        resp = client.post("/api/rule-engine/executions/99999999/start")
        assert resp.status_code == 404, resp.text

    def test_start_execution_rejects_non_pending(self, graph_id):
        """对已结束的执行记录启动 -> 409。"""
        from fastapi.testclient import TestClient
        from app import app as fastapi_app
        from backend.database import ExecutionHistory, SessionLocal

        db = SessionLocal()
        record = ExecutionHistory(
            graph_id=graph_id,
            status="completed",
            trigger_type="manual",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        eid = record.id
        db.close()

        client = TestClient(fastapi_app)
        resp = client.post(f"/api/rule-engine/executions/{eid}/start")
        assert resp.status_code == 409, resp.text

        db = SessionLocal()
        db.query(ExecutionHistory).filter(ExecutionHistory.id == eid).delete()
        db.commit()
        db.close()
