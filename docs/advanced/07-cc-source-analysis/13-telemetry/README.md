# 13 — 可观测性

CC 的遥测与可观测性体系——instrumentation.ts（825 行）与 sessionTracing.ts（927 行），Span 树、成本追踪与调试能力。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [可观测性源码分析](./01-telemetry-source.md) | Span 树构建、成本追踪、session tracing、调试链路 |

## 涉及源码

- `utils/telemetry/instrumentation.ts`（825 行）
- `utils/telemetry/sessionTracing.ts`（927 行）

## 对应理论章节

> [12 — 评估与优化](../../12-evaluation-optimization/README.md) — 没有可观测性就没有优化，遥测数据是持续改进的基础。
