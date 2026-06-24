# 进阶扩展 — 多模态 AI 系统化讲解

核心 16 章覆盖了 Agent 开发的完整知识栈：从 LLM 基础到工具调用，从 RAG 到多 Agent 协作，从评测到生产交付。但 AI 的世界不止于文本——2026 年的前沿模型已经能同时处理图像、语音、视频等多种模态。

本栏目从多模态的基本概念出发，按照"认知→模型演进→感知→创造→工程"的递进逻辑，分 5 章系统讲清楚多模态 AI 的全貌。无论你是想理解视觉语言模型、接入语音交互，还是生成图像视频，这里都能帮你建立完整的理解。

> 前置知识：本栏目假设你已完成核心 16 章的学习，尤其是 [02 LLM 基础](../02-llm-basics/README.md)、[05 工具调用](../05-tool-use/README.md)、[08 RAG](../08-rag-pipeline/README.md) 和 [09 记忆管理](../09-memory-management/README.md)。

## 章节导航

| 阶段 | 章节 | 核心问题 |
|------|------|----------|
| 认知与机制 | [01 多模态认知](./multimodal/01-multimodal-cognition/README.md) | 多模态是什么？技术怎么演变？核心机制是什么？ |
| 视觉理解 | [02 视觉语言模型](./multimodal/02-vision-language-models/README.md) | 从 CLIP 到 GPT-4o，视觉语言模型的演进与实战 |
| 语音交互 | [03 语音交互](./multimodal/03-speech-interaction/README.md) | 怎么让模型能听会说？ |
| 生成创造 | [04 多模态生成](./multimodal/04-multimodal-generation/README.md) | 怎么让模型生成图像和视频？ |
| 工程落地 | [05 工程落地](./multimodal/05-engineering-production/README.md) | 从 demo 到生产要补什么？ |
| 源码解析 | [07 Claude Code 源码](./cc-source-analysis/README.md) | 生产级 Agent 怎么把理论落地？ |


## 两条技术路线

多模态 AI 不是"一套统一技术"，而是两条截然不同的技术路线的结合：

- **理解侧**（Transformer 体系）：让模型"看懂"和"听懂"——输入图像/音频，输出文字/结构化信息
- **生成侧**（扩散模型体系）：让模型"创造"——输入文字描述，输出图像/视频

两条路线的架构、训练方式、推理过程和成本结构完全不同。"多模态核心机制"会详细拆解这个区分，后续章节分别深入。

## 文章索引

| 章节 | 文章 | 内容 |
|------|------|------|
| 01 多模态认知 | [什么是多模态 AI](./multimodal/01-multimodal-cognition/01-what-is-multimodal.md) | 定义、模态类型、为什么现在成熟了 |
| | [技术演进](./multimodal/01-multimodal-cognition/02-tech-evolution.md) | 三代架构：拼接式 → 指令微调 → 原生统一 |
| | [核心机制](./multimodal/01-multimodal-cognition/03-core-mechanisms.md) | 表示学习、跨模态对齐、注意力融合 |
| 02 视觉语言模型 | [VLM 演进](./multimodal/02-vision-language-models/01-vlm-evolution.md) | 从 CLIP 到 LLaVA：开源多模态对话的成熟之路 |
| | [商业模型对比](./multimodal/02-vision-language-models/02-commercial-vlms.md) | GPT-4o / Gemini / Claude 视觉能力对比 |
| | [视频理解](./multimodal/02-vision-language-models/03-video-understanding.md) | 帧采样、时序推理、长视频处理 |
| | [文档与 UI 理解](./multimodal/02-vision-language-models/04-document-and-ui.md) | PDF 解析、图表解读、截图识别 |
| | [视觉实战与成本](./multimodal/02-vision-language-models/05-vision-practice.md) | API 调用、分辨率策略、成本优化 |
| 03 语音交互 | [语音识别（STT）](./multimodal/03-speech-interaction/01-speech-recognition.md) | Whisper / DeepGram / 本地方案对比 |
| | [语音合成与实时交互](./multimodal/03-speech-interaction/02-speech-synthesis.md) | TTS 模型、Realtime API、打断机制 |
| 04 多模态生成 | [图像生成](./multimodal/04-multimodal-generation/01-image-generation.md) | 扩散模型原理、主流 API 调用 |
| | [视频生成](./multimodal/04-multimodal-generation/02-video-generation.md) | Sora / Runway / 可灵 / Veo |
| | [原生多模态输出](./multimodal/04-multimodal-generation/03-native-multimodal-output.md) | GPT-4o 原生生图、统一输出趋势 |
| | [生成实战](./multimodal/04-multimodal-generation/04-generation-practice.md) | 场景选型、Prompt 策略、成本控制 |
| 05 工程落地 | [评估体系](./multimodal/05-engineering-production/01-evaluation.md) | 各模态指标、Benchmark、端到端评测 |
| | [多模态 RAG](./multimodal/05-engineering-production/02-multimodal-rag.md) | 图片/文档检索、CLIP 索引、ColPali |
| | [成本建模与优化](./multimodal/05-engineering-production/03-cost-optimization.md) | 延迟叠加、模型路由、Token 预算 |
| | [部署与监控](./multimodal/05-engineering-production/04-deployment-monitoring.md) | 灰度上线、可观测性、fallback 策略 |
| | [安全与治理](./multimodal/05-engineering-production/05-safety-governance.md) | 图像注入攻击、合规、隐私保护 |
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
| | [CLI 命令系统](./cc-source-analysis/15-cli-commands/README.md) | 40+ slash 命令、命令注册与分发、命令生命周期 |
| | [终端 UI 框架](./cc-source-analysis/16-terminal-ui/README.md) | 自研 Ink 渲染器、React 组件树、焦点与动画 |
| | [IDE 集成层](./cc-source-analysis/17-ide-integration/README.md) | Bridge 系统、IDE 桥接协议、远程会话管理 |

