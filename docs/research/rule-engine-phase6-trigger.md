# Phase 6 技术实现文档：规则触发机制

> ⚠️ **实现前审核状态：** 待老大评审
> 文档版本：v1.0
> 基于调研：canvas-editor-research-2026-05-06.md
> 阶段：Phase 6
> 创建时间：2026-05-06

---

## 1. 阶段目标

**目标：** 实现规则的手动触发、定时触发和 Webhook 触发三种机制。

**验收标准：**
- [ ] 手动触发：点击按钮立即执行规则
- [ ] 定时触发：可配置 Cron 表达式，按计划执行
- [ ] Webhook 触发：提供 Webhook URL，外部请求触发执行
- [ ] 规则列表页面显示各规则的上次执行时间和状态
- [ ] 规则激活/停用切换生效

---

## 2. 触发类型定义

### 2.1 触发器类型

```typescript
// backend/services/rule_engine/models.py

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TriggerType(str, Enum):
    """触发器类型枚举。"""
    MANUAL = "manual"       # 手动触发
    TIMER = "timer"          # 定时触发
    WEBHOOK = "webhook"      # Webhook 触发
    EVENT = "event"          # 事件触发（预留）


class TimerConfig(BaseModel):
    """定时触发配置。"""
    cron: str = Field(..., description="Cron 表达式，如 '0 * * * *'")
    enabled: bool = Field(True, description="是否启用")
    timezone: str = Field("Asia/Shanghai", description="时区")


class WebhookConfig(BaseModel):
    """Webhook 触发配置。"""
    secret: Optional[str] = Field(None, description="签名密钥（可选）")
    enabled: bool = Field(True, description="是否启用")
    # 实际 webhook_id 在 RuleTrigger 中关联


class RuleTrigger(BaseModel):
    """规则触发器配置。"""
    id: int
    rule_id: int
    trigger_type: TriggerType
    config: dict = Field(default_factory=dict)  # TimerConfig 或 WebhookConfig
    enabled: bool = Field(True)
    created_at: datetime
    updated_at: datetime
```

### 2.2 规则激活状态

```python
# backend/models/rule.py

class Rule(BaseModel):
    """规则模型。"""
    id: int
    name: str
    description: Optional[str]
    graph_data: dict  # 规则图的完整数据
    variables: dict    # 规则变量

    # 触发配置
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_config: dict = {}

    # 状态
    is_active: bool = Field(False, description="是否激活")
    last_executed_at: Optional[datetime] = None
    last_execution_status: Optional[str] = None

    # 时间戳
    created_at: datetime
    updated_at: datetime
```

---

## 3. 手动触发

### 3.1 API 接口

```python
# backend/routers/rule_engine.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/rule-engine", tags=["规则引擎"])


class ExecuteRequest(BaseModel):
    """执行请求。"""
    rule_id: int
    trigger_type: str = "manual"
    trigger_data: dict = Field(default_factory=dict)


class ExecuteResponse(BaseModel):
    """执行响应。"""
    execution_id: int
    status: str
    message: str


@router.post("/rules/{rule_id}/execute", response_model=ExecuteResponse)
async def execute_rule(
    rule_id: int,
    request: ExecuteRequest = None
):
    """手动执行规则。

    Args:
        rule_id: 规则 ID
        request: 执行请求（可选）

    Returns:
        执行记录 ID 和状态
    """
    # 获取规则
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    # 创建执行记录
    execution = ExecutionHistory(
        rule_id=rule_id,
        trigger_type="manual",
        trigger_data=request.trigger_data if request else {},
        status="pending"
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # 异步执行（后台任务）
    asyncio.create_task(
        execute_rule_async(execution.id, rule.graph_data)
    )

    return ExecuteResponse(
        execution_id=execution.id,
        status="pending",
        message="规则执行已启动"
    )


async def execute_rule_async(execution_id: int, graph_data: dict):
    """异步执行规则（在后台运行）。"""
    from backend.services.rule_engine.executor import RuleGraphExecutor

    executor = RuleGraphExecutor(db=get_db(), ws_manager=connection_manager)

    try:
        result = await executor.execute(
            graph_data=graph_data,
            execution_id=execution_id,
            trigger_type="manual"
        )

        # 更新规则的最后执行状态
        rule = db.query(Rule).filter(
            Rule.id == result.get("rule_id")
        ).first()
        if rule:
            rule.last_executed_at = datetime.now()
            rule.last_execution_status = result.get("status", "completed")
            db.commit()

    except Exception as e:
        logger.error(f"规则执行失败: {e}")
        raise
```

---

## 4. 定时触发

### 4.1 APScheduler 集成

```python
# backend/services/scheduler.py

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime

from backend.database import get_db
from backend.models.rule import Rule, TriggerType
from backend.services.rule_engine.executor import RuleGraphExecutor
from backend.services.rule_engine.websocket_manager import connection_manager


class RuleScheduler:
    """规则调度器 - 管理所有定时任务的调度。"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={
                'default': MemoryJobStore()
            },
            job_defaults={
                'coalesce': True,  # 合并错过的执行
                'max_instances': 1  # 同一任务最多一个实例
            }
        )
        self._executor = None

    @property
    def executor(self):
        """懒加载执行器。"""
        if self._executor is None:
            self._executor = RuleGraphExecutor(
                db=get_db(),
                ws_manager=connection_manager
            )
        return self._executor

    def start(self):
        """启动调度器。"""
        self.scheduler.start()
        self._load_timer_rules()

    def stop(self):
        """停止调度器。"""
        self.scheduler.shutdown()

    def _load_timer_rules(self):
        """加载所有定时触发的规则。"""
        db = get_db()

        rules = db.query(Rule).filter(
            Rule.is_active == True,
            Rule.trigger_type == TriggerType.TIMER
        ).all()

        for rule in rules:
            self.add_timer_job(rule)

    def add_timer_job(self, rule: Rule):
        """添加定时任务。

        Args:
            rule: 规则对象
        """
        config = rule.trigger_config or {}
        cron_expr = config.get("cron", "0 * * * *")
        timezone = config.get("timezone", "Asia/Shanghai")

        job_id = f"rule_timer_{rule.id}"

        self.scheduler.add_job(
            func=self._execute_rule_job,
            trigger=CronTrigger.from_crontab(cron_expr, timezone=timezone),
            id=job_id,
            args=[rule.id],
            replace_existing=True
        )

        logger.info(f"添加定时任务: rule={rule.name}, cron={cron_expr}")

    def remove_timer_job(self, rule_id: int):
        """移除定时任务。"""
        job_id = f"rule_timer_{rule_id}"
        self.scheduler.remove_job(job_id)
        logger.info(f"移除定时任务: rule_id={rule_id}")

    async def _execute_rule_job(self, rule_id: int):
        """定时执行规则的后台任务。"""
        db = get_db()

        rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if not rule or not rule.is_active:
            return

        # 创建执行记录
        execution = ExecutionHistory(
            rule_id=rule_id,
            trigger_type="timer",
            trigger_data={"scheduled_at": datetime.now().isoformat()},
            status="pending"
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        try:
            # 执行规则
            result = await self.executor.execute(
                graph_data=rule.graph_data,
                execution_id=execution.id,
                trigger_type="timer",
                trigger_data={"scheduled_at": datetime.now().isoformat()}
            )

            # 更新状态
            rule.last_executed_at = datetime.now()
            rule.last_execution_status = result.get("status", "completed")
            db.commit()

        except Exception as e:
            logger.error(f"定时执行失败: rule_id={rule_id}, error={e}")
            rule.last_executed_at = datetime.now()
            rule.last_execution_status = "failed"
            db.commit()

    def update_timer_job(self, rule: Rule):
        """更新定时任务（重新调度）。"""
        if rule.is_active and rule.trigger_type == TriggerType.TIMER:
            self.remove_timer_job(rule.id)
            self.add_timer_job(rule)
        else:
            self.remove_timer_job(rule.id)


# 全局调度器实例
rule_scheduler: RuleScheduler = None


def get_scheduler() -> RuleScheduler:
    """获取调度器实例。"""
    global rule_scheduler
    if rule_scheduler is None:
        rule_scheduler = RuleScheduler()
    return rule_scheduler
```

### 4.2 启动时初始化

```python
# backend/main.py 或 app startup

from backend.services.scheduler import get_scheduler

@app.on_event("startup")
async def startup_event():
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("规则调度器已启动")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info("规则调度器已停止")
```

---

## 5. Webhook 触发

### 5.1 Webhook 生成与验证

```python
# backend/services/webhook_service.py

import hashlib
import hmac
import secrets
from typing import Optional
from fastapi import Request, HTTPException


class WebhookService:
    """Webhook 服务 - 管理 webhook 的生成和验证。"""

    @staticmethod
    def generate_webhook_id() -> str:
        """生成唯一的 webhook ID。"""
        return secrets.token_urlsafe(16)

    @staticmethod
    def generate_secret() -> str:
        """生成 webhook 签名密钥。"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def sign_payload(payload: bytes, secret: str) -> str:
        """生成签名。

        使用 HMAC-SHA256 对 payload 进行签名。
        """
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @staticmethod
    def verify_signature(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """验证签名。"""
        expected = WebhookService.sign_payload(payload, secret)
        return hmac.compare_digest(signature, expected)

    @staticmethod
    def parse_github_webhook(payload: bytes, signature: str, secret: str) -> bool:
        """验证 GitHub 风格 webhook 签名。

        GitHub 使用 'sha256=' 前缀。
        """
        if not signature.startswith('sha256='):
            return False
        return WebhookService.verify_signature(payload, signature, secret)
```

### 5.2 Webhook 路由

```python
# backend/routers/webhook.py

import asyncio
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.models.rule import Rule, TriggerType, RuleTrigger
from backend.services.webhook_service import WebhookService
from backend.services.scheduler import get_scheduler

router = APIRouter(prefix="/api/webhook", tags=["Webhook"])


class WebhookCreateResponse(BaseModel):
    """创建 Webhook 响应。"""
    webhook_id: str
    webhook_url: str
    secret: Optional[str]


class WebhookTriggerRequest(BaseModel):
    """Webhook 触发请求。"""
    rule_id: int
    trigger_data: dict = {}


@router.post("/register/{rule_id}", response_model=WebhookCreateResponse)
async def register_webhook(rule_id: int):
    """为规则注册 Webhook。

    返回 webhook URL，外部系统可以通过该 URL 触发规则执行。
    """
    db = get_db()

    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    # 生成 webhook ID 和密钥
    webhook_id = WebhookService.generate_webhook_id()
    secret = WebhookService.generate_secret()

    # 创建或更新 trigger 记录
    trigger = db.query(RuleTrigger).filter(
        RuleTrigger.rule_id == rule_id,
        RuleTrigger.trigger_type == TriggerType.WEBHOOK
    ).first()

    if trigger:
        trigger.config = {"webhook_id": webhook_id, "secret": secret, "enabled": True}
    else:
        trigger = RuleTrigger(
            rule_id=rule_id,
            trigger_type=TriggerType.WEBHOOK,
            config={"webhook_id": webhook_id, "secret": secret, "enabled": True},
            enabled=True
        )
        db.add(trigger)

    db.commit()

    # 生成 webhook URL
    # 实际域名应该在配置中
    base_url = "https://cogniflow.example.com"
    webhook_url = f"{base_url}/api/webhook/trigger/{webhook_id}"

    return WebhookCreateResponse(
        webhook_id=webhook_id,
        webhook_url=webhook_url,
        secret=secret
    )


@router.post("/trigger/{webhook_id}")
async def trigger_via_webhook(
    webhook_id: str,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """通过 Webhook 触发规则执行。

    Args:
        webhook_id: Webhook ID（URL 中的路径参数）
        request: FastAPI 请求对象
        x_webhook_signature: 可选的签名头
    """
    db = get_db()

    # 查找 webhook
    trigger = db.query(RuleTrigger).filter(
        RuleTrigger.trigger_type == TriggerType.WEBHOOK,
        RuleTrigger.enabled == True
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Webhook 不存在或已禁用")

    config = trigger.config or {}
    stored_webhook_id = config.get("webhook_id")
    secret = config.get("secret")

    # 验证 webhook_id
    if stored_webhook_id != webhook_id:
        raise HTTPException(status_code=404, detail="Webhook 不存在")

    # 验证签名（如果配置了密钥）
    if secret and x_webhook_signature:
        body = await request.body()
        if not WebhookService.parse_github_webhook(body, x_webhook_signature, secret):
            raise HTTPException(status_code=401, detail="签名验证失败")

    # 获取关联的规则
    rule = db.query(Rule).filter(Rule.id == trigger.rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="关联的规则不存在")

    # 解析请求体
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}

    # 创建执行记录
    execution = ExecutionHistory(
        rule_id=rule.id,
        trigger_type="webhook",
        trigger_data={"webhook_id": webhook_id, "body": body},
        status="pending"
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # 异步执行
    asyncio.create_task(execute_webhook_rule(execution.id, rule.graph_data))

    return {
        "status": "ok",
        "execution_id": execution.id,
        "message": "规则执行已触发"
    }


async def execute_webhook_rule(execution_id: int, graph_data: dict):
    """异步执行 Webhook 触发的规则。"""
    from backend.services.rule_engine.executor import RuleGraphExecutor
    from backend.services.rule_engine.websocket_manager import connection_manager

    executor = RuleGraphExecutor(db=get_db(), ws_manager=connection_manager)

    try:
        await executor.execute(
            graph_data=graph_data,
            execution_id=execution_id,
            trigger_type="webhook"
        )
    except Exception as e:
        logger.error(f"Webhook 规则执行失败: {e}")
```

---

## 6. 规则激活/停用

### 6.1 激活状态管理

```python
# backend/routers/rule_engine.py

@router.post("/rules/{rule_id}/activate")
async def activate_rule(rule_id: int):
    """激活规则。

    激活后：
    - 如果是定时触发，立即开始调度
    - 如果是 Webhook 触发，启用 Webhook
    """
    db = get_db()

    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule.is_active = True
    db.commit()

    # 处理定时触发
    if rule.trigger_type == TriggerType.TIMER:
        scheduler = get_scheduler()
        scheduler.add_timer_job(rule)

    return {"status": "ok", "message": "规则已激活"}


@router.post("/rules/{rule_id}/deactivate")
async def deactivate_rule(rule_id: int):
    """停用规则。

    停用后：
    - 定时任务被移除
    - Webhook 被禁用
    """
    db = get_db()

    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule.is_active = False
    db.commit()

    # 移除定时任务
    if rule.trigger_type == TriggerType.TIMER:
        scheduler = get_scheduler()
        scheduler.remove_timer_job(rule.id)

    return {"status": "ok", "message": "规则已停用"}
```

---

## 7. 规则列表页面

### 7.1 规则列表 API

```python
# backend/routers/rule_engine.py

class RuleListItem(BaseModel):
    """规则列表项。"""
    id: int
    name: str
    description: Optional[str]
    trigger_type: TriggerType
    is_active: bool
    last_executed_at: Optional[datetime]
    last_execution_status: Optional[str]
    node_count: int
    created_at: datetime


@router.get("/rules", response_model=List[RuleListItem])
async def list_rules(
    trigger_type: Optional[TriggerType] = None,
    is_active: Optional[bool] = None
):
    """获取规则列表。

    Args:
        trigger_type: 按触发类型过滤
        is_active: 按激活状态过滤
    """
    db = get_db()

    query = db.query(Rule)

    if trigger_type:
        query = query.filter(Rule.trigger_type == trigger_type)

    if is_active is not None:
        query = query.filter(Rule.is_active == is_active)

    rules = query.order_by(Rule.updated_at.desc()).all()

    result = []
    for rule in rules:
        # 计算节点数量
        graph_data = rule.graph_data or {}
        nodes = graph_data.get("nodes", {})
        node_count = len(nodes)

        result.append(RuleListItem(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            trigger_type=rule.trigger_type,
            is_active=rule.is_active,
            last_executed_at=rule.last_executed_at,
            last_execution_status=rule.last_execution_status,
            node_count=node_count,
            created_at=rule.created_at
        ))

    return result
```

### 7.2 前端规则管理页面

```vue
<!-- webui/src/views/RuleList.vue -->

<template>
  <div class="rule-list-page">
    <header class="page-header">
      <h1>规则管理</h1>
      <button class="btn primary" @click="onCreateRule">
        创建规则
      </button>
    </header>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <select v-model="filterTriggerType" class="filter-select">
        <option value="">全部类型</option>
        <option value="manual">手动触发</option>
        <option value="timer">定时触发</option>
        <option value="webhook">Webhook</option>
      </select>

      <select v-model="filterActive" class="filter-select">
        <option value="">全部状态</option>
        <option value="true">已激活</option>
        <option value="false">已停用</option>
      </select>
    </div>

    <!-- 规则列表 -->
    <div class="rule-grid">
      <div
        v-for="rule in filteredRules"
        :key="rule.id"
        class="rule-card"
        :class="{ inactive: !rule.is_active }"
      >
        <div class="rule-header">
          <h3>{{ rule.name }}</h3>
          <span class="trigger-badge" :class="rule.trigger_type">
            {{ triggerTypeName(rule.trigger_type) }}
          </span>
        </div>

        <p class="rule-desc">{{ rule.description || '暂无描述' }}</p>

        <div class="rule-meta">
          <span>节点: {{ rule.node_count }}</span>
          <span>状态: {{ rule.is_active ? '已激活' : '已停用' }}</span>
        </div>

        <div class="rule-status">
          <template v-if="rule.last_executed_at">
            <span class="last-run">
              上次执行: {{ formatTime(rule.last_executed_at) }}
            </span>
            <span
              class="status-indicator"
              :class="rule.last_execution_status"
            >
              {{ executionStatusName(rule.last_execution_status) }}
            </span>
          </template>
          <template v-else>
            <span class="no-run">从未执行</span>
          </template>
        </div>

        <div class="rule-actions">
          <button
            class="btn"
            :class="rule.is_active ? 'warning' : 'success'"
            @click="toggleActive(rule)"
          >
            {{ rule.is_active ? '停用' : '激活' }}
          </button>

          <button class="btn" @click="editRule(rule)">
            编辑
          </button>

          <button class="btn" @click="executeRule(rule)" :disabled="!rule.is_active">
            执行
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const rules = ref<RuleListItem[]>([])
const filterTriggerType = ref('')
const filterActive = ref('')

const filteredRules = computed(() => {
  return rules.value.filter(rule => {
    if (filterTriggerType.value && rule.trigger_type !== filterTriggerType.value) {
      return false
    }
    if (filterActive.value && String(rule.is_active) !== filterActive.value) {
      return false
    }
    return true
  })
})

function triggerTypeName(type: string): string {
  const names = {
    manual: '手动',
    timer: '定时',
    webhook: 'Webhook'
  }
  return names[type] || type
}

function executionStatusName(status: string): string {
  const names = {
    completed: '成功',
    failed: '失败',
    cancelled: '取消'
  }
  return names[status] || status
}

function formatTime(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

async function toggleActive(rule: RuleListItem) {
  const action = rule.is_active ? '停用' : '激活'
  try {
    await ElMessageBox.confirm(
      `确定要${action}规则 "${rule.name}" 吗？`,
      `${action}确认`,
      { type: 'warning' }
    )

    const api = rule.is_active ? 'deactivate' : 'activate'
    await fetch(`/api/rule-engine/rules/${rule.id}/${api}`, { method: 'POST' })

    rule.is_active = !rule.is_active
    ElMessage.success(`规则已${action}`)
  } catch (e) {
    // 用户取消
  }
}

async function executeRule(rule: RuleListItem) {
  try {
    const response = await fetch(`/api/rule-engine/rules/${rule.id}/execute`, {
      method: 'POST'
    })
    const data = await response.json()

    ElMessage.success({
      message: `执行已启动 (ID: ${data.execution_id})`,
      type: 'success'
    })
  } catch (e) {
    ElMessage.error('执行启动失败')
  }
}

function editRule(rule: RuleListItem) {
  // 导航到规则编辑页面
  router.push(`/rules/${rule.id}/edit`)
}

async function loadRules() {
  const response = await fetch('/api/rule-engine/rules')
  rules.value = await response.json()
}

loadRules()
</script>

<style scoped>
.rule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.rule-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}

.rule-card.inactive {
  opacity: 0.7;
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.trigger-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.trigger-badge.manual { background: #4CFF4C33; color: #4CFF4C; }
.trigger-badge.timer { background: #DC4FDC33; color: #DC4FDC; }
.trigger-badge.webhook { background: #00f0FF33; color: #00f0FF; }

.rule-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.rule-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.rule-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.last-run {
  font-size: 12px;
  color: var(--text-secondary);
}

.status-indicator {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-indicator.completed { background: #4CFF4C33; color: #4CFF4C; }
.status-indicator.failed { background: #FF4C4C33; color: #FF4C4C; }
.status-indicator.cancelled { background: #FFFF4C33; color: #FFFF4C; }

.rule-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
}

.btn.success {
  background: #4CFF4C33;
  color: #4CFF4C;
  border-color: #4CFF4C;
}

.btn.warning {
  background: #FFFF4C33;
  color: #FFFF4C;
  border-color: #FFFF4C;
}
</style>
```

---

## 8. Cron 表达式配置

### 8.1 Cron 输入组件

```vue
<!-- webui/src/components/rule-editor/CronInput.vue -->

<template>
  <div class="cron-input">
    <div class="cron-presets">
      <button
        v-for="preset in presets"
        :key="preset.value"
        class="preset-btn"
        :class="{ active: cron === preset.value }"
        @click="selectPreset(preset.value)"
      >
        {{ preset.label }}
      </button>
    </div>

    <div class="cron-editor">
      <input
        type="text"
        v-model="cron"
        class="cron-text"
        placeholder="* * * * *"
        @change="onCronChange"
      />
      <span class="cron-hint">分 时 日 月 周</span>
    </div>

    <div class="cron-preview" v-if="nextRuns.length > 0">
      <span class="label">下次执行:</span>
      <span v-for="(run, i) in nextRuns" :key="i" class="next-run">
        {{ formatTime(run) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import cronstrue from 'cronstrue'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const cron = ref(props.modelValue)

const presets = [
  { label: '每小时', value: '0 * * * *' },
  { label: '每天午夜', value: '0 0 * * *' },
  { label: '每天8点', value: '0 8 * * *' },
  { label: '每周一', value: '0 0 * * 1' },
  { label: '每月1号', value: '0 0 1 * *' }
]

function selectPreset(value: string) {
  cron.value = value
  emit('update:modelValue', value)
}

function onCronChange() {
  emit('update:modelValue', cron.value)
}

// 计算下次执行时间（使用 cron-parser 库）
const nextRuns = computed(() => {
  try {
    // 简单实现，实际应使用 cron-parser
    return []
  } catch (e) {
    return []
  }
})

function formatTime(date: Date): string {
  return date.toLocaleString('zh-CN')
}
</script>
```

---

## 9. 验收检查清单

### 9.1 手动触发
- [ ] 点击执行按钮创建执行记录
- [ ] 规则异步执行（不阻塞请求）
- [ ] 返回执行 ID 供查询

### 9.2 定时触发
- [ ] Cron 表达式正确解析
- [ ] 定时任务在正确时间执行
- [ ] 规则激活时定时任务启动
- [ ] 规则停用时定时任务移除

### 9.3 Webhook 触发
- [ ] 生成唯一的 Webhook URL
- [ ] 支持签名验证
- [ ] POST 请求能触发规则执行

### 9.4 激活/停用
- [ ] 激活按钮启用定时任务/Webhook
- [ ] 停用按钮停止定时任务/Webhook
- [ ] 状态在列表中正确显示

### 9.5 规则列表
- [ ] 显示所有规则信息
- [ ] 支持按类型和状态筛选
- [ ] 显示上次执行时间和状态
- [ ] 快捷操作按钮正确工作
