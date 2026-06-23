# AgentTool 架构：Claude Code 如何"派活"给子 Agent

> `tools/AgentTool/AgentTool.tsx` 有 2657 行，是 Claude Code 最复杂的工具之一。它不是简单的"调用另一个 Agent"，而是设计了一套完整的 fork/run/resume 生命周期，让子 Agent 在隔离环境中工作，完成后把结果压缩回父 Agent 的上下文。

你好，我是江小湖。

上一章 [记忆系统](../08-memory/README.md) 讲了如何让 Agent 记住跨会话的事实。但记忆只能解决"信息持久化"的问题——如果当前任务本身就超过了单次 LLM 调用的处理能力，怎么办？

Claude Code 的答案是：**子 Agent**。不是用一个更大的模型，而是把任务拆给多个 Agent 并行处理。`AgentTool` 就是负责这件事的工具。

## 目录

- [为什么需要子 Agent](#为什么需要子-agent)
- [AgentTool 的三态生命周期](#agenttool-的三态生命周期)
- [上下文隔离：不共享对话历史](#上下文隔离不共享对话历史)
- [父子通信协议](#父子通信协议)
- [错误处理与超时](#错误处理与超时)
- [总结](#总结)
- [参考链接](#参考链接)

## 为什么需要子 Agent

先回答一个问题：为什么不能直接让当前 Agent 继续处理？

| 场景 | 问题 | 子 Agent 解决方案 |
|------|------|------------------|
| **大规模重构** | 需要修改 50+ 文件，单次上下文装不下 | 拆成多个子任务，各由一个子 Agent 处理 |
| **多模块并行** | 前端、后端、测试可以同时写 | 启动多个子 Agent 并行 |
| **探索性任务** | 需要搜索代码库但不想污染当前上下文 | 子 Agent 探索，父 Agent 只接收摘要 |
| **危险操作** | 删除、格式化等不可逆操作 | 子 Agent 在隔离目录执行，失败不污染主工作区 |

Claude Code 不是"为了用子 Agent 而用子 Agent"——它的子 Agent 有明确的**触发条件**：

```typescript
// AgentTool 触发条件（简化版）
function shouldUseSubAgent(task: Task): boolean {
  // 1. 任务明确需要并行（用户说"同时处理 A 和 B"）
  if (task.requiresParallelism) return true;
  
  // 2. 任务涉及多个独立模块
  if (task.affectedModules.length > 3) return true;
  
  // 3. 任务是探索性的（搜索、调研）
  if (task.isExploratory) return true;
  
  // 4. 任务有潜在风险（删除、格式化）
  if (task.hasRiskOperation) return true;
  
  // 5. 当前上下文已接近上限的 80%
  if (currentContextUsage > 0.8) return true;
  
  return false;
}
```

**关键设计点**：子 Agent 不是默认行为，而是"条件触发"。这避免了不必要的开销——启动一个子 Agent 需要额外的进程、额外的 LLM 调用、额外的上下文管理，只有在"值得"的时候才用。

## AgentTool 的三态生命周期

`AgentTool.tsx` 的 2657 行大部分在干一件事：管理子 Agent 的**生命周期**。这个生命周期有三个状态：

```
┌─────────┐    fork      ┌─────────┐    run       ┌─────────┐
│  idle   │ ──────────→ │ running │ ──────────→ │ paused  │
└─────────┘             └─────────┘             └─────────┘
                                              │    │
                                              │ resume│
                                              ↓    ↓
                                           ┌─────────┐
                                           │ resumed │
                                           └─────────┘
```

### fork：创建子 Agent

`fork` 不是操作系统层面的 fork，而是**创建一个新的 Agent 实例**：

```typescript
// AgentTool fork（简化版）
async function forkSubAgent(
  parentSession: Session,
  taskDescription: string
): Promise<SubAgentHandle> {
  // 1. 生成独立会话 ID
  const subAgentId = generateSubAgentId(parentSession.id);
  
  // 2. 创建隔离的工作目录（Git Worktree）
  const worktreePath = await createWorktree(parentSession.cwd);
  
  // 3. 构建精简的上下文（不是复制父 Agent 的全部历史）
  const subAgentContext = buildSubAgentContext(
    parentSession,
    taskDescription
  );
  
  // 4. 启动子 Agent 进程
  const subProcess = spawnSubAgent({
    id: subAgentId,
    cwd: worktreePath,
    context: subAgentContext,
    parentSession: parentSession.id,
  });
  
  return { id: subAgentId, process: subProcess, worktree: worktreePath };
}
```

**fork 的四个步骤**：

1. **生成独立 ID**：子 Agent 有自己的会话 ID，与父 Agent 完全独立。这保证了遥测、日志、成本追踪都是分开的。

2. **创建 Worktree**：子 Agent 在 Git Worktree 中工作，不是直接操作父目录。这隔离了文件系统状态。

3. **构建精简上下文**：关键设计——**不复制父 Agent 的对话历史**。只传递任务描述和必要的上下文（如相关文件路径、项目结构）。这保持了子 Agent 的上下文干净。

4. **启动进程**：子 Agent 是一个独立的 Node.js 进程，有自己的事件循环和内存空间。

### run：执行子任务

子 Agent 启动后，进入 `run` 状态。它像正常的 Agent 一样工作：读取文件、调用工具、修改代码。但与父 Agent 的通信是**单向的**——子 Agent 不会主动打扰父 Agent，只在完成时汇报。

```typescript
// 子 Agent 执行循环（简化版）
async function runSubAgent(
  handle: SubAgentHandle,
  task: Task
): Promise<SubAgentResult> {
  const messages = [{
    role: 'system',
    content: buildSubAgentSystemPrompt(task)
  }, {
    role: 'user',
    content: task.description
  }];
  
  // 子 Agent 自己执行循环
  while (true) {
    const response = await callModel(messages);
    
    if (response.tool_use) {
      const results = await runTools(response.tool_use, {
        // 子 Agent 的权限比父 Agent 更严格
        permissionMode: 'restricted',
        // 只读工具可以并发，写入工具串行
        allowConcurrency: isReadOnlyTool,
      });
      messages.push(...results);
    }
    
    if (response.stop_reason === 'end_turn') {
      break;
    }
    
    // 检查是否超时
    if (Date.now() - handle.startTime > SUBAGENT_TIMEOUT) {
      return { status: 'timeout', partialResult: extractPartialResult(messages) };
    }
  }
  
  return { status: 'completed', result: extractResult(messages) };
}
```

**子 Agent 的权限限制**：子 Agent 运行在 `restricted` 模式下，不能执行某些危险操作（如 `rm -rf`、发送网络请求）。这防止了子 Agent 在隔离环境中"闯祸"。

### resume：合并结果

子 Agent 完成后，结果需要回到父 Agent。但**不是直接复制对话历史**——而是压缩成摘要：

```typescript
// resume：合并子 Agent 结果（简化版）
async function resumeSubAgent(
  parentSession: Session,
  handle: SubAgentHandle,
  result: SubAgentResult
): Promise<void> {
  if (result.status === 'completed') {
    // 成功：压缩结果为摘要，注入父 Agent 上下文
    const summary = await compressResult(result.result);
    parentSession.injectMemory({
      type: 'subagent_result',
      agent: handle.id,
      summary: summary,
      filesModified: result.filesModified,
    });
  } else if (result.status === 'timeout') {
    // 超时：注入部分结果 + 超时提示
    parentSession.injectMemory({
      type: 'subagent_timeout',
      agent: handle.id,
      partialResult: result.partialResult,
    });
  } else if (result.status === 'failed') {
    // 失败：注入错误信息，但不阻塞父 Agent
    parentSession.injectMemory({
      type: 'subagent_failed',
      agent: handle.id,
      error: result.error,
    });
  }
  
  // 清理 Worktree
  await cleanupWorktree(handle.worktree);
}
```

**resume 的关键设计**：
- 成功：压缩为 1-2K token 的摘要，注入父 Agent 的上下文
- 超时：注入部分结果，父 Agent 决定继续还是重试
- 失败：注入错误信息，父 Agent 可以重试或降级处理
- 清理：无论成功失败，Worktree 都会被清理

## 上下文隔离：不共享对话历史

子 Agent 最重要的设计原则是**上下文隔离**。这意味着：

```typescript
// 父 Agent 上下文 vs 子 Agent 上下文（简化版）
interface ParentContext {
  messages: Message[];      // 完整的对话历史（可能 100K+ token）
  memories: Memory[];       // 跨会话记忆
  toolResults: ToolResult[]; // 所有工具执行结果
}

interface SubAgentContext {
  taskDescription: string;   // 任务描述（用户原始请求的子集）
  relevantFiles: string[];   // 相关文件路径（父 Agent 筛选）
  projectStructure: string;  // 项目结构摘要（不是完整文件列表）
  // ❌ 没有父 Agent 的完整对话历史
  // ❌ 没有父 Agent 的工具调用结果
  // ❌ 没有父 Agent 的记忆
}
```

**为什么隔离**：

1. **上下文污染**：如果子 Agent 看到父 Agent 的全部历史，它会被无关信息干扰。比如父 Agent 之前讨论过 API 设计，子 Agent 的任务是写测试——API 设计的讨论对写测试是干扰。

2. **隐私隔离**：父 Agent 可能处理过敏感信息（如 API key、密码）。子 Agent 不应该看到这些。

3. **确定性**：子 Agent 的上下文是"干净的"，它的行为更容易预测和复现。

4. **成本**：100K 的父 Agent 上下文传给子 Agent，成本翻倍。隔离后子 Agent 的上下文通常只有 2-5K。

**上下文传递的取舍**：

| 信息 | 是否传递 | 原因 |
|------|----------|------|
| 任务描述 | ✅ | 必须知道做什么 |
| 相关文件路径 | ✅ | 知道操作哪些文件 |
| 项目结构摘要 | ✅ | 了解代码库组织 |
| 父 Agent 对话历史 | ❌ | 干扰 + 隐私 + 成本 |
| 父 Agent 工具结果 | ❌ | 子 Agent 自己重新执行 |
| 跨会话记忆 | 部分 | 只传与任务相关的记忆 |

## 父子通信协议

子 Agent 和父 Agent 之间的通信不是共享内存，而是**消息传递**：

```typescript
// 父子通信协议（简化版）
interface SubAgentMessage {
  type: 'progress' | 'result' | 'error' | 'permission_request';
  agentId: string;
  payload: unknown;
}

// 子 Agent 向父 Agent 发送消息
function sendToParent(message: SubAgentMessage): void {
  // 通过进程间通信（IPC）发送
  process.send({
    channel: 'subagent_message',
    data: message,
  });
}

// 父 Agent 接收消息
parentProcess.on('message', (msg: SubAgentMessage) => {
  if (msg.type === 'progress') {
    // 更新 UI 显示子 Agent 进度
    updateSubAgentProgress(msg.agentId, msg.payload);
  } else if (msg.type === 'permission_request') {
    // 子 Agent 请求权限（如写入敏感文件）
    handlePermissionRequest(msg.agentId, msg.payload);
  }
});
```

**通信协议的四类消息**：

1. **progress**：子 Agent 定期汇报进度（如"已处理 5/10 个文件"）。父 Agent 用这些进度更新 UI，让用户知道子 Agent 在干活。

2. **result**：子 Agent 完成时的最终结果。包含摘要、修改的文件列表、遇到的错误。

3. **error**：子 Agent 遇到无法恢复的错误时发送。父 Agent 决定重试、降级或放弃。

4. **permission_request**：子 Agent 的权限比父 Agent 更严格。当它需要执行受限操作时，向父 Agent 请求授权。这是"权限上浮"设计——危险操作必须由父 Agent 确认。

**为什么用消息传递而不是共享内存**：
- 进程隔离：子 Agent 是独立进程，天然不共享内存
- 可观测性：所有通信都有日志，便于调试
- 容错：如果子 Agent 崩溃，消息队列不会丢失
- 网络透明：未来如果需要跨机器调度子 Agent，消息传递可以直接扩展到网络通信

## 错误处理与超时

子 Agent 是独立进程，可能崩溃、超时或被用户中断。Claude Code 的错误处理策略是**优雅降级**：

```typescript
// 子 Agent 错误处理（简化版）
async function handleSubAgentError(
  handle: SubAgentHandle,
  error: SubAgentError
): Promise<void> {
  switch (error.type) {
    case 'timeout':
      // 超时：返回部分结果，父 Agent 决定继续还是重试
      const partial = await extractPartialResult(handle);
      await resumeWithPartialResult(handle, partial);
      break;
      
    case 'crash':
      // 崩溃：尝试恢复，失败则重试
      const recovered = await attemptRecover(handle);
      if (!recovered) {
        await retrySubAgent(handle, { maxRetries: 2 });
      }
      break;
      
    case 'user_abort':
      // 用户中断：立即停止，清理资源
      await terminateSubAgent(handle);
      await cleanupWorktree(handle.worktree);
      break;
      
    case 'permission_denied':
      // 权限被拒绝：记录失败，父 Agent 自行处理
      await resumeWithFailure(handle, 'permission_denied');
      break;
  }
}
```

**超时策略**：

子 Agent 有**硬超时**和**软超时**两层：

- **软超时**：当子 Agent 运行超过预期时间（如 5 分钟），父 Agent 发送一个"进度检查"消息。如果子 Agent 仍在有效工作，可以请求延长。
- **硬超时**：当子 Agent 运行超过绝对上限（如 30 分钟），强制终止。硬超时防止子 Agent 无限循环或卡死。

**为什么需要两层超时**：软超时给子 Agent"解释机会"——它可能在做一件复杂但正确的事，不应该被误杀。硬超时是最后的保险丝。

## 总结

- 子 Agent 不是默认行为，而是**条件触发**——并行需求、多模块、探索性任务、风险操作、上下文压力五种场景才启动。
- `AgentTool` 的生命周期分三态：**fork**（创建隔离实例）→ **run**（独立执行）→ **resume**（压缩结果回父 Agent）。
- **上下文隔离**是核心设计：子 Agent 不共享父 Agent 的对话历史，只接收任务描述和必要上下文。这防止了干扰、隐私泄露和成本翻倍。
- 父子通信用**消息传递**而非共享内存，支持 progress/result/error/permission_request 四类消息。
- 错误处理采用**优雅降级**策略：超时返回部分结果、崩溃尝试恢复、用户中断立即清理、权限拒绝记录失败。
- 子 Agent 的**硬超时 + 软超时**两层机制，既防止无限循环，又给正常耗时任务留余地。

> 下一篇：[Git Worktree 隔离](./02-worktree.md)，看 Claude Code 如何用 Git Worktree 实现文件系统层面的隔离。

## 参考链接

- [Claude Code AgentTool 源码](file:///E:/Projects/claude-code/src/tools/AgentTool/AgentTool.tsx)
- [Claude Code 子 Agent 调度源码](file:///E:/Projects/claude-code/src/tools/AgentTool/subagent.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
