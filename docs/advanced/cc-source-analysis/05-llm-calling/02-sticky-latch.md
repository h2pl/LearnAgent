# Sticky-on Latch

> Claude Code 每次 API 调用都带着 50-70K token 的系统提示词。如果某个 beta header 在会话中途切换，整个 Prompt Cache 就会失效。Sticky-on Latch 机制用 4 个全局锁解决这个问题——一旦打开，永不关闭。

你好，我是江小湖。

上一篇 [callModel 架构](./01-callmodel.md) 讲到 `claude.ts` 是 LLM 调用的完整管线。这一篇聚焦管线中最精妙的设计：**Prompt Cache 保护**。

## 目录

- [Prompt Cache 为什么这么重要](#prompt-cache-为什么这么重要)
- [缓存失效的 7 个诱因](#缓存失效的-7-个诱因)
- [4 个 Latch 锁的运作机制](#4-个-latch-锁的运作机制)
- [promptCacheBreakDetection：事后审计](#promptcachebreakdetection事后审计)
- [缓存保护的工程启示](#缓存保护的工程启示)
- [总结](#总结)
- [参考链接](#参考链接)

## Prompt Cache 为什么这么重要

Claude Code 的系统提示词在 50-70K token 之间。如果每次 API 调用都要重新上传这些 token，会产生两个后果：

1. **延迟增加**：70K token 的网络传输需要额外几百毫秒
2. **成本翻倍**：缓存命中的 token 价格是普通输入 token 的 10%，未命中则全额计费

以一个典型的 Agent 会话为例：10 轮对话，每轮 2000 个输出 token。如果每次缓存都失效，缓存写入 token 的额外开销约为 70K × 10 = 700K token，按 Claude Opus 的缓存写入价格计算，会增加数美元的成本。

因此，**保持 Prompt Cache 连续命中是整个会话的成本和延迟优化核心**。

## 缓存失效的 7 个诱因

`promptCacheBreakDetection.ts` 追踪了 7 个可能导致缓存失效的维度：

| 维度 | 追踪字段 | 触发场景 |
|------|---------|---------|
| 系统提示词 | `systemHash` | CLAUDE.md 更新、模式切换 |
| 工具 Schema | `toolsHash` + `perToolHashes` | MCP 工具连接/断开 |
| 缓存策略 | `cacheControlHash` | global↔org scope 翻转 |
| 模型名 | `model` | Fallback 触发模型切换 |
| Beta Headers | `betas` | AFK mode、Fast mode 切换 |
| Thinking 配置 | `effortValue` | reasoning_effort 参数变化 |
| 额外 Body | `extraBodyHash` | CLAUDE_CODE_EXTRA_BODY 环境变量变化 |

任何一次 API 调用，如果这 7 个维度中的任何一个发生了变化，Prompt Cache 就会失效。而 Claude Code 的很多功能——AFK 模式、Fast 模式、缓存编辑——都依赖动态切换 beta header，这正是最危险的缓存失效场景。

## 4 个 Latch 锁的运作机制

Sticky-on Latch 是 Claude Code 的解决方案：**会话级别只开不关的开关**。

```typescript
// claude.ts — 4 个 Latch 的初始化
let afkHeaderLatched = getAfkModeHeaderLatched() === true
if (!afkHeaderLatched && isAgenticQuery && isAutoModeActive()) {
  afkHeaderLatched = true
  setAfkModeHeaderLatched(true)  // 一旦设为 true，整个会话不再变化
}

let fastModeHeaderLatched = getFastModeHeaderLatched() === true
if (!fastModeHeaderLatched && isFastMode) {
  fastModeHeaderLatched = true
  setFastModeHeaderLatched(true)
}

let cacheEditingHeaderLatched = getCacheEditingHeaderLatched() === true
if (!cacheEditingHeaderLatched && cachedMCEnabled) {
  cacheEditingHeaderLatched = true
  setCacheEditingHeaderLatched(true)
}

let thinkingClearLatched = getThinkingClearLatched() === true
if (!thinkingClearLatched && isAgenticQuery && idleTime > 1h) {
  thinkingClearLatched = true
  setThinkingClearLatched(true)
}
```

四个 Latch 分别保护四类 beta header：

| Latch | 保护内容 | 为什么需要锁 |
|-------|---------|------------|
| `afkModeHeaderLatched` | AFK_MODE_BETA_HEADER | auto mode 启动后不能中途退出 |
| `fastModeHeaderLatched` | FAST_MODE_BETA_HEADER | fast mode 启用后不能中途关闭 |
| `cacheEditingHeaderLatched` | CACHE_EDITING_BETA_HEADER | 缓存编辑功能启用后不能关闭 |
| `thinkingClearLatched` | 清除 thinking 签名 | 闲置超过 1 小时后清空 thinking 上下文 |

核心逻辑极其简单：**每个 header 在首次需要时打开，之后永远不再变**。这保证了在同一个会话中，API 请求的系统提示词结构始终一致，Prompt Cache 始终命中。

### 为什么不在会话开始时就全部打开？

如果一开始就把所有 beta header 打开，会带来两个问题：

1. **不必要的缓存写入**：用户可能永远不用 AFK 模式，但缓存里会写入 AFK 相关的内容
2. **模型行为变化**：某些 beta header 会影响模型的输出风格和可用功能，提前打开可能产生意外效果

所以 Latch 采用"延迟启用"策略：只在真正需要的时候打开，但一旦打开就永久锁定。

## promptCacheBreakDetection：事后审计

即使有了 4 个 Latch，缓存仍然可能因非预期原因失效。`promptCacheBreakDetection.ts` 提供了事后审计能力。

每次 API 调用完成后，它会比较前后两次的 `PreviousState`：

```typescript
type PreviousState = {
  systemHash: number
  toolsHash: number
  cacheControlHash: number
  perToolHashes: Record<string, number>
  model: string
  betas: string[]
  // ... 更多维度
}
```

如果检测到缓存读 token 下降超过 2000（`MIN_CACHE_MISS_TOKENS`），且没有预期的变更（比如新增了工具），就会触发缓存失效诊断：

1. 找出是哪个维度发生了变化
2. 生成一个 diff 文件，保存到临时目录
3. 记录遥测事件，方便排查

diagnosis 还会区分**客户端侧失效**（系统提示词变了）和**服务端侧失效**（TTL 过期）。如果距离上次 API 调用超过 5 分钟，缓存失效可能是服务器端的 5 分钟 TTL 过期，不是 Claude Code 的 bug。

## 缓存保护的工程启示

Sticky-on Latch 的设计反映了一个重要的工程原则：**减少状态变化比增加缓存策略更有效**。

与其设计复杂的缓存失效检测和自动重建逻辑，不如从源头减少变化。4 个 Latch 用几十行代码就解决了最棘手的缓存失效问题，因为它直接消除了变化本身。

这个思路对所有依赖"远程缓存"的系统都有参考价值：**如果你不能让缓存自己变聪明，那就让状态少变。**

## 总结

- Prompt Cache 对 Claude Code 的成本和延迟至关重要——50-70K token 的系统提示词每次缓存失效都会产生显著开销。
- 缓存失效有 7 个诱因：系统提示词、工具 Schema、缓存策略、模型名、Beta Headers、Thinking 配置、额外 Body。
- Sticky-on Latch 用 4 个"只开不关"的全局锁保护缓存——AFK mode、Fast mode、Cache editing、Thinking clear。
- Latch 采用延迟启用策略：只在需要时打开，避免不必要的缓存写入和模型行为变化。
- `promptCacheBreakDetection` 提供事后审计——比较前后两次调用的 15 个维度，生成 diff 文件，区分客户端/服务端失效。
- 设计哲学：减少状态变化比增加缓存策略更有效。

> 下一篇：[Fallback 与多模型路由](./03-fallback.md)，看 Claude Code 如何在线路故障时自动切换到备选模型。

## 参考链接

- [Claude Code claude.ts — Latch 初始化](file:///E:/Projects/claude-code/src/services/api/claude.ts)
- [Claude Code promptCacheBreakDetection.ts](file:///E:/Projects/claude-code/src/services/api/promptCacheBreakDetection.ts)
- [Anthropic Prompt Caching 文档](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
