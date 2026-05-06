# -*- coding: utf-8 -*-
"""规则引擎定时触发调度器。

基于 APScheduler 的定时执行管理。
"""
import asyncio
import logging
from typing import Dict, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.services.rule_engine import GraphManager, RuleGraphExecutor
from backend.services.rule_engine.websocket_manager import rule_ws_manager

logger = logging.getLogger(__name__)


class RuleScheduler:
    """规则定时触发调度器。"""

    _instance: Optional["RuleScheduler"] = None

    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        # graph_id -> job_id 映射
        self._job_map: Dict[int, str] = {}

    @classmethod
    def get_instance(cls) -> "RuleScheduler":
        if cls._instance is None:
            cls._instance = RuleScheduler()
        return cls._instance

    def start(self):
        """启动调度器。"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("[RuleScheduler] 调度器已启动")

    def stop(self):
        """停止调度器。"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("[RuleScheduler] 调度器已停止")

    async def _execute_graph(self, graph_id: int, trigger_config: dict):
        """执行规则图（异步后台）。"""
        db = SessionLocal()
        try:
            manager = GraphManager(db)
            graph = manager.get_graph(graph_id)
            if graph is None:
                logger.warning(f"[RuleScheduler] 规则图 {graph_id} 不存在")
                return

            graph_data = manager.parse_graph_data(graph)

            # 创建执行记录
            executor = RuleGraphExecutor(db, ws_manager=rule_ws_manager)
            execution_id = executor.create_execution_record(
                graph_id=graph_id,
                trigger_type="timer",
                trigger_data=trigger_config,
            )

            # 异步执行
            asyncio.create_task(
                executor.execute(
                    graph_data=graph_data,
                    execution_id=execution_id,
                    trigger_type="timer",
                    trigger_data=trigger_config,
                )
            )
            logger.info(f"[RuleScheduler] 规则图 {graph_id} 定时执行已触发，execution_id={execution_id}")
        except Exception as e:
            logger.error(f"[RuleScheduler] 定时执行失败 graph_id={graph_id}: {e}")
        finally:
            db.close()

    def add_timer_job(self, graph_id: int, cron_expression: str):
        """添加定时任务。

        Args:
            graph_id: 规则图 ID
            cron_expression: Cron 表达式，如 "0 * * * *"（每整点）
        """
        # 移除旧任务（如果存在）
        self.remove_timer_job(graph_id)

        job_id = f"rule_graph_{graph_id}"

        # 解析 cron 表达式
        parts = cron_expression.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
        else:
            logger.warning(f"[RuleScheduler] 无效的 cron 表达式: {cron_expression}")
            return

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone="Asia/Shanghai",
        )

        self._scheduler.add_job(
            self._execute_graph,
            trigger=trigger,
            args=[graph_id, {"cron": cron_expression}],
            id=job_id,
            replace_existing=True,
        )
        self._job_map[graph_id] = job_id
        logger.info(f"[RuleScheduler] 添加定时任务 graph_id={graph_id} cron={cron_expression}")

    def remove_timer_job(self, graph_id: int):
        """移除定时任务。"""
        job_id = self._job_map.get(graph_id)
        if job_id and self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            del self._job_map[graph_id]
            logger.info(f"[RuleScheduler] 移除定时任务 graph_id={graph_id}")

    def get_active_jobs(self) -> Dict[int, str]:
        """获取所有活跃的定时任务映射。"""
        return dict(self._job_map)


# 全局调度器实例
rule_scheduler = RuleScheduler.get_instance()
