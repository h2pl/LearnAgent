# Resume 机制：长任务如何断点续传

> Claude Code 的会话可能持续数小时——重构大型代码库、迁移数据库、编写文档。如果中途崩溃或用户退出，不能从头再来。`resume` 机制利用 append-only 状态存储，在关键节点创建 checkpoint，恢复时从最近的 checkpoint 继续，而不是从零开始。

你好，我是江小湖。

上一篇 [状态管理](./01-state.md) 讲到 Claude Code 用 append-only 设计管理约 150 个状态字段。但 append-only 只是"记录历史"，真正让长任务可恢复的，是 **checkpoint** 和 **resume** 机制。

## 目录

- [Checkpoint 机制](#checkpoint-机制)
- [Resume 流程](#resume-流程)
- [Resume 的边界条件](#resume-的边界条件)
- [Session 超时与清理](#session-超时与清理)
- [Resume 的性能优化](#resume-的性能优化)
- [总结](#总结)
- [参考链接](#参考链接)

## Checkpoint 机制

Checkpoint 是状态的一个"快照"——在关键节点保存完整状态，以便后续恢复。Claude Code 的 checkpoint 策略是**自动 + 手动**结合：

```typescript
// Checkpoint 机制（简化版）
interface Checkpoint {
  id: string;              // 唯一标识
  timestamp: number;       // 创建时间
  state: SerializedState;   // 序列化状态
  reason: string;         // 创建原因
  message: string;         // 用户可见的描述
}

class CheckpointManager {
  private checkpoints: Checkpoint[] = [];
  private autoCheckpointInterval: number = 5 * 60 * 1000; // 5 分钟自动 checkpoint
  
  // 自动 Checkpoint：定时创建
  async startAutoCheckpoint(): Promise<void> {
    setInterval(async () => {
      await this.createCheckpoint('auto', 'Auto-save checkpoint');
    }, this.autoCheckpointInterval);
  }
  
  // 手动 Checkpoint：用户触发或关键事件触发
  async createCheckpoint(
    reason: string,
    message: string
  ): Promise<Checkpoint> {
    const state = await serializeState(getCurrentState());
    
    const checkpoint: Checkpoint = {
      id: generateCheckpointId(),
      timestamp: Date.now(),
      state,
      reason,
      message,
    };
    
    this.checkpoints.push(checkpoint);
    
    // 清理旧 checkpoint，只保留最近 N 个
    await this.cleanupOldCheckpoints();
    
    // 持久化到磁盘
    await this.saveCheckpoint(checkpoint);
    
    return checkpoint;
  }
  
  // 清理旧 checkpoint
  private async cleanupOldCheckpoints(): Promise<void> {
    const MAX_CHECKPOINTS = 10;
    if (this.checkpoints.length > MAX_CHECKPOINTS) {
      const toDelete = this.checkpoints.slice(0, -MAX_CHECKPOINTS);
      for (const cp of toDelete) {
        await this.deleteCheckpoint(cp.id);
      }
      this.checkpoints = this.checkpoints.slice(-MAX_CHECKPOINTS);
    }
  }
}
```

**Checkpoint 的触发时机**：

| 触发方式 | 时机 | 说明 |
|----------|------|------|
| **定时自动** | 每 5 分钟 | 防止意外崩溃导致大量工作丢失 |
| **工具调用后** | 每次危险操作后 | 删除、修改、网络请求后立即保存 |
| **模式切换** | 切换权限模式时 | 状态发生重大变化 |
| **扩展加载** | 加载/卸载 Skill/Plugin/MCP 后 | 工具列表发生变化 |
| **用户手动** | `/checkpoint` 命令 | 用户主动保存 |
| **会话结束时** | 用户退出或超时时 | 最后保存 |

**Checkpoint 的存储策略**：

```typescript
// Checkpoint 存储（简化版）
async function saveCheckpoint(checkpoint: Checkpoint): Promise<void> {
  const checkpointDir = path.join(os.homedir(), '.claude', 'checkpoints');
  await fs.mkdir(checkpointDir, { recursive: true });
  
  const checkpointPath = path.join(checkpointDir, `${checkpoint.id}.json`);
  
  // 使用临时文件 + 原子重命名（同 memdir 的 using 模式）
  const tempPath = `${checkpointPath}.tmp`;
  await fs.writeFile(tempPath, JSON.stringify(checkpoint, null, 2), 'utf-8');
  await fs.rename(tempPath, checkpointPath);
  
  // 同时更新索引
  await updateCheckpointIndex(checkpoint);
}
```

**为什么用临时文件 + 原子重命名**：
- 防止写入过程中崩溃导致文件损坏
- 保证 checkpoint 文件要么完整写入，要么不存在
- 与 memdir 的 using 资源管理一致

**Checkpoint 的保留策略**：

| 类型 | 保留数量 | 保留时间 | 原因 |
|------|----------|----------|------|
| 自动 checkpoint | 最近 10 个 | 7 天 | 防止磁盘无限增长 |
| 手动 checkpoint | 全部 | 30 天 | 用户主动保存的更重要 |
| 会话结束 checkpoint | 1 个 | 30 天 | 用于 resume |

## Resume 流程

Resume 是从 checkpoint 恢复会话的过程。Claude Code 的 resume 流程分三步：

```typescript
// Resume 流程（简化版）
async function resumeSession(checkpointId?: string): Promise<ResumeResult> {
  // 1. 找到要恢复的 checkpoint
  const checkpoint = await findCheckpoint(checkpointId);
  if (!checkpoint) {
    return { success: false, reason: 'No checkpoint found' };
  }
  
  // 2. 验证状态一致性
  const validation = await validateState(checkpoint.state);
  if (!validation.valid) {
    // 尝试修复
    const repaired = await attemptRepair(checkpoint.state, validation.errors);
    if (!repaired.success) {
      return { success: false, reason: 'State validation failed', errors: validation.errors };
    }
    checkpoint.state = repaired.state;
  }
  
  // 3. 重建会话状态
  const state = await deserializeState(checkpoint.state);
  
  // 4. 重新加载扩展
  await reloadExtensions(state.extensions);
  
  // 5. 重建 UI 状态（如果是 REPL 模式）
  if (isReplMode()) {
    await rebuildUI(state.ui);
  }
  
  // 6. 通知用户恢复成功
  return {
    success: true,
    checkpoint: checkpoint.id,
    restoredAt: Date.now(),
    message: `Session resumed from checkpoint created at ${new Date(checkpoint.timestamp).toLocaleString()}`,
  };
}
```

**Resume 的六个步骤**：

1. **查找 Checkpoint**：如果没有指定 checkpoint ID，使用最新的自动 checkpoint。如果指定了 ID，查找对应的 checkpoint。

2. **验证状态**：对 checkpoint 的状态做一致性检查（结构、类型、逻辑、哈希、扩展）。如果检查失败，尝试修复。

3. **反序列化状态**：把 JSON 格式的序列化状态恢复成内存中的 State 对象。

4. **重新加载扩展**：根据状态中的扩展列表，重新加载 Skill、Plugin、MCP Server。如果某个扩展已不可用，跳过并记录警告。

5. **重建 UI**：如果是 REPL 模式，恢复 UI 状态（滚动位置、选中的建议等）。如果是 headless 模式，跳过这一步。

6. **通知用户**：告诉用户恢复成功，以及恢复到了哪个时间点。

**Resume 的入口**：

Claude Code 提供多种方式触发 resume：

```bash
# 方式 1：启动时自动恢复上次的会话
claude --resume

# 方式 2：在 REPL 中手动恢复
claude
> /resume                    # 恢复最近的 checkpoint
> /resume abc123            # 恢复指定的 checkpoint
> /resume --list            # 列出所有可用的 checkpoint

# 方式 3：从崩溃中自动恢复
# Claude Code 启动时检测到上次会话异常退出，自动提示恢复
```

**自动恢复提示**：

```
⚠️  检测到上次会话异常退出（2024-06-15 14:32:00）

上次会话：重构 authentication 模块（已执行 23/45 个文件）

[恢复会话]  [放弃，开始新会话]  [查看详情]
```

## Resume 的边界条件

Resume 不是万能的，有些情况无法恢复或恢复后行为不一致：

```typescript
// Resume 边界条件处理（简化版）
async function handleResumeEdgeCases(
  checkpoint: Checkpoint
): Promise<ResumeResult> {
  // 边界 1：工作目录已改变
  if (checkpoint.state.cwd !== process.cwd()) {
    const shouldChdir = await confirm(`工作目录已从 ${checkpoint.state.cwd} 变为 ${process.cwd()}，是否切换回原目录？`);
    if (shouldChdir) {
      process.chdir(checkpoint.state.cwd);
    } else {
      return { success: false, reason: 'Working directory changed' };
    }
  }
  
  // 边界 2：文件系统已改变
  const changedFiles = await detectChangedFiles(checkpoint.state);
  if (changedFiles.length > 0) {
    const shouldContinue = await confirm(
      `检测到 ${changedFiles.length} 个文件在上次会话后被修改，是否继续恢复？`
    );
    if (!shouldContinue) {
      return { success: false, reason: 'Filesystem changed since checkpoint' };
    }
  }
  
  // 边界 3：Git 状态已改变
  if (checkpoint.state.git?.head !== await getGitHead()) {
    const shouldContinue = await confirm('Git 分支或提交已改变，是否继续恢复？');
    if (!shouldContinue) {
      return { success: false, reason: 'Git state changed' };
    }
  }
  
  // 边界 4：扩展版本已改变
  for (const skill of checkpoint.state.extensions.skills) {
    const currentSkill = await findSkill(skill);
    if (currentSkill && currentSkill.version !== checkpoint.state.skillVersions?.[skill]) {
      console.warn(`Skill ${skill} 版本已改变，可能导致行为不一致`);
    }
  }
  
  return { success: true };
}
```

**四大边界条件**：

1. **工作目录改变**：如果用户在上次会话后切换了目录，恢复时需要确认是否切回原目录。如果不切回，文件操作可能出错。

2. **文件系统改变**：如果用户在上次会话后用其他编辑器修改了文件，恢复后的状态与实际文件不一致。Claude Code 会检测这些变化并提示用户。

3. **Git 状态改变**：如果用户切换了分支或提交了代码，恢复后的代码库状态与 checkpoint 时不同。这可能导致"已修改的文件列表"不准确。

4. **扩展版本改变**：如果某个 Skill 或 Plugin 在两次会话之间更新了版本，恢复后的行为可能与 checkpoint 时不一致。Claude Code 会警告但不阻止恢复。

**部分恢复策略**：对于无法完全恢复的情况，Claude Code 支持**部分恢复**——只恢复会话配置和上下文，不恢复未完成的操作：

```typescript
// 部分恢复（简化版）
async function partialResume(checkpoint: Checkpoint): Promise<ResumeResult> {
  // 只恢复配置和上下文
  const partialState = {
    config: checkpoint.state.config,
    runtime: {
      messages: checkpoint.state.runtime.messages,
      turnCount: checkpoint.state.runtime.turnCount,
    },
    latches: checkpoint.state.latches,
  };
  
  // 不恢复未完成的操作
  // 不恢复工具调用历史
  // 不恢复扩展状态（重新加载）
  
  return await resumeSession(partialState);
}
```

## Session 超时与清理

长时间运行的会话会占用资源。Claude Code 有**超时机制**自动清理不活跃的会话：

```typescript
// Session 超时管理（简化版）
const SESSION_TIMEOUTS = {
  // 空闲超时：无交互时间
  idle: 30 * 60 * 1000,       // 30 分钟
  
  // 绝对超时：会话最大持续时间
  absolute: 8 * 60 * 60 * 1000, // 8 小时
  
  // 检查点超时：未恢复的检查点保留时间
  checkpoint: 7 * 24 * 60 * 60 * 1000, // 7 天
};

async function checkSessionTimeout(session: Session): Promise<void> {
  const now = Date.now();
  const idleTime = now - session.lastActiveAt;
  const totalTime = now - session.startedAt;
  
  // 检查空闲超时
  if (idleTime > SESSION_TIMEOUTS.idle) {
    console.log(`Session ${session.id} idle for ${idleTime}ms, saving checkpoint...`);
    await createCheckpoint('idle_timeout', 'Session idle timeout');
    await closeSession(session, 'idle_timeout');
  }
  
  // 检查绝对超时
  if (totalTime > SESSION_TIMEOUTS.absolute) {
    console.log(`Session ${session.id} exceeded max duration (${totalTime}ms), saving checkpoint...`);
    await createCheckpoint('absolute_timeout', 'Session max duration reached');
    await closeSession(session, 'absolute_timeout');
  }
}
```

**超时策略**：

| 超时类型 | 时间 | 触发条件 | 处理 |
|----------|------|----------|------|
| **空闲超时** | 30 分钟 | 无用户交互 | 保存 checkpoint，关闭会话 |
| **绝对超时** | 8 小时 | 会话总时长 | 保存 checkpoint，关闭会话 |
| **检查点超时** | 7 天 | 检查点创建后未恢复 | 删除旧检查点 |

**为什么设置 8 小时绝对超时**：
- 防止会话无限运行，占用内存和 API 配额
- 长时间运行的会话状态容易累积，重启可以清理
- 8 小时覆盖了一个工作日的长度，不会打断正常开发

## Resume 的性能优化

Resume 的性能关键在"恢复速度"——用户不想等待几分钟才能继续工作。Claude Code 有多个优化策略：

```typescript
// Resume 性能优化（简化版）
async function optimizedResume(checkpointId: string): Promise<ResumeResult> {
  // 优化 1：增量恢复（只恢复变化的部分）
  const lastCheckpoint = await getLastRestoredCheckpoint();
  const targetCheckpoint = await findCheckpoint(checkpointId);
  
  if (lastCheckpoint && lastCheckpoint.id === targetCheckpoint.id) {
    // 已经恢复过这个 checkpoint，跳过
    return { success: true, cached: true };
  }
  
  // 优化 2：并行恢复（不阻塞 UI）
  const [state, extensions] = await Promise.all([
    deserializeState(targetCheckpoint.state),
    reloadExtensions(targetCheckpoint.state.extensions),
  ]);
  
  // 优化 3：懒加载（扩展不立即初始化）
  for (const ext of extensions) {
    if (ext.type === 'plugin') {
      // Plugin 延迟初始化，等第一次使用时再加载
      await lazyLoadPlugin(ext);
    } else {
      // Skill 和 MCP Server 立即加载
      await ext.load();
    }
  }
  
  // 优化 4：压缩消息恢复（只恢复最近的 N 条）
  const recentMessages = state.runtime.messages.slice(-MAX_RESUME_MESSAGES);
  state.runtime.messages = recentMessages;
  
  return { success: true, state };
}
```

**四大性能优化**：

1. **增量恢复**：如果上次已经恢复过同一个 checkpoint，直接跳过。只恢复"新"的 checkpoint。

2. **并行恢复**：状态反序列化和扩展加载并行执行，不串行等待。

3. **懒加载**：Plugin 等重型扩展不立即初始化，等第一次使用时再加载。这减少了启动时的内存和 CPU 开销。

4. **压缩消息恢复**：只恢复最近的 N 条消息（如 50 条），而不是全部。旧消息在压缩后只保留摘要，不需要完整恢复。

**恢复时间目标**：

| 场景 | 目标时间 | 说明 |
|------|----------|------|
| 正常恢复（< 100 条消息） | < 2 秒 | 大多数场景 |
| 大型恢复（> 500 条消息） | < 5 秒 | 长会话 |
| 从崩溃恢复 | < 3 秒 | 包含额外检查 |

## 总结

- **Checkpoint** 在关键节点（定时、危险操作、模式切换、扩展加载、用户手动）保存状态快照，最多保留 10 个自动 checkpoint。
- **Resume 流程**六步：查找 checkpoint → 验证状态 → 反序列化 → 重新加载扩展 → 重建 UI → 通知用户。
- **四大边界条件**：工作目录改变、文件系统改变、Git 状态改变、扩展版本改变。Claude Code 检测并提示用户，支持部分恢复。
- **超时策略**：空闲 30 分钟、绝对 8 小时、检查点 7 天，自动保存 checkpoint 后关闭会话。
- **性能优化**：增量恢复、并行加载、懒加载、压缩消息恢复，目标恢复时间 < 2-5 秒。

> 学完本章后，请继续阅读 [13 — 可观测性](../13-telemetry/README.md)，看 Claude Code 如何追踪运行状态。

## 参考链接

- [Claude Code Checkpoint 源码](file:///E:/Projects/claude-code/src/utils/checkpoint.ts)
- [Claude Code Resume 机制](file:///E:/Projects/claude-code/src/utils/resume.ts)
- [Claude Code 会话管理](file:///E:/Projects/claude-code/src/utils/sessionStorage.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
