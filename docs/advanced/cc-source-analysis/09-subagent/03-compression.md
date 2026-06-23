# 上下文压缩：100K+ Token 如何变成 1-2K 摘要

> 子 Agent 完成后，它的完整对话历史可能有 100K+ token。但父 Agent 的上下文预算是有限的。Claude Code 的 `AgentTool` 在 `resume` 阶段做了一件关键的事：把子 Agent 的完整结果压缩成 1-2K token 的摘要，让父 Agent"知道发生了什么"而不需要"读完整对话"。

你好，我是江小湖。

前两篇讲了子 Agent 怎么**启动**、怎么**隔离**。但还有一个核心问题：子 Agent 干完活了，怎么向父 Agent**汇报**？

如果直接把子 Agent 的 100K token 对话历史塞进父 Agent 的上下文，父 Agent 的预算瞬间被吃光。Claude Code 的解决方案是**上下文压缩**——不是简单截断，而是用 LLM 生成结构化摘要。

## 目录

- [为什么需要压缩](#为什么需要压缩)
- [摘要生成：用 LLM 压缩 LLM](#摘要生成用-llm-压缩-llm)
- [结构化摘要格式](#结构化摘要格式)
- [Explore Agent vs Verification Agent](#explore-agent-vs-verification-agent)
- [压缩比与质量控制](#压缩比与质量控制)
- [总结](#总结)
- [参考链接](#参考链接)

## 为什么需要压缩

先看数字。一个典型的子 Agent 会话可能包含：

| 内容 | Token 估算 | 说明 |
|------|-----------|------|
| 系统提示词 | 5K | 子 Agent 的精简系统提示 |
| 任务描述 | 500 | 用户原始请求的子集 |
| 文件读取结果 | 20K | 读取 5-10 个文件的完整内容 |
| 工具调用记录 | 15K | read_file、grep、edit_file 等 |
| 模型思考过程 | 30K | 多轮推理和决策 |
| 最终输出 | 5K | 修改后的代码或总结 |
| **总计** | **~75K** | 典型子 Agent 会话 |

75K token 的完整对话，如果直接传给父 Agent，父 Agent 的 200K 预算瞬间少了 37%。如果同时有 3 个子 Agent，父 Agent 的上下文直接爆炸。

**压缩的目标**：把 75K 压缩到 **1-2K**，同时保留**关键信息**——子 Agent 做了什么、改了什么、遇到了什么问题。

```typescript
// 压缩需求计算（简化版）
function calculateCompressionNeed(
  subAgentResult: SubAgentResult
): CompressionPlan {
  const originalTokens = estimateTokens(subAgentResult.fullHistory);
  const budgetAvailable = parentContext.availableTokens;
  const targetTokens = Math.min(2000, budgetAvailable * 0.1); // 最多 2K 或预算的 10%
  
  return {
    originalTokens,
    targetTokens,
    compressionRatio: originalTokens / targetTokens, // 通常 30:1 到 50:1
    strategy: determineStrategy(originalTokens, targetTokens),
  };
}
```

## 摘要生成：用 LLM 压缩 LLM

Claude Code 的摘要不是模板填充，而是**用 LLM 生成**。这不是浪费——用一个小模型（如 Haiku）生成摘要，比把 75K 内容塞进大模型（Sonnet）便宜得多。

```typescript
// 摘要生成（简化版）
async function compressSubAgentResult(
  fullHistory: Message[],
  taskType: TaskType
): Promise<SubAgentSummary> {
  // 1. 提取关键信息（结构化提取，不走 LLM）
  const keyInfo = extractKeyInfo(fullHistory);
  
  // 2. 根据任务类型选择摘要模板
  const template = getSummaryTemplate(taskType);
  
  // 3. 调用轻量模型生成摘要
  const summary = await callModel({
    model: 'haiku', // 用轻量模型，成本低
    messages: [{
      role: 'system',
      content: `You are a result summarizer. Summarize the following sub-agent session into a concise report. Focus on: actions taken, files modified, key findings, and any errors or blockers. Keep under 1000 tokens.`,
    }, {
      role: 'user',
      content: formatHistoryForSummary(fullHistory, keyInfo),
    }],
    maxTokens: 1500,
  });
  
  return parseSummary(summary.content, keyInfo);
}
```

**摘要生成的三步**：

1. **结构化提取**：先不用 LLM，直接从对话历史中提取结构化信息——文件操作列表、工具调用次数、错误记录、最终输出。这些是"事实"，不需要 LLM 理解。

2. **模板选择**：不同类型的任务，摘要侧重点不同。Claude Code 内置了多种模板：

   | 任务类型 | 摘要侧重 | 模板 |
   |----------|----------|------|
   | 代码重构 | 修改的文件、函数签名变化、测试覆盖 | `refactoring` |
   | 探索搜索 | 搜索范围、找到的结果、未找到的 | `exploration` |
   | Bug 修复 | 根因分析、修复方案、验证结果 | `bugfix` |
   | 文档生成 | 生成的文档、覆盖范围、TODO | `documentation` |

3. **LLM 生成**：把结构化信息和模板喂给轻量模型，生成人可读的摘要。轻量模型（Haiku）的成本只有大模型（Sonnet）的 1/10，而摘要生成不需要复杂的推理能力。

## 结构化摘要格式

Claude Code 的摘要不是自由文本，而是**结构化格式**。这让父 Agent（和后续的 `findRelevantMemories`）能精确提取信息：

```markdown
## SubAgent Summary

**Task**: Refactor authentication module to use JWT tokens
**Agent ID**: subagent-abc123
**Status**: ✅ Completed
**Duration**: 4m 32s

### Actions Taken
- Read `src/auth/basic.ts` (156 lines)
- Read `src/auth/jwt.ts` (89 lines)
- Modified `src/auth/basic.ts` → replaced password check with JWT verification
- Created `src/auth/token-utils.ts` (45 lines) for token generation/validation
- Updated `tests/auth.test.ts` with 3 new test cases

### Files Modified
| File | Change | Lines |
|------|--------|-------|
| `src/auth/basic.ts` | Modified | ±12 |
| `src/auth/token-utils.ts` | Created | +45 |
| `tests/auth.test.ts` | Modified | +28 |

### Key Findings
- Existing password hash function (bcrypt) can be reused for JWT secret
- No breaking changes to public API

### Errors / Blockers
- None

### Verdict
Refactoring completed successfully. All tests pass. Ready to merge.
```

**结构化摘要的六个部分**：

1. **元信息**：任务描述、Agent ID、状态、耗时。让父 Agent 快速了解"这是什么任务、结果如何"。

2. **Actions Taken**：子 Agent 执行的关键操作。按时间顺序列出，让父 Agent 了解"过程"。

3. **Files Modified**：文件级别的修改清单。这是最重要的部分——父 Agent 需要知道哪些文件被改了，以便后续操作。

4. **Key Findings**：子 Agent 的"洞察"——不是做了什么，而是发现了什么。比如"找到了一个更优的实现方式"。

5. **Errors / Blockers**：遇到的问题。即使子 Agent 成功完成，也可能有警告或需要注意的事项。

6. **Verdict**：结论。父 Agent 可以直接读这个部分判断"是否需要进一步处理"。

**为什么用结构化格式而不是自由文本**：

- **可解析**：父 Agent 可以用正则或简单解析提取"Files Modified"列表，不需要理解自然语言。
- **可比较**：如果两个子 Agent 修改了同一文件，父 Agent 可以直接对比它们的文件列表。
- **可检索**：结构化摘要可以被 `findRelevantMemories` 索引，未来检索时更精确。

## Explore Agent vs Verification Agent

Claude Code 的源码里有两种特殊的子 Agent，它们的压缩策略不同：

### Explore Agent（探索型）

Explore Agent 的任务是"搜索和调研"——比如"找出代码库里所有使用 `eval()` 的地方"。它的输出通常是一组搜索结果，而不是代码修改。

```typescript
// Explore Agent 压缩策略（简化版）
function compressExploreResult(result: ExploreResult): Summary {
  // 探索型结果：保留"搜索范围"和"关键发现"
  return {
    type: 'exploration',
    searchScope: result.searchScope,      // 搜索了哪些目录/文件
    matchCount: result.matches.length,    // 找到多少匹配
    keyFindings: result.matches
      .filter(m => m.severity === 'high')   // 只保留高优先级的发现
      .map(m => ({
        file: m.file,
        line: m.line,
        snippet: m.snippet.slice(0, 100),   // 截断长片段
      })),
    // ❌ 不保留完整的搜索日志
    // ❌ 不保留每个匹配的完整上下文
  };
}
```

**Explore Agent 的压缩策略**：
- 保留**搜索范围**（搜了哪里）和**匹配数量**（找到多少）
- 只保留**高优先级**的匹配，低优先级的过滤掉
- 每个匹配的片段截断到 100 字符，保留"是什么"不保留"完整上下文"
- 不保留搜索过程的日志（如"grep 了 50 次"）

### Verification Agent（验证型）

Verification Agent 的任务是"验证和测试"——比如"运行测试套件，确认重构没有破坏功能"。它的输出是测试结果的总结。

```typescript
// Verification Agent 压缩策略（简化版）
function compressVerificationResult(result: VerificationResult): Summary {
  // 验证型结果：保留"测试覆盖"和"失败详情"
  return {
    type: 'verification',
    testSuite: result.testSuite,           // 运行了哪个测试套件
    totalTests: result.totalTests,           // 总测试数
    passed: result.passed,                   // 通过数
    failed: result.failed,                   // 失败数
    failures: result.failures.map(f => ({   // 只保留失败详情
      testName: f.testName,
      error: f.error.slice(0, 200),        // 截断错误信息
      stackTrace: f.stackTrace.slice(0, 3),  // 只保留前 3 层堆栈
    })),
    // ❌ 不保留通过的测试详情
    // ❌ 不保留测试日志的完整输出
  };
}
```

**Verification Agent 的压缩策略**：
- 保留**测试统计**（总数、通过、失败）
- 只保留**失败的测试详情**，通过的测试只计数
- 错误信息截断到 200 字符，堆栈只保留前 3 层
- 不保留完整的测试日志输出（可能几千行）

**为什么区分两种类型**：因为"探索"和"验证"的"关键信息"不同。探索的关键是"发现了什么"，验证的关键是"通过了没有"。如果用同一个模板压缩，会丢失各自的核心信息。

## 压缩比与质量控制

Claude Code 的压缩比通常在 **30:1 到 50:1** 之间——75K 的输入压缩到 1.5K 的摘要。但这个压缩比不是固定的，而是有**质量控制机制**：

```typescript
// 压缩质量控制（简化版）
async function compressWithQualityControl(
  fullHistory: Message[]
): Promise<CompressionResult> {
  // 1. 生成摘要
  const summary = await compressSubAgentResult(fullHistory);
  
  // 2. 评估摘要质量（自评估）
  const qualityScore = await evaluateSummaryQuality(fullHistory, summary);
  
  if (qualityScore < MIN_QUALITY_THRESHOLD) {
    // 质量不足：调整策略，增加关键信息保留
    const enhancedSummary = await compressWithEnhancedContext(fullHistory, summary);
    return { summary: enhancedSummary, qualityScore: qualityScore + 0.2 };
  }
  
  // 3. 检查压缩比
  const compressionRatio = estimateTokens(fullHistory) / estimateTokens(summary.content);
  
  if (compressionRatio < MIN_COMPRESSION_RATIO) {
    // 压缩比太低：进一步压缩
    const recompressed = await aggressiveCompress(summary);
    return { summary: recompressed, compressionRatio };
  }
  
  return { summary, qualityScore, compressionRatio };
}

// 质量评估（用 LLM 检查摘要是否遗漏关键信息）
async function evaluateSummaryQuality(
  fullHistory: Message[],
  summary: Summary
): Promise<number> {
  const checkResult = await callModel({
    model: 'haiku',
    messages: [{
      role: 'system',
      content: 'Check if the summary misses any critical information from the original session. Rate 0-1.',
    }, {
      role: 'user',
      content: `Original: ${formatHistoryForSummary(fullHistory)}\n\nSummary: ${summary.content}`,
    }],
  });
  
  return parseFloat(checkResult.content);
}
```

**质量控制的两层检查**：

1. **质量评估**：用 LLM 检查摘要是否遗漏了关键信息。比如子 Agent 修改了一个重要文件，但摘要里没有提到——质量评估会检测到这个遗漏，触发重新生成。

2. **压缩比检查**：如果压缩比低于 30:1（比如 75K 压缩到 3K），说明摘要可能太啰嗦。系统会进一步压缩，比如把"Actions Taken"列表从 10 条压缩到 5 条，或者把文件片段从 100 字符压缩到 50 字符。

**失败回退**：如果质量控制始终无法通过（比如子 Agent 做了太多复杂操作，1-2K 根本说不完），Claude Code 会**放弃压缩**，改为：
- 在摘要中标注"结果过于复杂，请查看完整日志"
- 提供子 Agent 的 Worktree 路径，让用户（或父 Agent）可以手动查看完整结果
- 把子 Agent 的完整结果写入 `memdir`，作为长期记忆保存

## 总结

- 子 Agent 的完整对话历史可能 75K+ token，直接传给父 Agent 会撑爆上下文预算。
- Claude Code 用**轻量模型（Haiku）生成结构化摘要**，实现 30:1 到 50:1 的压缩比。
- 摘要包含六个结构化部分：元信息、Actions、Files Modified、Key Findings、Errors、Verdict。
- **Explore Agent** 和 **Verification Agent** 有不同的压缩策略，保留各自的核心信息。
- **质量控制机制**通过 LLM 自评估检查遗漏，通过压缩比检查防止啰嗦，失败时回退到"查看完整日志"。
- 上下文压缩是子 Agent 架构的"最后一公里"——没有压缩，子 Agent 的结果无法有效回到父 Agent。

> 学完本章后，请继续阅读 [10 — 权限系统](../10-permissions/README.md)，看 Claude Code 如何控制子 Agent 的操作边界。

## 参考链接

- [Claude Code AgentTool 压缩逻辑](file:///E:/Projects/claude-code/src/tools/AgentTool/compress.ts)
- [Claude Code 摘要生成源码](file:///E:/Projects/claude-code/src/tools/AgentTool/summarize.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Claude Code 上下文压缩策略](file:///E:/Projects/claude-code/src/services/compact/compact.ts)
