# 05 — LLM 调用层

CC 的 LLM 统一调用封装——claude.ts（3419 行）与 client.ts（389 行），重试机制、token 用量追踪与多模型路由策略。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [LLM 调用层源码分析](./01-llm-calling-source.md) | 统一调用封装、重试机制、token 追踪、多模型路由 |

## 涉及源码

- `services/api/claude.ts`（3419 行）
- `services/api/client.ts`（389 行）

## 对应理论章节

> [03 — 提示工程](../../03-prompt-engineering/README.md) — 提示词如何最终送达模型并得到可靠响应。
