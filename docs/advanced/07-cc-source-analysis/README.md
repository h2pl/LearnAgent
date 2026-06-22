# Claude Code 源码解析 — 从理论到生产级 Agent

Claude Code 是 Anthropic 官方的终端 AI 编码助手，也是目前最成熟的零框架 Agent 实现之一。它不依赖 LangChain、LangGraph 等任何 Agent 框架，用纯 TypeScript 手写全部核心链路，代码量超过 51 万行。研究发现，其中仅 1.6% 是 AI 决策逻辑，其余都是围绕这个核心循环的确定性基础设施。

本栏目逐模块拆解 Claude Code 的核心源码，每个模块对应核心 16 章的一个理论概念——不是"它做了什么"，而是"它为什么这样做"以及"这个设计决策对应哪条架构原理"。

> 前置知识：本栏目假设你已完成核心 16 章的学习。每篇文章会回溯到对应章节的理论基础。
>
> 源码版本：基于 `E:/Projects/claude-code/` 本地源码，版本随更新同步。

## 章节导航

| 章节 | 主题 | 对应理论章节 | 核心源码 |
|------|------|-------------|----------|
| [01 整体架构](./01-architecture-overview/README.md) | 全局结构与模块划分 | 全局 | 51 万行代码全景 |
| [02 启动流程](./02-bootstrap/README.md) | 启动的三秒钟发生了什么 | Ch02 | entrypoints/ + bootstrap/ |
| [03 Agent 循环](./03-agent-loop/README.md) | while True 循环的核心机制 | Ch06 | query.ts (1729行) + QueryEngine.ts (1295行) |
| [04 工具系统](./04-tool-system/README.md) | buildTool 工厂与工具注册 | Ch05 | Tool.ts (792行) |
| [05 LLM 调用层](./05-llm-calling/README.md) | 统一调用、重试、多模型路由 | Ch02+03 | services/api/claude.ts (3419行) |
| [06 系统提示](./06-system-prompt/README.md) | 提示组装与缓存冻结 | Ch04 | systemPrompt.ts + prompts |
| [07 上下文压缩](./07-context-compaction/README.md) | 五层压缩管线 | Ch07 | services/compact/ (2960行) |
| [08 记忆系统](./08-memory/README.md) | 文件级持久记忆与反思 | Ch08+09 | memdir/ + autoDream/ |
| [09 子 Agent](./09-subagent/README.md) | 上下文隔离与消息路由 | Ch11+12 | tools/AgentTool/ (2657行) |
| [10 权限系统](./10-permissions/README.md) | 七种权限模式与 ML 分类器 | Ch13 | utils/permissions/ (1486行+20文件) |
| [11 扩展机制](./11-extensibility/README.md) | MCP/Skills/Hooks/Plugins | Ch10+11 | plugins/ + skills/ + hooks/ |
| [12 会话持久化](./12-session-persistence/README.md) | 断点续传与状态恢复 | Ch08 | sessionStorage + transcript |
| [13 可观测性](./13-telemetry/README.md) | Span 树与成本追踪 | Ch14 | utils/telemetry/ (1752行) |
| [14 设计哲学](./14-design-philosophy/README.md) | 五个核心价值观 | 全局 | 架构决策回溯 |

## 阅读建议

1. **先看全局**：从 01 整体架构开始，建立全局地图
2. **跟着数据流走**：02 启动 → 03 Agent 循环 → 04 工具 → 05 LLM 调用，这是请求处理的完整链路
3. **按需深入**：06-14 可以根据兴趣跳读，每章独立成篇
