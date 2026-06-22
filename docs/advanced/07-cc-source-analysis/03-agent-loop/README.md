# 03 — Agent 循环

CC 的 ReAct 循环核心——query.ts（1729 行）与 QueryEngine.ts（1295 行）的逐行分析，turn 管理、stop_reason 与并发工具执行。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [Agent 循环源码分析](./01-agent-loop-source.md) | query.ts + QueryEngine.ts，ReAct 循环、turn 管理、并发执行 |

## 涉及源码

- `query.ts`（1729 行）
- `QueryEngine.ts`（1295 行）

## 对应理论章节

> [06 — Agent 循环](../../06-agent-loop/README.md) — 先掌握 ReAct 模式的理论，再来看工业级实现。
