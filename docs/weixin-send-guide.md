# 微信文件发送指南

## 发送结果汇总

| 类型 | 方法 | 状态 | 说明 |
|------|------|------|------|
| 文本文件(.txt/.md) | `send_weixin_direct()` | ✅ 成功 | 120KB文件验证通过 |
| 图片(.jpg/.png) | `send_weixin_direct()` | ❌ 失败 | iLink ret=-2 |
| 微信消息(文字) | `WeixinAdapter.send()` | ✅ 成功 | 连接后可发 |

## 根因分析

### 1. send_message 工具超时问题
**错误**: `RuntimeError: Timeout context manager should be used inside a task`

**原因**: `asyncio.helpers.TimerContext.__enter__()` 要求必须在 `asyncio.Task` 内部调用：
```python
task = asyncio.current_task(loop=self._loop)
if task is None:
    raise RuntimeError("Timeout context manager should be used inside a task")
```

send_message 工具通过 `_run_async()` 间接调用，异步上下文传递存在问题。

### 2. 图片发送失败问题
**错误**: `iLink sendmessage error: ret=-2 errcode=None errmsg=unknown error`

**原因**: iLink 协议层不支持直接发送图片格式，需要通过其他 API。

## 正确用法

### 方法1：直接调用 send_weixin_direct()（最可靠）

```python
import asyncio
import os

os.environ['WEIXIN_TOKEN'] = os.getenv('WEIXIN_TOKEN', '')
os.environ['WEIXIN_ACCOUNT_ID'] = os.getenv('WEIXIN_ACCOUNT_ID', '')

async def send_file():
    from gateway.platforms.weixin import send_weixin_direct
    
    result = await send_weixin_direct(
        extra={'account_id': os.getenv('WEIXIN_ACCOUNT_ID', '')},
        token=os.getenv('WEIXIN_TOKEN', ''),
        chat_id='目标用户ID@im.wechat',
        message='文件描述文字',
        media_files=[('/path/to/file.txt', False)],  # (路径, 是否图片)
    )
    print(result)
    return result

# 执行
asyncio.run(send_file())
```

### 方法2：通过 WeixinAdapter（需先连接）

```python
import asyncio
from gateway.platforms.weixin import WeixinAdapter
from gateway.config import PlatformConfig

async def send_via_adapter():
    token = '你的WEIXIN_TOKEN'
    account_id = '你的WEIXIN_ACCOUNT_ID'
    
    adapter = WeixinAdapter(PlatformConfig(
        enabled=True,
        token=token,
        extra={'account_id': account_id}
    ))
    
    await adapter.connect()
    
    # 发送文本消息
    result = await adapter.send(
        chat_id='用户ID@im.wechat',
        content='消息内容'
    )
    
    await adapter.disconnect()
    return result

asyncio.run(send_via_adapter())
```

### 方法3：在 Hermes Agent 内部发送

由于工具框架会处理异步上下文，发送文本消息给指定用户：

```
send to weixin:o9cq80zGycxWhV1OiwjY16O0G0LU@im.wechat 消息内容
```

## 已知限制

1. **图片发送**: iLink 协议不支持，需要研究其他 API（如 `upload_image`）
2. **文件大小**: 大文件可能需要分片
3. **并发限制**: `_LIVE_ADAPTERS` 为空时无法复用连接

## 调试技巧

```python
# 查看活跃适配器
from gateway.platforms.weixin import _LIVE_ADAPTERS
print('活跃适配器:', list(_LIVE_ADAPTERS.keys()))

# 检查 token
import os
print('WEIXIN_TOKEN:', os.getenv('WEIXIN_TOKEN', '')[:10] + '...')
```

## 相关源码

- 微信适配器: `/root/.hermes/hermes-agent/gateway/platforms/weixin.py`
- 发送函数: `send_weixin_direct()` 第 1959 行
- 工具封装: `/root/.hermes/hermes-agent/model_tools.py` 第 270 行 `_run_async()`
