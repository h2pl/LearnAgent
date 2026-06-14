# 01 — LLM 基础

LLM 是 Agent 的大脑。在写 Prompt、调 API、搭 RAG 之前，你需要先建立对它的正确认知。

本章从应用开发者视角讲清楚：LLM 到底是什么、文本怎么变成数字（Token 和 Embedding）、Transformer 在里面扮演什么角色、模型是怎么训练出来的、以及它能做什么、不能做什么。这些认知直接决定你后续的设计判断——比如你知道了幻觉的本质，就能理解为什么需要 RAG；知道了 context window 的限制，就能理解为什么需要上下文工程。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [LLM 概述](./01-llm-overview.md) | LLM 的定义、核心原理、主流模型 |
| 02 | [LLM 的技术根基：从 NLP 到 Transformer](./02-nlp-to-transformer.md) | 规则→统计→深度学习→Transformer，LLM 之前的技术演进 |
| 03 | [LLM 发展简史](./03-llm-evolution.md) | 预训练范式 → 规模涌现 → RLHF 对齐 → ChatGPT → Agent 时代 |
| 04 | [Token 与 Embedding](./04-token-and-embedding.md) | 文本如何变成数字、语义向量、为什么 Token 是一切的基础 |
| 05 | [Transformer 架构直觉](./05-transformer-intuition.md) | 注意力机制、自回归生成、位置编码——只讲直觉不推公式 |
| 06 | [模型训练流程概览](./06-training-pipeline.md) | 预训练 → 指令微调(SFT) → 对齐(RLHF)，知道模型是怎么来的 |
| 07 | [能力与局限](./07-capabilities-and-limits.md) | 幻觉、知识截止、上下文限制、偏见 |

> 学完本章后，请继续阅读 [02 — 模型接入](../02-model-access/README.md)，进入模型选型与 API 调用实战。
