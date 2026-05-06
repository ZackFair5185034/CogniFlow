# -*- coding: utf-8 -*-
"""规则引擎 API 路由 - 提供规则图的 CRUD 和执行接口。"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import (
    RuleGraphCreate,
    RuleGraphUpdate,
    RuleGraphResponse,
    ExecutionTrigger,
    ExecutionResponse,
    ExecutionHistoryResponse,
    NodeDefinition,
)
from backend.services.rule_engine import GraphManager, RuleGraphExecutor
from backend.services.rule_engine.registry import init_builtin_executors

router = APIRouter(prefix="/api/rule-engine", tags=["规则引擎"])


# ============ 节点定义 ============

@router.get("/nodes/definitions", response_model=list[NodeDefinition])
async def get_node_definitions():
    """获取所有可用节点定义 - 用于前端渲染节点面板。"""
    registry = init_builtin_executors()
    return registry.get_definitions()


# ============ 规则图 CRUD ============

@router.post("/graphs", response_model=RuleGraphResponse)
async def create_graph(graph: RuleGraphCreate, db: Session = Depends(get_db)):
    """创建新规则图。"""
    manager = GraphManager(db)
    new_graph = manager.create_graph(
        name=graph.name,
        description=graph.description,
        nodes_json=graph.nodes_json,
        edges_json=graph.edges_json,
        variables_json=graph.variables_json,
        version=graph.version,
    )
    return new_graph


@router.get("/graphs", response_model=list[RuleGraphResponse])
async def list_graphs(db: Session = Depends(get_db)):
    """获取所有规则图列表。"""
    manager = GraphManager(db)
    return manager.get_all_graphs()


@router.get("/graphs/{graph_id}", response_model=RuleGraphResponse)
async def get_graph(graph_id: int, db: Session = Depends(get_db)):
    """获取指定规则图。"""
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")
    return graph


@router.get("/graphs/{graph_id}/detail")
async def get_graph_detail(graph_id: int, db: Session = Depends(get_db)):
    """获取规则图详情（包含解析后的节点和边数据）。"""
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")
    return manager.parse_graph_data(graph)


@router.patch("/graphs/{graph_id}/thumbnail", response_model=RuleGraphResponse)
async def update_graph_thumbnail(
    graph_id: int,
    thumbnail: str,
    db: Session = Depends(get_db),
):
    """更新规则图缩略图。"""
    manager = GraphManager(db)
    existing = manager.get_graph(graph_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="规则图不存在")
    updated_graph = manager.update_graph(graph_id=graph_id, thumbnail=thumbnail)
    return updated_graph


@router.put("/graphs/{graph_id}", response_model=RuleGraphResponse)
async def update_graph(
    graph_id: int,
    graph_update: RuleGraphUpdate,
    db: Session = Depends(get_db),
):
    """更新规则图。"""
    manager = GraphManager(db)

    # 检查是否存在
    existing = manager.get_graph(graph_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    updated_graph = manager.update_graph(
        graph_id=graph_id,
        name=graph_update.name,
        description=graph_update.description,
        nodes_json=graph_update.nodes_json,
        edges_json=graph_update.edges_json,
        variables_json=graph_update.variables_json,
        is_active=graph_update.is_active,
        thumbnail=graph_update.thumbnail,
    )
    return updated_graph


@router.delete("/graphs/{graph_id}")
async def delete_graph(graph_id: int, db: Session = Depends(get_db)):
    """删除规则图。"""
    manager = GraphManager(db)
    success = manager.delete_graph(graph_id)
    if not success:
        raise HTTPException(status_code=404, detail="规则图不存在")
    return {"message": "规则图已删除"}


@router.post("/graphs/{graph_id}/validate")
async def validate_graph(graph_id: int, db: Session = Depends(get_db)):
    """验证规则图的完整性。"""
    manager = GraphManager(db)
    is_valid, error_message = manager.validate_graph(graph_id)
    return {
        "valid": is_valid,
        "error": error_message,
    }


@router.post("/graphs/{graph_id}/activate", response_model=RuleGraphResponse)
async def activate_graph(graph_id: int, db: Session = Depends(get_db)):
    """激活规则图，并注册定时任务（如有 Cron 表达式）。"""
    manager = GraphManager(db)

    # 验证图的有效性
    is_valid, error_message = manager.validate_graph(graph_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"规则图验证失败: {error_message}")

    # 激活图
    updated_graph = manager.update_graph(graph_id=graph_id, is_active=True)

    # 注册定时任务
    from backend.services.rule_engine.scheduler import rule_scheduler
    graph = manager.get_graph(graph_id)
    if graph and graph.cron_expression:
        rule_scheduler.add_timer_job(graph_id, graph.cron_expression)
    elif graph and not graph.cron_expression:
        # 无 Cron 表达式则只移除旧任务
        rule_scheduler.remove_timer_job(graph_id)

    return updated_graph


@router.post("/graphs/{graph_id}/deactivate", response_model=RuleGraphResponse)
async def deactivate_graph(graph_id: int, db: Session = Depends(get_db)):
    """停用规则图，并移除定时任务。"""
    manager = GraphManager(db)
    updated_graph = manager.update_graph(graph_id=graph_id, is_active=False)

    # 移除定时任务
    from backend.services.rule_engine.scheduler import rule_scheduler
    rule_scheduler.remove_timer_job(graph_id)

    return updated_graph


# ============ 执行相关 ============

@router.get("/graphs/{graph_id}/webhook-url")
async def get_webhook_url(graph_id: int):
    """获取规则的 Webhook 触发 URL。

    外部系统可通过 POST 此 URL 触发规则执行。
    """
    # 实际 URL 由反向代理配置，这里只返回路径格式
    return {
        "webhook_url": f"/api/rule-engine/webhook/{graph_id}/trigger",
        "method": "POST",
        "description": "向此 URL 发送 POST 请求即可触发规则执行"
    }


@router.post("/webhook/{graph_id}/trigger", response_model=ExecutionResponse)
async def webhook_trigger(
    graph_id: int,
    background_tasks: BackgroundTasks,
    request_data: dict = None,
    db: Session = Depends(get_db),
):
    """Webhook 触发规则图执行。

    外部系统（如 GitHub CI、其他服务）可通过此端点触发规则。
    支持传递 JSON 数据作为 trigger_data。
    """
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    if not graph.is_active:
        raise HTTPException(status_code=403, detail="规则图未激活，无法通过 Webhook 触发")

    graph_data = manager.parse_graph_data(graph)

    # 传递请求数据到触发器节点
    trigger_data = request_data or {}

    executor = RuleGraphExecutor(db)
    execution_id = executor.create_execution_record(
        graph_id=graph_id,
        trigger_type="webhook",
        trigger_data=trigger_data,
    )

    from backend.services.rule_engine.websocket_manager import rule_ws_manager

    async def run_execution():
        ex = RuleGraphExecutor(db, ws_manager=rule_ws_manager)
        await ex.execute(
            graph_data=graph_data,
            execution_id=execution_id,
            trigger_type="webhook",
            trigger_data=trigger_data,
        )

    background_tasks.add_task(run_execution)

    return ExecutionResponse(
        execution_id=execution_id or 0,
        status="running",
        result={"message": "Webhook 触发执行已启动", "trigger_data": trigger_data},
    )


@router.post("/execute", response_model=ExecutionResponse)
async def execute_graph(
    trigger: ExecutionTrigger,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手动触发规则图执行。

    立即返回 execution_id，执行在后台异步进行，通过 WebSocket 推送进度。
    """
    manager = GraphManager(db)

    # 获取规则图
    graph = manager.get_graph(trigger.graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    # 解析图数据
    graph_data = manager.parse_graph_data(graph)

    # 创建执行记录（同步，拿到 execution_id）
    executor = RuleGraphExecutor(db)
    execution_id = executor.create_execution_record(
        graph_id=trigger.graph_id,
        trigger_type=trigger.trigger_type,
        trigger_data=trigger.trigger_data,
    )

    # 在后台异步执行，传入 rule_ws_manager
    from backend.services.rule_engine.websocket_manager import rule_ws_manager

    async def run_execution():
        ex = RuleGraphExecutor(db, ws_manager=rule_ws_manager)
        result = await ex.execute(
            graph_data=graph_data,
            execution_id=execution_id,
            trigger_type=trigger.trigger_type,
            trigger_data=trigger.trigger_data,
        )
        return result

    background_tasks.add_task(run_execution)

    # 立即返回，前端通过 WebSocket 订阅进度
    return ExecutionResponse(
        execution_id=execution_id or 0,
        status="running",
        result={"message": "执行已启动，请通过 WebSocket 订阅进度"},
    )


@router.get("/executions", response_model=list[ExecutionHistoryResponse])
async def list_executions(
    graph_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取执行历史列表。"""
    from backend.database import ExecutionHistory

    query = db.query(ExecutionHistory)
    if graph_id is not None:
        query = query.filter(ExecutionHistory.graph_id == graph_id)

    executions = query.order_by(ExecutionHistory.start_time.desc()).limit(limit).all()
    return executions


@router.get("/executions/{execution_id}", response_model=ExecutionHistoryResponse)
async def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """获取指定执行记录详情。"""
    from backend.database import ExecutionHistory

    execution = db.query(ExecutionHistory).filter(
        ExecutionHistory.id == execution_id
    ).first()

    if execution is None:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    return execution


@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(execution_id: int, db: Session = Depends(get_db)):
    """获取执行日志详情。"""
    from backend.database import ExecutionHistory, NodeExecutionLog

    # 获取执行记录
    execution = db.query(ExecutionHistory).filter(
        ExecutionHistory.id == execution_id
    ).first()

    if execution is None:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 获取节点执行日志
    node_logs = db.query(NodeExecutionLog).filter(
        NodeExecutionLog.execution_id == execution_id
    ).order_by(NodeExecutionLog.start_time).all()

    return {
        "execution": execution,
        "node_logs": [
            {
                "node_id": log.node_id,
                "node_type": log.node_type,
                "status": log.status,
                "input_data": log.input_data_json,
                "output_data": log.output_data_json,
                "error_message": log.error_message,
                "start_time": log.start_time,
                "end_time": log.end_time,
            }
            for log in node_logs
        ],
    }
