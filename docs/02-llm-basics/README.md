# 02 — LLM 基础

LLM 是 Agent 的大脑。在写 Prompt、调 API、搭 RAG 之前，你需要先建立对它的正确认知。

本章从应用开发者视角讲清楚：LLM 到底是什么、能做什么、不能做什么、文本怎么变成向量（Token 和 Embedding）、Transformer 在里面扮演什么角色、模型是怎么训练出来的。这 8 篇文章按"认知→能力→限制→原理→训练"的路径递进：先从 [认识大语言模型](./01-llm-overview.md) 建立基本概念，通过 [技术根基](./02-nlp-to-transformer.md) 和 [发展简史](./03-llm-evolution.md) 理解来龙去脉，再深入 [核心能力](./04-capabilities.md) 与 [局限](./05-limitations-and-countermeasures.md)，最后用 [Token 与 Embedding](./06-token-and-embedding.md)、[Transformer 原理](./07-transformer-internals.md) 和 [训练三阶段](./08-training-pipeline.md) 完成技术深潜。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [认识大语言模型（LLM）](./01-llm-overview.md) | LLM 的定义、核心原理、主流模型 |
| 02 | [LLM 的技术根基：从 NLP 到 Transformer](./02-nlp-to-transformer.md) | 规则→统计→深度学习→Transformer，LLM 之前的技术演进 |
| 03 | [LLM 发展简史](./03-llm-evolution.md) | 预训练范式 → 规模涌现 → RLHF 对齐 → ChatGPT → Agent 时代 |
| 04 | [LLM 核心能力](./04-capabilities.md) | 文本理解、推理、代码、少样本学习、指令遵循 |
| 05 | [LLM 的局限与工程对策](./05-limitations-and-countermeasures.md) | 每个局限的架构根因、具体失效案例、Agent 工程对策 |
| 06 | [Token 与 Embedding：文本是如何变成向量的](./06-token-and-embedding.md) | 分词原理、语义向量、Token 对成本和上下文的影响 |
| 07 | [Transformer 内部原理](./07-transformer-internals.md) | Block 结构、注意力计算、多头注意力、因果掩码、KV Cache |
| 08 | [从 Base 到 Chat：模型训练三阶段](./08-training-pipeline.md) | 预训练数据工程 → SFT → RLHF/DPO 对齐 → LoRA 微调实践 |

> 学完本章后，请继续阅读 [03 — 模型接入](../03-model-access/README.md)，进入模型选型与 API 调用实战。
