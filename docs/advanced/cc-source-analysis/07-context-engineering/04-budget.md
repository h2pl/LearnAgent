# 预算与熔断

> Claude Code 的 Token 预算系统像一个"家庭财务报表"：总收入是模型上下文窗口，支出分给用户消息、工具结果、系统提示词、压缩输出。熔断器在成本失控时切断，避免最坏情况。

你好，我是江小湖。

前几篇讲了 5 层压缩的具体实现。这一篇从"工程运维"的视角看 Claude Code 的 Token 预算和熔断机制——它们决定了你的会话什么时候开始慢、什么时候需要手动干预、以及什么时候 Claude Code 会主动保护你。

## 目录

- [Token 预算的分配模型](#token-预算的分配模型)
- [熔断器：三道防线](#熔断器三道防线)
- [成本可见性：$ 预算控制](#成本可见性-预算控制)
- [工程师的可调参数](#工程师的可调参数)
- [总结](#总结)
- [参考链接](#参考链接)

## Token 预算的分配模型

以 Claude Sonnet 4.6（200K 上下文窗口）为例，Token 预算的分配如下：

```
总收入: 200,000 token
─────────────────────────────
系统提示词:     ~55,000  (27.5%)  ← 固定开销
输出预留:       20,000  (10.0%)  ← 给本次响应
autocompact 缓冲: 13,000  (6.5%)  ← 压缩触发缓冲
─────────────────────────────
可用空间:     ~112,000  (56.0%)  ← 用户消息 + 工具结果
  ├── 用户消息
  ├── 工具结果
  ├── 模型历史输出
  └── 压缩后摘要
```

112K token 看起来很多，但一个典型的调试会话中：
- 一次 `BashTool` 输出：500-5000 token
- 一次 `ReadTool` 读文件：1000-10000 token
- 一次 `GrepTool` 搜索结果：500-3000 token

如果 Agent 执行 5 个工具调用，每个平均 2000 token，那就是 10K token。加上用户消息和历史输出，一个 20 轮对话轻轻松松吃掉 100K token。

这就是为什么 5 层压缩不是"可选优化"而是"必须的基础设施"。

### 三层阈值

```typescript
// autoCompact.ts
export const AUTOCOMPACT_BUFFER_TOKENS = 13_000      // autocompact 触发缓冲
export const WARNING_THRESHOLD_BUFFER_TOKENS = 20_000 // 警告线缓冲
export const ERROR_THRESHOLD_BUFFER_TOKENS = 20_000   // 错误线缓冲
export const MANUAL_COMPACT_BUFFER_TOKENS = 3_000     // 硬阻断缓冲
```

这些常量控制着四个关键行为：

| 阈值 | 距离窗口 | 系统行为 |
|------|---------|---------|
| Autocompact | 33K | 触发 autocompact |
| Warning | 20K | 黄色警告 |
| Error | 20K | 红色错误提示 |
| Blocking | 3K | 硬阻断新消息 |

注意 Warning 和 Error 共享同样的缓冲距离（20K），但它们的区别在于感知：
- **Warning**：系统自动压缩（autocompact）后仍显示，提示用户"上下文在快速增长"
- **Error**：压缩失败或熔断后显示，提示用户"需要手动处理"

## 熔断器：三道防线

Claude Code 有三道熔断防线：

### 1. autocompact 熔断（MAX_CONSECUTIVE_FAILURES = 3）

连续 3 次 autocompact 失败后停止尝试。这是最关键的熔断，防止无限重试死循环。

### 2. 压缩递归保护

```typescript
// autoCompact.ts — shouldAutoCompact
if (querySource === 'session_memory' || querySource === 'compact') {
  return false  // 压缩任务本身不触发压缩
}
```

压缩过程产生的子 Agent（`session_memory`、`compact`）不会再次触发压缩——防止递归压缩死循环。

### 3. contextCollapse 重置保护

autocompact 成功后会调用 `resetContextCollapse()` 清除 collapse store。这防止了"全对话总结 + 局部折叠"导致的信息重复。

## 成本可见性：$ 预算控制

Claude Code 支持 USD 预算上限：

```typescript
// ToolUseContext
maxBudgetUsd?: number
```

当累计 API 成本接近预算时：
1. Agent 循环收到 `token_budget_continuation` 原因，进入预算续写模式
2. 系统提示词中注入成本警告
3. 预算耗尽后，Agent 循环终止

成本不是简单粗暴的"到线就停"——Claude Code 会提前触发预警，让 Agent 在当前轮次"收尾"（完成当前的工具调用链，返回一个总结），而不是突然中断。

## 工程师的可调参数

生产环境部署时，以下环境变量可以调整预算行为：

| 环境变量 | 作用 | 默认值 |
|---------|------|--------|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 覆盖 autocompact 窗口大小 | 模型窗口 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 触发阈值百分比（1-100） | 自动计算 |
| `DISABLE_COMPACT` | 禁用所有压缩 | false |
| `DISABLE_AUTO_COMPACT` | 仅禁用 autocompact | false |
| `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` | 覆盖硬阻断阈值 | 窗口 - 3K |

这些参数的存在说明了 autocompact 的工程成熟度——它不是"一锤子买卖"，而是可以按实际需求调优的。

## 总结

- Token 预算的 56% 可供实际使用，44% 被系统提示词、输出预留和缓冲占用。
- 三层阈值（autocompact/warning/error/blocking）控制上下文压力的渐进式响应。
- 三道熔断防线防止压缩死循环：autocompact 连续失败 3 次、压缩递归保护、collapse 重置保护。
- USD 成本预算通过提前预警而非突然中断来实现优雅降级。
- 5 个环境变量允许工程师按实际部署调整预算参数。

> 下一篇：[记忆系统概览](../08-memory/01-memdir.md)，看 Claude Code 如何在会话之间保持知识。

## 参考链接

- [Claude Code autoCompact.ts — 阈值与熔断](file:///E:/Projects/claude-code/src/services/compact/autoCompact.ts)
- [Claude Code query.ts — 上下文管理集成](file:///E:/Projects/claude-code/src/query.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
