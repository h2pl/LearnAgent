# 工具执行 Pipeline

> 一次工具调用要经过 8 步：解析、校验、Hook 拦截、权限检查、并发决策、执行、结果组装、PostHook。`toolExecution.ts` 用 1700+ 行代码管住了这 8 步，每一步都可能是终止点。

你好，我是江小湖。

上一篇 [工具接口与注册](./01-tool-basics.md) 讲到 Claude Code 如何用统一的 `Tool` 接口管住 42 个工具。这一篇深入"执行层"：当一个工具调用从模型输出到结果返回，中间发生了什么。

## 目录

- [8 步流水线全景](#8-步流水线全景)
- [Step 1-2：工具查找与输入校验](#step-1-2工具查找与输入校验)
- [Step 3-4：PreHook 拦截与权限检查](#step-3-4prehook-拦截与权限检查)
- [Step 5：并发决策](#step-5并发决策)
- [Step 6-7：工具执行与结果组装](#step-6-7工具执行与结果组装)
- [Step 8：PostHook 与后处理](#step-8posthook-与后处理)
- [错误分类与可恢复性](#错误分类与可恢复性)
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


## 8 步流水线全景

`toolExecution.ts` 的入口是 `runToolUse()`，它是一个 async generator——每一步都可能 yield 消息更新给 Agent 循环，让 UI 实时反映执行状态。

```
模型输出 tool_use block
  ↓
1. 工具查找     — findToolByName，找不到直接返回错误
  ↓
2. 输入校验     — Zod safeParse → validateInput()
  ↓
3. PreHook 拦截  — runPreToolUseHooks（可修改输入、阻止执行、触发对话）
  ↓
4. 权限检查     — canUseTool → checkPermissions
  ↓
5. 并发决策     — isConcurrencySafe 决定是否与同行调用并行
  ↓
6. 工具执行     — tool.call(input, context)
  ↓
7. 结果组装     — mapToolResultToToolResultBlockParam
  ↓
8. PostHook      — runPostToolUseHooks
  ↓
结果返回 Agent 循环
```

每一步都是一个判定点。任何一步失败，后续步骤都不会执行，错误消息直接返回给模型。

## Step 1-2：工具查找与输入校验

### 工具查找与别名兼容

```typescript
// toolExecution.ts — runToolUse()
let tool = findToolByName(toolUseContext.options.tools, toolName)

// 找不到？检查是否已废弃的别名（如 KillShell → TaskStop）
if (!tool) {
  const fallbackTool = findToolByName(getAllBaseTools(), toolName)
  if (fallbackTool?.aliases?.includes(toolName)) {
    tool = fallbackTool
  }
}

// 最终找不到 → 直接返回错误给模型
if (!tool) {
  yield { message: createToolErrorMessage(`No such tool available: ${toolName}`) }
  return
}
```

别名兼容是一个精妙的设计。当工具被重命名（比如 `KillShell` 改为 `TaskStop`），旧名称仍然可以通过别名匹配到新工具。这让旧的回放记录不会因为工具重命名而中断。

### 输入校验两层

第一层是 Zod Schema 校验：

```typescript
const parsedInput = tool.inputSchema.safeParse(input)
if (!parsedInput.success) {
  return [{ message: createToolErrorMessage(formatZodValidationError(...)) }]
}
```

如果 Zod 校验失败，Claude Code 还会做一个额外判断：**这个工具是不是被延迟加载了但 Schema 没送给模型？** 如果是，会在错误消息里追加一个 hint，告诉模型先调 `ToolSearch` 加载工具，再重试。

第二层是业务校验：

```typescript
const isValidCall = await tool.validateInput?.(parsedInput.data, toolUseContext)
if (isValidCall?.result === false) {
  return [{ message: createToolErrorMessage(isValidCall.message) }]
}
```

`validateInput` 由每个工具自己实现。比如 `BashTool` 可以在这里判断命令是否需要取消（用户按了 Ctrl+C），而不是等到执行时才失败。

## Step 3-4：PreHook 拦截与权限检查

### PreToolUse Hook

在权限检查之前，先跑 PreHook。Hook 可以做四件事：

| 能力 | 说明 |
|------|------|
| 修改输入 | Hook 可以返回 `updatedInput`，用修改后的输入替换原始输入 |
| 阻止执行 | `preventContinuation` 标记为 true，工具不会执行 |
| 权限替代 | `hookPermissionResult` 直接返回 allow/deny，跳过后续权限检查 |
| 触发对话 | Hook 可以 yield 用户消息，比如要求确认操作 |

Hook 之后的 `processedInput` 可能和原始 `input` 完全不一样了——这是为什么 `backfillObservableInput` 的输入被 clone 一份：Hook 看到的是补全后的版本，但 `tool.call()` 拿到的是经过权限系统认可后的版本。

### 权限检查

权限检查分为通用权限（`canUseTool`）和工具特定权限（`checkPermissions`）：

```typescript
// 1. 先问通用权限系统
const permissionResult = await canUseTool(tool, processedInput)

// 2. 再问工具自己的特定判断
const toolPermissionResult = await tool.checkPermissions(processedInput, toolUseContext)
```

两个检查有先后顺序：通用权限是第一关，通过后才问工具特定权限。这避免了工具层的权限逻辑重复实现通用规则。

还有一个关键优化：**BashTool 的分类器是并行启动的**。在权限检查还在运行时，`startSpeculativeClassifierCheck` 已经把一个分类器任务丢给后台。等权限系统问"要不要安全分类"时，结果可能已经算好了。

## Step 5：并发决策

`isConcurrencySafe` 的返回值决定一个工具能否和其他工具同时执行。这个决策是**按调用实例**而非按工具类型做的——同一个 `BashTool`，`ls` 可以和 `grep` 并行，但 `git commit` 不能和其他命令抢锁。具体的分组策略在下一篇 [并发调度](./03-concurrency.md) 中详细展开。

## Step 6-7：工具执行与结果组装

工具执行本身很直接：调用 `tool.call(input, context, canUseTool, parentMessage, onProgress)`。

但在调用之前，还有一个防御性处理：`BashTool` 的 `_simulatedSedEdit` 字段会被剥离。这个字段是权限系统注入的内部标记，不应该出现在工具调用的参数里。

执行过程中的进度通过 `onProgress` 回调实时推给 UI。执行完成后，`mapToolResultToToolResultBlockParam` 把工具输出序列化为模型能理解的格式。

`streamedCheckPermissionsAndCallTool` 用 `Stream` 对象统一管理进度事件和最终结果——两者通过同一个 async iterable 流出，让 Agent 循环不需要区分"这是进度更新"还是"这是最终结果"。

## Step 8：PostHook 与后处理

工具执行完成后，PostHook 可以在结果返回模型之前插入额外的系统消息。常用于记录日志、触发副作用、或者插入安全提醒。

```typescript
for await (const result of runPostToolUseHooks(...)) {
  switch (result.type) {
    case 'additionalContext':
      resultingMessages.push(result.message)  // 追加到消息列表
      break
    case 'block':
      yield blockingResult  // 阻止结果返回，替换为错误消息
      return
  }
}
```

## 错误分类与可恢复性

`classifyToolError()` 对错误做了三级分类：

| 错误来源 | 分类逻辑 | 可恢复性 |
|---------|---------|---------|
| `TelemetrySafeError` | 读取 `telemetryMessage` | 可恢复 |
| Node.js errno（ENOENT/EACCES） | 读取 `error.code` | 可恢复 |
| 命名错误（ShellError/ImageSizeError） | 读取 `error.name` | 取决于上下文 |
| 未知 Error | 返回 `'Error'` | 通常不可恢复 |

这个分类用于遥测和日志，不直接影响执行流程。但帮助监控系统区分"用户的输入有错"和"系统出了问题"。

## 总结

- 工具执行经过 8 步流水线：查找→校验→PreHook→权限→并发→执行→结果→PostHook。
- 每一步都是一个判定点，任何一步失败都会中断后续步骤，错误返回给模型。
- 工具查找支持别名兼容，让旧回放记录不因工具重命名而中断。
- 输入校验有两层：Zod 类型校验 + validateInput 业务校验。
- PreHook 可以先于权限系统修改输入、替代权限决策、甚至阻止执行。
- BashTool 的分类器检查是并行启动的，减少用户等待时间。
- PostHook 用于在结果返回前插入额外的上下文或安全提醒。

> 下一篇：[并发调度](./03-concurrency.md)，看 Claude Code 如何让 42 个工具安全地并行工作。

## 参考链接

- [Claude Code toolExecution.ts 源码](file:///E:/Projects/claude-code/src/services/tools/toolExecution.ts)
- [Claude Code Tool.ts 接口定义](file:///E:/Projects/claude-code/src/Tool.ts)
- [Claude Code 权限系统](file:///E:/Projects/claude-code/src/utils/permissions/)
