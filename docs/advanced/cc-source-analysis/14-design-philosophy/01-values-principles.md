# 5 价值观 13 原则：Claude Code 的"宪法"

> 每个 Agent 框架都会做工具调用、记忆、子 Agent，但 Claude Code 是唯一一个把"应该怎么做"和"绝不能怎么做"写成宪法级文档的框架。从 `prompts.ts` 的 915 行系统提示词、`cyberRiskInstruction.ts` 的 Safeguards 红线，到 `undercover.ts` 的"不要暴露身份"，安全不是 afterthought——它是系统的第一层。

你好，我是江小湖。

上一章 [可观测性](../13-telemetry/README.md) 拆解了三层 Sink 如何让 Claude Code "看得见自己"。但看得见之后呢？数据告诉你了什么？这一切要回到源头——Anthropic 在设计 Claude Code 时，到底设了哪些"不准违反"的底线。

这就是本章要讲的：**5 个核心价值 + 13 条设计原则**，我们叫它 Claude Code 的"宪法"。和其他 Agent 框架不同，Claude Code 的设计哲学不是散文式的经验总结，而是直接写入代码——每一行系统提示词、每一个 feature flag、每一个 `USER_TYPE === 'ant'` 分支，都是 An Anthropic 内部原则的外化。

## 目录

- [价值观层：5 个核心理念](#价值观层5-个核心理念)
- [原则层：13 条工程法则](#原则层13-条工程法则)
- [代码中的宪法](#代码中的宪法)
- [从原则到代码的映射](#从原则到代码的映射)
- [总结](#总结)
- [参考链接](#参考链接)

## 价值观层：5 个核心理念

Claude Code 的价值观不是贴在飞书首页的标语——它们藏在 `prompts.ts` 的每一段提示词里，藏在 `cyberRiskInstruction.ts` 的 1549 字节红线里，藏在 `undercover.ts` 的 "Do Not Blow Your Cover" 里。

### 价值观 1：安全第一（Safety First）

这是最顶层、最硬性的价值观。不是"建议安全"，而是"安全是 absolute requirement"。

**代码证据**——`src/constants/cyberRiskInstruction.ts`：

```typescript
/**
 * IMPORTANT: DO NOT MODIFY THIS INSTRUCTION WITHOUT SAFEGUARDS TEAM REVIEW
 *
 * If you need to modify this instruction:
 *   1. Contact the Safeguards team (David Forsythe, Kyla Guru)
 *   2. Ensure proper evaluation of the changes
 *   3. Get explicit approval before merging
 */
export const CYBER_RISK_INSTRUCTION = `IMPORTANT: Assist with authorized security
testing, defensive security, CTF challenges, and educational contexts. Refuse
requests for destructive techniques, DoS attacks, mass targeting, supply chain
compromise, or detection evasion for malicious purposes. ...`
```

这个文件直接受 Safeguards 团队管控——不是产品经理、不是工程师，而是独立的 AI 安全团队。任何修改必须先经过他们的 review + evaluation + 显式批准。其他所有系统提示词片段都可以通过 `feature()` flag 远程开关，只有这个文件是硬编码的常量。

**背后的决策**：安全不是可 A/B 测试的 feature。就像飞机的氧气面罩不会因为"用户反馈感到不便"就被移除一样，这个指令的修改权限被锁定在组织架构的最顶层。

### 价值观 2：人类监督（Human Oversight）

Claude Code 的权限系统有三个层级（详见 [10-权限系统](../10-permissions/README.md)），但核心设计哲学是：**Agent 可以提建议，只有人类能做最终决定**。

体现在 `prompts.ts` 的 `getActionsSection()` 里：

```typescript
// constants/prompts.ts — getActionsSection()

`Carefully consider the reversibility and blast radius of actions. ...
For actions like these, consider the context, the action, and user
instructions, and by default transparently communicate the action
and ask for confirmation before proceeding. ...

A user approving an action (like a git push) once does NOT mean that
they approve it in all contexts, so unless actions are authorized
in advance in durable instructions like CLAUDE.md files, always
confirm first.`
```

关键设计：**一次性批准不等于持久授权**。`git push` 这次批准了，下次还得问。除非你把规则写在 `CLAUDE.md` 里。这和某些 Agent 框架"一旦信任就全放开"的做法形成鲜明对比。

### 价值观 3：谨慎行动（Measured Action）

"Measure twice, cut once"——这是 Claude Code 的行为准则。不是"想用户之所想、提前做优化"，而是"做被要求的、不做没被要求的"。

```typescript
// constants/prompts.ts — getSimpleDoingTasksSection()

`Don't add features, refactor code, or make "improvements" beyond what was
asked. A bug fix doesn't need surrounding code cleaned up. ...
Don't add docstrings, comments, or type annotations to code you didn't change.`
```

这听起来"懒惰"，但背后有深思熟虑：Agent 每次额外的"优化"都是潜在的 bug 来源。当 Agent 主动给你的代码加类型注解、修代码风格、重构周围逻辑时，它可能在引入你不需要也不想要的变更。**最小干预 = 最小风险**。

### 价值观 4：透明诚实（Transparent Honesty）

```typescript
// constants/prompts.ts — ant-only section

`Report outcomes faithfully: if tests fail, say so with the relevant output;
if you did not run a verification step, say that rather than implying it
succeeded. Never claim "all tests pass" when output shows failures, never
suppress or simplify failing checks (tests, lints, type errors) to manufacture
a green result, and never characterize incomplete or broken work as done.

Equally, when a check did pass or a task is complete, state it plainly —
do not hedge confirmed results with unnecessary disclaimers, downgrade
finished work to "partial," or re-verify things you already checked.
The goal is an accurate report, not a defensive one.`
```

这段注释标注为 `// @[MODEL LAUNCH]: False-claims mitigation for Capybara v8`。模型在 v8 版本出现了 29-30% 的不实声明率（"test passes" 但实际失败了），所以加了这段。

同样的诚实原则也体现在另一个方向——**不能过度防御**。如果测试确实通过了，就直说，不要把完成的成果降级为"部分完成"。诚实 = 既不夸大成功，也不掩饰失败。

### 价值观 5：用户感受优先（User Experience First）

Claude Code 是给人用的，不是给机器人用的。`getOutputEfficiencySection()` 里有一段对 Anthropic 内部员工的要求，展示了对沟通体验的极致关注：

```typescript
`When making updates, assume the person has stepped away and lost the thread.
They don't know codenames, abbreviations, or shorthand you created along the
way, and didn't track your process. Write so they can pick back up cold: use
complete, grammatically correct sentences without unexplained jargon. ...

Avoid semantic backtracking: structure each sentence so a person can read it
linearly, building up meaning without having to re-parse what came before.`
```

**"Semantic backtracking"**——这个要求普通 CLI 根本不会考虑：不要写需要人倒回去重读才能理解的句子。每句话必须是线性的、自包含的。这不是 AI 的默认行为，而是经过刻意设计的结果。

## 原则层：13 条工程法则

如果说 5 个价值观是"宪法"，那 13 条原则就是"法律"——价值观给出方向，原则给出实现路径。这些原则直接决定了 `prompts.ts` 中数百行的系统提示词。

### 可缓存性原则

**原则**：系统提示词的静态部分全局缓存，动态部分单独管理。

```typescript
// constants/prompts.ts

export const SYSTEM_PROMPT_DYNAMIC_BOUNDARY =
  '__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__'

// Boundary marker separating static (cross-org cacheable) content from dynamic.
// WARNING: Do not remove or reorder this marker without updating cache logic
//   in src/utils/api.ts (splitSysPromptPrefix) and
//     src/services/api/claude.ts (buildSystemPromptBlocks)
```

`DYNAMIC_BOUNDARY` 以上的内容（价值观、行为准则、工具使用指南）对所有用户、所有 session 都一样，可以在 Anthropic 的 API 层跨组织共享 Prompt Cache。边界以下是用户专属的 `MEMORY.md` 内容、语言偏好、MCP 指令——每个 session 都不同。

**缓存命中 = 省钱 + 加速**。如果每次 API 调用都重发完整的系统提示词，成本会增加 30-40%。

### 最小化原则

**原则**：Agent 每次行动只做被要求的事，不加戏、不预判。

```typescript
`Don't create helpers, utilities, or abstractions for one-time operations.
Don't design for hypothetical future requirements. The right amount of
complexity is what the task actually requires — no speculative abstractions,
but no half-finished implementations either. Three similar lines of code
is better than a premature abstraction.`
```

"三行重复好过一个过早抽象"——这是对 YAGNI（You Ain't Gonna Need It）的极限实践。

### 风险分层原则

**原则**：并非所有操作同等危险。Claude Code 按可逆性、影响范围、可见性三个维度将操作分四类。

```typescript
`- Local, reversible: freely act (edit files, run tests)
- Destructive: always confirm (delete files, drop tables, rm -rf)
- Hard-to-reverse: always confirm (force-push, amend published commits)
- Visible to others / affects shared state: always confirm
  (push code, create PRs, send Slack messages, modify CI/CD)`
```

这不是"所有工具都要确认"，而是**可逆的随便做，不可逆的一定问**。好的权限系统不是限制最多的，而是限制恰到好处的。

### 上下文隔离原则

**原则**：父 Agent 和子 Agent 之间共享信息需要显式传递，不是全局共享。

```typescript
// constants/prompts.ts — DEFAULT_AGENT_PROMPT

`Complete the task fully — don't gold-plate, but don't leave it half-done.
When you complete the task, respond with a concise report covering what was
done and any key findings — the caller will relay this to the user.`

// enhanceSystemPromptWithEnvDetails
`Agent threads always have their cwd reset between bash calls, as a result
please only use absolute file paths.`
```

子 Agent 被灌入一个精简版的系统提示词（`enhanceSystemPromptWithEnvDetails`），不包含父 Agent 的 `getSimpleDoingTasksSection()`、`getActionsSection()` 等完整提示词。子 Agent 的输出也会被父 Agent 压缩后再注入上下文。

### 容错降级原则

**原则**：每个 feature flag 都对应一个 fallback 路径——不做硬依赖。

```typescript
const proactiveModule =
  feature('PROACTIVE') || feature('KAIROS')
    ? require('../proactive/index.js')  // 可选，不存在也能正常运行
    : null

const skillSearchFeatureCheck = feature('EXPERIMENTAL_SKILL_SEARCH')
  ? require('../services/skillSearch/featureCheck.js')
  : null  // 不存在就跳过
```

这不是简单的 `if (feature)`，而是**条件 import**。`feature('PROACTIVE')` 返回 false 时，`proactiveModule` 就是 `null`，相关的系统提示词段落就不生成——整个模块像不存在一样。

### Prompt Cache 友好原则

**原则**：所有提示词碎片按"可缓存 vs 不可缓存"组织，高频变化的内容放到边界线以下。

`getSystemPrompt()` 返回的数组里，前 7 节（`getSimpleIntroSection` 到 `getOutputEfficiencySection`）是全静态的，中间是 `DYNAMIC_BOUNDARY` 分隔线，后面是 `systemPromptSection('memory', ...)` 这种动态内容。

### Undercover 原则——身份保护

**原则**：当 Agent 在公共仓库提交代码时，绝不泄露内部代号、模型版本或项目名称。

```typescript
// utils/undercover.ts

`NEVER include in commit messages or PR descriptions:
- Internal model codenames (animal names like Capybara, Tengu, etc.)
- Unreleased model version numbers (e.g., opus-4-7, sonnet-4-8)
- Internal repo or project names
- The phrase "Claude Code" or any mention that you are an AI
- Any hint of what model or version you are`
```

这在 README 里被称为 "Do Not Blow Your Cover"。不是隐喻——是真实的 Anthropic 员工在公共仓库协作时的身份保护策略。它甚至确认了 "Tengu" 可能是 Claude Code 的代号。

### 其余 6 条原则速览

| 原则 | 代码体现 |
|------|---------|
| **信息压缩原则** | `autocompact` 保留关键决策，`microcompact` 清除冗余工具结果 |
| **幂等与可恢复** | `cronScheduler.ts` 用 lockfile 防重入；`attachAnalyticsSink` 调用是幂等 |
| **不可见但可检** | `feature('TOKEN_BUDGET')` 控制 token 预算提示词的显示/隐藏 |
| **优先修复而非绕过** | `"try to identify root causes rather than bypassing safety checks (e.g. --no-verify)"` |
| **模型友好命名** | 所有常量/变量名自带文档价值：`CYBER_RISK_INSTRUCTION`、`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` |
| **可控的自主性** | `terminalFocus: unfocused → 高度自主；focused → 协作模式` |

## 代码中的宪法

这 5 个价值观 + 13 条原则，并不是一个独立文档——它们零散地分布在 Claude Code 的各个模块里：

```text
src/constants/
├── cyberRiskInstruction.ts  ← 价值观 1（安全红线）
├── prompts.ts               ← 价值观 2-5 + 原则层的大部分
├── common.ts                ← 缓存稳定性（getSessionStartDate 的 memoize）
│
src/utils/
├── undercover.ts            ← Undercover 原则
├── claudemd.ts              ← CLAUDE.md 优先原则（127KB，最复杂的提示词加载器）
│
src/constants/
├── systemPromptSections.ts  ← 可缓存性原则（DYNAMIC_BOUNDARY 的实现）
│
src/tools/
├── BashTool/                ← 风险分层原则（安全分级：safe / moderate / dangerous）
├── FileEditTool/            ← 最小化原则（精确替换而非全文重写）
│
src/coordinator/             ← 上下文隔离原则（子 Agent 独立上下文）
```

## 从原则到代码的映射

### 案例 1：`prompts.ts` 为什么有 `USER_TYPE === 'ant'` 分支？

整个 `prompts.ts` 里有至少 8 处 `process.env.USER_TYPE === 'ant'` 的条件分支。这不是 feature flag——`USER_TYPE` 是**构建时常量**（通过 Bun 的 `--define` 注入），在外部构建中这些分支会被**死代码消除（DCE）**。

为什么分两套？
- **外部用户**：得到简洁高效的系统提示词
- **内部团队**：得到更严格的 anti-Opus 过度优化警告、不实声明防御、更积极的搜索建议

内部版本在"对抗模型行为退化"上投入更多。外部用户不需要知道 Opus v8 有不实声明问题——但内部需要防御。

### 案例 2：Safeguards 审查不是 CI check，是组织架构

```typescript
// cybeRiskInstruction.ts
// IMPORTANT: DO NOT MODIFY THIS INSTRUCTION WITHOUT SAFEGUARDS TEAM REVIEW
//   1. Contact the Safeguards team (David Forsythe, Kyla Guru)
//   2. Ensure proper evaluation of the changes
//   3. Get explicit approval before merging
```

这不是 lint 规则——它点名了两个真人的名字（David Forsythe, Kyla Guru）。修改这个文件需要在合并前经过他们的人工审查。和大多数开源项目"有测试通过就合并"的流程完全不在一个层级。

### 案例 3：CLAUDE.md 的保护机制

CLAUDE.md 是用户指令的持久化载体，但它也是最脆弱的环节——一旦被覆盖就会丢失所有定制。Claude Code 为此设计了多层保护：

```typescript
// claudemd.ts 的加载顺序
// 1. Managed memory (/etc/claude-code/CLAUDE.md) — 全局
// 2. User memory (~/.claude/CLAUDE.md) — 用户级
// 3. Project memory (CLAUDE.md, .claude/CLAUDE.md, .claude/rules/*.md)
// 4. Local memory (CLAUDE.local.md) — 本地
//
// 加载顺序与优先级相反：后加载的覆盖先加载的
```

同时，`memdir/memdir.ts` 有 `MAX_ENTRYPOINT_LINES = 200` 和 `MAX_ENTRYPOINT_BYTES = 25_000` 两个硬限制，防止 MEMORY.md 膨胀到破坏缓存。

## 总结

Claude Code 的设计哲学不同于大多数 Agent 框架的关键在于：**设计原则不是文章里写的，是代码里编译进去的**。

五个核心价值观（安全第一、人类监督、谨慎行动、透明诚实、用户感受）和十三条工程法则不像大多数项目那样存在于 README 或设计文档中，而是直接编译进了系统提示词、feature gate 和安全规则里。

理解这些原则，才能真正理解 Claude Code 的架构——每当你看到一个 `if (process.env.USER_TYPE === 'ant')`，那不是临时 hack，那是组织架构在代码中的投影。

下一章 [工程取舍](./02-tradeoffs.md) 将继续深入，看 Undercover Mode、监督悖论和模型 vs 工程的边界这三个具体案例。

## 参考链接

- `src/constants/cyberRiskInstruction.ts` — Safeguards 安全红线（1549 字节）
- `src/constants/prompts.ts` — 915 行系统提示词（价值观的全部外化）
- `src/utils/undercover.ts` — Undercover"不暴露身份"机制
- `src/utils/claudemd.ts` — CLAUDE.md 加载优先链
- `src/constants/systemPromptSections.ts` — Prompt Cache 管理
- `src/tools/BashTool/` — 安全分级实现
- `src/constants/system.ts` — Ant 模型覆盖配置
