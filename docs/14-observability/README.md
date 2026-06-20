# 14 — 可观测性与监控

追踪让你看到 Agent 的每一步，监控让你实时掌握系统健康。五篇文章从 [可观测性设计原则](./01-observability-principles.md) 开始，依次讲解 [全链路追踪](./02-tracing-implementation.md)、[性能分析](./03-performance-analysis.md)、[成本优化](./04-cost-optimization.md)，最后以 [生产监控与告警](./05-production-monitoring.md) 收尾。

## 文章列表

| # | 文章 | 核心内容 |
|---|------|---------|
| 01 | [可观测性设计原则](01-observability-principles.md) | O11y 三支柱的 Agent 适配、设计原则、工具选型决策 |
| 02 | [全链路追踪实现](02-tracing-implementation.md) | 埋点模式、Span 设计、Trace ID 传播、采样与存储 |
| 03 | [性能分析与优化](03-performance-analysis.md) | 延迟模型、瓶颈识别、分层优化、性能案例 |
| 04 | [成本管理与优化](04-cost-optimization.md) | 成本归因、预算管控、优化策略、成本案例 |
| 05 | [生产监控与告警](05-production-monitoring.md) | SLI/SLO、仪表盘设计、告警规则、Runbook |

## 参考链接

- [LangFuse Documentation](https://langfuse.com/docs)
- [LangSmith Tracing](https://docs.smith.langchain.com/tracing)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Arize AI — LLM Observability](https://arize.com/llm-observability/)
