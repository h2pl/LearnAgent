# Agent 循环

> Claude Code 的核心是一个 88 行的 while 循环。但 `query.ts` 用 1612 行处理边界情况：输出截断、上下文溢出、工具失败、压缩重试，让模型驱动的循环能在生产环境里稳定运行。

你好，我是江小湖。

上一章 [初始化与 REPL](../02-startup-flow/03-initialization.md) 讲到，Claude Code 启动后会渲染 REPL 界面。从用户按下回车的那一刻起，真正的 Agent 工作才开始。这一阶段的核心就是 **Agent 循环**。

## 目录

- [循环的本质](#循环的本质)
- [状态机设计](#状态机设计)
- [Withholding 机制](#withholding-机制)
- [7 种继续原因](#7-种继续原因)
- [错误恢复](#错误恢复)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/03-agent-loop/loop-flow.svg" alt="Agent 循环" width="90%"/>
  <br/>
  <em>感知 → 决策 → 行动的 while 循环</em>
</p>



<p align="center">
  <img src="../../../../assets/cc-source-analysis/03-agent-loop/turn-state.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 03-agent-loop 配图</em>
</p>
## 循环的本质

Agent 循环的逻辑可以简化成下面这段代码：

```typescript
// query.ts 核心逻辑（高度简化）
while (true) {
  const response = await callModel(messages);

  if (response.tool_use) {
    const results = await runTools(response.tool_use);
    messages.push(...results);
  }

  if (response.stop_reason === 'end_turn') {
    break;
  }
}
```

模型读取上下文，决定下一步调用哪个工具。工具执行完成后，结果又被塞回上下文。模型再读、再决定、再调用，直到它主动停下来。

这就是 Claude Code 的 Kernel——一个由模型驱动的 while 循环。没有显式的 planner，没有状态机图，没有复杂的控制流。

但这只是"理想情况"。实际的 `query.ts` 有 1612 行，因为它要处理各种会让循环中断的边界情况。

## 状态机设计

循环状态用一个可变对象 `State` 跨迭代携带：

```typescript
// query.ts 中的 State 类型
type State = {
  messages: Message[]
  toolUseContext: ToolUseContext
  autoCompactTracking: AutoCompactTrackingState | undefined
  maxOutputTokensRecoveryCount: number
  hasAttemptedReactiveCompact: boolean
  maxOutputTokensOverride: number | undefined
  pendingToolUseSummary: Promise<ToolUseSummaryMessage | null> | undefined
  stopHookActive: boolean | undefined
  turnCount: number
  transition: Continue | undefined
}
```

每次迭代开始时，循环会解构这个状态对象。处理完后，用新的状态对象替换旧的，进入下一次迭代。

这种设计让循环的边界情况处理变得清晰：每个 continue site 都负责一种特定的恢复路径，而不是在一个巨大的函数里堆砌所有逻辑。

## Withholding 机制

Withholding 是 `query.ts` 里一个非常精妙的设计。它的作用是：**在确认能否恢复之前，不要把错误暴露给上层。**

比如当模型输出因 `max_output_tokens` 被截断时，流式返回里会出现一个错误消息。如果直接把它交给用户或 SDK 调用方，会话可能直接终止。Claude Code 选择先把它"扣留"下来，尝试恢复：

```typescript
// query.ts（简化）
let withheld = false
if (isWithheldMaxOutputTokens(message)) {
  withheld = true
}

// 只有无法恢复时才 yield 被扣留的错误
if (无法恢复) {
  yield withheldErrorMessage
  return { reason: 'max_output_tokens_recovery_failed' }
}
```

类似地，`prompt_too_long` 错误也会被 Withholding，然后尝试响应式压缩或上下文折叠。

这个设计对应了一个生产级原则：**不要让中间状态误杀整个会话。** 很多 recoverable 的错误都应该有一次自救机会。

## 7 种继续原因

循环在每次迭代结束时，会记录一个 `transition.reason`，说明为什么进入下一次迭代。源码里能看到这些 reason：

| reason | 含义 |
|--------|------|
| `next_turn` | 正常进入下一轮 |
| `reactive_compact_retry` | 响应式压缩后重试 |
| `collapse_drain_retry` | 上下文折叠排空后重试 |
| `max_output_tokens_escalate` | 输出 token 上限提升后重试 |
| `max_output_tokens_recovery` | 输出截断后恢复 |
| `token_budget_continuation` | 任务预算内继续 |
| `stop_hook_blocking` | stop hook 阻塞后重试 |

这些 reason 不是装饰，而是调试和测试的关键抓手。通过检查 `transition.reason`，测试可以断言某条恢复路径确实被触发了，而不需要检查消息内容。

## 错误恢复

Claude Code 的循环有 7 层恢复策略。每一层都对应一种特定的失败场景：

1. **输出截断恢复**：当 `max_output_tokens` 触发时，最多重试 3 次，逐步提升上限。
2. **响应式压缩**：当 API 返回 prompt too long 时，立即压缩上下文并重试。
3. **自动压缩**：在请求前主动压缩上下文，避免触发 API 错误。
4. **上下文折叠**：把历史消息归档成摘要，减少上下文长度。
5. **Snip 裁剪**：直接删掉早期无用的工具结果。
6. **Microcompact**：压缩单个工具结果的内容。
7. **Token 预算内继续**：任务预算模式下，自动续写直到预算耗尽。

这些策略从便宜到贵依次触发。大部分情况下，前两层就能解决问题，不需要动用最昂贵的全 session 总结。

## 总结

- Claude Code 的 Agent 循环核心是一个 88 行的 while 循环，由模型驱动。
- 实际 `query.ts` 有 1612 行，用于处理生产环境中的各种边界情况。
- 循环状态用可变 `State` 对象跨迭代携带，职责清晰。
- Withholding 机制让 recoverable 错误有一次自救机会，避免误杀会话。
- 7 种 `transition.reason` 让恢复路径可观测、可测试。
- 7 层错误恢复策略从便宜到贵依次触发，保证长对话稳定。

> 下一篇：[工具系统](../04-tool-system/01-tool-basics.md)，看 Claude Code 如何把 42 个工具组织成一套可扩展的执行体系。

## 参考链接

- [Claude Code Agent 循环源码](file:///E:/Projects/claude-code/src/query.ts)
- [Claude Code 工具编排源码](file:///E:/Projects/claude-code/src/services/tools/toolOrchestration.ts)
- [Dive into Claude Code — MBZUAI/UCL 论文](https://arxiv.org/abs/2604.14228)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
