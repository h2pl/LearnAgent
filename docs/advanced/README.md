# 进阶扩展 — 多模态 AI 系统化讲解

核心 16 章覆盖了 Agent 开发的完整知识栈：从 LLM 基础到工具调用，从 RAG 到多 Agent 协作，从评测到生产交付。但 AI 的世界不止于文本——2026 年的前沿模型已经能同时处理图像、语音、视频等多种模态。

本栏目从多模态的基本概念出发，按照"认知→感知→创造→集成→工程"的递进逻辑，分 6 章系统讲清楚多模态 AI 的全貌。无论你是想让 Agent 看懂截图、听懂语音、还是生成图像，这里都能帮你建立完整的理解。

> 前置知识：本栏目假设你已完成核心 16 章的学习，尤其是 [02 LLM 基础](../02-llm-basics/README.md)、[05 工具调用](../05-tool-use/README.md)、[08 RAG](../08-rag-pipeline/README.md) 和 [09 记忆管理](../09-memory-management/README.md)。

## 章节导航

| 阶段 | 章节 | 核心问题 |
|------|------|----------|
| 认知与机制 | [01 多模态基础](./01-multimodal-fundamentals/README.md) | 多模态是什么？模型内部怎么处理不同模态的信息？ |
| 视觉感知 | [02 多模态视觉](./02-multimodal-vision/README.md) | 怎么让模型看懂图片、视频和文档？ |
| 语音感知 | [03 语音与音频](./03-multimodal-speech/README.md) | 怎么让模型能听能说？ |
| 创造能力 | [04 多模态生成](./04-multimodal-generation/README.md) | 怎么让模型生成图像和视频？ |
| 综合与推理 | [05 多模态集成](./05-multimodal-integration/README.md) | 多模态综合推理、检索与 Agent 怎么做？ |
| 工程实践 | [06 多模态工程](./06-multimodal-engineering/README.md) | 从 demo 到生产要补什么？ |

## 两条技术路线

多模态 AI 不是"一套统一技术"，而是两条截然不同的技术路线的结合：

- **理解侧**（Transformer 体系）：让模型"看懂"和"听懂"——输入图像/音频，输出文字/结构化信息
- **生成侧**（扩散模型体系）：让模型"创造"——输入文字描述，输出图像/视频

两条路线的架构、训练方式、推理过程和成本结构完全不同。第 1 章会详细拆解这个区分，后续章节分别深入。

## 文章索引

| 章节 | 文章 | 内容 |
|------|------|------|
| 01 多模态基础 | [多模态 AI 全景](./01-multimodal-fundamentals/01-multimodal-landscape.md) | 什么是多模态、模态异质性、2026 模型全景、模态组合速查 |
| | [多模态核心机制](./01-multimodal-fundamentals/02-core-mechanisms.md) | 理解 vs 生成两条路线、编码、融合、对齐 |
| | [跨模态表示学习](./01-multimodal-fundamentals/03-cross-modal-representation.md) | CLIP 训练机制、对比学习、多模态嵌入模型、向量空间几何 |
| 02 多模态视觉 | [视觉理解](./02-multimodal-vision/01-vision-understanding.md) | 图像/视频理解 API、Computer Use、视觉 RAG、成本优化 |
| | [视频理解](./02-multimodal-vision/02-video-understanding.md) | 帧采样策略、长视频处理、时序推理、模型能力对比 |
| | [文档与图表理解](./02-multimodal-vision/03-document-understanding.md) | PDF 解析、版面分析、表格提取、图表解读、方案选型 |
| 03 语音与音频 | [语音与音频](./03-multimodal-speech/01-speech-and-audio.md) | STT/TTS、Realtime API、语音 Agent 循环、中断处理 |
| 04 多模态生成 | [图像与视频生成](./04-multimodal-generation/01-image-and-video-generation.md) | 扩散模型机制、API 对比、条件引导、视频生成、Prompt 策略 |
| | [原生多模态输出](./04-multimodal-generation/02-native-multimodal-output.md) | Gemini Imagen 3、GPT-5 images、统一 API vs 专用模型 |
| 05 多模态集成 | [多模态推理](./05-multimodal-integration/01-cross-modal-reasoning.md) | 跨模态推理、能力边界、多步推理链、多模态记忆 |
| | [多模态 RAG](./05-multimodal-integration/02-multimodal-rag.md) | 多模态检索、CLIP 索引、视觉知识库、框架支持 |
| | [多模态 Agent](./05-multimodal-integration/03-multimodal-agents.md) | Computer Use、视觉 grounding、Agent 规划、方案对比 |
| 06 多模态工程 | [多模态工程实践](./06-multimodal-engineering/02-multimodal-in-production.md) | 评估指标、成本模型、可观测性、安全治理、上线 checklist |
