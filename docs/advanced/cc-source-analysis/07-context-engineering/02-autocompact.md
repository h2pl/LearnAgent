# 自动压缩

> autocompact 是 5 层压缩中唯一需要调用 LLM 的一层。它有一个精妙的熔断机制：连续失败 3 次就停止尝试——这个数字来自 BQ 数据分析，曾有一个会话尝试了 3272 次全失败。

你好，我是江小湖。

上一篇 [五层压缩概览](./01-five-layers.md) 介绍了 5 层压缩的全局视角。这一篇聚焦最昂贵的一层：autocompact。

## 目录

- [触发阈值：不是到了 200K 才开始压](#触发阈值不是到了-200k-才开始压)
- [COMPACTABLE_TOOLS：什么能压、什么不能压](#compactable_tools什么能压什么不能压)
- [熔断机制：MAX_CONSECUTIVE_FAILURES = 3](#熔断机制max_consecutive_failures--3)
- [CLAUDE.md 永不删除的实现](#claudemd-永不删除的实现)
- [压缩结果的后处理](#压缩结果的后处理)
- [总结](#总结)
- [参考链接](#参考链接)

## 触发阈值：不是到了 200K 才开始压

autocompact 的触发不是等到上下文满了才动手——它是**提前触发**的：

```typescript
// autoCompact.ts
export function getAutoCompactThreshold(model: string): number {
  const effectiveContextWindow = getEffectiveContextWindowSize(model)
  const autocompactThreshold =
    effectiveContextWindow - AUTOCOMPACT_BUFFER_TOKENS  // 13000
  return autocompactThreshold
}
```

`effectiveContextWindow` 是模型的实际上下文窗口（如 200K）减去预留的输出空间（20K，给压缩结果本身的输出）。`AUTOCOMPACT_BUFFER_TOKENS` 是额外的 13K token 缓冲——保证压缩完成时上下文不会刚好溢出。

以 Claude Sonnet 4.6 为例：
- 上下文窗口：200K
- 减输出预留：-20K
- 减 autocompact 缓冲：-13K
- **实际触发阈值：~167K token**

这意味着在上下文还剩 33K token 的空间时，autocompact 就已经触发了。这个提前量保证了：
1. 压缩过程本身有足够的输出 token
2. 压缩后的新消息不会立即再度触发压缩
3. 用户可以继续对话而不用等压缩完成

### 三级警告体系

`calculateTokenWarningState` 定义了三个级别：

```typescript
export function calculateTokenWarningState(tokenUsage, model) {
  const warningThreshold = threshold - 20_000  // 警告线
  const errorThreshold = threshold - 20_000     // 错误线
  const blockingLimit = actualWindow - 3_000    // 硬阻断

  return {
    isAboveWarningThreshold: tokenUsage >= warningThreshold,
    isAboveErrorThreshold: tokenUsage >= errorThreshold,
    isAtBlockingLimit: tokenUsage >= blockingLimit,
  }
}
```

| 级别 | 阈值 | 系统行为 |
|------|------|---------|
| Warning | 阈值 - 20K | UI 显示黄色警告 |
| Error | 阈值 - 20K | UI 显示红色错误提示 |
| Blocking | 窗口 - 3K | 阻止发送新消息 |

这些阈值通过 `QueryEngine` 在每次 API 调用前检查，决定是否触发压缩或显示警告。

## COMPACTABLE_TOOLS：什么能压、什么不能压

不是所有工具结果都可以压缩。`microCompact.ts` 里定义了白名单：

```typescript
const COMPACTABLE_TOOLS = new Set([
  FILE_READ_TOOL_NAME,    // 文件内容（可压缩）
  ...SHELL_TOOL_NAMES,    // Bash/PowerShell 输出（可压缩）
  GREP_TOOL_NAME,         // 搜索结果（可压缩）
  GLOB_TOOL_NAME,         // 文件列表（可压缩）
  WEB_SEARCH_TOOL_NAME,   // 网页搜索结果（可压缩）
  WEB_FETCH_TOOL_NAME,    // 网页抓取内容（可压缩）
  FILE_EDIT_TOOL_NAME,    // 编辑结果（可压缩）
  FILE_WRITE_TOOL_NAME,   // 写入结果（可压缩）
])
```

白名单之外的工具结果不会被压缩——它们的输出要么本身就很简洁（如 TodoWriteTool），要么压缩后意义不大（如 AgentTool 的返回）。

### 压缩策略的粒度

不同工具类型有不同的压缩策略：

- **BashTool**：保留命令和退出码，压缩 stdout/stderr
- **ReadTool**：保留文件名和行数范围，压缩内容
- **GrepTool**：保留匹配统计，压缩具体匹配行

这种按工具类型定制的压缩策略，比一刀切的截断要聪明得多。

## 熔断机制：MAX_CONSECUTIVE_FAILURES = 3

autocompact 有一个关键的熔断器：

```typescript
const MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3
```

注释解释了为什么是 3：

> BQ 2026-03-10: 1,279 sessions had 50+ consecutive failures (up to 3,272) in a single session, wasting ~250K API calls/day globally.

在引入熔断之前，有些会话会陷入"压缩→失败→重试→再失败"的死循环。每次失败浪费一次 autocompact API 调用（~20K output token），一天全球浪费约 25 万次 API 调用。

熔断逻辑很简单：

```typescript
// autoCompact.ts
if (tracking.consecutiveFailures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES) {
  logForDebugging(
    `autocompact: circuit breaker tripped after ${tracking.consecutiveFailures} consecutive failures`
  )
  return  // 不再尝试
}
```

连续 3 次失败后，整个会话不再触发 autocompact。这意味着该会话只能靠前 4 层压缩管理上下文。如果 4 层都搞不定，用户会看到"上下文已满"的提示——但这比无限循环好得多。

## CLAUDE.md 永不删除的实现

在 `compactConversation` 中，CLAUDE.md 的信息被标记为"保留段"：

```typescript
// compact.ts — annotateBoundaryWithPreservedSegment
export function annotateBoundaryWithPreservedSegment(
  result: CompactionResult,
  preservedSegment: Message[],
): CompactionResult {
  // CLAUDE.md 的内容被附加到压缩结果中，不被压缩
}
```

`messagesToKeep` 字段用于存储需要完整保留的消息——主要是系统级别的上下文注入（CLAUDE.md、安全守则、项目配置）。

这个设计保证了即使用户进行了 50 轮对话，CLAUDE.md 中记录的架构约束和编码规范仍然完整地存在于上下文中。

## 压缩结果的后处理

`postCompactCleanup.ts` 在 autocompact 完成后执行清理工作：

1. 清除旧的 collapse state（contextCollapse 的数据）
2. 标记压缩完成，重置 turnCounter
3. 重置 `consecutiveFailures`（成功压缩后重置熔断计数器）

这个后处理保证了每次成功压缩后，系统回到一个干净的状态，为下一轮对话做好准备。

## 总结

- autocompact 提前触发（~167K），保留 33K token 缓冲给压缩输出和新消息。
- 三级警告体系（Warning/Error/Blocking）让用户提前感知上下文压力。
- COMPACTABLE_TOOLS 白名单定义了可压缩的工具范围，不同工具有不同的压缩策略。
- 熔断机制（3 次连续失败）避免无限重试，曾节省全球每天 25 万次 API 调用。
- CLAUDE.md 被标记为"保留段"，在压缩中永不删除。
- 压缩完成后执行后处理，重置状态为下一轮做准备。

> 下一篇：[微压缩与折叠](./03-micro-collapse.md)，深入 microcompact 的按 tool_use_id 压缩和 contextCollapse 的跨轮次持久化。

## 参考链接

- [Claude Code autoCompact.ts 源码](file:///E:/Projects/claude-code/src/services/compact/autoCompact.ts)
- [Claude Code compact.ts 源码](file:///E:/Projects/claude-code/src/services/compact/compact.ts)
- [Claude Code postCompactCleanup.ts](file:///E:/Projects/claude-code/src/services/compact/postCompactCleanup.ts)
