# Git Worktree 隔离：子 Agent 的"独立工作间"

> Claude Code 的子 Agent 不直接在父目录工作，而是为每个子 Agent 创建一个 Git Worktree。这是文件系统层面的隔离——子 Agent 的所有文件操作都在独立目录，即使删错了文件也不会影响主工作区。

你好，我是江小湖。

上一篇 [AgentTool 架构](./01-agenttool.md) 讲到子 Agent 的生命周期分 fork/run/resume 三态。`fork` 的第一步就是创建隔离的工作目录。但"隔离"不是简单的 `mkdir`——Claude Code 选择了 **Git Worktree**。

为什么要用 Git Worktree？`cp -r` 复制一份代码不行吗？

## 目录

- [为什么用 Git Worktree](#为什么用-git-worktree)
- [Worktree 的创建与销毁](#worktree-的创建与销毁)
- [状态隔离：子 Agent 不污染父进程](#状态隔离子-agent-不污染父进程)
- [合并策略：如何把结果带回主工作区](#合并策略如何把结果带回主工作区)
- [Worktree 的限额与性能](#worktree-的限额与性能)
- [总结](#总结)
- [参考链接](#参考链接)

## 为什么用 Git Worktree

先对比几种隔离方案：

| 方案 | 创建成本 | 磁盘占用 | 状态同步 | 适用场景 |
|------|----------|----------|----------|----------|
| `cp -r` 复制目录 | 高（全量复制） | 2x | 手动 | 无 Git 的项目 |
| Docker 容器 | 中（镜像 + 启动） | 大 | 复杂 | 完全隔离环境 |
| Git Worktree | 低（硬链接） | ~0（共享 object） | 自动 | Git 管理的代码库 |

**Git Worktree 的核心优势**：

1. **零成本创建**：Worktree 不是复制文件，而是创建一个新的工作目录，指向同一个 `.git` 对象库。文件内容通过**硬链接**共享，创建几乎瞬间完成。

2. **自动状态同步**：子 Agent 在 Worktree 中修改的文件，本质上是 Git 的一个分支。合并时用 Git 的标准工具，不需要手动复制文件。

3. **天然回滚**：如果子 Agent 搞砸了，直接删除 Worktree 即可，主工作区完全不受影响。

4. **与 Git 生态一致**：开发者已经熟悉 Git 的分支、合并、冲突解决，不需要学习新的隔离机制。

```bash
# Git Worktree 的底层原理
# 主工作区
~/my-project/.git/          # Git 对象库（所有版本历史）
~/my-project/src/           # 当前工作文件

# 创建 Worktree（不是复制！）
git worktree add ../my-project-subagent-1

# 结果
~/my-project-subagent-1/.git  # 指向主仓库的指针（不是完整 .git）
~/my-project-subagent-1/src/  # 硬链接共享的文件（修改时 COW）
```

**写时复制（COW）**：当子 Agent 修改文件时，Git 不会立即复制整个文件，而是创建一个新的 blob 对象。被修改的文件在新 Worktree 中指向新 blob，未被修改的文件仍然共享原 blob。这意味着：如果子 Agent 只修改了 3 个文件，磁盘额外占用只有这 3 个文件的新版本，而不是整个代码库。

## Worktree 的创建与销毁

Claude Code 在 `fork` 阶段创建 Worktree，在 `resume` 阶段销毁。这个过程被封装成了工具函数：

```typescript
// Worktree 创建（简化版）
async function createWorktree(
  parentCwd: string,
  subAgentId: string
): Promise<string> {
  const gitRoot = await findGitRoot(parentCwd);
  const worktreeName = `subagent-${subAgentId}-${Date.now()}`;
  const worktreePath = path.join(gitRoot, '.git', 'worktrees', worktreeName);
  
  // 执行 git worktree add
  await execGit(['worktree', 'add', worktreePath, '-b', worktreeName]);
  
  // 配置 Worktree 的 Git 忽略（不共享父的 .gitignore 修改）
  await fs.writeFile(
    path.join(worktreePath, '.git', 'info', 'exclude'),
    '.subagent-cache\n*.subagent.log\n'
  );
  
  return worktreePath;
}
```

**创建步骤**：

1. **找到 Git 根目录**：从父 Agent 的当前目录向上找 `.git` 文件夹。如果找不到（非 Git 项目），回退到 `cp -r` 方案。

2. **生成 Worktree 名称**：格式为 `subagent-{id}-{timestamp}`。timestamp 防止名称冲突，也便于清理时识别过期 Worktree。

3. **执行 `git worktree add`**：创建新的工作目录和独立分支。`-b` 参数创建新分支，子 Agent 的所有修改都在这个分支上。

4. **配置局部忽略**：每个 Worktree 有自己的 `info/exclude` 文件，定义子 Agent 特有的忽略规则（如 `.subagent-cache` 文件）。

**销毁步骤**：

```typescript
// Worktree 销毁（简化版）
async function cleanupWorktree(worktreePath: string): Promise<void> {
  // 1. 检查 Worktree 是否还存在（可能已被手动删除）
  if (!await fs.exists(worktreePath)) {
    return;
  }
  
  // 2. 检查是否有未提交的修改
  const status = await execGit(['status', '--porcelain'], { cwd: worktreePath });
  
  if (status.trim().length > 0) {
    // 有未提交修改：先 stash，然后删除
    await execGit(['stash', 'push', '-m', 'subagent-cleanup'], { cwd: worktreePath });
  }
  
  // 3. 删除 Worktree 目录
  await fs.rm(worktreePath, { recursive: true, force: true });
  
  // 4. 删除对应的 Git 分支
  const branchName = path.basename(worktreePath);
  await execGit(['branch', '-D', branchName]);
  
  // 5. 从 Git 的 worktree 列表中移除
  await execGit(['worktree', 'prune']);
}
```

**销毁的五个步骤**：

1. **存在检查**：如果 Worktree 已被手动删除（如用户清理了），直接跳过。

2. **未提交修改处理**：如果子 Agent 还有未提交的修改（比如被中断或超时），先 stash 再删除。这防止了数据丢失——虽然子 Agent 的结果通常通过消息传递回父 Agent，但文件修改可能也有价值。

3. **删除目录**：递归删除 Worktree 目录。这是安全的，因为 Worktree 与主仓库共享 object 库，删除 Worktree 不会删除任何 Git 对象。

4. **删除分支**：子 Agent 的分支在完成后不再需要，删除保持仓库整洁。

5. **prune**：Git 的 `worktree prune` 会清理内部记录中已不存在的 Worktree 条目。

## 状态隔离：子 Agent 不污染父进程

Worktree 的最大价值是**状态隔离**。子 Agent 在 Worktree 中的所有操作——文件创建、修改、删除——都在独立目录中，不会立即影响主工作区：

```typescript
// 状态隔离示例（简化版）
async function demonstrateIsolation(): Promise<void> {
  // 主工作区状态
  const parentFiles = await fs.readdir(parentCwd);
  console.log('主工作区文件:', parentFiles);
  // → ['src', 'package.json', 'README.md']
  
  // 子 Agent 在 Worktree 中创建文件
  await fs.writeFile(
    path.join(worktreePath, 'src', 'new-feature.ts'),
    '// 新功能代码'
  );
  
  // 子 Agent 删除文件
  await fs.unlink(path.join(worktreePath, 'README.md'));
  
  // 主工作区状态不变！
  const parentFilesAfter = await fs.readdir(parentCwd);
  console.log('主工作区文件（子 Agent 操作后）:', parentFilesAfter);
  // → ['src', 'package.json', 'README.md']  ← README.md 还在！
  
  // 只有 Worktree 中的状态变了
  const worktreeFiles = await fs.readdir(worktreePath);
  console.log('Worktree 文件:', worktreeFiles);
  // → ['src', 'package.json', 'README.md']  ← 但这里 README.md 被删了
}
```

**隔离的范围**：

| 层面 | 隔离方式 | 效果 |
|------|----------|------|
| **文件系统** | Git Worktree | 文件操作完全隔离 |
| **Git 状态** | 独立分支 | commit、stash 不影响主分支 |
| **Node 模块** | 共享 `node_modules` | 不重复安装，但子 Agent 安装新包不影响主工作区 |
| **环境变量** | 继承 + 隔离 | 子 Agent 可以设置自己的环境变量 |
| **进程** | 独立进程 | 崩溃、内存泄漏不影响父 Agent |

**Node 模块的共享**：Claude Code 做了一个优化——子 Agent 的 Worktree 通过符号链接共享父工作区的 `node_modules`。这避免了每次创建子 Agent 都重新安装依赖（可能几分钟）。子 Agent 如果需要安装新包，会在自己的 Worktree 中安装，不影响主工作区的 `node_modules`。

```bash
# Worktree 中的 node_modules 是符号链接
~/my-project-subagent-1/node_modules → ~/my-project/node_modules
```

## 合并策略：如何把结果带回主工作区

子 Agent 完成后，它在 Worktree 中的修改需要合并到主工作区。Claude Code 不是简单地 `cp -r`，而是使用**Git 合并策略**：

```typescript
// 合并子 Agent 结果（简化版）
async function mergeSubAgentResult(
  worktreePath: string,
  parentCwd: string
): Promise<MergeResult> {
  const branchName = path.basename(worktreePath);
  
  // 1. 子 Agent 先提交自己的工作（在 Worktree 中）
  await execGit(['add', '.'], { cwd: worktreePath });
  await execGit(['commit', '-m', `Subagent work: ${branchName}`], { cwd: worktreePath });
  
  // 2. 切换到主工作区，合并子 Agent 的分支
  await execGit(['merge', branchName, '--no-ff', '-m', `Merge subagent: ${branchName}`], {
    cwd: parentCwd
  });
  
  // 3. 检查合并结果
  const mergeStatus = await execGit(['status', '--porcelain'], { cwd: parentCwd });
  
  if (mergeStatus.includes('UU')) {
    // 有冲突：需要手动解决
    return {
      status: 'conflict',
      conflictFiles: parseConflictFiles(mergeStatus),
    };
  }
  
  return { status: 'success' };
}
```

**合并策略的三个要点**：

1. **子 Agent 先提交**：在合并前，子 Agent 必须在 Worktree 中做 `git commit`。这保证了合并的是原子快照，而不是中间状态。

2. **`--no-ff` 强制创建合并提交**：即使可以快进合并，也创建独立的合并提交。这保留了"子 Agent 完成了一次工作"的历史记录，便于追溯。

3. **冲突检测**：如果子 Agent 和父 Agent（或其他子 Agent）修改了同一文件，Git 会报告冲突。Claude Code 的处理策略是：
   - 把冲突文件标记出来
   - 在父 Agent 的上下文中注入冲突信息
   - 让父 Agent（或用户）决定如何解决

**为什么不用 `cp -r` 直接复制**：

如果用 `cp -r`，子 Agent 修改的文件会被直接覆盖到主工作区。这有两个问题：

1. **无法检测冲突**：如果父工作区在子 Agent 运行期间也修改了同一文件，`cp -r` 会直接覆盖，静默丢失修改。

2. **无法回滚**：如果子 Agent 的结果有问题，没有 Git 历史可以回退。

Git 合并通过三路合并（three-way merge）可以精确检测冲突，并保留完整历史。

## Worktree 的限额与性能

子 Agent 可以并行运行，但 Worktree 不是无限的。Claude Code 设置了以下限额：

```typescript
// Worktree 限额（简化版）
const WORKTREE_LIMITS = {
  // 同时运行的子 Agent 上限
  maxConcurrentSubAgents: 5,
  
  // 每个子 Agent 的 Worktree 数量上限（复用）
  maxWorktreesPerSubAgent: 1,
  
  // Worktree 存活时间上限（超时后强制清理）
  maxWorktreeLifetime: 30 * 60 * 1000, // 30 分钟
  
  // 磁盘空间上限（Worktree 总大小）
  maxTotalWorktreeSize: 500 * 1024 * 1024, // 500MB
};
```

**限额的设计逻辑**：

1. **最多 5 个并行子 Agent**：超过 5 个并行 Agent，LLM 调用成本和网络 I/O 会呈指数增长。而且大部分任务不需要超过 5 个并行度。

2. **30 分钟存活上限**：如果一个子 Agent 卡死或忘记清理，30 分钟后 KAIROS 会自动清理它的 Worktree。这是"防止孤儿 Worktree"的保险机制。

3. **500MB 磁盘上限**：虽然 Worktree 本身不占空间（硬链接），但子 Agent 可能生成临时文件（如构建产物、日志）。500MB 防止磁盘被临时文件撑满。

**性能优化**：

```typescript
// Worktree 复用（简化版）
async function getOrCreateWorktree(
  subAgentId: string
): Promise<string> {
  // 检查是否有可复用的 Worktree
  const existingWorktree = await findReusableWorktree(subAgentId);
  if (existingWorktree) {
    // 复用：重置到主分支最新状态，省去重新创建
    await execGit(['reset', '--hard', 'HEAD'], { cwd: existingWorktree });
    return existingWorktree;
  }
  
  // 没有可复用的，创建新的
  return createWorktree(parentCwd, subAgentId);
}
```

**Worktree 复用**：如果同一个子 Agent（或同一类任务）需要多次 fork，Claude Code 会复用已有的 Worktree，而不是每次都创建新的。复用时用 `git reset --hard` 把 Worktree 重置到主分支最新状态，这比重新创建 Worktree 更快。

## 总结

- Claude Code 用 **Git Worktree** 实现子 Agent 的文件系统隔离，而不是 `cp -r` 或 Docker。
- Worktree 的**硬链接 + 写时复制**让创建几乎零成本，磁盘占用最小化。
- 销毁时遵循**存在检查 → stash 未提交修改 → 删除目录 → 删除分支 → prune** 五步，防止数据丢失。
- **状态隔离**覆盖文件系统、Git 状态、进程和环境变量，但 `node_modules` 通过符号链接共享以节省磁盘。
- 合并时用 **Git 三路合并**而非直接复制，可以检测冲突、保留历史、支持回滚。
- **限额机制**（5 并发、30 分钟存活、500MB 磁盘）防止资源泄漏，**Worktree 复用**减少重复创建开销。

> 下一篇：[上下文压缩](./03-compression.md)，看子 Agent 如何把 100K+ token 的结果压缩成 1-2K 的摘要，让父 Agent 的上下文不被撑爆。

## 参考链接

- [Claude Code Worktree 管理源码](file:///E:/Projects/claude-code/src/tools/AgentTool/worktree.ts)
- [Git Worktree 官方文档](https://git-scm.com/docs/git-worktree)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
