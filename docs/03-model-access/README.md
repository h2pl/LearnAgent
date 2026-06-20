# 03 — 模型接入

从选模型到跑通代码。本章按"选型→调参→调用→深入→部署→微调"的路径展开：先用 [主流模型对比](./01-model-comparison.md) 建立选型框架，接着掌握 [关键参数](./02-key-parameters-and-tuning.md) 的调优方法，然后通过 [API 调用实战](./03-api-calling.md) 获得第一手体验。之后再深入理解 [模型变体](./04-model-variants-landscape.md)、[推理模型](./05-deep-thinking-and-reasoning.md)、[本地部署](./06-local-deployment.md) 和 [微调](./07-finetuning-guide.md) 等高级话题。学完你将拥有一个支持多模型切换的对话服务。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [主流模型对比与选型](./01-model-comparison.md) | 跨厂商对比、同厂商产品线选型、上下文窗口、成本对比、选型决策框架 |
| 02 | [关键参数与调优](./02-key-parameters-and-tuning.md) | temperature / top_p / max_tokens 的实际效果、Agent 调参模板 |
| 03 | [LLM API 调用实战](./03-api-calling.md) | 调用层级概览（SDK/HTTP/CLI/中间商）、OpenAI SDK 基础调用、流式输出、多模型统一接口、错误处理 |
| 04 | [模型变体速查](./04-model-variants-landscape.md) | 训练阶段（Base/Instruct/Chat/Reasoning）、能力专精（Code/Math/Vision/Function Calling）、部署形态（量化/蒸馏/合并/剪枝）、专用家族（Embedding/Rerank/语音）、行业场景 |
| 05 | [深度思考与推理能力](./05-deep-thinking-and-reasoning.md) | `reasoning_effort` 参数调用、成本权衡、Agent 规划层最佳实践 |
| 06 | [模型本地部署实战](./06-local-deployment.md) | Ollama/vLLM 本地跑模型、量化（Q4/Q8）、GPU 需求与性能 |
| 07 | [模型微调实战指南](./07-finetuning-guide.md) | 微调 vs Prompt vs RAG 决策、LoRA/QLoRA 实操、训练数据准备、常见坑 |

> 学完本章后，请继续阅读 [04 — Prompt 工程](../04-prompt-engineering/README.md)，学习如何通过文字精确控制模型行为。
