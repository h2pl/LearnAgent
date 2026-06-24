> 在 Claude Code 里，模型不是等所有工具都列出来再一起执行，而是边收流边执行。负责这件事的就是 StreamingToolExecutor。

# StreamingToolExecutor

你好，我是江小湖。

上一篇 [消息预处理流水线](./02-preprocessing.md) 讲的是模型调用前的上下文瘦身。这一篇进入模型调用后的工具执行阶段，看 Claude Code 如何在流式响应中并发调度工具。

## 目录

- [为什么需要流式执行](#为什么需要流式执行)
- [并发安全判定](#并发安全判定)
- [siblingAbortController 机制](#siblingabortcontroller-机制)
- [执行队列与调度策略](#执行队列与调度策略)
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
## 为什么需要流式执行

传统做法是：模型一次输出多个 `tool_use`，主循环收集完所有工具调用，再批量执行。Claude Code 不走这条路。

它的选择是**边收边执行**：只要从 SSE 流里读到一个完整的 `tool_use` 块，立刻开始执行。这样做的好处很明显：

- **降低首工具等待时间**：用户不必等模型说完所有话才能看到第一个工具开始跑
- **提高并行度**：并发安全的工具可以一起跑
- **更快获得反馈**：工具结果可以更快流回模型，开启下一轮

但流式执行也增加了复杂度。StreamingToolExecutor 就是用来封装这些复杂度的。

## 并发安全判定

每个工具在定义时都会声明自己是否 `isConcurrencySafe`：

| 工具类型 | 是否并发安全 | 原因 |
|---------|-------------|------|
| Read / Glob / Grep | 是 | 只读，不修改状态 |
| Write / Edit | 否 | 修改文件，串行更可控 |
| Bash | 否 | 命令之间可能有依赖 |

StreamingToolExecutor 里有一个 `canExecuteTool` 方法，判断当前工具能不能立刻执行：

```typescript
private canExecuteTool(isConcurrencySafe: boolean): boolean {
  const executingTools = this.getExecutingTools();
  if (executingTools.length === 0) return true;
  return isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe);
}
```

规则很简单：

- 如果队列为空，任何工具都能直接跑
- 如果队列里已经有工具在跑，只有"并发安全"的工具才能加入
- 一旦队列里出现非并发安全的工具，后续所有工具必须等它完成

这意味着系统会尽可能并行读操作，但写操作被天然串行化。

## siblingAbortController 机制

多个 Bash 命令并行跑的时候，如果一个失败了，其他兄弟进程应该怎么办？Claude Code 的做法是：**取消兄弟进程，但不终止整个 turn**。

实现这个靠的是 `siblingAbortController`：

```typescript
this.siblingAbortController = createChildAbortController(parentAbortController);
```

每个并行工具执行时会拿到一个 per-tool child controller，它的父级就是 `siblingAbortController`。当某个工具失败时：

```typescript
this.siblingAbortController.abort('sibling_error');
```

这会导致所有正在运行的兄弟工具被取消。但关键点在于：**它不会 abort 父级 controller**，所以整个 Agent 循环继续，只有这一轮里出错的兄弟工具被取消。

被取消的兄弟工具会收到一条结果消息：

```
Cancelled: parallel tool call <name> errored
```

这样模型在下一次决策时，仍然知道这些工具没有完成，而不是凭空消失。

## 执行队列与调度策略

StreamingToolExecutor 内部维护一个执行队列。当新的 `tool_use` 从流中到达时：

1. 解析工具输入，检查并发安全性
2. 如果可以执行，立即启动
3. 如果不能执行，入队等待
4. 当一个工具完成后，检查队列头部，按规则启动下一个

这个调度策略保证了两点：

- **最大化并行**：尽可能多的读操作同时跑
- **保证顺序**：写操作和 Bash 按顺序执行，避免竞态

## 总结

- StreamingToolExecutor 让 Claude Code 可以边收流边执行工具。
- 并发安全工具并行执行，非并发安全工具串行执行。
- siblingAbortController 实现兄弟工具错误级联取消，但不终止整个 turn。
- 这个设计在降低延迟的同时，保证了操作的安全性和可预测性。

> 第 3 章到此结束。下一章：[工具系统](../04-tool-system/README.md)，深入看 42 个工具的接口、注册和执行 Pipeline。

## 参考链接

- [Claude Code StreamingToolExecutor 源码](file:///E:/Projects/claude-code/src/services/tools/StreamingToolExecutor.ts)
- [Claude Code Tool.ts 工具基类](file:///E:/Projects/claude-code/src/Tool.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
