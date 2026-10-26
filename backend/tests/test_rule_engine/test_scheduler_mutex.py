# -*- coding: utf-8 -*-
"""调度器执行互斥测试。

2026-10-24 复核发现: 旧版测试全部只覆盖「skip 路径」(测试自己先占锁再触发),
从未验证「执行进行中锁是否仍被持有」, 因此是**假绿**。

真实缺陷: `_execute_graph` 用 `asyncio.create_task` 启动执行, 函数随即返回,
`finally` 里的 `lock.release()` 立刻释放锁 —— 锁只覆盖了「触发瞬间」,
不覆盖「执行过程」, Cron 间隔短于执行耗时会重复起一份执行。

本文件锁定:
1. 执行进行中, 该图的锁必须处于占用状态;
2. 执行进行中, 第二次触发必须被跳过(不重复执行);
3. 执行结束后, 锁必须释放, 下次触发能正常进入;
4. 不同图之间互不影响。
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from backend.services.rule_engine.scheduler import RuleScheduler


def _patch_deps(mock_exec_cls):
    """打桩调度器依赖: SessionLocal / GraphManager / RuleGraphExecutor。"""
    return (
        patch("backend.services.rule_engine.scheduler.SessionLocal"),
        patch("backend.services.rule_engine.scheduler.GraphManager"),
        patch("backend.services.rule_engine.scheduler.RuleGraphExecutor", mock_exec_cls),
    )


class TestSchedulerMutex:
    """定时执行互斥。"""

    @pytest.mark.asyncio
    async def test_lock_is_held_during_execution(self):
        """锁必须覆盖整个执行过程, 而不是只覆盖触发瞬间。"""
        scheduler = RuleScheduler()
        graph_id = 200
        started = asyncio.Event()
        release = asyncio.Event()
        held_during_execution: list[bool] = []

        async def fake_execute(*args, **kwargs):
            held_during_execution.append(scheduler._get_lock(graph_id).locked())
            started.set()
            await release.wait()
            return {"status": "completed"}

        mock_exec_cls = MagicMock()
        mock_exec_cls.return_value.create_execution_record.return_value = 999
        mock_exec_cls.return_value.execute = fake_execute

        p1, p2, p3 = _patch_deps(mock_exec_cls)
        with p1 as mock_session_local, p2 as mock_gm_cls, p3:
            mock_gm_cls.return_value.get_graph.return_value = MagicMock()
            mock_gm_cls.return_value.parse_graph_data.return_value = {
                "nodes": {}, "edges": [],
            }

            task = asyncio.create_task(scheduler._execute_graph(graph_id, {}))
            await asyncio.wait_for(started.wait(), timeout=2.0)

            # 执行进行中, 锁必须被持有
            assert scheduler._get_lock(graph_id).locked(), (
                "执行进行中锁未持有 —— 互斥失效(create_task 后立即 release)"
            )
            assert held_during_execution == [True], (
                f"执行期间锁未持有: {held_during_execution}"
            )

            release.set()
            await asyncio.wait_for(task, timeout=2.0)

        # 执行结束后锁必须释放
        assert not scheduler._get_lock(graph_id).locked(), "执行结束后锁未释放"

    @pytest.mark.asyncio
    async def test_second_trigger_skipped_while_running(self):
        """上一次执行未结束时, 第二次触发必须被跳过(不重复执行)。"""
        scheduler = RuleScheduler()
        graph_id = 201
        started = asyncio.Event()
        release = asyncio.Event()
        executed: list[int] = []

        async def fake_execute(*args, **kwargs):
            executed.append(kwargs.get("execution_id"))
            started.set()
            await release.wait()
            return {"status": "completed"}

        mock_exec_cls = MagicMock()
        mock_exec_cls.return_value.create_execution_record.return_value = 1001
        mock_exec_cls.return_value.execute = fake_execute

        p1, p2, p3 = _patch_deps(mock_exec_cls)
        with p1, p2 as mock_gm_cls, p3:
            mock_gm_cls.return_value.get_graph.return_value = MagicMock()
            mock_gm_cls.return_value.parse_graph_data.return_value = {
                "nodes": {}, "edges": [],
            }

            first = asyncio.create_task(scheduler._execute_graph(graph_id, {}))
            await asyncio.wait_for(started.wait(), timeout=2.0)

            # 执行尚未结束 —— 第二次触发必须被跳过
            await asyncio.wait_for(scheduler._execute_graph(graph_id, {}), timeout=2.0)

            release.set()
            await asyncio.wait_for(first, timeout=2.0)

        assert len(executed) == 1, f"实际执行了 {len(executed)} 次, 互斥失效"

    @pytest.mark.asyncio
    async def test_lock_released_after_execution_allows_next_run(self):
        """执行结束后, 下次触发能正常进入(锁没有泄漏)。"""
        scheduler = RuleScheduler()
        graph_id = 202
        executed: list[int] = []

        async def fake_execute(*args, **kwargs):
            executed.append(kwargs.get("execution_id"))
            return {"status": "completed"}

        mock_exec_cls = MagicMock()
        mock_exec_cls.return_value.create_execution_record.return_value = 1002
        mock_exec_cls.return_value.execute = fake_execute

        p1, p2, p3 = _patch_deps(mock_exec_cls)
        with p1, p2 as mock_gm_cls, p3:
            mock_gm_cls.return_value.get_graph.return_value = MagicMock()
            mock_gm_cls.return_value.parse_graph_data.return_value = {
                "nodes": {}, "edges": [],
            }

            await scheduler._execute_graph(graph_id, {})
            await scheduler._execute_graph(graph_id, {})

        assert len(executed) == 2, "锁泄漏, 第二次触发被误跳过"
        assert not scheduler._get_lock(graph_id).locked()

    def test_different_graphs_have_independent_locks(self):
        """不同图有独立锁, 互不影响。"""
        scheduler = RuleScheduler()
        lock_a = scheduler._get_lock(1)
        lock_b = scheduler._get_lock(2)

        assert lock_a is not lock_b, "不同 graph_id 应创建独立 lock 实例"
