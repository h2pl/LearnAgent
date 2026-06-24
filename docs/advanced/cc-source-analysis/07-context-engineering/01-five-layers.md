# 五层压缩概览

> Claude Code 用 5 层渐进式压缩管理 200K 上下文窗口：从最便宜的削预算到最昂贵的全对话总结。每一层解决一种上下文膨胀，92% 的情况在前两层就能搞定。

你好，我是江小湖。

在 [03 Agent 循环 — 消息预处理](../03-agent-loop/02-preprocessing.md) 中我们概览了 5 层预处理的顺序。这一篇站在"上下文工程"的视角重新审视这 5 层：每一层独立解决什么问题、为什么按照这个顺序、以及它们之间的协作关系。

## 目录

- [为什么是 5 层而不是 1 层](#为什么是-5-层而不是-1-层)
- [逐层解析](#逐层解析)
- [层间协作：信息损失的阶梯](#层间协作信息损失的阶梯)
- [压缩决策树：哪层在什么条件下触发](#压缩决策树哪层在什么条件下触发)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/07-context-engineering/compression-layers.svg" alt="上下文压缩" width="90%"/>
  <br/>
  <em>200K Token 窗口的 5 层压缩机制</em>
</p>



<p align="center">
  <img src="../../../../assets/cc-source-analysis/07-context-engineering/autocompact-flow.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 07-context-engineering 配图</em>
</p>
## 为什么是 5 层而不是 1 层

一个直觉的想法是：上下文快满了，直接做个全对话总结不就行了？

问题是：**全对话总结贵**。它需要调用一次 LLM，产生延迟和费用，而且会粗暴地丢细节。一次典型的 autocompact 需要 3000-20000 个输出 token，按 Claude Opus 的价格算，每次压缩成本在 0.05-0.30 USD。

所以 Claude Code 设计了 5 层压缩，从最便宜的到最贵的依次尝试：

```
原始上下文 (200K token)
  ↓
1. applyToolResultBudget   — 削预算：每个工具结果不超过 N chars
  成本: 零（纯截断）         信息损失: 低（截断的可恢复）
  ↓
2. snip                    — 删孤儿：删掉早期没再被引用的工具结果
  成本: 零（不调 LLM）      信息损失: 中（删了就没了）
  ↓
3. microcompact            — 单结果压缩：把单个工具结果替换为摘要
  成本: 低（不调 LLM，用规则） 信息损失: 中
  ↓
4. contextCollapse         — 多轮折叠：把连续的多轮对话归档为摘要
  成本: 中（调用 LLM）       信息损失: 中高
  ↓
5. autocompact             — 全对话总结：整段历史总结为一段摘要
  成本: 高（调用 LLM，3K-20K output） 信息损失: 高
  ↓
模型看到压缩后的上下文
```

5 层的核心思想：**尽量用低成本、低信息损失的方式解决问题。** 第 1-3 层不调 LLM，第 4-5 层才调用。实际使用中，92% 的上下文压力在前两层就被化解了。

## 逐层解析

### 第 1 层：applyToolResultBudget

**解决的问题**：单个工具结果太大。

某些工具（ReadTool 读大文件、GlobTool 返回大量匹配）会产生超长输出。如果不限制，一个工具结果就可能占掉几万 token。

这一层根据工具配置里的 `maxResultSizeChars`，把过长的结果截断或替换为占位符。被替换的内容不会从会话历史中删除——它们被存到磁盘文件中，需要时可以通过 `ReadTool` 重新读取。

关键是：**被截断的内容是可恢复的。** 这和其他层的不可逆压缩完全不同。

### 第 2 层：snip

**解决的问题**：早期无用的工具结果堆积。

在一段长对话里，前面某轮调用的 `BashTool` 输出可能只对那一轮有意义，后面再也没被引用过。snip 识别这些"孤儿"工具结果，把它们从当前上下文里移除。

关键特点：snip **只删消息，不总结**。所以它是完全免费的——不需要调用任何 LLM。

### 第 3 层：microcompact

**解决的问题**：单个工具结果的语义冗余。

microcompact 按 `tool_use_id` 匹配，把某个工具结果的完整内容替换成一段短摘要。比如一次 `BashTool` 输出的几百行日志，可以被压缩成一句话。

microcompact 只压缩特定类型的工具（ReadTool、BashTool、GrepTool、GlobTool 等），对 EditTool 和 WriteTool 的输出不做压缩——这些输出通常本身就是简洁的。

microcompact 还有一个关键设计：它**只认 tool_use_id，从不检查内容**。这保证了它和 applyToolResultBudget 可以安全组合，互不干扰。

### 第 4 层：contextCollapse

**解决的问题**：多轮对话的累积膨胀。

microcompact 解决的是"单个结果太大"，contextCollapse 解决的是"对话轮次太多"。它把连续的多轮对话归档成一个摘要消息，存入 collapse store。每次循环开始时，重放 collapse store 的提交日志来重建压缩后的视图。

这个设计的精妙之处：**压缩效果跨轮次持久化**。即使当前循环没有触发新的折叠，之前的折叠仍然生效。

### 第 5 层：autocompact

**解决的问题**：前 4 层都搞不定的极端长对话。

autocompact 调用一次 LLM，把整段历史总结为摘要。这是最贵的一层。具体实现见下一篇 [自动压缩](./02-autocompact.md)。

## 层间协作：信息损失的阶梯

| 层 | 成本 | 信息损失 | 可逆性 | 适用场景 |
|-----|------|---------|--------|---------|
| applyToolResultBudget | 零 | 低 | ✅ 可恢复 | 读大文件 |
| snip | 零 | 中 | ❌ 不可逆 | 一次性命令输出 |
| microcompact | 低 | 中 | ❌ 不可逆 | 冗长日志 |
| contextCollapse | 中 | 中高 | ❌ 不可逆 | 多轮对话 |
| autocompact | 高 | 高 | ❌ 不可逆 | 极端长对话 |

## 压缩决策树：哪层在什么条件下触发

```
每次模型调用前:
  1. applyToolResultBudget — 始终执行（无副作用）
  2. IF token 接近阈值:
     a. snip — 始终尝试
     b. IF snip 后仍然超标:
        microcompact — 按 tool_use_id 压缩可压缩工具
        IF microcompact 后仍然超标:
          contextCollapse — 折叠多轮对话
          IF contextCollapse 后仍然超标:
            autocompact — 全对话总结
            IF autocompact 连续失败 3 次:
              熔断（不再尝试压缩）
```

第 03 章已经详细介绍了这个流程在 `query.ts` 中的实现。这里强调一个关键洞察：**这个顺序保证了在绝大多数会话中（80%+），上下文管理是零成本的。**

## 总结

- 5 层压缩从便宜到贵依次触发：削预算 → 删孤儿 → 单结果压缩 → 多轮折叠 → 全对话总结。
- 前 3 层不调 LLM，第 4-5 层才调用。92% 的上下文压力在前两层化解。
- 第 1 层是可逆的（内容存磁盘），其他层不可逆。
- 压缩决策树保证了在 80%+ 的会话中，上下文管理是零成本的。
- 层间通过 `tool_use_id` 协作，互不干扰。

> 下一篇：[自动压缩](./02-autocompact.md)，深入 autocompact 的触发阈值、熔断机制和 CLAUDE.md 保护。

## 参考链接

- [Claude Code compact/ 目录](file:///E:/Projects/claude-code/src/services/compact/)
- [Claude Code query.ts — 预处理逻辑](file:///E:/Projects/claude-code/src/query.ts)
- [Claude Code Tool.ts — maxResultSizeChars](file:///E:/Projects/claude-code/src/Tool.ts)
