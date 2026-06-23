# Fallback 与多模型路由

> Claude Code 不是死磕一个模型。当主模型不可用时，`withRetry` 会抛出 `FallbackTriggeredError`，Agent 循环捕获后切换到备选模型。切换时要清除 thinking 签名、重建系统提示词、重置 token 限制——不是简单的"换一个 API Key"。

你好，我是江小湖。

上一篇 [Sticky-on Latch](./02-sticky-latch.md) 讲到 4 个 Latch 保护 Prompt Cache。这一篇看另一个维度的容错：当模型不可用时，Claude Code 如何自动切换。

## 目录

- [Fallback 触发链路](#fallback-触发链路)
- [切换时的 5 项清理工作](#切换时的-5-项清理工作)
- [多模型路由：不止一个备胎](#多模型路由不止一个备胎)
- [Opus 降级：智能切换](#opus-降级智能切换)
- [Agent 级别模型覆盖](#agent-级别模型覆盖)
- [总结](#总结)
- [参考链接](#参考链接)

## Fallback 触发链路

Fallback 的触发是一个两阶段过程。首先 `withRetry` 在重试耗尽后抛出 `FallbackTriggeredError`：

```typescript
// withRetry.ts — 简化逻辑
export async function* withRetry<T>(...) {
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      const result = await operation(client, attempt, retryContext)
      return result
    } catch (error) {
      if (error instanceof CannotRetryError) throw error
      if (isTransientCapacityError(error) && consecutive529Errors >= MAX_529_RETRIES) {
        // 529 重试耗尽 → 触发 Fallback
        throw new FallbackTriggeredError(options.model, options.fallbackModel)
      }
      lastError = error
      await sleep(BASE_DELAY_MS * 2 ** (attempt - 1))
    }
  }
  // 所有重试耗尽 → 触发 Fallback
  throw new FallbackTriggeredError(options.model, options.fallbackModel)
}
```

然后 Agent 循环的 `query.ts` 捕获这个异常：

```typescript
// query.ts — Fallback 处理
try {
  for await (const event of queryModelWithStreaming({...})) {
    // 正常流式处理
  }
} catch (error) {
  if (error instanceof FallbackTriggeredError) {
    // 切换到备选模型，重建系统提示
    currentModel = error.fallbackModel
    systemPrompt = rebuildSystemPrompt(currentModel)
    // 重新发起请求
    continue
  }
  throw error
}
```

关键点：**Fallback 对 Agent 循环是透明的**——循环不知道发生了什么，只是被要求换一个模型再试。这保证了 Fallback 不影响 Agent 的决策逻辑。

## 切换时的 5 项清理工作

模型切换不是简单的"换一个 model 参数"。Claude Code 需要做 5 项清理：

### 1. 清除 Thinking 签名

不同模型的 thinking 能力不同。Opus 支持 extended thinking，Sonnet 支持 adaptive thinking，Haiku 根本不支持 thinking。如果切换到不兼容的模型，需要清除 thinking 配置：

```typescript
// 概念示意
if (!modelSupportsThinking(fallbackModel)) {
  thinkingConfig = { type: 'disabled' }
}
```

### 2. 重建系统提示词

系统提示词中包含模型特定的指令。比如某些 beta header 只在第一方 API 上生效。切换模型后需要重新拼装系统提示词。

### 3. 重置 Token 限制

不同模型的 `max_output_tokens` 上限不同。Opus 最大 32K，Sonnet 最大 64K，Haiku 最大 8192。`maxOutputTokensOverride` 需要重新计算。

### 4. 清除 Latch 状态（部分）

Fast mode header 只在第一方 API 上支持。如果 Fallback 到了第三方 API，`fastModeHeaderLatched` 需要关闭。

### 5. 更新 Prompt 缓存策略

不同模型的 Prompt Cache TTL 和 scope 可能不同。切换到新模型后，缓存策略需要重新计算。

## 多模型路由：不止一个备胎

Claude Code 的模型路由不是简单的"主→备"两级切换。它有多个备选路径：

```
主模型 (如 claude-sonnet-4-6)
  ↓ 529 超限 / 502 错误
备选 1: Opus 降级 (claude-opus-4-6)
  ↓ 仍然失败
备选 2: 第三方 API (如 Bedrock/Vertex)
  ↓ 仍然失败
备选 3: Sonnet fallback (claude-sonnet-4-5)
```

每次 Fallback 都会缩小模型的参数规模或切换到备用 API 提供商。这个优先级链保证了：只要还有一个可用的 Claude 模型，Agent 就不会停。

`getAPIProvider()` 函数决定当前使用哪个 API 提供商——Anthropic 第一方、AWS Bedrock、GCP Vertex。如果第一方 API 不可用，`withRetry` 中的 `getClient()` 会自动尝试切换到其他提供商。

## Opus 降级：智能切换

Opus 是一个特殊场景——它比 Sonnet 更强大但也更昂贵。Claude Code 只有在特定任务上才使用 Opus：

```typescript
// 概念示意
function shouldUseOpus(task: string): boolean {
  return task.includes('architecture') ||
         task.includes('refactor') ||
         task.includes('design')
}
```

如果 Opus 遇到 529，Fallback 会先尝试切换到 Sonnet。Sonnet 可以处理相同的任务，只是质量可能稍低——但这比完全失败要好。

对于非 Opus 特定的任务，Claude Code 默认使用 Sonnet。Sonnet 的 Fallback 路径更短：Sonnet → Bedrock Sonnet → Vertex Sonnet → 降级 Haiku（仅小任务）。

## Agent 级别模型覆盖

每个 Agent 可以单独指定模型。子 Agent 可能用更小的模型（如 Haiku）做简单任务：

```typescript
// AgentTool 的配置
export const GENERAL_PURPOSE_AGENT = defineAgent({
  model: 'claude-haiku-4-5',  // 子 Agent 用轻量模型
  // ...
})
```

这意味着 Fallback 也是按 Agent 粒度执行的。主 Agent 的 Fallback 不影响子 Agent，反之亦然。每个 Agent 的模型切换都是独立的。

## 总结

- Fallback 由 `withRetry` 的重试耗尽触发，抛出 `FallbackTriggeredError`，Agent 循环透明处理。
- 切换模型需要 5 项清理：清除 thinking 签名、重建提示词、重置 token 限制、清除 Latch、更新缓存策略。
- 多模型路由有 4 级备选：主模型 → Opus 降级 → 第三方 API → Sonnet fallback。
- Opus 只在特定任务上使用，降级到 Sonnet 是预期路径。
- Fallback 按 Agent 粒度独立执行，子 Agent 的切换不影响主 Agent。

> 下一篇：[系统提示词动态拼装](../06-system-prompt-engineering/01-dynamic-assembly.md)，看 53KB 的提示词如何由数百个碎片在运行时组装。

## 参考链接

- [Claude Code withRetry.ts — FallbackTriggeredError](file:///E:/Projects/claude-code/src/services/api/withRetry.ts)
- [Claude Code claude.ts — queryModelWithStreaming](file:///E:/Projects/claude-code/src/services/api/claude.ts)
- [Claude Code Agent 模型配置](file:///E:/Projects/claude-code/src/utils/model/)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
