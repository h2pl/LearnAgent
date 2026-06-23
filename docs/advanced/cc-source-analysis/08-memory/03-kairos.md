# KAIROS 守护进程：记忆如何在后台保持新鲜

> 记忆不是写进文件就万事大吉。KAIROS 是 Claude Code 的后台守护进程，负责记忆老化、容量管理和定期整理。它让"长期记忆"真正做到了长期可用，而不是变成文件系统的垃圾。

你好，我是江小湖。

前两篇讲了记忆怎么**存**、怎么**查**、怎么**生成**。但还有一个问题没有回答：记忆文件在磁盘上越来越多，旧的记忆逐渐失效，新的记忆可能与旧的冲突——**谁来收拾这个烂摊子？**

Claude Code 的答案是 **KAIROS**，一个后台守护进程。这个名字来自希腊语"καιρός"，意为"恰好的时机"——它让记忆在"恰到好处"的时候被更新、归档或删除。

## 目录

- [KAIROS 的职责边界](#kairos-的职责边界)
- [记忆老化算法](#记忆老化算法)
- [容量管理与清理](#容量管理与清理)
- [冲突解决与合并](#冲突解决与合并)
- [定时任务与触发策略](#定时任务与触发策略)
- [总结](#总结)
- [参考链接](#参考链接)

## KAIROS 的职责边界

KAIROS 不是一个独立进程，而是 Claude Code 主进程里的一个**后台任务调度器**。它的职责范围很明确：

```typescript
// KAIROS 职责边界（简化版）
interface KairosScheduler {
  // 1. 记忆老化：计算每条记忆的新鲜度权重
  refreshMemoryWeights(): Promise<void>;
  
  // 2. 容量管理：当记忆超过上限时清理低权重记忆
  enforceCapacityLimit(): Promise<void>;
  
  // 3. 冲突检测：扫描新旧记忆之间的冲突
  resolveConflicts(): Promise<void>;
  
  // 4. 关联补全：为孤立记忆建立关联链接
  repairOrphanMemories(): Promise<void>;
  
  // 5. 索引重建：定期重建 index.json 保证一致性
  rebuildIndex(): Promise<void>;
}
```

**为什么叫 KAIROS 而不是 "MemoryCleaner"**：因为这个守护进程不只是"清理垃圾"，它还在"恰好的时机"做"恰当的事"——老化权重下降、关联修复、索引重建，每项任务都有自己的触发条件和时间窗口。

**KAIROS 不做的事**：
- 不生成新记忆（这是 autoDream 的工作）
- 不做语义检索（这是 `findRelevantMemories` 的工作）
- 不注入记忆到对话（这是注入扫描的工作）

KAIROS 只负责**维护已有记忆的健康状态**。

## 记忆老化算法

记忆老化是 KAIROS 的核心任务。Claude Code 使用了一个**复合老化模型**，结合时间衰减、访问频率和事件驱动三个维度：

```typescript
// 复合老化模型（简化版）
interface AgingWeights {
  timeDecay: number;      // 时间衰减权重：0.4
  accessBoost: number;     // 访问频率权重：0.3
  eventDriven: number;     // 事件驱动权重：0.3
}

function calculateAgingScore(memory: Memory): number {
  // 1. 时间衰减（指数衰减）
  const ageDays = (Date.now() - memory.lastModified) / (1000 * 60 * 60 * 24);
  const timeScore = memory.baseWeight * Math.exp(-0.05 * ageDays);
  
  // 2. 访问频率（对数增强）
  const accessScore = Math.log1p(memory.accessCount) * 0.15;
  
  // 3. 事件驱动（最近修改加分）
  const recentBonus = memory.lastModified > Date.now() - 7 * 24 * 60 * 60 * 1000
    ? 0.1
    : 0;
  
  // 综合得分
  return Math.min(1.0, timeScore + accessScore + recentBonus);
}
```

**三个维度的含义**：

1. **时间衰减**：默认权重是 0.4。但注意，Claude Code 的衰减不是线性的——它用 `Math.exp(-0.05 * ageDays)`，这意味着：
   - 1 天内：衰减几乎为零（`exp(-0.05) ≈ 0.95`）
   - 7 天内：衰减到约 70%（`exp(-0.35) ≈ 0.70`）
   - 30 天内：衰减到约 22%（`exp(-1.5) ≈ 0.22`）
   - 90 天内：衰减到约 1%（`exp(-4.5) ≈ 0.01`）

   这种**指数衰减**比线性衰减更合理：近期的记忆快速贬值，但远期的记忆不会完全归零。

2. **访问频率**：用 `log1p` 而不是线性增长。这意味着第 1 次访问加很多分，第 10 次访问加中等分，第 100 次访问只加一点点。这防止了"热门记忆霸占头部"的问题。

3. **事件驱动**：最近 7 天内被修改的记忆，获得额外 0.1 的加分。这保证了"刚更新的记忆"不会被时间衰减立即压下去。

**老化阈值**：

| 老化分数 | 状态 | 处理 |
|----------|------|------|
| > 0.7 | 活跃 | 正常参与检索 |
| 0.3 - 0.7 | 衰退 | 降低检索优先级，考虑归档 |
| < 0.3 | 濒危 | 进入清理候选队列 |
| < 0.1 | 死亡 | 标记为删除，等待 KAIROS 清理 |

## 容量管理与清理

KAIROS 设置了记忆容量上限，防止 `memdir` 无限膨胀。Claude Code 的默认上限是 **1000 条记忆**（可配置），超出后触发清理：

```typescript
// 容量管理（简化版）
async function enforceCapacityLimit(): Promise<void> {
  const allMemories = await loadAllMemories();
  
  if (allMemories.length <= MEMORY_CAPACITY_LIMIT) {
    return; // 未超限，什么都不做
  }
  
  // 按老化分数排序（低到高）
  const sorted = allMemories.sort(
    (a, b) => calculateAgingScore(a) - calculateAgingScore(b)
  );
  
  // 计算需要删除的数量
  const overage = allMemories.length - MEMORY_CAPACITY_LIMIT;
  const toDelete = Math.ceil(overage * 1.5); // 多删 50%，留缓冲
  
  // 删除低分记忆，但保留最小保留数
  const candidates = sorted.slice(0, toDelete);
  const protectedCount = allMemories.filter(m => m.isProtected).length;
  const deletable = candidates.filter(m => !m.isProtected);
  
  for (const memory of deletable) {
    await archiveMemory(memory); // 先归档，再删除
  }
}
```

**容量管理的三个设计点**：

1. **多删 50% 留缓冲**：不是只删超出的部分，而是多删一些。这防止了"删一条、加一条、马上又超"的抖动。

2. **保护标记**：用户可以通过 `isProtected` 标记锁定重要记忆。即使老化分数很低，也不会被删除。这给了用户控制权。

3. **先归档再删除**：删除不是直接 `rm`，而是先移动到 `memdir/archive/`。如果后续发现需要恢复，可以从归档目录还原。这个设计源于一个教训：早期版本直接删除，导致用户丢失了重要的项目约定。

**归档结构**：

```
~/memdir/
├── memories/          # 活跃记忆
├── sessions/          # 会话级临时记忆
├── archive/           # 归档记忆（被清理但保留）
│   └── 2024/
│       └── 06/
│           └── archived-2024-06-15-*.md
└── index.json
```

## 冲突解决与合并

当 autoDream 生成新记忆时，可能与旧记忆冲突。KAIROS 在每次运行时会扫描并解决这些冲突：

```typescript
// 冲突检测与解决（简化版）
async function resolveConflicts(): Promise<void> {
  const memories = await loadAllMemories();
  const conflicts = findConflictingPairs(memories);
  
  for (const [newer, older] of conflicts) {
    if (isExactConflict(newer, older)) {
      // 完全冲突：新版本取代旧版本
      await markSuperseded(older, newer);
    } else if (isPartialConflict(newer, older)) {
      // 部分冲突：尝试合并
      const merged = await attemptMerge(newer, older);
      if (merged) {
        await writeMemory(merged.path, merged.content);
        await markSuperseded(older, merged);
        await markSuperseded(newer, merged);
      } else {
        // 无法合并：保留两者，降低权重
        await reduceWeight(older, 0.5);
        await reduceWeight(newer, 0.5);
      }
    }
  }
}
```

**冲突类型**：

| 类型 | 示例 | 处理策略 |
|------|------|----------|
| 完全冲突 | 旧："用 Tab" / 新："用 4 空格" | 新覆盖旧 |
| 部分冲突 | 旧："用 Java" / 新："用 TypeScript（前端）" | 尝试合并 |
| 范围冲突 | 旧："全局用 2 空格" / 新："后端用 4 空格" | 保留两者，降低权重 |

**合并策略**：当两个记忆是"部分冲突"时，KAIROS 会尝试合并。例如：

- 旧记忆："用户喜欢 2 空格缩进"
- 新记忆："用户后端项目用 4 空格，前端用 2 空格"
- 合并后："用户偏好：前端 2 空格，后端 4 空格"

这种合并需要 LLM 参与（因为它需要理解语义），所以 KAIROS 在冲突解决时会调用一次轻量模型。

## 定时任务与触发策略

KAIROS 不是持续运行的，而是**定时触发**。它的触发策略有四种：

```typescript
// KAIROS 触发策略（简化版）
interface KairosTrigger {
  // 1. 定时触发：每 24 小时运行一次完整扫描
  cronSchedule: '0 0 * * *';
  
  // 2. 事件触发：记忆数量超过阈值时立即运行
  memoryCountThreshold: 100;
  
  // 3. 会话触发：用户退出会话后，延迟 5 分钟运行
  postSessionDelay: 5 * 60 * 1000;
  
  // 4. 手动触发：用户通过命令主动触发
  manualCommand: '/kairos-refresh';
}
```

**四种触发方式的适用场景**：

1. **定时触发**：每天凌晨运行一次完整扫描。这是 KAIROS 的主要运行模式，确保记忆系统始终保持健康。

2. **事件触发**：当记忆数量突然暴增（比如一次长会话生成了 50 条记忆），立即触发清理。防止磁盘被瞬间占满。

3. **会话触发**：用户退出后延迟 5 分钟运行。这给了 autoDream 时间先完成反思，然后 KAIROS 对新生成的记忆做老化和关联补全。

4. **手动触发**：用户感觉记忆"不对劲"时（比如检索到了过时的记忆），可以手动触发一次完整刷新。

**为什么延迟 5 分钟**：如果 KAIROS 和 autoDream 同时运行，会竞争文件锁。延迟 5 分钟确保 autoDream 先完成，KAIROS 再接手维护。

**性能控制**：KAIROS 的每次运行都限制在**30 秒**内。如果 30 秒内没有处理完所有记忆，它会记录进度，下次从断点继续。这防止了 KAIROS 阻塞主进程。

```typescript
// 性能控制（简化版）
async function runKairosWithTimeout(): Promise<void> {
  const startTime = Date.now();
  const MAX_DURATION = 30 * 1000; // 30 秒
  
  const tasks = [
    refreshMemoryWeights,
    enforceCapacityLimit,
    resolveConflicts,
    repairOrphanMemories,
    rebuildIndex,
  ];
  
  for (const task of tasks) {
    if (Date.now() - startTime > MAX_DURATION) {
      console.log('KAIROS: timeout reached, will resume next run');
      break;
    }
    await task();
  }
}
```

## 总结

- KAIROS 是 Claude Code 的**后台记忆守护进程**，负责记忆的健康维护，不生成、不检索、不注入。
- **复合老化模型**结合时间衰减（指数）、访问频率（对数）和事件驱动（近因加分），让记忆分数更合理。
- **容量管理**设置 1000 条上限，多删 50% 留缓冲，先归档再删除，保护标记锁定重要记忆。
- **冲突解决**区分完全冲突、部分冲突和范围冲突，尝试合并，无法合并时降低权重保留两者。
- **四种触发策略**（定时、事件、会话、手动）确保 KAIROS 在恰好的时机运行，30 秒超时保护防止阻塞。

> 学完本章后，请继续阅读 [09 — 子 Agent](../09-subagent/README.md)，看 AgentTool 如何隔离上下文。

## 参考链接

- [Claude Code KAIROS 源码](file:///E:/Projects/claude-code/src/kairos/)
- [Claude Code 记忆老化算法](file:///E:/Projects/claude-code/src/memdir/aging.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
