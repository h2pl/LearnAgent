# 12 — 多 Agent

多 Agent 解决的核心问题不是"怎么通信"，而是**系统该怎么拆、角色该怎么分、拆了之后怎么管**。五篇文章从 [架构模式](./01-architecture-patterns.md) 和 [角色设计](./02-role-design.md) 入手，通过 [CrewAI](./03-crewai-research-team.md) 和 [LangGraph](./04-langgraph-workflow.md) 两个实战案例落地，最后以 [设计权衡](./05-design-tradeoffs.md) 收尾。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [多 Agent 架构模式](./01-architecture-patterns.md) | 四种核心模式（Orchestrator/Worker、Supervisor、Peer-to-Peer、Pipeline）对比与选型 |
| 02 | [角色设计与任务分解](./02-role-design.md) | Agent 边界划分、任务拆分策略、意图路由、冲突处理 |
| 03 | [CrewAI 实战：研究团队](./03-crewai-research-team.md) | 多角色协作的完整案例，从角色定义到任务编排到结果聚合 |
| 04 | [LangGraph 实战：工作流编排](./04-langgraph-workflow.md) | 状态图驱动的多 Agent 协作，断点恢复与人机协作 |
| 05 | [多 Agent 系统设计权衡](./05-design-tradeoffs.md) | 什么时候该拆、通信成本、错误传播、可观测性、演进路线 |

> 学完本章后，请继续阅读 [13 — 评测](../13-evaluation/README.md)，学习如何评估你的 Agent 系统质量。
