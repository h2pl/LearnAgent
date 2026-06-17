# 02 — 模型接入

在 [01 — LLM 基础](../01-llm-basics/README.md) 建立认知之后，这一章带你从选模型到跑通代码：先建立全局认知，认识 API 关键参数，再立刻动手调用 API 获得第一手体验，然后深入理解模型变体、推理模型、本地部署等高级话题。

学完这部分，你将拥有一个支持多模型切换的对话服务，这是后续所有章节的代码基础。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [主流模型对比与选型](./01-model-comparison.md) | 跨厂商对比、同厂商产品线选型、上下文窗口、成本对比、选型决策框架 |
| 02 | [关键参数与调优](./02-key-parameters.md) | temperature / top_p / max_tokens 的实际效果、Agent 调参模板 |
| 03 | [LLM API 调用实战](./03-api-calling.md) | 调用层级概览（SDK/HTTP/CLI/中间商）、OpenAI SDK 基础调用、流式输出、多模型统一接口、错误处理 |
| 04 | [模型变体速查](./04-model-variants-landscape.md) | 训练阶段（Base/Instruct/Chat/Reasoning）、能力专精（Code/Math/Vision/Function Calling）、部署形态（量化/蒸馏/合并/剪枝）、专用家族（Embedding/Rerank/语音）、行业场景 |
| 05 | [深度思考与推理能力](./05-reasoning-models.md) | `reasoning_effort` 参数调用、成本权衡、Agent 规划层最佳实践 |
| 06 | [本地部署实战](./06-local-deployment.md) | Ollama/vLLM 本地跑模型、量化（Q4/Q8）、GPU 需求与性能 |
| 07 | [微调实战指南](./07-finetuning-guide.md) | 微调 vs Prompt vs RAG 决策、LoRA/QLoRA 实操、训练数据准备、常见坑 |

> 学完本章后，请继续阅读 [03 — Prompt 工程](../03-prompt-engineering/README.md)，学习如何通过文字精确控制模型行为。
