# 05 — 多模态集成：推理、检索与 Agent

前三章分别讲了视觉、语音、生成。本章是多模态的汇聚点：怎么把各模态串起来做综合推理、怎么构建多模态知识检索系统、怎么让 Agent 在多模态环境中自主行动。

## 学习路径

本章三篇文章覆盖"推理→检索→行动"的递进关系。

### 1. 跨模态推理

[多模态推理](./01-cross-modal-reasoning.md) 是多模态的高级形态——当模型需要同时处理图像、文字、语音做综合判断时，事情比单模态复杂得多。这篇讲清楚能力边界、多步推理链策略、多模态记忆和评估方法。

### 2. 多模态 RAG

[多模态 RAG](./02-multimodal-rag.md) 把主线第 8 章的 RAG 知识扩展到多模态维度：图+文双通道检索、CLIP 语义索引、视觉知识库的构建方法。

### 3. 多模态 Agent

[多模态 Agent](./03-multimodal-agents.md) 聚焦"行动"维度：Computer Use 深入、视觉 grounding、屏幕 Agent 的工程模式、主流方案对比。

## 文章总览

| 文章 | 内容 |
|------|------|
| [多模态推理](./01-cross-modal-reasoning.md) | 跨模态推理、能力边界、多步推理链、多模态记忆 |
| [多模态 RAG](./02-multimodal-rag.md) | 多模态检索、CLIP 索引、视觉知识库、框架支持 |
| [多模态 Agent](./03-multimodal-agents.md) | Computer Use、视觉 grounding、Agent 规划、方案对比 |

> 上一章：[04 — 多模态生成](../04-multimodal-generation/README.md) —— 创造能力
>
> 下一章：[06 — 多模态工程](../06-multimodal-engineering/README.md) —— 评估、成本与生产交付。
