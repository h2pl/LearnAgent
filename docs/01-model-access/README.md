# 01 — 模型接入

LLM 是 Agent 的大脑，这一章的目标是从应用开发者视角彻底搞懂它。

我们把内容分成两个部分。第一部分「LLM 基础」解决认知问题：LLM 到底是什么、文本怎么变成数字（Token 和 Embedding）、Transformer 在里面扮演什么角色、模型是怎么训练出来的、以及它能做什么不能做什么。这些认知直接决定了你后续写 Prompt、设计工具调用、构建 RAG 时的判断力——比如你知道了幻觉的本质，就能理解为什么需要 RAG；知道了 context window 的限制，就能理解为什么需要上下文工程。

第二部分「模型选型与 API 调用」解决动手问题：市面上模型这么多该选哪个、API 怎么调通、流式输出怎么实现、关键参数（temperature、max_tokens）到底怎么影响输出。学完这部分，你将拥有一个支持多模型切换的对话服务，这是后续所有章节的代码基础。

## 目录

### LLM 基础

| # | 文章 | 内容 |
|---|------|------|
| 01 | [什么是大语言模型](./llm-basics/01-what-is-llm.md) | LLM 的定义、与传统 NLP 的区别、发展脉络 |
| 02 | [Token 与 Embedding](./llm-basics/02-token-and-embedding.md) | 文本如何变成数字、语义向量、为什么 Token 是一切的基础 |
| 03 | [Transformer 架构直觉](./llm-basics/03-transformer-intuition.md) | 注意力机制、自回归生成、位置编码——只讲直觉不推公式 |
| 04 | [模型训练流程概览](./llm-basics/04-training-pipeline.md) | 预训练 → 指令微调(SFT) → 对齐(RLHF)，知道模型是怎么来的 |
| 05 | [能力与局限](./llm-basics/05-capabilities-and-limits.md) | 幻觉、知识截止、上下文限制、偏见 |

### 模型选型与 API 调用

| # | 文章 | 内容 |
|---|------|------|
| 06 | [主流模型对比与选型](./model-comparison.md) | GPT-4o / Claude / Qwen / Llama / DeepSeek 对比、选型决策 |
| 07 | [LLM API 调用实战](./api-calling.md) | OpenAI SDK、流式输出、多模型统一接口、代码示例 |
| 08 | [关键参数与调优](./key-parameters.md) | temperature / top_p / max_tokens 的实际效果、常见踩坑 |
