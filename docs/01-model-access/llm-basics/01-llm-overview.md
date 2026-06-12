# LLM 概述

## 目录

- [概述](#概述)
- [LLM 的定义](#llm-的定义)
- [一句话理解核心原理](#一句话理解核心原理)
- [参考链接](#参考链接)

## 概述

这篇文章回答一个最基础的问题：**大语言模型（Large Language Model, LLM）到底是什么？**

你不需要能训练一个 LLM，但作为应用开发者，你需要知道它的本质、它和传统 NLP 技术的区别、以及它是怎么一步步发展到今天的。这些认知会直接影响你后续对 Prompt、RAG、Agent 的理解和判断。

## LLM 的定义

**大语言模型是一类基于深度神经网络（主要是 Transformer 架构）的语言模型，通过在海量文本数据上进行预训练，获得了通用的语言理解和生成能力。**

拆开来理解：

- **"大"（Large）**：指的是模型参数量巨大。GPT-3 有 1750 亿参数，GPT-4 的参数量未公开但估计在万亿级别。参数越多，模型能学到的语言模式就越复杂。
- **"语言模型"（Language Model）**：本质上是一个概率模型——给定一段文本，预测下一个最可能出现的词（token）。这个看似简单的任务，在足够大的模型和足够多的数据上训练后，涌现出了令人惊讶的能力。
- **"预训练"（Pre-trained）**：LLM 不是为某个特定任务设计的，而是先在海量通用语料（书籍、网页、代码等）上训练，学会语言的通用规律，然后再通过微调适配具体任务。

当前主流的 LLM 包括（截至 2026 年 6 月，综合 [LLM Stats](https://llm-stats.com/)、[Arena Leaderboard](https://arena.ai/leaderboard) 数据）：

**闭源模型**

| 模型 | 公司 | 定位 | 特点 |
|------|------|------|------|
| Claude Fable 5 | Anthropic | Agentic 编码 | Quality Index 100/100，SWE-Bench 95% |
| Claude Opus 4.8 | Anthropic | 编码 + Agent | Quality Index 99/100，GPQA 94.6% |
| GPT-5.5 | OpenAI | 通用旗舰 | 多模态，统一推理模式 |
| Gemini 3.1 Pro | Google | 科研 + 长上下文 | AIME 满分，超长上下文窗口 |
| Grok 4.3 | xAI | Agentic + 实时信息 | 200 万 tokens 上下文 |
| Claude Sonnet 4.6 | Anthropic | 日用编程 | 性价比最佳的编程主力 |

**开源 / 开放权重模型**

| 模型 | 公司 | 定位 | 特点 |
|------|------|------|------|
| Kimi K2.6 | Moonshot | 综合 | 开源第一（GPQA 90.5%） |
| DeepSeek V4 Pro | DeepSeek | 推理 + 代码 | MoE 架构，极致性价比 |
| Qwen 3.7 Max | 阿里巴巴 | 长程 Agent | Top 10 最便宜（$1.25/M tok），中文强 |
| GLM-5.1 | 智谱 | Agent 原生 | 综合排名前列 |
| Llama 4 | Meta | 通用 | 社区生态最活跃 |
| Gemma 4 | Google | 端侧部署 | 轻量高效，多种规格 |

> 模型迭代非常快，以上排名随时可能变化。实时排行请参考 [Arena Leaderboard](https://arena.ai/leaderboard)、[LLM Stats](https://llm-stats.com/leaderboards/llm-leaderboard) 或 [LMSYS Chatbot Arena](https://chat.lmsys.org/)。

## 一句话理解核心原理

LLM 的核心原理可以用一句话概括：

> **给定前面所有的词，预测下一个词。**

这就是所谓的**自回归生成（Autoregressive Generation）**。当你向 ChatGPT 提问时，它并不是"理解"了你的问题然后"思考"出答案，而是根据你的输入（加上 system prompt 等上下文），一个 token 一个 token 地预测最可能出现的下一个 token，直到生成完整的回答。

举个例子：

```
输入: "中国的首都是"
预测过程:
  → "北"  (概率最高)
  → "京"  (概率最高)
  → "。"  (停止)
```

这个机制有几个重要推论，会贯穿整个课程：

1. **LLM 的输出是概率性的**，不是确定性的。同样的输入可能产生不同的输出（取决于 temperature 等参数）。
2. **LLM 没有"真正的理解"**，它是一个极其强大的模式匹配器。它在训练数据中学到了语言的统计规律，然后用这些规律来生成看起来合理的文本。
3. **LLM 会"幻觉"**——它会自信地生成看似正确但实际上是编造的内容，因为它优化的目标是"生成最可能的下一个词"，而不是"生成正确的事实"。

LLM 不是凭空出现的——它背后是几十年 NLP（自然语言处理）技术的积累，从手写规则到统计学习，再到深度学习，最终 Transformer 架构的出现让一切质变。理解这段演进史，你就能明白 LLM 为什么是今天这个样子。

> 接下来请阅读 [从 NLP 到 Transformer](./02-nlp-to-transformer.md)，了解 LLM 之前的技术演进，以及 Transformer 如何改变了一切。

## 参考链接

- [Attention Is All You Need (2017)](https://arxiv.org/abs/1706.03762) — Transformer 原始论文
- [Wikipedia — Large Language Model](https://en.wikipedia.org/wiki/Large_language_model)
- [3Blue1Brown — But what is a GPT?](https://www.youtube.com/watch?v=wjZofJX0v4M) — 直观的视频讲解
- [Andrej Karpathy — State of GPT](https://www.youtube.com/watch?v=bZQun8Y4L2A) — GPT 训练全流程概览
- [Scaling Laws for Neural Language Models (2020)](https://arxiv.org/abs/2001.08361) — 规模定律原始论文
