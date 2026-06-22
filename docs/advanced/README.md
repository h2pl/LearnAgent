# 进阶扩展 — 多模态 AI 系统化讲解

核心 16 章覆盖了 Agent 开发的完整知识栈：从 LLM 基础到工具调用，从 RAG 到多 Agent 协作，从评测到生产交付。但 AI 的世界不止于文本——2026 年的前沿模型已经能同时处理图像、语音、视频等多种模态。

本栏目从多模态的基本概念出发，按照"认知→感知→创造→集成→工程"的递进逻辑，分 6 章系统讲清楚多模态 AI 的全貌。无论你是想让 Agent 看懂截图、听懂语音、还是生成图像，这里都能帮你建立完整的理解。

> 前置知识：本栏目假设你已完成核心 16 章的学习，尤其是 [02 LLM 基础](../02-llm-basics/README.md)、[05 工具调用](../05-tool-use/README.md)、[08 RAG](../08-rag-pipeline/README.md) 和 [09 记忆管理](../09-memory-management/README.md)。

## 章节导航

| 阶段 | 章节 | 核心问题 |
|------|------|----------|
| 认知与机制 | [01 多模态基础](./multimodal/01-multimodal-fundamentals/README.md) | 多模态是什么？模型内部怎么处理不同模态的信息？ |
| 视觉感知 | [02 多模态视觉](./multimodal/02-multimodal-vision/README.md) | 怎么让模型看懂图片、视频和文档？ |
| 语音感知 | [03 语音与音频](./multimodal/03-multimodal-speech/README.md) | 怎么让模型能听能说？ |
| 创造能力 | [04 多模态生成](./multimodal/04-multimodal-generation/README.md) | 怎么让模型生成图像和视频？ |
| 综合与推理 | [05 多模态集成](./multimodal/05-multimodal-integration/README.md) | 多模态综合推理、检索与 Agent 怎么做？ |
| 工程实践 | [06 多模态工程](./multimodal/06-multimodal-engineering/README.md) | 从 demo 到生产要补什么？ |
| 源码解析 | [07 Claude Code 源码](./cc-source-analysis/README.md) | 生产级 Agent 怎么把理论落地？ |


## 两条技术路线

多模态 AI 不是"一套统一技术"，而是两条截然不同的技术路线的结合：

- **理解侧**（Transformer 体系）：让模型"看懂"和"听懂"——输入图像/音频，输出文字/结构化信息
- **生成侧**（扩散模型体系）：让模型"创造"——输入文字描述，输出图像/视频

两条路线的架构、训练方式、推理过程和成本结构完全不同。"多模态核心机制"会详细拆解这个区分，后续章节分别深入。

## 文章索引

| 章节 | 文章 | 内容 |
|------|------|------|
| 01 多模态基础 | [什么是多模态](./multimodal/01-multimodal-fundamentals/01-what-is-multimodal.md) | 概念、单模态 vs 多模态、成熟的三个转折点 |
| | [为什么需要多模态](./multimodal/01-multimodal-fundamentals/02-why-multimodal.md) | 流水线方案的三大问题、原生方案的优势 |
| | [模态异质性](./multimodal/01-multimodal-fundamentals/03-modality-heterogeneity.md) | 四种模态的表示差异、模态组合速查 |
| | [两条技术路线](./multimodal/01-multimodal-fundamentals/04-two-tech-routes.md) | 理解 vs 生成、架构对比、API 统一趋势 |
| | [2026 模型全景与选型](./multimodal/01-multimodal-fundamentals/05-model-landscape.md) | 模型梯队、能力对比、场景选型 |
| | [多模态表示与翻译](./multimodal/01-multimodal-fundamentals/06-representation-and-translation.md) | 单模态编码、联合/协调表示、示例/生成式翻译、文生图/视频 |
| | [对齐、融合与协同学习](./multimodal/01-multimodal-fundamentals/07-alignment-fusion-colearning.md) | 显式/隐式对齐、注意力机制、融合策略、协同学习、零样本 |
| 02 多模态视觉 | [视觉理解](./multimodal/02-multimodal-vision/01-vision-understanding.md) | 图像/视频理解 API、Computer Use、视觉 RAG、成本优化 |
| | [视频理解](./multimodal/02-multimodal-vision/02-video-understanding.md) | 帧采样策略、长视频处理、时序推理、模型能力对比 |
| | [文档与图表理解](./multimodal/02-multimodal-vision/03-document-understanding.md) | PDF 解析、版面分析、表格提取、图表解读、方案选型 |
| | [实战指南](./multimodal/02-multimodal-vision/04-practical-guide.md) | 场景判断、模型选型决策树、工作流设计、质量调优 |
| | [Agent 场景](./multimodal/02-multimodal-vision/05-agent-scenarios.md) | 屏幕 Agent、文档处理、视觉 QA、多模态 RAG |
| | [成本优化](./multimodal/02-multimodal-vision/06-cost-optimization.md) | 分辨率优化、缓存策略、Batch API、视频专项优化 |
| 03 语音与音频 | [语音与音频](./multimodal/03-multimodal-speech/01-speech-and-audio.md) | STT/TTS、Realtime API、语音 Agent 循环、中断处理 |
| 04 多模态生成 | [图像与视频生成](./multimodal/04-multimodal-generation/01-image-and-video-generation.md) | 扩散模型机制、API 对比、条件引导、视频生成、Prompt 策略 |
| | [原生多模态输出](./multimodal/04-multimodal-generation/02-native-multimodal-output.md) | Gemini Imagen 3、GPT-5 images、统一 API vs 专用模型 |
| 05 多模态集成 | [多模态推理](./multimodal/05-multimodal-integration/01-cross-modal-reasoning.md) | 跨模态推理、能力边界、多步推理链、多模态记忆 |
| | [多模态 RAG](./multimodal/05-multimodal-integration/02-multimodal-rag.md) | 多模态检索、CLIP 索引、视觉知识库、框架支持 |
| | [多模态 Agent](./multimodal/05-multimodal-integration/03-multimodal-agents.md) | Computer Use、视觉 grounding、Agent 规划、方案对比 |
| 06 多模态工程 | [多模态工程实践](./multimodal/06-multimodal-engineering/02-multimodal-in-production.md) | 评估指标、成本模型、可观测性、安全治理、上线 checklist |
| 07 CC源码解析 | [整体架构](./cc-source-analysis/01-architecture-overview/README.md) | 51万行代码全景、模块划分、1.6% AI决策逻辑 |
| | [启动流程](./cc-source-analysis/02-bootstrap/README.md) | entrypoints/bootstrap、启动优化、并行预取 |
| | [Agent 循环](./cc-source-analysis/03-agent-loop/README.md) | query.ts 1729行 while True、turn管理、stop_reason |
| | [工具系统](./cc-source-analysis/04-tool-system/README.md) | Tool.ts buildTool工厂、Schema生成、权限回调 |
| | [LLM 调用层](./cc-source-analysis/05-llm-calling/README.md) | 3419行统一调用、重试、token追踪、多模型路由 |
| | [系统提示词](./cc-source-analysis/06-system-prompt-engineering/README.md) | 提示词组装、缓存冻结、DYNAMIC_BOUNDARY |
| | [上下文工程](./cc-source-analysis/07-context-engineering/README.md) | 五层压缩管线、autoCompact、microCompact |
| | [记忆系统](./cc-source-analysis/08-memory/README.md) | memdir文件级持久、autoDream反思提炼 |
| | [子Agent](./cc-source-analysis/09-subagent/README.md) | AgentTool 2657行、上下文隔离、Git Worktree |
| | [权限系统](./cc-source-analysis/10-permissions/README.md) | 七种权限模式、ML分类器、危险模式拦截 |
| | [扩展机制](./cc-source-analysis/11-extensibility/README.md) | MCP + Skills + Hooks + Plugins 四种扩展方式 |
| | [会话持久化](./cc-source-analysis/12-session-persistence/README.md) | 断点续传、checkpoint、状态恢复 |
| | [可观测性](./cc-source-analysis/13-telemetry/README.md) | Span树、成本追踪、telemetry 1752行 |
| | [设计哲学](./cc-source-analysis/14-design-philosophy/README.md) | 五个核心价值观、设计原则到技术实现 |

