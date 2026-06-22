# 08 — 记忆系统

CC 的文件级持久记忆与反思提炼机制——memdir 模块（507 行）实现基于文件的长期记忆，autoDream（324 行）实现离线反思。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [记忆系统源码分析](./01-memory-source.md) | memdir 文件记忆、findRelevantMemories 检索、autoDream 反思提炼 |

## 涉及源码

- `memdir/memdir.ts`（507 行）
- `memdir/findRelevantMemories.ts`（141 行）
- `services/autoDream/autoDream.ts`（324 行）

## 对应理论章节

> [08 — 记忆与状态](../../08-memory-state/README.md) — 先理解记忆的理论模型，再来看工业级持久记忆的实现。
