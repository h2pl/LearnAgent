# 02 — 模型接入

在 [01 — LLM 基础](../01-llm-basics/README.md) 建立认知之后，这一章带你从选模型到跑通代码：先建立全局认知，再立刻动手调用 API 获得第一手体验，然后深入理解模型尺寸、推理模型、本地部署等高级话题，最后掌握关键参数的调优技巧。

学完这部分，你将拥有一个支持多模型切换的对话服务，这是后续所有章节的代码基础。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [主流模型对比与选型](./01-model-comparison.md) | GPT / Claude / Qwen / DeepSeek 对比、选型决策框架 |
| 02 | [LLM API 调用实战](./02-api-calling.md) | 调用层级概览（SDK/HTTP/CLI/中间商）、OpenAI SDK 基础调用、流式输出、多模型统一接口、错误处理 |
| 03 | [模型尺寸与上下文窗口](./03-model-sizes-and-context.md) | 同一家族的不同尺寸（Haiku/Sonnet/Opus）、上下文窗口对比、小模型何时够用 |
| 04 | [模型变体速查](./04-model-variants-landscape.md) | 训练阶段（Base/Instruct/Chat/Reasoning）、能力专精（Code/Math/Vision/Function Calling）、部署形态（量化/蒸馏/合并/剪枝）、专用家族（Embedding/Rerank/语音）、行业场景 |
| 05 | [推理模型专题](./05-reasoning-models.md) | o1/R1/Gemini Thinking/QwQ 等推理模型的机制、何时用、怎么调用 |
| 06 | [本地部署实战](./06-local-deployment.md) | Ollama/vLLM 本地跑模型、量化（Q4/Q8）、GPU 需求与性能 |
| 07 | [关键参数与调优](./07-key-parameters.md) | temperature / top_p / max_tokens 的实际效果、Agent 调参模板 |

> 学完本章后，请继续阅读 [03 — Prompt 工程](../03-prompt-engineering/README.md)，学习如何通过文字精确控制模型行为。
