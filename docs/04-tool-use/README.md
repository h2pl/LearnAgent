# 04 — 工具调用

本章在整个体系中位于 [Prompt 工程](../03-prompt-engineering/README.md) 之后，解决 Agent 的"行动力"问题：怎么让 LLM 调用外部函数、API 和数据库，执行真实操作。学完本章，你的 Agent 将拥有与外部世界交互的手。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [工具调用机制与原理](./01-tool-calling-mechanism.md) | 从 Function Calling 到 Tool Use，完整四步流程，三大平台差异 |
| 02 | [工具 Schema 设计](./02-tool-schema-design.md) | JSON Schema 设计原则，四条黄金法则，五大反模式 |
| 03 | [多工具编排策略](./03-multi-tool-orchestration.md) | 并行调用、链式依赖、结果聚合、上下文管理、工具筛选 |
| 04 | [MCP 与工具生态](./04-mcp-and-tool-ecosystem.md) | Model Context Protocol，标准化工具层，2026 生态现状 |
| 05 | [MCP 实战全流程](./05-mcp-in-practice.md) | 从零搭建 MCP Server，MCP Inspector 调试，客户端配置，远程部署，认证与错误处理 |

> 学完本章后，请继续阅读 [05 — Agent 循环](../05-agent-loop/README.md)，了解 Agent 如何自主规划多步任务。

## 参考链接

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview)
- [Google Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [MCP Specification](https://modelcontextprotocol.io/)
