# UnoCSS 样式规范（CogniFlow WebUI）

> 本文件是 CogniFlow 前端项目的 **样式编写宪法**。所有新写、改动的样式必须按本文执行。
> 历史包袱（已存在的违规）按"修复路线"分波处理，详见 [§ 4 修复路线](#4-历史包袱修复路线)。

**最后更新**: 2026-09-12（v2 设计令牌 + 文档与实现对齐）
**适用范围**: `webui/src/**/*.vue` 内的所有样式
**不属于本文范围**:
- `src/style/_element-plus*.scss` — Element Plus 主题覆盖（必须 SCSS，UnoCSS 帮不了）
- `src/style/_variables.scss` — 设计令牌（CSS 变量定义，UnoCSS 用 `text-[var(--xxx)]` 引用）
- `src/style/_animations.scss` — 全局 `@keyframes`（UnoCSS 不管 keyframe）

---

## 1. 核心规则（必读）

### 1.1 优先级顺序

按下列优先级使用，**前面的能解决问题就不要用后面的**：

1. **UnoCSS shortcut**（`uno.config.ts` 里定义的 `ui-*` / `cf-*` 类）
2. **UnoCSS utility**（`flex` / `gap-4` / `text-[var(--xxx)]` 之类）
3. **UnoCSS `@apply`**（在 `<style>` 块里组合多个 utility）
4. **内联 `:style` 对象**（仅限**真正动态**的值：width 进度、坐标、颜色绑定）
5. **`<style lang="scss" scoped>` 块**（**仅当前 4 条都帮不了**才用，必须有 § 1.2 的注释说明理由）
6. ❌ **禁止** 静态 `style="..."` 内联字符串
7. ❌ **禁止** 在 .vue 组件里写**裸 CSS 选择器**（`.foo { color: red }` 这种零 `@apply` 纯手写的）

### 1.2 不得已写 SCSS 块的 4 个合法理由

写 `<style lang="scss" scoped>` 块**必须**在文件顶部加注释说明属于哪一类，否则 PR 审查直接打回。

```scss
// UNOCSS-EXCEPTION: 1) 第三方组件 :deep 穿透
// UNOCSS-EXCEPTION: 2) @keyframes 定义
// UNOCSS-EXCEPTION: 3) CSS 变量插值到非 utility 可表达的属性（gradient/clip-path）
// UNOCSS-EXCEPTION: 4) 浏览器伪元素 ::before / ::content 等 UnoCSS 表达不了的
```

**示例（合法）**：
```vue
<style lang="scss" scoped>
// UNOCSS-EXCEPTION: 3) linear-gradient + background-clip:text，utility 无法表达
.cf-gradient-text {
  background: linear-gradient(90deg, var(--text-primary), var(--accent-blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
</style>
```

**示例（不合法，PR 打回）**：
```vue
<style lang="scss" scoped>
/* 注释缺失 */
.my-btn {
  background: red;  /* 这个直接写 class="bg-red-500" 就行 */
}
</style>
```

### 1.3 命名体系（`ui-*` 是实际生效的那套）

> **ENG 修正 (2026-09-12)**：本文件原称"项目已确定所有新写代码用 `cf-*`"，
> 但实测 `cf-btn` / `cf-card` / `cf-input` / `cf-badge` 等 **全项目 0 命中**，
> 且 `_common.scss` **文件已不存在**（2026-06-18 内容迁至 `uno.config.ts`）。
> 实际生效的是 **`ui-*` 系列**（`ui-btn` 70 处、`ui-card` 28 处…）。

**项目实际约定**：所有按钮/卡片/标签/输入类组件用 **`ui-*` shortcut**
（定义在 `uno.config.ts` 的 `shortcuts`）。

**`cf-*` 前缀目前只有两个体系在用**：
- `cf-gradient-text` — 页面标题渐变文字（6 个视图在用）
- `cf-loading` / `cf-loading--overlay` / `cf-loading__container` / `cf-loading__ring` / `cf-loading__text` — LoadingSpinner

**命名单一来源**：所有 shortcut **只**定义在 `uno.config.ts`，SCSS 文件里不再定义组件类。

**判定**：写新类之前先看 `uno.config.ts` 的 `shortcuts` 块——**已经有就别写第二遍**。

---

## 2. 快速参考

### 2.1 常用 shortcut 速查表

> **ENG 修正 (2026-09-12)**：原表列的 12 个 shortcut 里 **11 个不存在**（`cf-btn*` / `cf-card*` / `cf-flex*` /
> `cf-text-*` / `cf-badge` / `cf-input`），按它写会得到静默失效的类名。下表是**实测存在**的清单。

完整列表见 `uno.config.ts` 的 `shortcuts`，高频用到的：

| 用途 | 类名 | 备注 |
|------|------|----------|
| 按钮基类 | `ui-btn` | 13px / `px-4 py-2` / 6px 圆角 |
| 主按钮 | `ui-btn ui-btn-primary` | 品牌青底 + **深墨字**（`text-[var(--on-vibrant)]`） |
| 语义按钮 | `ui-btn ui-btn-success` / `ui-btn-danger` | 同样用深墨字，**禁止 `text-white`** |
| 次要按钮 | `ui-btn ui-btn-secondary` | 修饰符，hover 点亮品牌青 |
| 小按钮 | `ui-btn ui-btn-small` / `ui-btn-xs` / `ui-btn-sm` | `ui-btn-sm` 是修饰符（内部 `!` 强制覆盖） |
| 图标按钮 | `ui-btn-icon` | 34×34 |
| 卡片 | `ui-card` / `ui-card-header` / `ui-card-content` | 背景+边框+圆角 |
| 标签 | `ui-tag` + `ui-tag-blue` / `-green` / `-yellow` / `-red` | 语义底 + 语义字 |
| 输入框 | `ui-input` | 全宽 + 深色底 + 聚焦青边 |
| 徽章 | `ui-badge` | mono 字体 |
| 滚动条 | `ui-scrollbar` | — |
| 标题渐变 | `cf-gradient-text` | 6 个视图页头在用 |
| 加载态 | `cf-loading` 系列 | LoadingSpinner 专用 |

**两条硬规则（v2 新增）：**

1. **亮色底上禁止白字。** 白字在品牌青 `#22d3ee` 上仅 1.81:1、在 v1 蓝 `#5898ff` 上也仅 2.86:1，
   都不可读。一律用 `text-[var(--on-vibrant)]`（`#04161a`，在五个亮底色上 5.50–10.24:1）。
2. **分类色必须走令牌。** 节点分类色用 `var(--cat-<name>)` / `-bg` / `-fg`，不要写字面量。
   JS canvas 绘图（小地图、`ctx.strokeStyle`）例外，用 hex 字面量（`var()` 在 canvas API 上不解析）。

**原则**：能用 shortcut 不用 utility（更短 + 团队统一）。

### 2.2 引用设计令牌

颜色 / 字号 / 圆角 / 间距全部走 `var(--xxx)` 引用 `src/style/_variables.scss` 定义的 CSS 变量：

```html
<!-- ✅ 正确 -->
<div class="bg-[var(--bg-primary)] text-[var(--text-secondary)] rounded-md">

<!-- ❌ 错误：硬编码颜色 -->
<div class="bg-[#0d0d14] text-[#9090a8] rounded-[6px]">

<!-- ❌ 错误：用 Tailwind 调色板 -->
<div class="bg-gray-900 text-gray-400 rounded">
```

### 2.3 动态值用 `:style`

```vue
<!-- ✅ 正确：动态进度条 -->
<div :style="{ width: progress + '%' }" class="h-full bg-[var(--accent-blue)]" />

<!-- ✅ 正确：动态背景色（用户选择） -->
<div :style="{ background: cat.color }" />

<!-- ❌ 错误：静态值用 :style -->
<div :style="{ display: 'none' }" />  <!-- 应该用 class="hidden" -->
```

---

## 3. 反模式清单（PR 审查时必看）

> **2026-09-12 状态**：违规 5（静态内联 `style="..."`）**已清零**（11 处 → 0）；
> 违规 6（`ui-*` / `cf-*` 两套并存）**已裁定**（`ui-*` 为准）。
> 违规 1 / 2 / 4 / 7 仍未处理，见 §4.3 的待办清单。

### 3.1 违规 1：UnoCSS shortcut 和 SCSS 块**双定义同类名**

**症状**：`uno.config.ts` 已定义 `cf-loading`，`.vue` 文件里又写 SCSS `.cf-loading { ... }`。

**风险**：编译顺序决定谁覆盖，行为不可预测。

**案例**：`LoadingSpinner.vue:32-90` 整段 SCSS 和 `uno.config.ts:65` `cf-loading` 重复。

**修法**：删除 SCSS 块，只留 shortcut。

### 3.2 违规 2：同一段 SCSS 在 5+ 个文件**重复**

**症状**：6 个 view 文件都写同一段 `linear-gradient(90deg, var(--text-primary), var(--accent-blue)) + -webkit-background-clip: text`。

**案例**：`Launch.vue:1498` / `Annotate.vue:~1290` / `AtlasDetail.vue:1237` / `ModelList.vue:975` / `AtlasList.vue:341` / `Training.vue:497`。

**修法**：抽到 `uno.config.ts` shortcut（如 `cf-gradient-text`），全文件用类名引用。

### 3.3 违规 3：设计文档和实际代码**冲突**

**症状**：`_animations.scss` 注释"移除所有装饰性动画（脉冲、发光）"，但 `Training.vue:534-537` 又写 `@keyframes pulse` + `box-shadow: 0 0 8px var(--accent-blue)`。

**风险**：新人按文档走，写出与代码不一致的样式。

**修法**：要么改 `Training.vue` 删 pulse 和发光，要么改设计文档认可装饰。**禁止文档和代码长期打架**。

### 3.3b 违规 3b：同名 `@keyframes` 多文件重复定义（**已摸排，暂不修**）

**症状**：4 个 view 文件各自定义 `@keyframes dialogIn`，**且动效参数不一致**：
- `Annotate.vue:1593` — `scale(0.95) translateY(-10px)` / 0.2s
- `Annotate.vue:1703` — 同上 / **0.15s**
- `AtlasDetail.vue:1707` — `scale(0.95)`（无 translateY）/ 0.3s
- `ModelList.vue:1150` — `scale(0.95) translateY(20px)` / 0.3s
- `AtlasList.vue:422` — 同 ModelList / 0.3s

**为什么重复**：`_animations.scss:19` 已经有全局 `@keyframes dialogIn`（= Annotate 版本），但因为它是**全局**与 **scoped keyframe 同名**，Vue scoped 加 `[data-v-xxx]` 后缀变成 `dialogIn-xxx` 各文件**不冲突**，所以各自重写没人发现。**全局的 dialogIn 是死代码**。

**为什么不修（老大 2026-06-18 拍板 C）**：
- 3 种动效语义不同，强行合并有视觉回归
- 拆 3 个语义名（`dialogIn-top/bottom/scale`）会让"过渡态"反而变多，违反"砍过渡态"哲学
- 收益低（5 行 SCSS），风险高（5 处 animation 引用改名）

**留作 TODO**：如果以后真要做，建议**全项目统一定一个**（最常用的是 `scale(0.95) translateY(20px)` —— 3 个 view 在用），删其余 4 个 keyframe 块。

### 3.4 违规 4：EP 主题样式**散落在 view 文件**

**症状**：`.vue` 文件用 `:deep(.el-input__wrapper) { ... }` 改 EP 组件样式，逻辑上属于全局 EP 主题。

**案例**：`ModelList.vue:993-1026` 整块 `.el-table` 覆盖、`AtlasDetail.vue:1264-1271` `.el-input__wrapper`。

**修法**：移到 `src/style/_element-plus.scss` 集中管理。

### 3.5 违规 5：静态 `style="..."` 内联字符串

**症状**：`<div style="display: none">`、`<div style="position: relative; min-height: 400px">`。

**风险**：和 UnoCSS utility 重复，难统一。

**案例**：`Home.vue:4` `style="position: relative; min-height: 400px;"`、`Annotate.vue:425` `style="display: none"`。

**修法**：
- `style="display: none"` → `class="hidden"`
- `style="position: relative; min-height: 400px;"` → `class="relative min-h-[400px]"`

### 3.6 违规 6：`.ui-*` 和 `.cf-*` **两套并存**

**症状**：文档推荐 `cf-btn` / `cf-card`，代码里实际是 `.ui-btn` / `.ui-card`，两套说法并存。
（2026-09-12 已裁定：**`ui-*` 为准**，`cf-*` 仅保留 `cf-gradient-text` + `cf-loading` 系列。）

**风险**：新人不知道用哪套，PR 审查会扯皮。

**修法（已裁定 2026-09-12）**：以 **`ui-*` 为准**；不要再引入新的 `cf-*` 组件类。

> 原写法是「迁到 `cf-*`」，方向反了 —— `cf-*` 组件类实际 **0 命中**，`ui-*` 才是 130+ 处在用的那套。

### 3.7 违规 7：`<style scoped>` 块里写**零 `@apply` 纯手写 CSS**

**症状**：整个块都是 `display: flex; align-items: center; ...`，一行 `@apply` 都没有。

**风险**：UnoCSS 帮不上，纯 SCSS 块项目应该**默认走 `<style lang="scss" scoped>` 而不是 UnoCSS 体系**。

**案例**：`Home.vue:362-426` 整段 `.stat-card` / `.stat-icon` / `.main-grid` 都是硬 CSS。

**修法**：能转 `@apply` 就转，转不了就写§ 1.2 的注释说明。

---

## 4. 历史包袱修复路线

**不要一次性重构**。按 3 波走，每波独立 commit、独立 4 件套验证、独立 review。

### 4.1 🟢 第 1 波：低风险清理（建议**第一个 PR**）

**改动范围**：3 个文件，纯删除 / 替换，零设计变更。

1. `webui/src/components/LoadingSpinner.vue` — 删整个 `<style lang="scss" scoped>` 块（90 行 → 0 行）
   - 验证：`cf-loading` / `cf-loading--small` / `--medium` / `--large` shortcut 已存在
2. `webui/src/views/Home.vue:4` — `style="position: relative; min-height: 400px;"` 改为 `class="relative min-h-[400px]"`
3. `webui/src/views/Annotate.vue:425` — `style="display: none"` 改为 `class="hidden"`

**验证**：4 件套（vue-tsc + pnpm build + pytest + git diff 复审）

### 4.2 🟡 第 2 波：提取 shortcut（中风险）

**改动范围**：`uno.config.ts` + 6 个 view 文件 + 1 个 training 文件。

1. `uno.config.ts` 新增 3 个 shortcut：
   - `cf-gradient-text` — 消除 5+ 处 `linear-gradient` 文字渐变重复
   - `cf-loading--small/medium/large` — LoadingSpinner 在 4.1 已删，这里如果 shortcut 不全就补
   - `cf-stat-pill-running/completed` — 提取 Training.vue 的状态点样式
2. 6 个 view 文件的 `linear-gradient` 块替换为 `class="cf-gradient-text"`
3. `Training.vue:534-537` `@keyframes pulse` + `box-shadow: 0 0 8px` —— **和老大拍**：
   - 选项 A：保留（接受装饰性动画，文档加"Training 页面例外"）
   - 选项 B：删除（严格按设计文档"无装饰"原则）

**验证**：4 件套 + 视觉对比（截图前后）。

### 4.3 🔴 第 3 波：体系合并（**已裁定，部分完成** 2026-09-12）

**决策已定**：**保留 `ui-*`，砍 `cf-*` 的说法**（反过来了 —— 原文推荐保留 `cf-*`，但实测
`cf-*` 组件类 0 命中，`ui-*` 才是 130+ 处在用的）。

**已完成：**
1. ~~决策保留哪套~~ → **`ui-*` 为准**，已写入 §1.3
2. ~~`_common.scss` 删除~~ → **该文件 2026-06-18 已不存在**，内容在 `uno.config.ts`
3. ~~静态 `style="..."` 清零~~ → **已完成**（11 处 → 0）
4. ~~文档与实现对齐~~ → **已完成**（本文件 §1.3 / §2.1 / §3.6，CLAUDE.md §7.3 / §7.5 / §7.4.1，COGNIFLOW_DESIGN.md）

**仍待处理：**
5. 8 个 view 文件的 `:deep` EP 覆盖**全部移入** `src/style/_element-plus.scss`
6. `--accent-blue*` 三个兼容别名 → 迁移 176 处引用后删除别名，统一用 `--accent*`
7. 中立灰阶硬编码（`#888` 25 处、`#666` 10、`#555` 10、`#444` 8、`#e0e0e8`/`#e0e0e0` 各 7）→ 令牌
8. 规则画布内部暗色（`#1e1e2e` 16 处、`#2a2a3a` 12、`#3a3a5c` 7…）→ 令牌（属画布重构范围）
9. `RuleCanvas.vue` 2097 行 scoped 块（`@apply` 用量为 0）与 alpha 漂移归一化（青色有 13 种 alpha 值）

**验证**：4 件套 + 视觉回归 + 端到端 smoke test（每个 view 跑一遍关键流程）。

---

## 5. PR 审查 checklist

提交涉及样式的 PR 时，**作者自审 + reviewer 复审** 都按这个清单过：

- [ ] 没有引入**新的** `.ui-*` 类
- [ ] 没有**静态** `style="..."` 内联
- [ ] `<style lang="scss" scoped>` 块**有 § 1.2 注释**说明理由
- [ ] 没有**零 `@apply`** 纯手写 SCSS 块
- [ ] 颜色 / 圆角 / 间距**全部走 `var(--xxx)`**，没有硬编码
- [ ] 没有**重复 shortcut**（先看 `uno.config.ts` 已有不）
- [ ] `:deep` 用法有正当理由（穿透 EP），且**不是新增**（应优先放 `_element-plus.scss`）
- [ ] 4 件套绿（vue-tsc / pnpm build / pytest / git diff 复审）

---

## 6. 参考资料

- `webui/uno.config.ts` — UnoCSS 配置（shortcut 都在这）
- `webui/src/style/_variables.scss` — 设计令牌（CSS 变量定义）
- `webui/src/style/_element-plus.scss` — EP 主题覆盖（唯一允许的"非 UnoCSS 入口"）
- `webui/src/style/_animations.scss` — 全局 keyframe
- `CLAUDE.md` — 项目协作规则（4 件套红线、信任红线）

---

**附：本规范违反"我加了 X"类声称红线**——以后任何声称"按规范改了"必须有 `git diff` 截图对应行号、4 件套日志、视觉对比为证。**否则视为未完成。**
