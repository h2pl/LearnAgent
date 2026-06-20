# 13 — 评测

没有评测的 Agent 只是 demo。本章用五篇文章建立完整的评测体系：从 [评测体系与指标](./01-evaluation-system.md) 和 [确定性评测](./02-deterministic-evaluation.md) 入手，再到 [LLM-as-Judge](./03-llm-as-judge.md) 自动评测、[评测驱动开发](./04-eval-driven-development.md) 工作流，最后以 [生产环境评测](./05-production-evaluation.md) 收尾。

## 文章列表

| # | 文章 | 核心内容 |
|---|------|---------|
| 01 | [评测体系与指标](01-evaluation-system.md) | 三层评测体系、评测方法谱系、四种评测集、核心指标定义 |
| 02 | [确定性评测方法](02-deterministic-evaluation.md) | 代码检查、执行验证、参考比对、混合方法、选型指南 |
| 03 | [LLM-as-Judge：用 LLM 做自动评测](03-llm-as-judge.md) | LLM 定位、评分模式、Prompt 工程、校准与偏差 |
| 04 | [评测驱动开发实践](04-eval-driven-development.md) | EDD 工作流、CI/CD 门禁、回归测试策略、A/B 测试 |
| 05 | [生产环境评测实践](05-production-evaluation.md) | 在线评测、用户反馈、回放测试、漂移检测 |

## 参考链接

- [Anthropic — Evaluating AI Agents](https://www.anthropic.com/engineering/evaluating-ai-agents)
- [LangSmith Evaluation Concepts](https://docs.smith.langchain.com/evaluation/concepts)
- [OpenAI Evals Framework](https://github.com/openai/evals)
- [DeepEval](https://docs.confident-ai.com/)