# UnoCSS 样式规范（CogniFlow WebUI）

> 本文件是 CogniFlow 前端项目的 **样式编写宪法**。所有新写、改动的样式必须按本文执行。
> 历史包袱（已存在的违规）按"修复路线"分波处理，详见 [§ 4 修复路线](#4-历史包袱修复路线)。

**最后更新**: 2026-06-18
**适用范围**: `webui/src/**/*.vue` 内的所有样式
**不属于本文范围**:
- `src/style/_element-plus*.scss` — Element Plus 主题覆盖（必须 SCSS，UnoCSS 帮不了）
- `src/style/_variables.scss` — 设计令牌（CSS 变量定义，UnoCSS 用 `text-[var(--xxx)]` 引用）
- `src/style/_animations.scss` — 全局 `@keyframes`（UnoCSS 不管 keyframe）

---

## 1. 核心规则（必读）

### 1.1 优先级顺序

按下列优先级使用，**前面的能解决问题就不要用后面的**：

1. **UnoCSS shortcut**（`uno.config.ts` 里定义的 `cf-*` 类）
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

### 1.3 命名体系（cf-* vs ui-* 二选一）

**项目已确定**：所有新写代码用 **`cf-*` shortcut**（定义在 `uno.config.ts`）。

**`.ui-*` 体系**（`src/style/_common.scss`）**仅用于**：
- 第三方组件（Element Plus）需要**非 scoped** 样式时
- 老代码逐步迁移期间，**不能新增** `.ui-*` 类

**判定**：写新类之前先看 `uno.config.ts` 的 `shortcuts` 块——**已经有就别写第二遍**。

---

## 2. 快速参考

### 2.1 常用 shortcut 速查表

完整列表见 `uno.config.ts`，高频用到的：

| 用途 | 类名 | 替代手写 |
|------|------|----------|
| 主按钮 | `cf-btn-primary` | `px-4 py-2 rounded-md ...` 8 行 |
| 次按钮 | `cf-btn` | 同上 7 行 |
| 小按钮 | `cf-btn-small` | `px-2.5 py-1.5 ...` 6 行 |
| 图标按钮 | `cf-btn-icon` | `w-9 h-9 flex ...` 5 行 |
| 卡片容器 | `cf-card` | `bg-[var(--bg-card)] border ...` 3 行 |
| 卡片头 | `cf-card-header` | `flex items-center gap-3 px-5 py-4 ...` 4 行 |
| 卡片内容 | `cf-card-content` | `p-5` 1 行 |
| 弹性列 | `cf-flex-col` | `flex flex-col` 2 行 |
| 文本副 | `cf-text-muted` | `text-[var(--text-muted)]` 1 行（也 OK） |
| 文本次 | `cf-text-secondary` | `text-[var(--text-secondary)]` 1 行（也 OK） |
| 徽章 | `cf-badge` | `px-2 py-0.5 ...` 6 行 |
| 输入框 | `cf-input` | `w-full px-3.5 py-2.5 ...` 7 行 |
| 加载态 | `cf-loading` | `absolute inset-0 flex ...` 5 行 |

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

**症状**：老代码用 `.ui-btn` / `.ui-card`，新代码用 `cf-btn` / `cf-card`，同一项目里**两套都活**。

**风险**：新人不知道用哪套，PR 审查会扯皮。

**修法**：逐步把 `.ui-*` 迁到 `cf-*`，**禁止新增** `.ui-*` 类。

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

### 4.3 🔴 第 3 波：体系合并（高风险，最后做）

**改动范围**：`_common.scss` 整文件 + 8 个 view 的类名替换 + 全局 grep 验证。

1. **决策**：保留 `cf-*` 砍 `ui-*`（推荐），还是反过来。
2. `src/style/_common.scss` 删除 / 改名为 `_legacy-ui.scss`。
3. 全项目 grep `.ui-btn` / `.ui-card` / `.ui-tag` / `.ui-input` / `.ui-badge` / `.ui-scrollbar` → 替换为对应 `cf-*`。
4. 全项目 grep `cf-*` 确保和 `uno.config.ts` 100% 对应。
5. 8 个 view 文件的 `:deep` EP 覆盖**全部移入** `src/style/_element-plus.scss`。
6. 全文搜 `style="..."` 静态内联 → 0 命中。

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
