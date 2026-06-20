# 01 — AI Agent 生态认知

在动手之前，先搞清楚 AI Agent 到底是什么。本章从定义出发，逐步扩展到市场全貌和代表产品，建立完整的认知框架。

## 学习路径

本文是整本指南的起点。如果你对 Agent 还没有系统认知，建议按顺序阅读；如果已有基础，可以跳过 [什么是 AI Agent](./01-what-is-agent.md)，直接从 [2026 主流 Agent 全景](./02-mainstream-agents.md) 开始。

### 1. 理解 Agent 的本质

[什么是 AI Agent](./01-what-is-agent.md) 回答最根本的问题：Agent 是什么、和 Chatbot 有什么本质区别、什么时候该用 Agent、什么时候不该用。读完你会得到一个清晰的判断框架，而不是一个模糊的概念。

### 2. 看清市场全貌

[2026 主流 Agent 全景](./02-mainstream-agents.md) 用一个双维框架（七大品类 × L1-L5 能力分级）帮你纵览整个 Agent 市场。这一篇是地图——后续所有章节涉及的具体技术概念，都能在这张地图上找到位置。

### 3. 三个典型产品

理论框架需要实例来锚定。三个产品分别代表三个不同的品类方向：

- **[Claude Code](./03-claude-code.md)** —— 编程 Agent 的标杆，展示了 Agent 在垂直领域的深度
- **[OpenClaw](./04-openclaw.md)** —— 本地优先的个人助理，展示了多通道覆盖和持久记忆的实践
- **[Hermes Agent](./05-hermes-agent.md)** —— 开源自动化的代表，展示了 Agent 自我进化的可能性

这三个案例不是为了罗列产品，而是让你看到同一个"Agent"概念在不同品类下的不同实现形态。读完这三篇，你对品类框架的理解会从抽象的表格变成具体的认知。

## 文章总览

| 文章 | 内容 |
|------|------|
| [什么是 AI Agent](./01-what-is-agent.md) | Agent 核心定义、与 Chatbot/Workflow 的区别、适用场景 |
| [2026 主流 Agent 全景](./02-mainstream-agents.md) | 七大品类 × L1-L5 双维框架：编程、研究、个人助理、企业平台等 |
| [Claude Code：编程 Agent 的标杆](./03-claude-code.md) | 终端原生编程 Agent，深度代码理解，SWE-bench ~72% |
| [OpenClaw：本地优先的个人 AI 助理](./04-openclaw.md) | 本地运行，20+ 通道覆盖，持久记忆 |
| [Hermes Agent：自主成长的开源 Agent](./05-hermes-agent.md) | 200+ 模型自由切换，自动技能创建，编码 Agent 编排 |

> 下一章：[02 — LLM 基础](../02-llm-basics/README.md) —— 本章建立了 Agent 的认知框架，下一章进入底层，理解驱动 Agent 的 LLM 是怎么工作的。
