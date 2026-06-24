# 51 万行的真相

> Claude Code 源码泄露事件暴露了 51 万行 TypeScript 代码，其中真正负责 AI 决策的逻辑不到 2%。其余 98% 都是让 Agent 在生产环境里不出事的工程基础设施。

你好，我是江小湖。

2026 年 3 月，Anthropic 发布 Claude Code 时犯下了一个低级错误：npm 包的 source map 没有正确清理，导致整个项目的 TypeScript 源码被公开。1884 个文件，51 万行代码，从入口到工具、从权限到记忆，全部摊开在公众面前。

这不是某个开源 demo，而是一个在商业环境里被成千上万开发者付费使用的 AI 编程助手。拿到这份源码，相当于拿到了一张生产级 Agent 架构的"参考答案"。读完之后，最强烈的感受不是"模型有多强"，而是：**做 Agent，工程化才是主菜。**

## 目录

- [1.6% 的真相](#16-的真相)
- [代码分布](#代码分布)
- [三种运行模式](#三种运行模式)
- [Kernel + Harness 架构](#kernel--harness-架构)
- [总结](#总结)
- [参考链接](#参考链接)

## 1.6% 的真相

先抛出一个数字：**51 万行代码中，真正决定 AI 怎么思考的，只占 1.6%。**

剩下的 98.4% 是什么？启动优化、权限管理、上下文压缩、会话持久化、终端渲染、工具调度、MCP 集成、可观测性——这些不是让模型"更聪明"，而是让模型"不闯祸"。

<p align="center">
  <img src="../../../../assets/cc-source-analysis/01-architecture-overview/code-distribution.svg" alt="Claude Code 代码分布" width="90%"/>
  <br/>
  <em>Claude Code 代码分布：AI 决策逻辑仅占 1.6%</em>
</p>

这个比例本身就在回答一个问题：**生产级 Agent 的复杂度在哪里？** 不在模型调用那几行循环，而在模型调用之外的整个确定性系统。

模型负责"想"，工程负责"做"。想错了可以重想，做坏了文件就真没了。Claude Code 把 98% 的力气花在"怎么做对"上，而不是"怎么想得更炫"。

## 代码分布

把 51 万行代码按模块摊开，会得到下面这张表：

| 模块 | 文件数 | 代码行数 | 占比 | 职责 |
|------|--------|----------|------|------|
| 基础设施 | 564 | ~330,000 | 64% | 工具函数、类型定义、平台适配 |
| 终端 UI | 389 | ~70,000 | 14% | React + Ink 渲染 |
| 权限与安全 | - | ~60,000 | 12% | 多层权限检查、Bash 沙箱 |
| 工具系统 | 184 | ~29,000 | 6% | 42 个工具实现 |
| 命令系统 | 207 | ~15,000 | 3% | 40+ slash 命令 |
| Agent 核心 | - | ~8,000 | **1.6%** | while 循环、工具调度 |

"Agent 核心"不到 8,000 行，其中真正的 while 循环只有 88 行。但这 88 行被 40 多万行工程代码托着。

几个关键文件的规模也值得记住：

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.tsx` | 4683 | 主入口，启动编排 |
| `services/api/claude.ts` | 3212 | LLM 统一调用层 |
| `bootstrap/state.ts` | 1758 | 全局状态（约 150 个字段） |
| `query.ts` | 1612 | Agent 循环核心 |
| `services/compact/compact.ts` | 1581 | 上下文压缩主逻辑 |
| `tools/AgentTool/AgentTool.tsx` | 1320 | 子 Agent 调度 |
| `Tool.ts` | 754 | 工具基类定义 |

注意 `bootstrap/state.ts`，这一个文件就定义了约 150 个全局状态字段。它从侧面说明：要让一个 Agent 在生产环境里稳定运行，需要跟踪的东西远比一个 demo 多得多。

## 三种运行模式

Claude Code 不是一个程序，是三个程序共用一个核心。

| 模式 | 命令 | 使用场景 | 特点 |
|------|------|----------|------|
| REPL 模式 | `claude` | 交互式终端编程 | React/Ink 渲染，支持中断 |
| Print 模式 | `claude -p` | 脚本和 CI/CD 集成 | stdin 进、stdout 出 |
| SDK 模式 | TypeScript / Python SDK | 被其他程序调用 | JSON 通信，可嵌入 IDE |

三种模式共享同一个 Agent 循环、同一套工具系统和同一个权限层。差别只在入口和 UI 层。

REPL 模式是给人用的。你在终端敲下 `claude`，看到一个漂亮的交互界面，可以打字、可以中断、可以看每个工具的执行过程。

Print 模式是给脚本用的。`echo "帮我重构这个函数" | claude -p`，stdin 变成 prompt，stdout 返回结果，可以串在 CI/CD 流水线里。

SDK 模式是给开发者用的。其他程序可以把 Claude Code 当作底层引擎，通过 JSON 协议调用它的能力。

`main.tsx` 有 4683 行，一个重要原因就是它要同时处理这三个入口的所有分支。

## Kernel + Harness 架构

研究者把 Claude Code 的架构概括为 **Kernel + Harness**：一个极薄的 AI 内核，包在一个很厚的确定性外壳里。

<p align="center">
  <img src="../../../assets/advanced/cc-source-analysis/kernel-harness.svg" alt="Kernel + Harness 架构" width="90%"/>
  <br/>
  <em>AI 内核只负责决策，其余由确定性 Harness 兜底</em>
</p>

**Kernel** 就是那 88 行的 while 循环。模型读取上下文，决定下一步调用哪个工具，观察工具返回，然后继续。没有复杂的 planner，没有显式的状态机，没有多步编排图。

**Harness** 是 40 多万行工程基础设施。权限、压缩、存储、调度、渲染、启动优化、可观测性——所有确定性逻辑都在 Kernel 外面。

这个分工带来一个关键优势：**可预测性和可测试性**。AI 行为难以保证，但工程行为可以。把不确定性锁在 Kernel 里，其余部分用传统软件工程方法保障，是 Claude Code 稳定性的来源。

## 总结

- Claude Code 源码泄露事件暴露了 51 万行 TypeScript 代码，其中 **AI 决策逻辑仅占 1.6%**。
- 其余 98.4% 是工程基础设施：权限、压缩、存储、调度、渲染、可观测性等。
- Claude Code 提供 REPL、Print、SDK 三种运行模式，共享同一套核心。
- 整体架构可以用 **Kernel + Harness** 概括：AI 负责决策，工程负责兜底。

这个比例和架构设计本身就在传递一个结论：**Agent 的壁垒不是模型能力，而是工程能力。** 模型决定 Agent 能做什么，工程决定 Agent 能不能用。

> 下一篇：[五层架构](./02-five-layers.md)，拆解 Claude Code 的代码是如何组织的。

## 参考链接

- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Claude Code 源码泄露事件技术分析](https://arstechnica.com/ai/2026/03/claude-code-source-code-leak-technical-analysis/)
- [Dive into Claude Code — MBZUAI/UCL 论文](https://arxiv.org/abs/2604.14228)
- [AgentDevGuide 多模态系列 — 写作风格参考](https://github.com/h2pl/LearnAgent/tree/main/docs/advanced/multimodal)
