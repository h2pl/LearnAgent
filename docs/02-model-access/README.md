# 02 — 模型接入

在 [01 — LLM 基础](../01-llm-basics/README.md) 建立认知之后，这一章解决动手问题：市面上模型这么多该选哪个、同一家族不同尺寸怎么挑、推理模型和普通模型有什么区别、API 怎么调通、能不能本地部署、关键参数到底怎么影响输出。

学完这部分，你将拥有一个支持多模型切换的对话服务，这是后续所有章节的代码基础。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [主流模型对比与选型](./01-model-comparison.md) | GPT / Claude / Qwen / DeepSeek 对比、选型决策框架 |
| 02 | [模型尺寸与变体](./02-model-variants.md) | 同一家族的不同尺寸（Haiku/Sonnet/Opus）、小模型什么时候够用 |
| 03 | [推理模型专题](./03-reasoning-models.md) | o1/R1 等推理模型的机制、何时用、怎么调用 |
| 04 | [LLM API 调用实战](./04-api-calling.md) | OpenAI SDK、流式输出、多模型统一接口、错误处理 |
| 05 | [本地部署实战](./05-local-deployment.md) | Ollama/vLLM 本地跑模型、量化（Q4/Q8）、GPU 需求与性能 |
| 06 | [关键参数与调优](./06-key-parameters.md) | temperature / top_p / max_tokens 的实际效果、Agent 调参模板 |

> 学完本章后，请继续阅读 [03 — Prompt 工程](../03-prompt-engineering/README.md)，学习如何通过文字精确控制模型行为。
