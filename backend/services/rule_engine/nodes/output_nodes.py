# -*- coding: utf-8 -*-
"""输出类节点 - 结果输出节点。

按 Phase 1 设计文档实现：
docs/research/rule-engine-phase1-node-registry.md

节点分类: output (#FF4C4C)
"""
import json
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from backend.services.rule_engine.models import NodeDefinition, NodeCategory, PortDefinition, PortType
from .base import BaseExecutor


class SaveResultNode(BaseExecutor):
    """保存结果节点 - 将结果保存到文件或数据库。

    配置项:
        output_path: str - 输出文件路径
        format: str - 保存格式 (json/csv/image)
    """

    node_type = "save_result"
    category = NodeCategory.OUTPUT
    display_name = "保存结果"
    description = "将执行结果保存到文件"
    icon = "save"
    color = "#FF4C4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "data": PortDefinition(
                    name="数据",
                    type="ANY",
                    required=True,
                    description="要保存的数据"
                ),
            },
            outputs={
                "success": PortDefinition(
                    name="成功",
                    type="BOOLEAN",
                    description="是否保存成功"
                ),
                "path": PortDefinition(
                    name="文件路径",
                    type="STRING",
                    description="保存的文件路径"
                ),
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        import os

        params = self.config.get("params", {})
        output_path = params.get("output_path", "/tmp/rule_result.json")
        file_format = params.get("format", "json")

        data = inputs.get("data", {})

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path) or "/tmp", exist_ok=True)

            if file_format == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            elif file_format == "csv":
                # 简单 CSV 保存
                import csv
                if isinstance(data, list) and data:
                    with open(output_path, "w", encoding="utf-8", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                else:
                    return {"success": False, "path": "", "error": "CSV 格式需要列表数据"}
            else:
                return {"success": False, "path": "", "error": f"不支持的格式: {file_format}"}

            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "path": "", "error": str(e)}


class NotificationNode(BaseExecutor):
    """通知节点 - 发送通知。

    配置项:
        notification_type: str - 通知类型 (email/sms/webhook/console)
        recipients: list[str] - 接收者列表
        message: str - 通知内容
    """

    node_type = "notification"
    category = NodeCategory.OUTPUT
    display_name = "发送通知"
    description = "发送通知消息"
    icon = "bell"
    color = "#FF4C4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "sent": PortDefinition(
                    name="已发送",
                    type="BOOLEAN",
                    description="是否发送成功"
                ),
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        notification_type = params.get("notification_type", "console")
        recipients = params.get("recipients", [])
        message_template = params.get("message", "规则执行完成")

        # 模板变量替换
        try:
            message = message_template.format(**context.variables)
        except (KeyError, ValueError):
            message = message_template

        if notification_type == "console":
            print(f"[Notification] {message}")
            return {"sent": True, "message": message}
        elif notification_type == "webhook":
            # 发送 webhook
            import httpx
            webhook_url = recipients[0] if recipients else None
            if webhook_url:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(webhook_url, json={"message": message})
                        return {"sent": response.status_code == 200, "message": message}
                except Exception as e:
                    return {"sent": False, "message": message, "error": str(e)}
        # TODO: email, sms 等其他通知类型

        return {"sent": False, "error": f"不支持的通知类型: {notification_type}"}


class DisplayNode(BaseExecutor):
    """显示节点 - 在界面上显示结果（调试用）。

    配置项:
        title: str - 显示标题
    """

    node_type = "display"
    category = NodeCategory.OUTPUT
    display_name = "显示结果"
    description = "显示节点执行结果（调试用）"
    icon = "eye"
    color = "#FF4C4C"

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "data": PortDefinition(
                    name="数据",
                    type="ANY",
                    required=True,
                    description="要显示的数据"
                ),
            },
            outputs={
                "displayed": PortDefinition(
                    name="已显示",
                    type="BOOLEAN",
                    description="是否显示成功"
                ),
            }
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        data = inputs.get("data", {})

        # 打印到日志
        import logging
        logger = logging.getLogger("rule_engine")
        logger.info(f"[Display] {json.dumps(data, indent=2, default=str)[:500]}")

        return {"displayed": True, "data": data}
