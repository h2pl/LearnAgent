# 11 — 扩展协议

真实的 Agent 系统不是孤岛——它们需要互相通信、共享工具、跨平台协作。**协议就是让这一切成为可能的基础设施。** 六篇文章从 [协议全景](./01-protocol-landscape.md) 出发，深入 [MCP](./02-mcp-in-depth.md)、[A2A](./03-a2a-and-beyond.md) 及其实战，再到 [轻量级约定](./05-lightweight-conventions.md) 和 [协议组合选型](./06-protocol-composition.md)，覆盖整个 Agent 开放生态的拼图。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [扩展协议全景](./01-protocol-landscape.md) | 协议分层模型、MCP / A2A / ACP / ANP / AG-UI / OAP 全局格局、2026 行业共识 |
| 02 | [MCP 深入](./02-mcp-in-depth.md) | 协议治理与版本化、Gateway 企业部署、MCP vs Function Calling 的关系、回链 [MCP 与工具生态](../05-tool-use/04-mcp-and-tool-ecosystem.md) 实现细节 |
| 03 | [A2A 与 Agent 通信协议](./03-a2a-and-beyond.md) | A2A 企业协作（Agent Card / 任务生命周期 / 三种交互模式）、ACP 并入后的统一 A2A、ANP 去中心化身份与发现 |
| 04 | [A2A 实战：多 Agent 协作实现](./04-a2a-in-practice.md) | A2A SDK 环境搭建、Agent Card 声明、Server 实现、三种交互模式编码、完整的多 Agent 协作案例 |
| 05 | [轻量级约定：Skills 与 AGENTS.md](./05-lightweight-conventions.md) | Skills 结构化知识包格式、AGENTS.md 能力声明、本项目 skills/ 实践、厂商 Skills 实现对比（Claude Code / Copilot / Cursor） |
| 06 | [协议组合与选型](./06-protocol-composition.md) | 分层采纳路线图、选型决策树、多协议组合模式（MCP+A2A、MCP+ANP 等）、OAP 全栈方案、MVP→生产演进路径 |

> 学完本章后，请继续阅读 [12 — 多 Agent](../12-multi-agent/README.md)，进入多 Agent 协作的世界。
