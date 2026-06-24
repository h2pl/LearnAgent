# 并发调度

> Claude Code 不会一次性执行所有工具。`toolOrchestration.ts` 先把工具列表按安全性分组，再把"安全组"和"不安全组"交错执行。安全的最大并发数为 10，不安全的串行执行。

你好，我是江小湖。

上一篇 [工具执行 Pipeline](./02-execution-pipeline.md) 讲到单个工具的 8 步执行流程。这一篇看"批量调度"：当模型一次返回了 5 个工具调用，Claude Code 怎么决定谁来并行、谁得排队。

## 目录

- [分批策略：按安全性分组](#分批策略按安全性分组)
- [并行执行：concurrent 批的调度](#并行执行concurrent-批的调度)
- [串行执行：non-concurrent 批的调度](#串行执行non-concurrent-批的调度)
- [Context 的跨工具传递](#context-的跨工具传递)
- [siblingAbortController：级联取消](#siblingabortcontroller级联取消)
- [并发上限与配置](#并发上限与配置)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/04-tool-system/execution-pipeline.svg" alt="工具执行管道" width="90%"/>
  <br/>
  <em>4 层流水线：发现 → 校验 → 调度 → 收集</em>
</p>

<p align="center">
  <img src="../../../../assets/cc-source-analysis/04-tool-system/tool-types.svg" alt="工具类型概览" width="90%"/>
  <br/>
  <em>42 个内置工具的 6 大分类</em>
</p>


## 分批策略：按安全性分组

`toolOrchestration.ts` 的核心函数是 `partitionToolCalls`。它不关心工具的名字，只关心一个布尔值：`isConcurrencySafe`。

```typescript
function partitionToolCalls(
  toolUseMessages: ToolUseBlock[],
  toolUseContext: ToolUseContext,
): Batch[] {
  return toolUseMessages.reduce((acc, toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)
    const parsedInput = tool?.inputSchema.safeParse(toolUse.input)
    const isConcurrencySafe = parsedInput?.success
      ? tool?.isConcurrencySafe(parsedInput.data)
      : false

    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1].blocks.push(toolUse)
    } else {
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }
    return acc
  }, [])
}
```

分组逻辑很简单但很聪明：**连续的 safe 工具合并成一批并行执行，每个 unsafe 工具独占一个串行批**。

```
模型输出: [ReadTool, GrepTool, BashTool(rm), GlobTool, ReadTool]
                            ↓ partitionToolCalls
分组结果:
  批1: [ReadTool, GrepTool]          ← 并行（连续 safe）
  批2: [BashTool(rm)]                ← 串行（unsafe）
  批3: [GlobTool, ReadTool]          ← 并行（连续 safe）
```

如果一个 unsafe 工具被 safe 工具包围，safe 工具会被拆分到两个批中依次执行。这保证了 unsafe 工具执行完之前，后续的 safe 操作不会抢跑。

注意：`isConcurrencySafe` 抛异常时会被捕获并当作 `false`。这是 fail-safe 设计——如果 BashTool 的 shell-quote 解析失败，宁可保守地串行执行。

## 并行执行：concurrent 批的调度

安全的工具调用通过 `runToolsConcurrently` 处理：

```typescript
async function* runToolsConcurrently(
  toolUseMessages: ToolUseBlock[],
  ...
): AsyncGenerator<MessageUpdateLazy, void> {
  yield* all(
    toolUseMessages.map(async function* (toolUse) {
      toolUseContext.setInProgressToolUseIDs(prev =>
        new Set(prev).add(toolUse.id)
      )
      yield* runToolUse(toolUse, ...)
      markToolUseAsComplete(toolUseContext, toolUse.id)
    }),
    getMaxToolUseConcurrency(),  // 默认 10
  )
}
```

核心是 `all()` 函数——它接受一组 async generator 和一个最大并发数，控制同时运行的任务数量。不是 `Promise.all` 那样全部炸开，而是像一个有宽度限制的通道。

每个并行工具通过 `setInProgressToolUseIDs` 标记自己的状态。这个状态有两个用途：

1. **渲染 UI**：终端可以显示"正在执行：ReadTool + GrepTool + GlobTool"
2. **中断控制**：用户可以按 Ctrl+C 取消所有正在执行的工具

## 串行执行：non-concurrent 批的调度

不安全的工具调用通过 `runToolsSerially` 处理。逻辑更简单：一次一个，等上一个完成才开始下一个。

```typescript
async function* runToolsSerially(
  toolUseMessages: ToolUseBlock[],
  ...
): AsyncGenerator<MessageUpdate, void> {
  let currentContext = toolUseContext

  for (const toolUse of toolUseMessages) {
    for await (const update of runToolUse(toolUse, ..., currentContext)) {
      if (update.contextModifier) {
        currentContext = update.contextModifier.modifyContext(currentContext)
      }
      yield { message: update.message, newContext: currentContext }
    }
  }
}
```

注意串行执行的 context 是实时更新的。前一个工具执行完后，它的 `contextModifier` 会应用到下一个工具的上下文。比如 `BashTool` 执行完 `mkdir` 后，后续的 `FileWriteTool` 能看到已创建的目录结构。

## Context 的跨工具传递

在并行批中，所有工具共享同一个 `toolUseContext`，但 context 的修改是**延迟应用**的：

```typescript
// runTools() 中
const queuedContextModifiers = {}

for await (const update of runToolsConcurrently(...)) {
  if (update.contextModifier) {
    const { toolUseID, modifyContext } = update.contextModifier
    queuedContextModifiers[toolUseID] = modifyContext
  }
  yield { message: update.message, newContext: currentContext }
}

// 整批执行完后，统一应用所有 context 修改
for (const block of blocks) {
  const modifier = queuedContextModifiers[block.id]
  if (modifier) currentContext = modifier(currentContext)
}
```

这个设计很关键：并行工具之间不能互相污染 context。如果 `ReadTool` 读到一半，`GrepTool` 突然改了 `readFileState`，会导致 `ReadTool` 的结果不准确。所以 context 的修改全部累积起来，等整批结束再统一应用。

## siblingAbortController：级联取消

`siblingAbortController` 是并发调度中最精妙的设计。当一个工具执行失败时，它可以通过这个控制器取消所有同伴。

```typescript
// 概念示意
const abortController = new AbortController()
const siblingAbortController = {
  signal: abortController.signal,
  abort: (reason) => abortController.abort(reason),
}
```

级联取消的典型场景：一个并行批里有 3 个 `ReadTool` 和 1 个 `FileEditTool`。如果 `FileEditTool` 失败，剩下的 `ReadTool` 已经没有意义了——因为编辑失败，文件状态没变，读出来的内容也可能是旧的。

## 并发上限与配置

最大并发数由环境变量 `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` 控制，默认 10：

```typescript
function getMaxToolUseConcurrency(): number {
  return parseInt(
    process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '', 10
  ) || 10
}
```

10 这个数字不是随便选的。同时调用 10 个工具意味着可能同时发起 10 个文件读取、10 个搜索查询、或者混合操作。再多的话，文件系统的 I/O 带宽会成为瓶颈，操作系统层面的上下文切换也会带来额外开销。

## 总结

- `partitionToolCalls` 按 `isConcurrencySafe` 将工具调用分为安全批和非安全批。
- 连续的 safe 工具合并为同一批并行执行，每个 unsafe 工具独占一个串行批。
- 并行批通过 `all()` 函数控制最大并发数（默认 10）。
- 并行工具的 context 修改延迟到整批结束后统一应用，避免互相污染。
- `siblingAbortController` 实现级联取消：一个工具失败，同批的其他工具立即停止。
- 串行工具的 context 实时更新，前一个工具的结果会传递给下一个工具。

> 下一篇：[关键工具实现](./04-key-tools.md)，深入 BashTool、EditTool、AgentTool 的设计取舍。

## 参考链接

- [Claude Code toolOrchestration.ts 源码](file:///E:/Projects/claude-code/src/services/tools/toolOrchestration.ts)
- [Claude Code toolExecution.ts 源码](file:///E:/Projects/claude-code/src/services/tools/toolExecution.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
