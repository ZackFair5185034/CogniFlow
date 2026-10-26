# -*- coding: utf-8 -*-
"""WebSocket 批量刷新的竞态回归测试。

背景 (2026-10-24 人工走查发现):
`RuleExecutionConnectionManager.broadcast()` 只在 `self._flush_task.done()` 时
才新建刷新任务, 而刷新任务的**发送阶段在锁外**(要 await ws.send_text)。
该阶段到达的消息会进 `_pending_messages` 缓冲, 但此时刷新任务还没结束,
`done()` 为 False → 不会再有第二个刷新任务 → **消息被永久滞留**。

典型症状: `execution_complete` 恰好在上一个批次的发送途中到达时被吞掉,
前端状态永远停在「执行中」, 节点状态却是成功的 —— 业务闭环断在最后一步。

本测试锁定: 发送阶段到达的消息必须被下一轮刷新发出。
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


class BlockingWebSocket(FakeWebSocket):
    """send_text 会阻塞 —— 用来把刷新任务精确卡在「发送阶段」。

    发送阶段在锁外, 正是在这个窗口里到达的消息会被旧实现吞掉。
    """

    def __init__(self):
        super().__init__()
        self.gate = asyncio.Event()
        self.entered = asyncio.Event()

    async def send_text(self, text: str):
        self.entered.set()
        await self.gate.wait()
        self.sent.append(text)


def _flatten(sent: list[str]) -> list[str]:
    """把收到的报文摊平成 type 列表 (batch 会被拆开)。"""
    types: list[str] = []
    for raw in sent:
        payload = json.loads(raw)
        if payload.get("type") == "batch":
            types.extend(m.get("type") for m in payload.get("messages", []))
        else:
            types.append(payload.get("type"))
    return types


@pytest.fixture
def manager():
    return RuleExecutionConnectionManager()


class TestFlushRace:
    """刷新任务发送阶段的消息不能被滞留。"""

    @pytest.mark.asyncio
    async def test_message_during_send_phase_is_delivered(self, manager):
        """发送阶段到达的消息必须被后续刷新发出, 而不是永久滞留。"""
        ws = BlockingWebSocket()
        await manager.connect(ws, execution_ids=[7])

        # 第一条消息 —— 触发刷新任务, 并把任务卡在发送阶段
        await manager.broadcast({"execution_id": 7, "type": "node_started", "node_id": "a"})
        await asyncio.wait_for(ws.entered.wait(), timeout=2)

        # 关键: 此刻刷新任务正在发送(锁外), 这条消息在旧实现里会被滞留
        await manager.broadcast({
            "execution_id": 7,
            "type": "execution_complete",
            "status": "completed",
        })

        # 放行发送
        ws.gate.set()
        await asyncio.sleep(manager.BATCH_WINDOW_SEC * 6 + 0.1)

        types = _flatten(ws.sent)
        assert "node_started" in types
        assert "execution_complete" in types, f"execution_complete 被滞留, 实际收到: {types}"

    @pytest.mark.asyncio
    async def test_all_messages_arrive_in_order(self, manager):
        """连续多条消息一条都不能少 (按到达顺序)。"""
        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[9])

        for i in range(5):
            await manager.broadcast({
                "execution_id": 9,
                "type": "node_started",
                "node_id": f"n{i}",
            })
        await asyncio.sleep(manager.BATCH_WINDOW_SEC * 6 + 0.1)

        types = _flatten(ws.sent)
        assert types.count("node_started") == 5

    @pytest.mark.asyncio
    async def test_flush_task_is_released_when_idle(self, manager):
        """缓冲区清空后刷新任务应退出, 后续广播能重新拉起。"""
        ws = FakeWebSocket()
        await manager.connect(ws, execution_ids=[11])

        await manager.broadcast({"execution_id": 11, "type": "node_started", "node_id": "a"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC * 6 + 0.1)
        assert manager._flush_task is None

        # 空闲之后再来一条 —— 必须还能发出去
        await manager.broadcast({"execution_id": 11, "type": "execution_complete"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC * 6 + 0.1)

        assert "execution_complete" in _flatten(ws.sent)

    @pytest.mark.asyncio
    async def test_message_without_execution_id_is_ignored(self, manager):
        """没有 execution_id 的消息直接忽略, 不进缓冲。"""
        await manager.broadcast({"type": "node_started", "node_id": "a"})
        await asyncio.sleep(manager.BATCH_WINDOW_SEC * 6 + 0.1)

        assert manager._pending_messages == {}
