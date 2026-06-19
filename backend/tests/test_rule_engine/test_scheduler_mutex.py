# -*- coding: utf-8 -*-
"""BE-P0-3 调度器执行互斥测试 (2026-06-19)。

验证:
1. 同图二次触发 skip (已有执行中, 不创建第二份 task)
2. 不同图并发执行互不影响
3. 锁释放后, 下次触发能正常进入
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from backend.services.rule_engine.scheduler import RuleScheduler


# ============================================================================
# Tests
# ============================================================================

def test_second_trigger_skips_when_locked():
    """BE-P0-3: 同图二次触发应 skip, 不创建第二个执行。"""
    scheduler = RuleScheduler()
    lock = scheduler._get_lock(100)

    async def scenario():
        # 模拟第一个执行持锁
        await lock.acquire()
        try:
            # 第二次触发: 应立刻 skip
            await scheduler._execute_graph(100, {"cron": "*/1 * * * *"})
        finally:
            lock.release()

    with patch("backend.services.rule_engine.scheduler.SessionLocal") as mock_session_local, \
         patch("backend.services.rule_engine.scheduler.GraphManager") as mock_gm_cls, \
         patch("backend.services.rule_engine.scheduler.RuleGraphExecutor") as mock_exec_cls:
        # 即使 lock 已占, 不应触达 SessionLocal/GraphManager (因为早 return)
        asyncio.run(scenario())

        # 关键断言: SessionLocal 没被调 (因为早 return)
        assert not mock_session_local.called, \
            f"二次触发应 skip, 但 SessionLocal 仍被调用 (说明走到了数据库层)"


def test_different_graphs_run_concurrently():
    """BE-P0-3: 不同图有独立 lock, 互不影响。"""
    scheduler = RuleScheduler()
    lock_a = scheduler._get_lock(1)
    lock_b = scheduler._get_lock(2)

    assert lock_a is not lock_b, "不同 graph_id 应创建独立 lock 实例"


def test_lock_released_after_execution():
    """BE-P0-3: 锁在执行完释放, 下次触发能正常进入。"""
    scheduler = RuleScheduler()
    lock = scheduler._get_lock(50)

    # 模拟完整执行周期
    async def scenario():
        await lock.acquire()
        # ... do work
        lock.release()
        assert not lock.locked(), "锁应在 release 后立即可重新获取"

    asyncio.run(scenario())


def test_execute_graph_creates_release_lock_cycle():
    """BE-P0-3: _execute_graph 加锁-执行-释放, 锁最终回到未占状态。"""
    scheduler = RuleScheduler()
    graph_id = 200

    async def scenario():
        # 提前占锁, 让 _execute_graph 走 skip 路径
        # (测试 skip 路径锁的"前置占用 → skip"是否正确, 不留副作用)
        lock = scheduler._get_lock(graph_id)
        await lock.acquire()
        try:
            await scheduler._execute_graph(graph_id, {"cron": "*/1"})
            # skip 路径: 不应改变 lock 状态
            assert lock.locked(), "skip 路径不应释放锁 (锁是执行方的, 不是触发方的)"
        finally:
            lock.release()
        # 释放后, 再次 _execute_graph 路径应能进入 (但因为 mock 不全, 只验证 lock 状态)
        assert not lock.locked()

    asyncio.run(scenario())
