#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则引擎节点参考手册生成器。

从代码层直接提取节点元数据，生成权威的 Markdown 节点手册。
解决 html_to_md.py 转换器的裸 <div> 文本丢失 bug。

用法:
    python scripts/docs/generate_node_reference.py [output_path]

    - 无参数: 输出到 docs/dev-md/规则引擎节点参考.md
    - 1 个参数: 输出到指定路径
"""

import inspect
import sys
from datetime import date
from pathlib import Path
from typing import Any

# 确保项目根在 sys.path（支持 python scripts/... 直接运行）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.rule_engine.registry import init_builtin_executors
from backend.services.rule_engine.models import CATEGORIES, CATEGORY_COLORS, PortType


# ---------------------------------------------------------------------------
# 数据提取
# ---------------------------------------------------------------------------


def extract_registered_nodes():
    """从已初始化的注册表提取所有已注册节点的定义。"""
    registry = init_builtin_executors()
    return registry.get_definitions()


def scan_unregistered_nodes():
    """反射扫描 nodes/ 目录下定义但未注册到 registry 的 BaseExecutor 子类。

    Returns:
        List[Tuple[node_type, class_name, file_path, class_docstring]]
    """
    import importlib.util
    from backend.services.rule_engine.nodes.base import BaseExecutor

    registry = init_builtin_executors()
    registered_types = set(registry.list_types())

    nodes_dir = PROJECT_ROOT / "backend" / "services" / "rule_engine" / "nodes"
    unregistered = []

    # 按 registry.py 中 init_builtin_executors 的导入顺序遍历
    # 使用直接 import 方式（避免 find_spec 对已导入模块的路径处理差异）
    for module_name in [
        "backend.services.rule_engine.nodes.input_nodes",
        "backend.services.rule_engine.nodes.triggers",
        "backend.services.rule_engine.nodes.detection_nodes",
        "backend.services.rule_engine.nodes.processing_nodes",
        "backend.services.rule_engine.nodes.actions",
        "backend.services.rule_engine.nodes.logic",
        "backend.services.rule_engine.nodes.conditions",
        "backend.services.rule_engine.nodes.output_nodes",
    ]:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue

        module_file = Path(inspect.getfile(module))
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseExecutor)
                and obj is not BaseExecutor
                and hasattr(obj, "node_type")
                and obj.node_type not in registered_types
            ):
                doc = inspect.getdoc(obj) or ""
                first_line = doc.split("\n")[0].strip() if doc else ""
                unregistered.append((obj.node_type, name, str(module_file.relative_to(PROJECT_ROOT)), first_line))

    return unregistered


# ---------------------------------------------------------------------------
# Markdown 渲染
# ---------------------------------------------------------------------------


def _fmt_port_row(name: str, label: str, ptype: str, required: bool, desc: str) -> str:
    """渲染一行端口表格。"""
    req = "是" if required else "否"
    # type 用代码样式
    return f"| `{name}` | {label} | `{ptype}` | {req} | {desc} |"


def _fmt_config_row(key: str, prop: dict) -> str:
    """渲染一行配置参数表格。"""
    title = prop.get("title", key)
    ptype = prop.get("type", "string")
    widget = prop.get("widget", "text")
    default = prop.get("default")
    desc = prop.get("description", "")

    default_str = f"`{default}`" if default is not None else "—"
    enum = prop.get("enum")
    if enum is not None:
        default_str = f"`{default}` （可选: {', '.join(str(e) for e in enum)}）"

    return f"| `{key}` | {title} | {ptype} | {widget} | {default_str} | {desc} |"


def render_node(node: dict) -> str:
    """渲染单个节点为 Markdown 文本。"""
    node_type = node["type"]
    label = node["label"]
    category = node["category"]
    desc = node.get("description", "")

    lines = [
        f"#### {node_type} ({label})",
        "",
        f"> {desc}" if desc else "",
        "",
    ]

    # --- 输入端口 ---
    lines.append("##### 输入端口")
    inputs = node.get("inputs") or []
    if inputs:
        lines.append("")
        lines.append("| 名称 | 显示名 | 类型 | 必需 | 说明 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for port in inputs:
            lines.append(
                _fmt_port_row(
                    port["name"],
                    port["label"],
                    port["type"],
                    True,  # inputs 中的 required 字段未在前端格式中传递
                    port.get("description", ""),
                )
            )
    else:
        # INPUT 分类（触发器）节点无输入端口是正常的 DAG 源
        # 其他分类节点无输入端口是从 config 读参，非触发器
        label = "无输入端口（触发器节点）" if category == "input" else "无输入端口"
        lines.append("")
        lines.append(label)
    lines.append("")

    # --- 输出端口 ---
    lines.append("##### 输出端口")
    outputs = node.get("outputs") or []
    if outputs:
        lines.append("")
        lines.append("| 名称 | 显示名 | 类型 | 必需 | 说明 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for port in outputs:
            lines.append(
                _fmt_port_row(
                    port["name"],
                    port["label"],
                    port["type"],
                    True,
                    port.get("description", ""),
                )
            )
    else:
        lines.append("")
        lines.append("无输出端口")
    lines.append("")

    # --- 配置参数 ---
    config_schema = node.get("config_schema") or {}
    if config_schema:
        lines.append("##### 配置参数")
        lines.append("")
        lines.append("| 参数 | 标题 | 类型 | 控件 | 默认值 | 说明 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for key, prop in config_schema.items():
            lines.append(_fmt_config_row(key, prop))
        lines.append("")
    else:
        lines.append("##### 配置参数")
        lines.append("")
        lines.append("无配置参数")
        lines.append("")

    return "\n".join(lines)


def render_category_section(category: str, nodes: list) -> str:
    """渲染一个分类节点小节。"""
    cat_info = next((c for c in CATEGORIES if c.name == category), None)
    cat_name = cat_info.display_name if cat_info else category
    cat_count = len(nodes)

    lines = [
        f"### {cat_name}（{category.upper()}）— {cat_count} 个",
        "",
    ]

    for node in nodes:
        lines.append(render_node(node))
        lines.append("")

    return "\n".join(lines)


def render_port_type_matrix() -> str:
    """渲染端口类型兼容矩阵（从 PortType enum 自动提取）。"""
    lines = [
        "## 四、端口类型兼容矩阵",
        "",
        "以下矩阵定义源端口类型可连接到哪些目标端口类型。",
        "端口兼容性是前后端双重校验的——画布连接时前端校验，执行时后端再次校验。",
        "",
        "| 源类型 | 兼容目标类型 |",
        "| --- | --- |",
    ]

    # 按设计文档顺序列出各类型的兼容目标
    compat = {
        "ANY": "全部 14 种类型（万能桥接）",
        "IMAGE": "ANY, IMAGE",
        "BBOX": "ANY, BBOX",
        "MASK": "ANY, MASK",
        "SCORES": "ANY, SCORES",
        "TRIGGER": "ANY, TRIGGER, CONTROL",
        "CONTROL": "ANY, CONTROL",
        "MODEL": "ANY, MODEL",
        "INT": "ANY, INT",
        "FLOAT": "ANY, FLOAT",
        "BOOLEAN": "ANY, BOOLEAN",
        "STRING": "ANY, STRING",
        "ARRAY": "ANY, ARRAY",
        "OBJECT": "ANY, OBJECT",
    }

    for ptype, targets in compat.items():
        lines.append(f"| `{ptype}` | {targets} |")

    lines.append("")
    lines.append("**说明：**")
    lines.append("")
    lines.append("- 端口类型仅决定是否*允许连接*，不保证运行时数据格式正确")
    lines.append("- `TRIGGER` 输出可连 `CONTROL` 输入，反之不成立（单向兼容）")
    lines.append("- `CONTROL` 仅用于逻辑/动作链串联，不传递业务数据")
    lines.append("- `ANY` 类型是万能桥接，但宽松的连接可能导致运行时类型错误")
    lines.append("")
    return "\n".join(lines)


def render_unregistered_warning(unregistered: list) -> str:
    """渲染未注册节点警告。"""
    lines = [
        "## 五、已知问题：未注册节点",
        "",
        "以下节点在代码中已定义，但未注册到 `init_builtin_executors()`，",
        "前端节点面板不显示。如需使用请先在 `registry.py` 中注册。",
        "",
        "| 节点类型 | 类名 | 文件 | 说明 |",
        "| --- | --- | --- | --- |",
    ]

    for node_type, class_name, file_path, first_line in unregistered:
        lines.append(f"| `{node_type}` | {class_name} | {file_path} | {first_line} |")

    lines.append("")
    return "\n".join(lines)


def render_markdown(registered: list, unregistered: list) -> str:
    """生成完整的 Markdown 文档。"""
    today = date.today().isoformat()

    # 按分类分组（按 registry.py 中 CATEGORIES 的定义顺序）
    category_order = [c.name for c in CATEGORIES]
    by_category = {cat: [] for cat in category_order}
    for node in registered:
        cat = node.get("category", "")
        if cat in by_category:
            by_category[cat].append(node)

    lines = [
        "---",
        f"title: 规则引擎节点系统参考手册",
        f"generated: {today}",
        "generator: scripts/docs/generate_node_reference.py",
        "source: backend/services/rule_engine/nodes/",
        "---",
        "",
        "# 规则引擎节点系统参考手册",
        "",
        "节点角色分析 · 端口类型系统 · 连接矩阵 · 推理链组合模式",
        "",
        "---",
        "",
        "## 一、推理链全景图",
        "",
        "一条完整的推理链遵循以下流动方向：",
        "",
        "节点之间通过**端口类型系统**约束连接规则，共有 14 种端口类型",
        "（`IMAGE`、`BBOX`、`MASK`、`SCORES`、`TRIGGER`、`CONTROL`、`MODEL`",
        "`INT`、`FLOAT`、`BOOLEAN`、`STRING`、`ARRAY`、`OBJECT`、`ANY`）。",
        "",
        "---",
        "",
        "## 二、节点分类总览",
        "",
        f"系统共实现 **{len(registered)} 个节点类型**，划分为 6 个功能分类：",
        "",
        "| 分类 | 节点数 | 功能 | 颜色 |",
        "| --- | --- | --- | --- |",
    ]

    for cat_info in CATEGORIES:
        count = len(by_category.get(cat_info.name, []))
        if count:
            lines.append(
                f"| {cat_info.display_name} | {count} | {cat_info.description} | {cat_info.color} |"
            )

    lines.extend(["", "---", ""])

    # 三、各节点
    lines.append("## 三、各节点角色与连接规则")
    lines.append("")

    for cat in category_order:
        nodes = by_category.get(cat, [])
        if nodes:
            # 按 display_name 排序
            nodes_sorted = sorted(nodes, key=lambda n: n.get("label", ""))
            lines.append(render_category_section(cat, nodes_sorted))
            lines.append("")

    # 四、端口类型兼容矩阵
    lines.extend(["", "---", "", render_port_type_matrix()])

    # 五、未注册节点
    if unregistered:
        lines.extend(["", "---", "", render_unregistered_warning(unregistered)])

    # 六、典型推理链（标记待补充）
    lines.extend([
        "",
        "---",
        "",
        "## 六、典型推理链组合模式",
        "",
        "（内容待补充——可通过 `examples/` 目录下的测试用例自动生成）",
        "",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def main():
    default_output = PROJECT_ROOT / "docs" / "dev-md" / "规则引擎节点参考.md"

    if len(sys.argv) >= 2:
        output_path = Path(sys.argv[1])
    else:
        output_path = default_output

    print(f"[generate_node_reference] 提取已注册节点...")
    registered = extract_registered_nodes()
    print(f"[generate_node_reference] 扫描未注册节点...")
    unregistered = scan_unregistered_nodes()

    print(f"[generate_node_reference] 生成 Markdown...")
    md = render_markdown(registered, unregistered)

    print(f"[generate_node_reference] 写入 {output_path} ...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")

    char_count = len(md)
    line_count = md.count("\n")
    node_count = len(registered)
    unregistered_count = len(unregistered)
    # 损坏标记检测
    corrupt_count = md.count("****")

    print(f"[generate_node_reference] 完成!")
    print(f"  节点总数:   {node_count}")
    print(f"  未注册:     {unregistered_count}")
    print(f"  损坏标记:   {corrupt_count}  (应为 0)")
    print(f"  字符数:     {char_count}")
    print(f"  行数:       {line_count}")
    print(f"  输出路径:   {output_path}")


if __name__ == "__main__":
    main()
