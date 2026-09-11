# -*- coding: utf-8 -*-
"""规则图 schema 迁移框架 - P0-B (2026-09-11)。

当图 JSON 结构发生不兼容变更时, 注册迁移函数将旧版数据升级到新版本。
所有迁移失败均为 soft warn (不抛异常), 保留原数据 + 不升级 schema_version,
避免破坏现有规则图。

设计要点:
- 单调迁移链: from_version → to_version (按字典序升序, 通常步长 1)
- 每步迁移函数签名: (nodes, edges, variables) -> (new_nodes, new_edges, new_variables)
- 当前版本由 CURRENT_SCHEMA_VERSION 声明, 与 RuleGraph.schema_version 字段对齐
"""
import logging
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

# 当前 schema 版本号, 与 RuleGraph.schema_version 字段对齐。
# 每次新增不兼容变更时:
#   1. CURRENT_SCHEMA_VERSION += 1
#   2. 注册迁移: @register_migration(prev_v, CURRENT_SCHEMA_VERSION)
CURRENT_SCHEMA_VERSION = 1


class MigrationError(Exception):
    """迁移链不完整 (缺少 from_v -> to_v 的注册迁移函数)。"""
    pass


# 迁移函数注册表: (from_v, to_v) -> callable
_MIGRATIONS: Dict[Tuple[int, int], Callable[[List[dict], List[dict], Dict[str, Any]], Tuple[List[dict], List[dict], Dict[str, Any]]]] = {}


def register_migration(from_v: int, to_v: int):
    """装饰器: 注册从 from_v 到 to_v 的迁移函数。

    使用示例:
        @register_migration(1, 2)
        def _migrate_v1_to_v2(nodes, edges, variables):
            # 在此转换 nodes/edges/variables 结构
            return nodes, edges, variables
    """
    def decorator(func):
        if (from_v, to_v) in _MIGRATIONS:
            logger.warning("迁移 %d -> %d 已被覆盖", from_v, to_v)
        _MIGRATIONS[(from_v, to_v)] = func
        return func
    return decorator


def migrate_graph_data(
    nodes: List[dict],
    edges: List[dict],
    variables: Dict[str, Any],
    from_version: int,
) -> Tuple[List[dict], List[dict], Dict[str, Any], int]:
    """按注册表顺序应用迁移, 沿 from_version 链式升级直到达到 CURRENT_SCHEMA_VERSION。

    语义说明:
    - 若 from_version >= CURRENT_SCHEMA_VERSION, 不做迁移, 原样返回。
    - 若 from_version < CURRENT_SCHEMA_VERSION, 沿注册链迁移直到达到 CURRENT。
      中间步骤缺失则抛 MigrationError (由调用方 try/except 做 soft warn)。

    Args:
        nodes: 当前图的节点列表
        edges: 当前图的边列表
        variables: 当前图的变量字典
        from_version: 当前图的 schema_version

    Returns:
        (new_nodes, new_edges, new_variables, new_version) - 升级后的数据与最新版本号。
        若 from_version 已达注册链顶端, 原样返回。

    Raises:
        MigrationError: 中间迁移步骤缺失, 无法达到 CURRENT_SCHEMA_VERSION
    """
    current_nodes = list(nodes) if nodes else []
    current_edges = list(edges) if edges else []
    current_vars = dict(variables) if variables else {}
    current_v = from_version

    # 已等于或高于当前版本, 无需迁移
    if current_v >= CURRENT_SCHEMA_VERSION:
        return current_nodes, current_edges, current_vars, current_v

    # 沿注册链迁移, 直到达到 CURRENT_SCHEMA_VERSION
    while current_v < CURRENT_SCHEMA_VERSION:
        target_v = current_v + 1
        key = (current_v, target_v)
        migrator = _MIGRATIONS.get(key)
        if migrator is None:
            raise MigrationError(
                f"未找到迁移函数 {current_v} -> {target_v}，"
                f"请注册 @register_migration({current_v}, {target_v})"
            )
        logger.info("应用规则图迁移 %d -> %d", current_v, target_v)
        current_nodes, current_edges, current_vars = migrator(
            current_nodes, current_edges, current_vars
        )
        current_v = target_v

    return current_nodes, current_edges, current_vars, current_v


def ensure_rule_graph_schema_column() -> bool:
    """启动期幂等地为 rule_graph 表补齐 schema_version 列。

    Returns:
        是否实际执行了 ALTER TABLE (False 表示列已存在或表尚未创建)
    """
    try:
        from sqlalchemy import inspect, text
        from backend.database import engine
    except Exception as e:
        logger.warning("ensure_rule_graph_schema_column 跳过: %s", e)
        return False

    inspector = inspect(engine)
    if "rule_graph" not in inspector.get_table_names():
        return False

    columns = {c["name"] for c in inspector.get_columns("rule_graph")}
    if "schema_version" in columns:
        return False

    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE rule_graph ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1"
        ))
    logger.info("已为 rule_graph 表添加 schema_version 列 (默认 1)")
    return True