# -*- coding: utf-8 -*-
"""规则引擎 API 路由 - 提供规则图的 CRUD 和执行接口。"""
import secrets
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
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

@router.get("/nodes/definitions")
async def get_node_definitions():
    """获取所有可用节点定义 - 用于前端渲染节点面板。"""
    import traceback, sys
    try:
        registry = init_builtin_executors()
        return registry.get_definitions()
    except Exception as e:
        traceback.print_exc()
        # 返回 500 错误及详情
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


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
    # P0-A: update_graph 现返回 (graph, warnings), 解构时给空列表兜底
    updated_graph, _warnings = manager.update_graph(graph_id=graph_id, thumbnail=thumbnail)
    return updated_graph


@router.put("/graphs/{graph_id}", response_model=RuleGraphResponse)
async def update_graph(
    graph_id: int,
    graph_update: RuleGraphUpdate,
    db: Session = Depends(get_db),
):
    """更新规则图。

    P0-A: 响应头 X-Config-Warnings 携带保存期配置校验警告列表 (逗号分隔)。
    """
    manager = GraphManager(db)

    # 检查是否存在
    existing = manager.get_graph(graph_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    # P0-A: update_graph 现返回 (graph, warnings), 警告透传响应头供前端展示
    updated_graph, warnings = manager.update_graph(
        graph_id=graph_id,
        name=graph_update.name,
        description=graph_update.description,
        nodes_json=graph_update.nodes_json,
        edges_json=graph_update.edges_json,
        variables_json=graph_update.variables_json,
        is_active=graph_update.is_active,
        thumbnail=graph_update.thumbnail,
    )
    if warnings:
        # 用 JSON 响应体透传警告 (前端可解析), 同时放响应头 (兼容旧客户端)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content={
                **(_graph_to_dict(updated_graph) if updated_graph else {}),
                "warnings": warnings,
            },
            headers={"X-Config-Warnings": ",".join(warnings)},
        )
    return updated_graph


def _graph_to_dict(graph):
    """RuleGraph ORM -> 响应 dict, 用于包裹 warnings 字段。"""
    return {
        "id": graph.id,
        "name": graph.name,
        "description": graph.description,
        "nodes_json": graph.nodes_json,
        "edges_json": graph.edges_json,
        "variables_json": graph.variables_json,
        "version": graph.version,
        "is_active": graph.is_active,
        "cron_expression": graph.cron_expression,
        "thumbnail": graph.thumbnail,
        "schema_version": getattr(graph, "schema_version", None),
        "created_at": graph.created_at,
        "updated_at": graph.updated_at,
    }


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
    updated_graph, _warnings = manager.update_graph(graph_id=graph_id, is_active=True)

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
    updated_graph, _warnings = manager.update_graph(graph_id=graph_id, is_active=False)

    # 移除定时任务
    from backend.services.rule_engine.scheduler import rule_scheduler
    rule_scheduler.remove_timer_job(graph_id)

    return updated_graph


# ============ 执行相关 ============

@router.get("/graphs/{graph_id}/webhook-url")
async def get_webhook_url(graph_id: int, db: Session = Depends(get_db)):
    """获取规则的 Webhook 触发 URL 和认证信息。

    外部系统可通过 POST 此 URL 触发规则执行。
    """
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    # 检查是否配置了 API Key
    has_api_key = bool(graph.webhook_api_key)

    return {
        "webhook_url": f"/api/rule-engine/webhook/{graph_id}/trigger",
        "method": "POST",
        "auth_type": "api_key" if has_api_key else "none",
        "has_api_key": has_api_key,
        "description": "向此 URL 发送 POST 请求即可触发规则执行，认证通过 X-API-Key header 提供"
    }


@router.post("/graphs/{graph_id}/webhook-api-key")
async def generate_webhook_api_key(graph_id: int, db: Session = Depends(get_db)):
    """为规则图生成或更新 Webhook API Key。

    返回完整的 API Key（仅此一次可见，请妥善保管）。
    """
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    # 生成新的 API Key（32字节十六进制字符串，64字符）
    new_api_key = secrets.token_hex(32)
    graph.webhook_api_key = new_api_key
    db.commit()

    return {
        "graph_id": graph_id,
        "webhook_api_key": new_api_key,
        "warning": "请妥善保管此 API Key，刷新页面后将不再显示",
        "usage": "在请求时通过 X-API-Key header 提供此 Key"
    }


@router.delete("/graphs/{graph_id}/webhook-api-key")
async def delete_webhook_api_key(graph_id: int, db: Session = Depends(get_db)):
    """删除规则图的 Webhook API Key（禁用 Webhook 认证）。"""
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    graph.webhook_api_key = None
    db.commit()

    return {"message": "Webhook API Key 已删除，此规则的 Webhook 认证已被禁用"}


@router.post("/webhook/{graph_id}/trigger", response_model=ExecutionResponse)
async def webhook_trigger(
    graph_id: int,
    background_tasks: BackgroundTasks,
    request_data: dict = None,
    x_api_key: Optional[str] = Header(None, description="Webhook API Key 认证"),
    db: Session = Depends(get_db),
):
    """Webhook 触发规则图执行。

    外部系统（如 GitHub CI、其他服务）可通过此端点触发规则。
    支持传递 JSON 数据作为 trigger_data。
    需要通过 X-API-Key header 提供 API Key 进行认证。
    """
    manager = GraphManager(db)
    graph = manager.get_graph(graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    if not graph.is_active:
        raise HTTPException(status_code=403, detail="规则图未激活，无法通过 Webhook 触发")

    # API Key 认证校验
    if graph.webhook_api_key:
        # 如果规则图配置了 API Key，必须提供且匹配
        if not x_api_key:
            raise HTTPException(
                status_code=401,
                detail="缺少 API Key，请通过 X-API-Key header 提供有效的认证信息"
            )
        if not secrets.compare_digest(x_api_key, graph.webhook_api_key):
            raise HTTPException(status_code=401, detail="无效的 API Key")
    else:
        # 如果规则图未配置 API Key，拒绝所有请求（安全默认）
        raise HTTPException(
            status_code=401,
            detail="此规则图未配置 Webhook 认证，请先设置 API Key"
        )

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
        # Phase 19.1: 异常处理 — execution 状态永远从 pending 转走
        # 之前 background_tasks 吞异常, execution record 卡 pending
        from backend.services.rule_engine.executor import RuleGraphExecutor
        from backend.services.rule_engine.exceptions import ValidationError, ExecutorError, CycleError
        from backend.database import ExecutionHistory
        from sqlalchemy.orm import Session
        import traceback
        ex = RuleGraphExecutor(db, ws_manager=rule_ws_manager)
        try:
            result = await ex.execute(
                graph_data=graph_data,
                execution_id=execution_id,
                trigger_type=trigger.trigger_type,
                trigger_data=trigger.trigger_data,
            )
            return result
        except (ValidationError, ExecutorError, CycleError) as e:
            # 业务异常: 标记 failed
            try:
                rec = db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
                if rec:
                    rec.status = "failed"
                    rec.end_time = datetime.now()
                    rec.error = str(e)
                    db.commit()
            except Exception:
                db.rollback()
            return {"status": "failed", "error": str(e)}
        except Exception as e:
            # 未知异常: 同样标记 failed, 保留 traceback 给日志
            tb = traceback.format_exc()
            try:
                rec = db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
                if rec:
                    rec.status = "failed"
                    rec.end_time = datetime.now()
                    rec.error = f"{type(e).__name__}: {str(e)}\n{tb[:500]}"
                    db.commit()
            except Exception:
                db.rollback()
            return {"status": "failed", "error": str(e)}

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
    """获取执行日志详情。

    返回 List[dict]，每项为一条节点执行日志（按 start_time 升序）。
    执行记录不存在返回 404；执行存在但无节点日志时返回空列表。

    历史：原实现返回 {execution: {...}, node_logs: [...]} 包装对象，
    前端按 list 解析时失败（'str' object has no attribute 'keys'）。
    REST 约定 "X 的日志" 应直接返回日志数组。
    """
    from backend.database import ExecutionHistory, NodeExecutionLog

    # 仅校验执行记录存在（不再返回整个对象，前端不需要）
    execution_exists = db.query(ExecutionHistory.id).filter(
        ExecutionHistory.id == execution_id
    ).first()
    if execution_exists is None:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 获取节点执行日志
    node_logs = db.query(NodeExecutionLog).filter(
        NodeExecutionLog.execution_id == execution_id
    ).order_by(NodeExecutionLog.start_time).all()

    return [
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
    ]


@router.delete("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: int, db: Session = Depends(get_db)):
    """取消正在执行的规则图。

    向执行上下文发送取消请求，执行将尽可能快地停止。
    """
    from backend.database import ExecutionHistory

    # 检查执行记录是否存在
    execution = db.query(ExecutionHistory).filter(
        ExecutionHistory.id == execution_id
    ).first()

    if execution is None:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 调用执行器的取消方法
    success = RuleGraphExecutor.cancel_execution(execution_id)

    if success:
        return {"message": "取消请求已发送", "execution_id": execution_id}
    else:
        raise HTTPException(
            status_code=404,
            detail="执行上下文不存在或已结束，无法取消"
        )
