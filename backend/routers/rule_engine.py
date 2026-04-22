# -*- coding: utf-8 -*-
"""规则引擎 API 路由 - 提供规则图的 CRUD 和执行接口。"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    RuleGraphCreate,
    RuleGraphUpdate,
    RuleGraphResponse,
    ExecutionTrigger,
    ExecutionResponse,
    ExecutionHistoryResponse,
    NodeDefinition,
)
from services.rule_engine import GraphManager, RuleGraphExecutor
from services.rule_engine.registry import init_builtin_executors

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
    """激活规则图。"""
    manager = GraphManager(db)

    # 验证图的有效性
    is_valid, error_message = manager.validate_graph(graph_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"规则图验证失败: {error_message}")

    # 激活图
    updated_graph = manager.update_graph(graph_id=graph_id, is_active=True)
    return updated_graph


@router.post("/graphs/{graph_id}/deactivate", response_model=RuleGraphResponse)
async def deactivate_graph(graph_id: int, db: Session = Depends(get_db)):
    """停用规则图。"""
    manager = GraphManager(db)
    updated_graph = manager.update_graph(graph_id=graph_id, is_active=False)
    return updated_graph


# ============ 执行相关 ============

@router.post("/execute", response_model=ExecutionResponse)
async def execute_graph(
    trigger: ExecutionTrigger,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手动触发规则图执行。"""
    manager = GraphManager(db)

    # 获取规则图
    graph = manager.get_graph(trigger.graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="规则图不存在")

    # 解析图数据
    graph_data = manager.parse_graph_data(graph)

    # 创建执行记录
    executor = RuleGraphExecutor(db)
    execution_id = executor.create_execution_record(
        graph_id=trigger.graph_id,
        trigger_type=trigger.trigger_type,
        trigger_data=trigger.trigger_data,
    )

    # 在后台执行
    async def run_execution():
        result = await executor.execute(
            graph_data=graph_data,
            execution_id=execution_id,
            trigger_type=trigger.trigger_type,
            trigger_data=trigger.trigger_data,
        )
        return result

    # 执行并返回结果
    result = await run_execution()

    return ExecutionResponse(
        execution_id=execution_id or 0,
        status=result["status"],
        result=result,
    )


@router.get("/executions", response_model=list[ExecutionHistoryResponse])
async def list_executions(
    graph_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取执行历史列表。"""
    from database import ExecutionHistory

    query = db.query(ExecutionHistory)
    if graph_id is not None:
        query = query.filter(ExecutionHistory.graph_id == graph_id)

    executions = query.order_by(ExecutionHistory.start_time.desc()).limit(limit).all()
    return executions


@router.get("/executions/{execution_id}", response_model=ExecutionHistoryResponse)
async def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """获取指定执行记录详情。"""
    from database import ExecutionHistory

    execution = db.query(ExecutionHistory).filter(
        ExecutionHistory.id == execution_id
    ).first()

    if execution is None:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    return execution


@router.get("/executions/{execution_id}/logs")
async def get_execution_logs(execution_id: int, db: Session = Depends(get_db)):
    """获取执行日志详情。"""
    from database import ExecutionHistory, NodeExecutionLog

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
