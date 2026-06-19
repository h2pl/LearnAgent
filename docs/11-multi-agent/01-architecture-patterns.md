# 多 Agent 架构模式

> [扩展协议](../10-protocols/01-protocol-landscape.md) 一章解决了 Agent 之间"怎么通信"，本章解决"通信之后怎么设计"。四个核心架构模式——Orchestrator/Worker、Supervisor、Peer-to-Peer、Pipeline——各有适用场景。

## 目录

- [为什么需要架构模式](#为什么需要架构模式)
- [模式一：Orchestrator/Worker（主从）](#模式一orchestratorworker主从)
- [模式二：Supervisor（监督）](#模式二supervisor监督)
- [模式三：Peer-to-Peer（对等）](#模式三peer-to-peer对等)
- [模式四：Pipeline（流水线）](#模式四pipeline流水线)
- [四种模式对比](#四种模式对比)
- [选型决策](#选型决策)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。[A2A 实战：多 Agent 协作实现](../10-protocols/04-a2a-in-practice.md) 中，你写了一个主 Agent 调用两个子 Agent 的案例。那是最简单的**主从模式**。但真实世界的多 Agent 系统远不止这一种模式——有的需要监督者控制质量、有的需要对等协作、有的适合流水线处理。

本文介绍四种核心架构模式，每种模式的适用场景、优缺点、和实际案例。

## 为什么需要架构模式

多 Agent 不是"把 Agent 拆小再连起来"这么简单。拆的方式决定了系统的复杂度天花板。

<p align="center">
  <img src="../../assets/11-multi-agent/architecture-patterns-overview.svg" alt="四种多 Agent 架构模式概览" width="95%"/>
</p>

**四种模式解决四类问题**：

| 模式 | 核心问题 | 类比 |
|------|---------|------|
| Orchestrator/Worker | 谁做决策？ | CEO + 部门 |
| Supervisor | 谁把控质量？ | 主编 + 记者 |
| Peer-to-Peer | 怎么横向协调？ | 同事合作 |
| Pipeline | 怎么分阶段？ | 工厂流水线 |

**没有银弹**。一个大系统里可能同时使用多种模式——Orchestrator 调度 Worker，Worker 内部可能用 Pipeline，而 Worker 之间在某些环节用 Peer-to-Peer。

## 模式一：Orchestrator/Worker（主从）

### 架构

一个主 Agent 负责接收任务、拆解为子任务、分派给 Worker Agent，然后汇总结果。

### 适用场景

- 任务可以自然拆分为独立子任务
- Worker 之间不需要互相通信
- 需要一个统一入口做上下文管理和结果聚合

### 优点

| 优点 | 说明 |
|------|------|
| 简单 | 逻辑清晰，一个入口一个出口 |
| 可调试 | 所有决策路径经过 Orchestrator，日志完整 |
| 容错 | Orchestrator 可以重试失败 Worker |

### 缺点

| 缺点 | 说明 |
|------|------|
| 单点瓶颈 | Orchestrator 可能成为性能和决策瓶颈 |
| 灵活性低 | Worker 的协作必须经过 Orchestrator |

### 实际案例

[A2A 实战：多 Agent 协作实现](../10-protocols/04-a2a-in-practice.md) 的案例就是典型的 Orchestrator/Worker——主 Agent 拆解"分析 MCP 进展"任务，搜索 Agent 查资料，报表 Agent 写报告，主 Agent 汇总。

```python
# Orchestrator 核心逻辑
async def orchestrate(user_request: str):
    search_result = await search_agent.search(user_request)
    report_result = await report_agent.generate(search_result)
    return assemble(user_request, search_result, report_result)
```

## 模式二：Supervisor（监督）

### 架构

Worker Agent 先产出结果，Supervisor Agent 审核质量，不合格的退回重做。有时 Supervisor 也做方向引导——告诉 Worker "这个方向不对，换一个思路"。

### 适用场景

- 结果质量要求高（代码审查、内容审核、安全检测）
- 需要多轮迭代才能达到标准
- Worker 可能产生低质量输出，需要质量控制

### 实际应用

Anthropic 在实践中大量使用 Supervisor 模式。例如写代码场景：一个 Worker Agent 写代码，一个 Supervisor Agent 审查代码质量、检查单元测试覆盖、验证是否符合项目规范。

```python
async def supervised_generate(topic: str):
    max_iterations = 3
    for i in range(max_iterations):
        content = await writer_agent.write(topic)
        feedback = await supervisor_agent.review(content)
        if feedback["passed"]:
            return content
        topic = f"{topic}，改进：{feedback['suggestions']}"
    raise MaxRetriesExceeded()
```

**关键设计**：限定迭代次数。不加限制的 Supervisor 循环可能陷入无限争吵。3 次是一个合理的上限——超过说明 Worker 或 Supervisor 的设计有问题。

## 模式三：Peer-to-Peer（对等）

### 架构

Agent 之间直接通信，没有中心节点。每个 Agent 知道自己能做什么、需要找谁。

### 适用场景

- Agent 功能对等、互相协作
- 没有天然的"主控者"
- 需要动态发现和协商

### 实际应用

A2A 协议天然支持 Peer-to-Peer——每个 Agent 发布自己的 Agent Card，其他 Agent 直接通过 Agent Card 发现和调用。

```python
# Agent A 发现 Agent B 的能力后直接委托
card = await discover_agent("capability:data_analysis")
result = await a2a_client.send_task(
    target=card.endpoints[0],
    task=Task(message=Message(parts=[TextPart(text="分析上季度数据")]))
)
```

### 挑战

Peer-to-Peer 模式去中心化程度最高，但也最难管控：

- **调试困难**：没有中心节点，追踪一次完整请求路径需要跨多个 Agent 串联日志
- **协调复杂**：两个 Agent 同时调用同一个资源可能产生冲突
- **一致性难保证**：没有 Orchestrator 管理上下文，每个 Agent 看到的信息可能不一致

适合对等协作场景（多个专家 Agent 讨论问题），不适合需要强一致性的流水线任务。

## 模式四：Pipeline（流水线）

### 架构

任务按阶段顺序传递，前一个阶段的输出是后一个阶段的输入。每个 Agent 只处理一个阶段。

### 适用场景

- 任务有明确的阶段划分
- 每个阶段有独立的数据处理逻辑
- 阶段间可以并行（通过缓冲队列）

### 实际应用

内容生产流水线：选题 Agent → 大纲 Agent → 写作 Agent → 配图 Agent → 审核 Agent → 发布 Agent。

```python
# Pipeline 链式调用
pipeline = [
    topic_agent,
    outline_agent,
    writing_agent,
    illustration_agent,
    review_agent,
    publish_agent
]

async def run_pipeline(input_data):
    data = input_data
    for agent in pipeline:
        data = await agent.process(data)
    return data
```

### 并行优化

Pipeline 模式天然支持并行。如果阶段之间有缓冲区，多个 Agent 可以同时工作在不同任务上——写作 Agent 在处理文章 A 的同时，审核 Agent 审核文章 B，互不干扰。

## 四种模式对比

<p align="center">
  <img src="../../assets/11-multi-agent/pattern-comparison.svg" alt="四种架构模式对比维度表" width="95%"/>
</p>

| 维度 | Orchestrator/Worker | Supervisor | Peer-to-Peer | Pipeline |
|------|-------------------|-----------|-------------|----------|
| **控制方式** | 中心化 | 中心化审查 | 去中心化 | 顺序传递 |
| **复杂度** | 低 | 中 | 高 | 中 |
| **灵活性** | 中 | 中 | 高 | 低 |
| **可调试性** | 高 | 高 | 低 | 中 |
| **容错性** | 中（Orchestrator 单点） | 中（Supervisor 单点） | 高 | 低（上游失败全链中断） |
| **并行度** | Worker 可并行 | 串行（审核等待） | 天然并行 | 阶段间可并行 |
| **典型场景** | 研究团队、任务分发 | 代码审查、内容审核 | 开放 Agent 网络 | 数据处理、内容生产 |

## 选型决策

没有绝对的"最好模式"，只有"最适合当前阶段"的模式。

- **刚起步**：从 Orchestrator/Worker 开始。最简单，最可控。大部分多 Agent 系统从这个模式起步，足够覆盖 80% 场景
- **需要质量控制**：加一层 Supervisor。在 Orchestrator/Worker 基础上，让 Supervisor 审核关键节点的输出
- **Agent 数量 > 10 个**：考虑 Pipeline 或 Peer-to-Peer。Orchestrator 在管理十几个 Worker 时开始吃力
- **去中心化协作**：Peer-to-Peer。使用 A2A 协议的动态发现，适合开放系统

**建议**：大多数团队从 Orchestrator/Worker 起步，再按需演进到混合模式。

## 总结

- **四种核心架构模式**：Orchestrator/Worker（主从）、Supervisor（监督）、Peer-to-Peer（对等）、Pipeline（流水线）
- **没有银弹**：大系统通常混合使用多种模式，不同环节用不同的模式
- **从 Orchestrator/Worker 起步**：最简单，覆盖 80% 场景
- **Supervisor 解决质量问题**：限定迭代次数（3 次为宜），避免无限循环
- **Peer-to-Peer 灵活性最高**：但也最难调试和管控

> 下一篇 [角色设计与任务分解](./02-role-design.md)——选定了架构模式之后，怎么给每个 Agent 划边界、拆任务、分职责？

## 参考链接

- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [LangGraph — Multi-Agent Patterns](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [Google A2A — Patterns](https://github.com/google/A2A)
- [OpenAI — Agents Patterns](https://platform.openai.com/docs/guides/agents)
