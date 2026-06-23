# callModel 架构

> `services/api/claude.ts` 有 3420 行，是 Claude Code 最长的单文件。它统一了流式调用、重试、Prompt 缓存保护、Token 追踪和多模型路由——把 LLM 调用变成一条整洁的管线。

你好，我是江小湖。

上一篇 [关键工具实现](../04-tool-system/04-key-tools.md) 讲到 BashTool、FileEditTool 和 AgentTool 的设计取舍。这一篇进入更底层的一层：Agent 循环调用模型时，到底经过了什么。

## 目录

- [3420 行的职责分解](#3420-行的职责分解)
- [流式调用：从 queryModelWithStreaming 到 SSE 解析](#流式调用从-querymodelwithstreaming-到-sse-解析)
- [消息规范化：11 步预处理](#消息规范化11-步预处理)
- [重试策略：withRetry 的 10 次机会](#重试策略withretry-的-10-次机会)
- [Token 追踪与成本核算](#token-追踪与成本核算)
- [总结](#总结)
- [参考链接](#参考链接)

## 3420 行的职责分解

`claude.ts` 不是一个"API 调用工具"——它是一个完整的调用管线。按照职责可以分成六个阶段：

| 阶段 | 核心函数 | 做什么 |
|------|---------|--------|
| **消息预处理** | `normalizeMessagesForAPI` | 压缩、去重、配对 tool_use/tool_result |
| **系统提示拼装** | `buildSystemPromptBlocks` | 动态注入模式、工具描述、上下文 |
| **Latch 判定** | 4 个 setXxxLatched | 决定哪些 beta header 需要锁定 |
| **流式执行** | `queryModelWithStreaming` | 发起 SSE 请求、解析事件流 |
| **重试恢复** | `withRetry` | 处理 401/429/529、token 刷新、Fallback |
| **结果后处理** | `accumulateUsage` | 统计 token 消耗、计算成本 |

Agent 循环调用时只需要传消息列表、系统提示词、工具列表和配置，剩下的全部由 `claude.ts` 内部处理。

## 流式调用：从 queryModelWithStreaming 到 SSE 解析

核心调用函数是 `queryModelWithStreaming`，它是一个 async generator：

```typescript
export async function* queryModelWithStreaming({
  messages,
  systemPrompt,
  thinkingConfig,
  tools,
  signal,
  options,
}: QueryModelParams): AsyncGenerator<StreamEvent, AssistantMessage> {
  // 1. 预处理消息
  messagesForAPI = normalizeMessagesForAPI(messages)
  messagesForAPI = ensureToolResultPairing(messagesForAPI)

  // 2. 拼装系统提示词
  systemPrompt = asSystemPrompt([
    getAttributionHeader(fingerprint),
    ...systemPrompt,
  ])

  // 3. 构建缓存的 system blocks
  const system = buildSystemPromptBlocks(systemPrompt, enablePromptCaching)

  // 4. 发起流式请求
  const stream = await client.beta.messages.stream({...})

  // 5. 逐事件 yield
  for await (const event of stream) {
    yield { type: 'content_block_delta', ... }
  }
}
```

它的返回值是一个 `AsyncGenerator<StreamEvent, AssistantMessage>`——在流式传输过程中持续 yield 事件，流结束时返回完整的 `AssistantMessage`。Agent 循环通过 `for await...of` 消费这个 generator，每收到一个 delta 就更新 UI。

## 消息规范化：11 步预处理

在调用 API 之前，消息列表经过 `normalizeMessagesForAPI` 的 11 步处理：

1. **压缩 tool_result**：超长的工具结果被替换为文件路径引用
2. **Snip 裁剪**：删除早期无用的孤儿工具结果
3. **Microcompact**：按 `tool_use_id` 压缩单个结果
4. **Context Collapse**：把多轮对话折叠成摘要
5. **Autocompact**：调用 LLM 做全对话总结（最昂贵的一步）
6. **Strip 内部字段**：移除 `_simulatedSedEdit` 等内部标记
7. **配对校验**：`ensureToolResultPairing` 确保每个 tool_use 都有对应结果
8. **Strip advisor blocks**：如果没有 advisor beta header，移除 advisor 内容
9. **Strip 超量媒体**：超过 100 个媒体项时删除最旧的
10. **注入延迟工具名**：如果启用了 ToolSearch，插入 deferred tool 列表
11. **Fingerprint**：计算第一条用户消息的指纹，用于遥测

这 11 步的目标是一致的：**在模型看到消息之前，把消息变成它最容易处理的形态**。

## 重试策略：withRetry 的 10 次机会

`withRetry` 是 Claude Code 的重试引擎，支持最多 10 次重试：

```typescript
const DEFAULT_MAX_RETRIES = 10
const BASE_DELAY_MS = 500
const MAX_529_RETRIES = 3
```

| 错误类型 | 重试策略 | 特殊处理 |
|---------|---------|---------|
| 401 Unauthorized | 刷新 OAuth token 后重试 | 清除 client 缓存 |
| 403 Token Revoked | 同 401 | 另一个进程可能刷新了 token |
| 429 Rate Limit | 指数退避重试 | persistent 模式下无限重试 |
| 529 Overloaded | 最多 3 次 | 非前台任务直接跳过 |
| ECONNRESET/EPIPE | 禁用 Keep-Alive 后重试 | 旧连接失效 |
| Bedrock/Vertex 认证错误 | 清除凭证缓存后重试 | 环境凭证可能过期 |

529 重试有一个精妙的设计：**只有前台任务才重试**。`shouldRetry529` 检查 `querySource`，像 `compact`、`classifier`、`summary` 这类后台任务遇到 529 直接放弃——用户不感知失败，且每次重试会在网关层放大 3-10 倍负载。

`CannotRetryError` 和 `FallbackTriggeredError` 是两个特殊的错误类。前者表示"这个错误无法重试"（比如输入验证错误、内容安全拦截），后者表示"已经切换到备选模型"。

## Token 追踪与成本核算

`claude.ts` 在每次 API 调用后通过 `accumulateUsage` 统计 token 消耗：

```typescript
export function accumulateUsage(
  current: BetaUsage,
  delta: BetaMessageDeltaUsage,
): BetaUsage {
  return {
    input_tokens: (current.input_tokens || 0) + (delta.input_tokens || 0),
    output_tokens: (current.output_tokens || 0) + (delta.output_tokens || 0),
    cache_read_input_tokens:
      (current.cache_read_input_tokens || 0) +
      (delta.cache_read_input_tokens || 0),
    cache_creation_input_tokens:
      (current.cache_creation_input_tokens || 0) +
      (delta.cache_creation_input_tokens || 0),
  }
}
```

Token 统计是累加的——流式响应的每个 delta 都带有增量 token 信息，全部累加起来得到本次调用的总消耗。

成本核算在 `calculateUSDCost` 中完成，根据模型名匹配对应的定价表，乘以 token 数量得到 USD 成本，最后通过 `addToTotalSessionCost` 累加到会话总成本中。如果设置了 `maxBudgetUsd`，超出预算后 Agent 循环会收到预警。

## 总结

- `claude.ts` 是 3420 行的 LLM 调用管线，按职责分为消息预处理、系统提示拼装、Latch 判定、流式执行、重试恢复、结果后处理六个阶段。
- 消息在调用前经过 11 步规范化，目标是把消息变成模型最容易处理的形态。
- `withRetry` 支持最多 10 次重试，529 错误只有前台任务才重试，后台任务直接放弃。
- `CannotRetryError` 标记不可重试的错误，`FallbackTriggeredError` 标记已切换到备选模型。
- Token 统计是累加的，成本核算按模型定价表实时计算并累加到会话预算中。

> 下一篇：[Sticky-on Latch](./02-sticky-latch.md)，看 Claude Code 如何通过 4 个 Latch 保护 50-70K token 的 Prompt Cache 不被意外清空。

## 参考链接

- [Claude Code claude.ts 源码](file:///E:/Projects/claude-code/src/services/api/claude.ts)
- [Claude Code withRetry.ts 源码](file:///E:/Projects/claude-code/src/services/api/withRetry.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
