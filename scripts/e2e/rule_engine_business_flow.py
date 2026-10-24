# -*- coding: utf-8 -*-
"""端到端业务闭环验收脚本。

在**隔离环境**中构建一条真实可跑的规则链并执行, 校验:
  1. execution_history 新增记录且状态真实;
  2. node_execution_log 每个节点一条;
  3. 动作节点真的拿到了上游数据(不是 None);
  4. 顶层 failed_nodes 为空;
  5. 动作层可达 —— 触发器 -> 分支 -> 动作 的边能通过端口类型校验。

链路口径(按真实节点端口定义, 2026-10-24 实测):
  manual_trigger.triggered (BOOLEAN)  -> branch.condition  (BOOLEAN)   ✓
  branch.true                (CONTROL) -> log_action.trigger (TRIGGER)  ✓
  branch.false               (CONTROL) -> wait_action.trigger (TRIGGER) ✓

这两条边正是旧前端 4 条兼容规则会拒绝的组合(BOOLEAN→TRIGGER、CONTROL→TRIGGER),
VueFlow 会在 isValidConnection 阶段把边静默丢弃 —— 动作层因此事实上不可达。
统一矩阵 + 共享矩阵校验修复后, 这条链真正跑得通。

用法(必须用隔离 DATA_DIR, 严禁指向生产数据目录):
    $env:DATA_DIR="$env:TEMP\\cf_e2e\\data"
    $env:PYTHONPATH="."
    .\\.venv\\Scripts\\python.exe scripts\\e2e\\rule_engine_business_flow.py

退出码 0 表示业务闭环成立。
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# 必须在导入 backend 之前设置隔离的 DATA_DIR
_TMP_DATA_DIR = Path(tempfile.gettempdir()) / "cf_e2e" / "data"
os.environ.setdefault("DATA_DIR", str(_TMP_DATA_DIR))
_TMP_DATA_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database import (  # noqa: E402
    ExecutionHistory,
    NodeExecutionLog,
    SessionLocal,
    init_db,
)
from backend.services.rule_engine.executor import RuleGraphExecutor  # noqa: E402
from backend.services.rule_engine.registry import init_builtin_executors  # noqa: E402


def build_graph() -> dict:
    """构造一条最小可跑通的业务链: 触发器 -> 分支 -> 动作。"""
    return {
        "nodes": {
            "n_trigger": {
                "id": "n_trigger",
                "type": "manual_trigger",
                "data": {"type": "manual_trigger", "connections": {}},
            },
            "n_branch": {
                "id": "n_branch",
                "type": "branch",
                "data": {"type": "branch", "connections": {}},
            },
            "n_log": {
                "id": "n_log",
                "type": "log_action",
                "data": {
                    "type": "log_action",
                    "config": {"message": "条件成立"},
                    "connections": {},
                },
            },
            "n_wait": {
                "id": "n_wait",
                "type": "wait_action",
                "data": {
                    "type": "wait_action",
                    "config": {"duration": 0.1},
                    "connections": {},
                },
            },
        },
        "edges": [
            {"source": "n_trigger", "target": "n_branch",
             "source_handle": "triggered", "target_handle": "condition"},
            {"source": "n_branch", "target": "n_log",
             "source_handle": "true", "target_handle": "trigger"},
            {"source": "n_branch", "target": "n_wait",
             "source_handle": "false", "target_handle": "trigger"},
        ],
        "variables": {},
    }


async def run_flow(execution_id: int, db) -> dict:
    """执行一次规则图, 返回执行结果。

    必须传入 db: 否则执行器不会写 node_execution_log, 也不会更新执行记录状态。
    """
    executor = RuleGraphExecutor(db)
    return await executor.execute(
        graph_data=build_graph(),
        execution_id=execution_id,
        trigger_type="manual",
        trigger_data={},
    )


def main() -> int:
    """执行验收并打印结论。"""
    init_db()
    init_builtin_executors()

    db = SessionLocal()
    executor = RuleGraphExecutor(db)
    execution_id = executor.create_execution_record(
        graph_id=0, trigger_type="manual", trigger_data={}
    )

    result = asyncio.run(run_flow(execution_id, db))

    record = db.query(ExecutionHistory).filter(
        ExecutionHistory.id == execution_id
    ).first()
    logs = db.query(NodeExecutionLog).filter(
        NodeExecutionLog.execution_id == execution_id
    ).all()

    print("=" * 60)
    print("执行结果:", json.dumps(
        {k: v for k, v in result.items() if k != "node_results"},
        ensure_ascii=False, default=str,
    ))
    print("执行记录状态:", record.status if record else "<无记录>")
    print("节点执行日志条数:", len(logs))
    for log in logs:
        print(f"  - {log.node_id} ({log.node_type}): {log.status}")
    print("=" * 60)

    problems = []
    if record is None:
        problems.append("没有生成 execution_history 记录")
    elif record.status != "completed":
        problems.append(f"执行记录状态不是 completed: {record.status}")
    if len(logs) < 3:
        problems.append(f"节点执行日志只有 {len(logs)} 条, 期望 >= 3")
    if result.get("failed_nodes"):
        problems.append(f"存在失败节点: {result['failed_nodes']}")

    node_results = result.get("node_results") or {}
    node_status = (result.get("summary") or {}).get("node_status") or {}

    # 断言 1: 触发器 -> 分支 的数据流真的通了。
    # branch 的 condition 只能来自 manual_trigger.triggered 的输出;
    # 拿不到上游数据时 inputs.get("condition", False) 恒为 False, 分支会走 false。
    branch_out = node_results.get("n_branch") or {}
    if branch_out.get("condition_result") is not True:
        problems.append(
            f"触发器->分支 数据流未通: condition_result={branch_out.get('condition_result')}"
        )

    # 断言 2: 分支 -> 动作 的数据流通了, 动作层真的可达并执行。
    # branch.true (CONTROL) -> log_action.trigger (TRIGGER) 这条边
    # 在旧前端 4 条兼容规则下会被 VueFlow 静默丢弃, 动作层事实上不可达。
    log_out = node_results.get("n_log") or {}
    if not log_out:
        problems.append("动作节点 n_log 没有产生输出(动作层不可达)")
    elif log_out.get("logged") is not True:
        problems.append(f"动作节点 n_log 执行异常: {log_out}")

    # 断言 3: 分支的另一条路应当被跳过(分支语义正确)
    if node_status.get("n_wait") not in (None, "skipped"):
        problems.append(f"未走到的分支不该执行: n_wait={node_status.get('n_wait')}")

    db.close()

    if problems:
        print("验收失败:")
        for p in problems:
            print("  X", p)
        return 1

    print("业务闭环成立")
    return 0


if __name__ == "__main__":
    sys.exit(main())
