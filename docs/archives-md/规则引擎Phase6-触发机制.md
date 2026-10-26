# Phase 6 技术实现文档：规则触发机制
实现规则的手动触发、定时触发和 Webhook 触发三种机制

---

## 一、阶段目标
**目标：**实现规则的手动触发、定时触发和 Webhook 触发三种机制。

**验收标准：**

 
- 手动触发：点击按钮立即执行规则 
- 定时触发：可配置 Cron 表达式，按计划执行 
- Webhook 触发：提供 Webhook URL，外部请求触发执行 
- 规则列表页面显示各规则的上次执行时间和状态 
- 规则激活/停用切换生效 

## 二、触发类型定义

### 2.1 触发器类型枚举
        
| 类型 | 说明 |
| --- | --- |
| `MANUAL` | 手动触发 |
| `TIMER` | 定时触发 |
| `WEBHOOK` | Webhook 触发 |
| `EVENT` | 事件触发（预留） |

### 2.2 规则激活状态
规则模型包含触发配置和执行状态：

 
- `trigger_type` — 触发类型 
- `trigger_config` — 触发配置（TimerConfig / WebhookConfig） 
- `is_active` — 是否激活 
- `last_executed_at` — 上次执行时间 
- `last_execution_status` — 上次执行状态 

## 三、手动触发

### 3.1 API 接口

```text
POST /api/rule-engine/rules/{rule_id}/execute
Request Body:
{ "rule_id": 1, "trigger_type": "manual", "trigger_data": {} }

Response 202:
{ "execution_id": 123, "status": "pending", "message": "规则执行已启动" }
```

执行在后台异步进行，不阻塞请求。

## 四、定时触发

### 4.1 APScheduler 集成
使用 `AsyncIOScheduler` 实现定时调度：

 
- `add_timer_job()` — 按 Cron 表达式添加定时任务 
- `remove_timer_job()` — 移除定时任务 
- `update_timer_job()` — 重新调度（修改配置后） 
- 启动时从数据库加载所有定时规则 

### 4.2 启动初始化

```python
@app.on_event("startup")
async def startup_event():
    scheduler = get_scheduler()
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler = get_scheduler()
    scheduler.stop()
```

### 4.3 Cron 表达式配置
CronInput 组件提供常用预设和手动编辑：

         
| 预设 | Cron 表达式 |
| --- | --- |
| 每小时 | `0 * * * *` |
| 每天午夜 | `0 0 * * *` |
| 每天8点 | `0 8 * * *` |
| 每周一 | `0 0 * * 1` |
| 每月1号 | `0 0 1 * *` |

## 五、Webhook 触发

### 5.1 Webhook 注册

```text
POST /api/webhook/register/{rule_id}
Response:
{
  "webhook_id": "xxx",
  "webhook_url": "https://host/api/webhook/trigger/xxx",
  "secret": "xxx"  // HMAC-SHA256 签名密钥
}
```

### 5.2 Webhook 签名验证
使用 HMAC-SHA256 签名验证请求来源：

 
- `sign_payload()` — 生成签名 `sha256=...` 
- `verify_signature()` — 验证签名（恒定时间比较防时序攻击） 
- `parse_github_webhook()` — GitHub 风格 `sha256=` 前缀验证 

### 5.3 Webhook 触发端点

```text
POST /api/webhook/trigger/{webhook_id}
Headers: X-Webhook-Signature (可选)
Body: JSON 数据（作为 trigger_data 传入）

Response:
{ "status": "ok", "execution_id": 123, "message": "规则执行已触发" }
```

## 六、规则激活/停用

### 6.1 激活

```text
POST /api/rule-engine/rules/{rule_id}/activate
# 定时触发：立即开始调度
# Webhook：启用 webhook
```

### 6.2 停用

```text
POST /api/rule-engine/rules/{rule_id}/deactivate
# 定时任务被移除
# Webhook 被禁用
```

## 七、规则列表页面

### 7.1 规则列表 API

```text
GET /api/rule-engine/rules?trigger_type=&is_active=
Response:
[
  {
    "id": 1,
    "name": "My Rule",
    "trigger_type": "timer",
    "is_active": true,
    "last_executed_at": "2026-05-06T...",
    "last_execution_status": "completed",
    "node_count": 5,
    "created_at": "..."
  }
]
```

### 7.2 规则卡片功能
规则卡片显示：

 
- 规则名称和描述 
- 触发类型徽章（手动/定时/Webhook） 
- 激活状态 
- 节点数量 
- 上次执行时间和状态 
快捷操作：激活/停用切换、执行、编辑

## 八、验收检查清单
                     
| 类别 | 验收项 |
| --- | --- |
| 手动触发 | 点击执行按钮创建执行记录 |
| 规则异步执行（不阻塞请求） |  |
| 返回执行 ID 供查询 |  |
| 定时触发 | Cron 表达式正确解析 |
| 定时任务在正确时间执行 |  |
| 规则激活时定时任务启动 |  |
| 规则停用时定时任务移除 |  |
| Webhook 触发 | 生成唯一的 Webhook URL |
| 支持签名验证 |  |
| POST 请求能触发规则执行 |  |
| 激活/停用 | 激活按钮启用定时任务/Webhook |
| 停用按钮停止定时任务/Webhook |  |
| 状态在列表中正确显示 |  |
| 规则列表 | 显示所有规则信息 |
| 支持按类型和状态筛选 |  |
| 显示上次执行时间和状态 |  |
| 快捷操作按钮正确工作 |  |
