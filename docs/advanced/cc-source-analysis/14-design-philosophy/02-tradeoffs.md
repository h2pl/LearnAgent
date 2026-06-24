# 工程取舍：Undercover Mode、监督悖论与模型-工程的边界

> 设计哲学不是只有"做什么"，更重要的往往是"不做什么"。Claude Code 的代码里藏着三个最值得讨论的取舍：Undercover Mode 如何用"信息阻断"对抗身份泄露的熵增趋势、监督悖论中如何在信任与验证之间找到平衡点、以及为什么把上下文压缩做成系统级而非模型级。

你好，我是江小湖。

[上一篇文章](./01-values-principles.md) 讲了 Claude Code 的 5 个价值观和 13 条原则如何在代码中落地。但原则之间有时会互相冲突——安全 vs 效率、自主 vs 监督、模型能力 vs 工程基建。真正的工程智慧不在原则本身，而在原则之间的**取舍**。

本文深入三个具体的取舍案例，每个都揭示了 Claude Code 团队对 Agent 系统本质的理解。

## 目录

- [Undercover Mode：信息阻断的艺术](#undercover-mode信息阻断的艺术)
- [监督悖论：信任与验证的平衡](#监督悖论信任与验证的平衡)
- [模型 vs 工程的边界](#模型-vs-工程的边界)
- [Anti-Distillation：反向蒸馏保护](#anti-distillation反向蒸馏保护)
- [KAIROS：未公开的自主模式](#kairos未公开的自主模式)
- [Feature Flag 工程学](#feature-flag-工程学)
- [总结](#总结)
- [参考链接](#参考链接)

## Undercover Mode：信息阻断的艺术

### 为什么需要"伪装"？

Anthropic 员工用 Claude Code 给公共开源仓库贡献代码。如果 Agent 在 commit message 里写 "1-shotted by claude-opus-4-6" 或 "Generated with Claude Code"，就暴露了：
1. 内部模型的代号和版本号
2. 存在一个名为"Claude Code"的内部工具

更微妙的是——Anthropic 可能在 GitHub 上伪装成独立开发者。README 确认了这一点：**Undercover Mode 不只是隐藏工具名，而是隐藏"使用 AI"这件事本身。**

### 设计决策 1：只有 ON，没有 OFF

```typescript
// utils/undercover.ts — isUndercover()

export function isUndercover(): boolean {
  if (process.env.USER_TYPE === 'ant') {
    if (isEnvTruthy(process.env.CLAUDE_CODE_UNDERCOVER)) return true
    // Auto: active UNLESS we've positively confirmed we're in an allowlisted
    // internal repo. 'external', 'none', and null all resolve to ON.
    return getRepoClassCached() !== 'internal'
  }
  return false
}
```

核心决策：**默认是 ON，只有在确认是内部仓库时才关闭。没有强制关闭的选项。**

为什么？注释给出了答案：`// There is NO force-OFF.`——理由是"If we're not confident we're in an internal repo, we stay undercover." 宁可过度安全也不冒险。这体现了 Anthropic 的安全文化：不是"确认危险才防护"，而是"不确定安全就防护"。

### 设计决策 2：死代码消除——对外部构建完全不可见

```typescript
function getUndercoverInstructions(): string {
  if (process.env.USER_TYPE === 'ant') {
    return `## UNDERCOVER MODE — CRITICAL ...`
  }
  return ''  // 外部构建永远走这个分支
}
```

因为 `USER_TYPE` 是 Bun 构建时常量（`--define` 注入），Bun 的 dead-code elimination 会把 `if (process.env.USER_TYPE === 'ant')` 的整个分支从外部构建中移除。**外部用户甚至看不到 Undercover Mode 的提示词**——镜像仓库的 README 能看到，但使用的 npm 包里没有。

### 信息阻断的具体规则

```typescript
`NEVER include:
- Internal model codenames (animal names like Capybara, Tengu, etc.)
- Unreleased model version numbers
- Internal repo or project names
- The phrase "Claude Code" or any mention that you are an AI
- Any hint of what model or version you are
- Co-Authored-By lines or any other attribution`
```

这些不是建议——是硬规则（"NEVER"）。而且细节考虑很周全：
- **"Capybara, Tengu"** 这个名字被显式提及，确认了 Anthropic 用动物名做模型代号
- **"Co-Authored-By"** 被禁止——说明早期版本可能在这一点上出过事
- **"Any mention that you are an AI"**——这是最彻底的：commit message 应该像人类写的一样

### 这个取舍的代价

完全的信息阻断意味着 Agent 在公共仓库运行时，**额外的自我审查开销**——它必须在每次生成 commit message 时，刻意不要暴露身份。但 Anthropic 的选择是：**多花一些 token 做信息审查，远好过一次身份暴露的代价。**

## 监督悖论：信任与验证的平衡

### 悖论的定义

监督悖论（Oversight Paradox）的核心问题：

> 如果我们给 Agent 足够的能力自主工作，它就可能在不需要我们的时候做错事；如果我们每次都要求人类确认，Agent 就失去了自主工作的价值。

Claude Code 的解决方案是一个**信任梯度**：

```
完全自主 ←——————————————————————→ 完全人工
  (terminalFocus=unfocused)      (terminalFocus=focused)
  (可逆操作)                      (不可逆操作)
  (CLAUDE.md 已授权)              (首次执行)
  (低风险工具)                    (高风险工具)
```

### 维度 1：terminalFocus——用户是否在场

```typescript
// prompts.ts — getProactiveSection()

`- Unfocused: The user is away. Lean heavily into autonomous action —
  make decisions, explore, commit, push. Only pause for genuinely
  irreversible or high-risk actions.
- Focused: The user is watching. Be more collaborative — surface choices,
  ask before committing to large changes, and keep your output concise.`
```

这不是简单的是/否二元判断。**用户在场时，Agent 的行为模式从"决策者"变成"建议者"**。同样的操作（比如 `git commit`），用户在场时 Agent 会问"要提交吗？"，用户离开时 Agent 会自主提交——**同一个工具在不同情境下的权限不同。**

### 维度 2：动作可逆性

```typescript
// prompts.ts — getActionsSection()

`- Local, reversible actions (editing files, running tests): freely act
- Destructive operations (deleting files, rm -rf): ask first
- Hard-to-reverse (force-push, amend published commits): ask first
- Visible to others (push, create PRs, send Slack): ask first`
```

这里的精妙之处：**分类标准不是操作本身，而是操作的后果。**`git push` 是可逆的（`git push -f` 之前），但因为它对外可见（其他人会收到通知），所以仍需要确认。**可见性 = 需要确认 = 社交风险 > 技术风险。**

### 维度 3：授权范围——无"永久信任"

```typescript
`A user approving an action (like a git push) once does NOT
mean that they approve it in all contexts, so unless actions
are authorized in advance in durable instructions like CLAUDE.md
files, always confirm first. Authorization stands for the scope
specified, not beyond.`
```

对比某些 Agent 框架：一旦用户在权限对话框点了"Always allow"，就永久信任所有类似操作。Claude Code 的反向选择：**一次性批准只在当前 context 有效，换个 context 还得问。**

### 取舍的结果

这个设计牺牲了一些效率（每次新场景都要重新确认），但换来了一个重要的安全属性：**Agent 永远不会因为"上一次我说可以"而在错误的上下文中做出危险操作。**

## 模型 vs 工程的边界

### 核心张力

Agent 系统面临一个根本性的架构问题：

> 哪些能力应该放在模型里（via 提示词），哪些应该放在工程里（via 代码逻辑）？

回答这个问题，等于决定了整个系统的复杂度分配。Claude Code 的答案很明确：

### 应该靠模型的事情

| 任务 | 实现 | 原因 |
|------|------|------|
| 判断代码是否安全回退 | 提示词引导 | 需要理解语义，不能靠正则 |
| 选择哪些记忆与当前查询相关 | `findRelevantMemories` → Sonnet side-query | 语义匹配是模型的强项 |
| 决定何时主动联系用户 | KAIROS 规则 + 模型判断 | 社交判断需要模型 |
| commit message 的自然语言质量 | Undercover Mode 提示词 | 不能用模板 |

### 应该靠工程的事情

| 任务 | 实现 | 原因 |
|------|------|------|
| Token 计数和预算控制 | `tokenBudget.ts` 的正则解析 | 精确数学计算，模型做不好 |
| 触发 autocompact 的阈值 | 硬编码 `~167K` 触发条件 | 确定性逻辑，不能靠模型判断 |
| file lock 防止并发写 | `lockfile.ts` | 原子性保证 |
| 路径安全校验 | `memdir/paths.ts` | 防御注入攻击 |
| 事件队列的幂等排空 | `analytics/index.ts` | 数据完整性 |

### 案例：为什么上下文压缩是工程行为？

上下文压缩（compact）是全系统最重要、最影响使用体验的操作之一。一个常见的选择是把压缩逻辑交给模型："请把上面的对话总结成一段摘要"。

Claude Code 没有这样做。`analyzeContext.ts`（44313 字节）和 `collapseReadSearch.ts`（39011 字节）是两段超过 3 万行的纯工程代码，用正则、启发式规则、时间衰减算法做压缩。

**原因**：
1. **确定性**——每次压缩的结果应该可预测、可审计。靠模型做摘要，同样的输入可能得到不同的输出。
2. **成本**——每次压缩调用一次 Sonnet 做摘要，会大幅增加延迟和费用。
3. **准确性**——工程压缩可以保留精确的 key-value 对（`tool_use_id → result`），模型的摘要可能丢失细节。

### 案例：为什么记忆选择靠模型？

和压缩相反，`findRelevantMemories` 调用了一个 side-query 给 Sonnet：

```typescript
// memdir/findRelevantMemories.ts

const SELECT_MEMORIES_SYSTEM_PROMPT = `You are selecting memories that will
be useful to Claude Code as it processes a user's query. ...

Return a list of filenames for the memories that will clearly be useful
(up to 5). Only include memories that you are certain will be helpful
based on their name and description.`
```

为什么这里选择模型？因为**"哪个记忆与当前查询有关"本质上是语义匹配问题**。`"上次调试 Python 环境变量的经验"` 是否与 `"安装一个新的 npm 包"` 相关？这不只是一个关键词匹配问题。工程方法（TF-IDF、embedding 相似度）可以做初筛，但最终选择交给模型做。

### 边界判断 = 架构决策

Claude Code 的"模型 vs 工程"判断可以总结为三条启发式规则：

1. **精确计算 → 工程**（token 计数、阈值判断、原子操作）
2. **语义理解 → 模型**（相关性判断、自然语言生成、社交判断）
3. **安全约束 → 工程 + Safeguards 审查**（不能靠提示词保证安全，必须靠代码）

这三条规则决定了整个系统的复杂度分配。

## 总结

## Anti-Distillation：反向蒸馏保护

Claude Code 源码中最隐秘的机制之一，是对抗模型蒸馏的防御系统。

### 为什么需要 Anti-Distillation？

模型蒸馏（Distillation）是用大模型（teacher）的输出来训练小模型（student）的技术。如果一个竞争对手通过 Claude Code 的 API 收集大量对话数据，就可以训练出一个模仿 Claude Code 行为的竞品模型。

Anthropic 在这个问题上选择了**从数据收集阶段就主动防御**——而不是被动等待。

### 防御层 1：fake_tools

Claude Code 在 API 请求中注入了 `anti_distillation: ['fake_tools']` 标志。服务器端会在系统提示词中注入**虚构的工具定义**。任何基于抓取 API 流量来训练模型的竞争对手，会把这些虚假工具定义当成真实的工具 schema。训练出的模型会尝试调用不存在的工具——导致行为异常。

### 防御层 2：CONNECTOR_TEXT

第二层防御在服务器端：模型生成的文本在两个工具调用之间被缓冲、摘要并用加密签名签名，然后只返回摘要给 API 流量记录器（而非完整的 reasoning chain）。即使竞争对手拦截 API 流量，也只能得到摘要，得不到完整的推理链。

这两个机制的设计哲学是相同的——**不阻止蒸馏，而是让蒸馏的结果不可靠**。与其在法律上追诉，不如让偷数据的人得到劣质模型。

### 取舍代价

Anti-distillation 增加了每次请求的 token 开销（fake_tools 需要额外的系统提示词空间），也增加了服务端延迟（CONNECTOR_TEXT 的摘要计算）。但 Anthropic 的判断是：**这些开销远低于模型被成功蒸馏的商业损失。**

## KAIROS：未公开的自主模式

源码中隐藏着一个完整的自主 Agent 模式——KAIROS。它在 feature flag 后面被锁定，但代码已经完整实现。

### 24/7 自主运行

```typescript
// 概念性——KAIROS 的核心循环
// 每隔几秒收到一个 tick prompt："anything worth doing right now?"
// Agent 评估当前状态 → 决定行动或保持静默
```

KAIROS 有三个独占工具：
- **Push notifications**：即使用户关闭终端，也能推送到桌面或手机
- **File delivery**：主动创建和发送文件
- **PR subscriptions**：监控 GitHub 并自主响应代码变更

它保持只追加的每日日志（不可删除），每晚运行 autoDream（已在第 08 章详述）来整理记忆。

### 工程取舍：主动性 vs 克制

KAIROS 最深的工程挑战不是"能不能做事"，而是"什么时候不做"。一个 24/7 运行的 Agent 如果过于主动，会变成噪音；如果过于被动，就失去了自主性的价值。

代码中的解决方案：**tick 系统不携带上下文**——每次 tick 都是 fresh start，Agent 必须从状态文件中读取当前情况，然后独立决定是否行动。这确保了 KAIROS 不会因为"刚才做了一件好事"就陷入无限循环的自夸。

## Feature Flag 工程学

Claude Code 源码中有 44 个 feature flag 和 20+ 个未发布的特性。这不是偶然的——这是一种设计哲学：**构建完整功能，然后慢慢打开。**

### Flag 驱动架构

```typescript
// 典型的 feature flag 模式
const proactive = feature('PROACTIVE') || feature('KAIROS')
  ? require('./commands/proactive.js').default
  : null

// COMMANDS() 中：
...(proactive ? [proactive] : [])
```

这种模式的好处：
1. **完整的 Dead Code Elimination**——未启用的功能在外部构建中完全消失
2. **渐进式发布**——内部团队先使用，收集数据，然后决定是否公开
3. **A/B 测试**——同一个功能可以用 GrowthBook 在用户群中做实验
4. **紧急关闭**——出问题时 growthbook 可以远程关机，不需要重新发布 npm 包

### 风险

44 个 flag 的交互矩阵在理论上可能有 `2^44` 种组合。实际中 Anthropic 用"flag 组合在 CI 中测试"来管理这种复杂性——但这也是潜在的测试噩梦。

## 总结

三个核心取舍 + 两个隐藏机制 + flag 工程学，揭示了 Claude Code 团队的工程哲学：

1. **Undercover Mode**：安全设计 = "宁可过度防御，不可事后修复"。默认 ON、不可关闭、完全编译时消除。
2. **监督悖论**：信任是**多维梯度**——用户在场、操作可逆性、授权范围、上下文一致性，四维度同时判断。
3. **模型-工程边界**：精确计算 → 工程；语义理解 → 模型；安全 → 工程 + 人工审查。
4. **Anti-Distillation**：不阻止蒸馏，而是让蒸馏的结果不可靠。数据收集阶段主动防御优先于事后追诉。
5. **Feature Flag 工程**：完整构建 → 渐进式打开 → DCE 保护。44 个 flag 管理功能的生命周期。

这些取舍不是代码补丁——它们是 Claude Code 设计哲学的核心 DNA。理解它们，才能理解为什么代码中到处都是 `USER_TYPE === 'ant'`、`feature('...')`、和 `### WARNING: DO NOT REMOVE`——这些都是原则在代码中的投影。

> 学完本章后，请继续阅读 [15 — CLI 命令系统](../15-cli-commands/README.md)，看 Claude Code 如何将 40+ slash 命令的复杂系统设计为可扩展的插件架构。

## 参考链接

- `src/utils/undercover.ts` — Undercover Mode 的完整实现
- `src/constants/prompts.ts` — 系统提示词中的安全与信任原则
- `src/constants/cyberRiskInstruction.ts` — Safeguards 安全红线
- `src/utils/analyzeContext.ts` — 上下文压缩的工程实现（44313 字节）
- `src/memdir/findRelevantMemories.ts` — 记忆选择的模型侧实现
- `src/utils/tokenBudget.ts` — Token 预算解析
- `src/utils/fastMode.ts` — Fast Mode 的工程决策
