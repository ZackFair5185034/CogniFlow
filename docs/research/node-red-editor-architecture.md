# Node-RED 编辑器架构研究报告

## 一、源码架构概览

Node-RED 采用 monorepo 结构，核心包位于 `packages/node_modules/@node-red/`：

| 包名 | 职责 |
|------|------|
| `editor-client` | 前端编辑器 UI（SVG 画布、节点编辑对话框、侧边栏） |
| `runtime` | 后端运行时（消息流执行引擎、节点注册表） |
| `registry` | 节点模块的发现、加载、注册管理 |
| `editor-api` | 编辑器与后端通信的 REST API |

---

## 二、前端编辑器架构

### 2.1 技术选型

**编辑器核心：自研 + D3.js + Monaco**

- **画布渲染**: D3.js SVG（`view.js`）— 不是 Canvas，不是 WebGL
- **节点编辑对话框**: 自研 + Monaco Editor（VS Code 内核，`vendor/monaco/`）
- **UI 框架**: jQuery + 原生 DOM 操作
- **包管理**: 事件驱动架构（`RED.events`）

**入口点** (`main.js`):
```javascript
RED.init({ apiRootUrl: "" })
```

### 2.2 画布实现（SVG + D3）

`view.js` 实现了 Node-RED 的画布，采用 **D3.js + SVG** 而非 Canvas/WebGL：

```javascript
outer = d3.select("#red-ui-workspace-chart")
    .append("svg:svg")
    .attr("width", 8000)   // 固定空间尺寸
    .attr("height", 8000)
    .attr("pointer-events", "all")
    .style("touch-action", "none");
```

**SVG 层结构**（注释原文）:
```
#red-ui-workspace-chart
 └─ <svg> "outer"
     └─ <g>
         ├─ <g>.red-ui-workspace-chart-event-layer  — 事件处理
         ├─ <rect>.red-ui-workspace-chart-background — 背景
         ├─ <g>.red-ui-workspace-chart-grid         — 网格线
         ├─ <g> "groupLayer"                        — 节点组
         ├─ <g> "linkLayer"                         — 连接线
         ├─ <g> "junctionLayer"                     — 汇合点
         ├─ <g> "dragGroupLayer"                    — 拖拽层
         └─ <g> "nodeLayer"                         — 节点本体
```

**D3 使用方式**: 仅用于 DOM 操作和事件绑定，**没有使用 D3 的 zoom behavior**，缩放是手动实现的。

### 2.3 缩放/平移实现（纯手动，非 D3 zoom）

Node-RED 使用自定义缩放逻辑，不依赖 D3 的 `d3.zoomBehavior`：

```javascript
// view.js 中的缩放范围
scaleFactor = Math.min(2, Math.max(0.3, scaleFactor + delta));
// 范围: [0.3, 2.0]，步进 0.1

function zoomView(factor) {
    var screenSize = [chart.width(), chart.height()];
    var scrollPos = [chart.scrollLeft(), chart.scrollTop()];
    // 以屏幕中心为缩放中心
    var center = [(scrollPos[0] + screenSize[0]/2)/scaleFactor,
                  (scrollPos[1] + screenSize[1]/2)/scaleFactor];
    scaleFactor = factor;
    // 调整 scroll 保持中心点不变
    var newCenter = [...];
    var delta = [(newCenter[0]-center[0])*scaleFactor, ...];
    chart.scrollLeft(scrollPos[0]-delta[0]);
    chart.scrollTop(scrollPos[1]-delta[1]);
    redraw();  // 触发重绘
}
```

**触摸缩放** (pinch gesture):
```javascript
startTouchDistance = Math.hypot(touch0.pageX - touch1.pageX, touch0.pageY - touch1.pageY);
scaleFactor = Math.min(2, Math.max(0.3, scaleFactor + 
    Math.floor(((moveTouchDistance*100)-(startTouchDistance*100))/10000)));
```

### 2.4 重绘机制（dirty flag 模式）

Node-RED **没有虚拟化渲染**（不计算 viewport裁剪），而是用 **dirty flag** 优化：

```javascript
function redraw() {
    if (arguments.length === 0) {
        // 全量重绘
        outer.selectAll(".red-ui-flow-node").attr("transform", ...);
        outer.selectAll(".red-ui-flow-link").attr("d", ...);
    }
}
// 节点位置变化时标记 dirty，触发重绘
node.dirty = true;
```

实际代码中大量使用 `dirty` 标记，只有标记了 dirty 的元素才会重新渲染。

### 2.5 节点分类和搜索

Palette 编辑器 (`palette-editor.js`) 管理节点分类和搜索：
- 节点按 `category` 分组
- 支持关键词过滤搜索
- 节点图标从 HTML 模板动态生成

---

## 三、节点类型系统

### 3.1 节点定义结构

节点通过 `RED.nodes.registerType(type, constructor, opts)` 注册：

```javascript
// 运行时节点定义示例
RED.nodes.registerType("my-node", function(n) {
    this.on("input", function(msg, send, done) {
        // 处理消息
        send(msg);  // 发送到下游
        done();     // 完成信号
    });
}, {
    category: "function",      // Palette 分类
    defaults: {                // 属性定义
        name: { value: "" },
        topic: { value: "", validate: RED.validators.number }
    },
    inputs: 1,                 // 输入端口数
    outputs: 1,                // 输出端口数
    icon: "icon/file.svg",     // 节点图标
    paletteLabel: function() {...},
    oneditprepare: function() {...},  // 编辑对话框准备
    oneditsave: function() {...},
    oneditcancel: function() {...}
});
```

### 3.2 属性验证

支持两种验证器格式：
- **v2.x**: `validate: function() { return true/false }`
- **v3.x**: `validate: function() { return "error string" }`

验证核心逻辑 (`editor.js`):
```javascript
function validateNodeProperties(node, props, oldNode) {
    // 返回验证错误数组
    // 空数组 = 验证通过
}
```

### 3.3 节点注册表（Registry）

`@node-red/registry` 包负责：
1. **发现**: 扫描 `node_modules` 查找节点模块
2. **加载**: `loader.loadNodeSet()` 动态 require 节点 JS
3. **注册**: `registry.registerNodeConstructor()` 注册到运行时
4. **库**: 节点贡献的 HTML 模板存储在节点目录

---

## 四、运行时执行引擎

### 4.1 消息流机制（Message/Node/Connection）

**消息结构** (`Node.send()`):
```javascript
{
    msg: { payload: "..." },      // 用户消息对象
    source: { id, node, port },   // 来源节点
    destination: { id, node },    // 目标节点
    cloneMessage: false
}
```

**发送优化** (`Node.send`):
```javascript
// 优化1: 单线连接 → 直接引用
if (this.wires.length === 1 && this.wires[0].length === 1) {
    this._wire = this.wires[0][0];  // 直接引用目标节点
    this.send = /* 快捷路径 */;
}
// 优化2: 无连接 → NOOP
if (wc === 0) {
    this.send = NOOP_SEND;
}
```

### 4.2 边的数据结构（Wire）

```javascript
// wires: 二维数组 [outputIndex][targetNodeIds]
node.wires = [
    ["node-id-1", "node-id-2"],   // output 0 的目标
    ["node-id-3"],                 // output 1 的目标
];
// 支持多输出端口、分支、汇聚
```

### 4.3 消息接收 (`Node.receive`) 和 Hook 系统

```javascript
Node.prototype.receive = function(msg) {
    hooks.trigger("onReceive", { msg, destination: { id: this.id } }, (err) => {
        if (err) { this.error(err); return; }
        // 调用 input 事件处理器
        this._emitInput(msg);
    });
};
```

支持 **同步/异步两种 input 回调**：
- `callback.length === 3` → 异步回调（含 `done` 参数）
- 否则 → 同步回调

### 4.4 执行调度（事件驱动 + 异步）

Node-RED **运行时是单线程事件循环**：

```javascript
// Flow.js - Flow 类管理一组节点的执行
class Flow {
    async start(diff) {
        // 按组（group）顺序初始化节点
        for (let i = 0; i < this.groupOrder.length; i++) {
            await this.groups[this.groupOrder[i]].start();
        }
    }
}
```

**部署锁** (`flows.js`):
```javascript
const Mutex = require('async-mutex').Mutex;
const mutex = new Mutex();
// setFlows() 使用互斥锁确保部署原子性
return mutex.runExclusive(async function() { ... });
```

**完成处理** (`Node._complete`):
```javascript
Node.prototype._complete = function(msg, error) {
    hooks.trigger("onComplete", { msg, error, node: {...} }, ...);
    this._flow.handleComplete(this, msg);  // 传递给 complete 节点
};
```

### 4.5 环境变量和配置

```javascript
// flowUtil.evaluateEnvProperties() 支持多种类型
{ name: "API_KEY", type: "cred" }    // 凭证类型
{ name: "TIMEOUT", type: "num", value: "5000" }
{ name: "CONFIG", type: "conf-type", value: "${myConfig}" }  // 配置节点引用
```

---

## 五、通信机制

### 5.1 Editor ↔ Runtime 通信

Node-RED 使用 **HTTP REST API + WebSocket 双向通信**：

**REST API** (`@node-red/editor-api`):
```
GET    /flows          — 获取当前流程配置
POST   /flows          — 部署新流程
GET    /flow/:id       — 获取单个流程
PUT    /flow/:id       — 更新流程
DELETE /flow/:id        — 删除流程
GET    /nodes          — 获取已注册节点列表
POST   /nodes/:type    — 获取节点信息
```

**WebSocket 事件** (通过 `runtime.events`):
```javascript
events.emit("runtime-event", { id: "runtime-state", retain: true });
// → 前端通过 socket.io 监听 "runtime-event"
```

### 5.2 部署类型

```javascript
// flows.js - 支持4种部署粒度
deploymentType: "full"   // 完整部署（重启所有节点）
deploymentType: "nodes"  // 仅重启修改的节点
deploymentType: "flows"  // 仅重启修改的流程
deploymentType: "reload" // 重新加载（不重启）
```

### 5.3 凭证管理

```javascript
// credentials.js - 加密存储在 flows.json 之外
credentials.load(config.credentials);  // 解密加载
credentials.add(id, creds);             // 添加凭证
credentials.clean(config);              // 清理过期凭证
credentials.export();                   // 导出加密
```

---

## 六、编辑器-运行时集成

### 6.1 子流程（Subflow）

子流程是一种特殊节点类型，运行时通过类型前缀识别：
```javascript
// 类型名: "subflow:" + subflowId
type: "subflow:abc123"
// 编辑时子流程节点验证委托给子流程定义本身
if (node.type.indexOf("subflow:") === 0) {
    subflow = RED.nodes.subflow(node.type.substring(8));
    isValid = subflow.valid;
}
```

### 6.2 节点编辑流程

```
用户双击节点
  → RED.editor.editConfigNode() / editNode()
  → 弹出编辑对话框（可自定义 EditPane）
  → 用户修改属性
  → validateNode() 实时验证
  → oneditsave() 保存
  → RED.nodes.dirty(true) 标记需要部署
  → 用户点击部署
  → POST /flows → 运行时重载
```

### 6.3 节点状态显示

```javascript
// 节点可设置状态（右下角图标颜色）
node.status({ fill: "green", shape: "dot", text: "connected" });
// 或通过 catch 节点捕获错误
```

---

## 七、关键技术点总结

| 维度 | Node-RED 方案 | 备注 |
|------|--------------|------|
| 画布渲染 | SVG + D3.js | 固定 8000×8000 空间，CSS scroll 滚动 |
| 缩放实现 | 纯手动 scaleFactor | 范围 [0.3, 2.0]，非 D3 zoom |
| 重绘优化 | dirty flag | 非虚拟化，无 viewport culling |
| 运行时 | Node.js 单线程 | 事件驱动 + async hooks |
| 消息路由 | Wire 二维数组 | 支持多输出/分支/汇聚 |
| 部署锁 | async-mutex | 保证部署原子性 |
| 节点注册 | registry 包 | 动态 require，运行时加载 |
| 编辑器通信 | HTTP REST + WebSocket | socket.io 双向事件 |

---

## 八、对 CogniFlow 的参考价值

1. **画布技术选型**: Node-RED 用 SVG 适合节点编辑器（编辑态），但运行态（监控）可能需要 Canvas/WebGL
2. **消息流模型**: Wire 二维数组结构简单高效，支持多输出和分支汇聚
3. **节点注册**: 运行时动态加载机制值得借鉴（松耦合）
4. **Dirty Flag**: 比虚拟化更简单，适合中小规模流程（<1000 节点）
5. **Subflow 模式**: 可嵌套的子流程设计支持模块化
6. **部署粒度**: 四级部署策略（full/nodes/flows/reload）可借鉴
7. **编辑器-运行时分离**: REST API 解耦，支持分布式部署
