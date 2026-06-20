# 多 Agent 系统设计权衡

> 前面四篇教你怎么拆、怎么分、怎么编。但更重要的一个问题：**什么时候不应该拆？** 多 Agent 不是免费的——通信有成本、调试有难度、错误会传播。本文讲清这些权衡，让你知道什么时候值得拆，什么时候一个 Agent 就够了。

## 目录

- [多 Agent 的真实成本](#多-agent-的真实成本)
- [什么时候不该拆](#什么时候不该拆)
- [错误传播与隔离](#错误传播与隔离)
- [可观测性设计](#可观测性设计)
- [演进路线：从单体到多 Agent](#演进路线从单体到多-agent)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面四篇文章一直在讲怎么拆、怎么设计、怎么编排。但如果你觉得"多 Agent 就是比单 Agent 好"，那就掉进坑了。

**多 Agent 系统的第一大敌是复杂度**。每拆出一个 Agent，就多了一个通信链路、一个故障点、一层调试难度。本文是你搭建多 Agent 系统前必须读的"劝退指南"——让你知道什么时候该拆，什么时候不该。

## 多 Agent 的真实成本

### 延迟成本

两个 Agent 之间通信一次，至少增加一轮 LLM 调用 + 消息序列化/反序列化。一个经过 3 个 Agent 的链式调用，总延迟是 3 倍单体 Agent + 2 次网络通信。

| 组件 | 单体 Agent | 3 Agent 流水线 |
|------|-----------|---------------|
| LLM 推理 | 1 次 | 3 次 |
| 上下文管理 | 一次加载 | 3 次拼接 |
| 网络通信 | 0 | 2 次 A2A 调用 |
| 总延迟 | ~3s | ~10s |

### 上下文碎片化

每个 Agent 只看到任务的一部分。Agent A 产生了重要的中间推理结果，Agent B 不知道——因为上下文没有传递。解决这个问题需要**跨 Agent 的上下文传递机制**（共享记忆层、MCP Resource），这本身又是复杂度。

### 调试复杂度

单体 Agent 的调试是线性的——查一次对话日志就行。多 Agent 调试是图遍历——你需要串起跨多个 Agent 的请求链、定位哪个 Agent 传错了参数、哪个 Agent 误解了指令。

```python
# 单体 Agent 调试
[用户消息] → [推理] → [工具调用] → [回应]
# 一条线，清晰

# 多 Agent 调试
[用户] → [Orchestrator] → [搜索 Agent] → [Orchestrator]
                            ↓
                    [报表 Agent] → [Orchestrator] → [用户]
# 网状，需要追踪调用链
```

## 什么时候不该拆

以下是几个"不要拆"的场景：

### 场景一：任务简单直接

用户问"明天天气怎么样"，一个 Agent + 一个天气 MCP Server 就够了。拆出"意图识别 Agent" + "天气查询 Agent" + "回答格式化 Agent"是过度设计。

**判断标准**：如果你能用一个 Python 函数 + 一个 MCP Server 解决问题，就不要拆。

### 场景二：Agent 高度依赖共享上下文

两个 Agent 需要频繁交换大量上下文。比如一个 Agent 需要知道另一个 Agent 的全部推理过程才能做判断。这种情况应该合并。

**判断标准**：超过 30% 的交互是"把 A 的结果原样传给 B"。

### 场景三：延迟敏感

用户期望秒级响应。多 Agent 的链式调用至少增加 2-3 倍延迟。如果延迟是硬约束，优先考虑单体 Agent。

**判断标准**：目标响应时间 < 5 秒 → 优先单体。

### 场景四：团队规模小

1-2 人团队维护一个多 Agent 系统，调试和运维成本可能超过单体 Agent。每个 Agent 需要独立的配置、监控、日志分析——这些对单人团队是不小的负担。

## 错误传播与隔离

多 Agent 系统最隐蔽的问题是错误传播：

```
Agent A 返回错误数据
  → Agent B 基于错误数据做出错误决策
    → Agent C 进一步放大错误
      → 最终输出完全不可用（且难以追踪根源）
```

### 防御策略

**策略一：每个 Agent 做输入校验**

```python
async def search_agent(task: Task) -> Task:
    query = task.message.parts[0].text
    if len(query) > 500:
        return Task(status="failed", error="查询过长")
    # 正常处理...
```

**策略二：超时熔断**

单个 Agent 超过设定时间未响应，Orchestrator 直接标记失败并走降级路径。

```python
try:
    result = await asyncio.wait_for(
        agent.process(task), timeout=30.0
    )
except asyncio.TimeoutError:
    result = fallback_response("搜索服务超时，返回缓存数据")
```

**策略三：降级方案**

关键 Agent 不可用时，Orchestrator 应该有备选方案：

```python
async def safe_search(agent, query):
    if not await agent.health_check():
        return await backup_search(query)  # 备用搜索引擎
    return await agent.search(query)
```

**策略四：输出验证**

每个 Agent 的输出都应该经过一个验证步骤——格式检查、范围检查、一致性检查。不符合预期的输出直接标记异常，不进入下一个 Agent。

<p align="center">
  <img src="../../assets/12-multi-agent/error-propagation-defense.svg" alt="多 Agent 错误传播链与四道防线" width="90%"/>
  <br/><em>图：错误传播链与输入校验、超时熔断、降级、输出验证</em>
</p>

## 可观测性设计

单体 Agent 的日志很简单：请求进来，响应出去。多 Agent 需要**分布式追踪**。

### 追踪 ID

```python
import uuid
from contextvars import ContextVar

trace_id_var = ContextVar("trace_id")

async def orchestrator(request):
    trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    log(f"[{trace_id}] 开始处理")

    result_a = await agent_a.process(request)
    log(f"[{trace_id}] Agent A 完成")
    result_b = await agent_b.process(result_a)
    log(f"[{trace_id}] Agent B 完成")

    return result_b
```

每个请求分配一个 trace_id，贯穿所有 Agent 的日志。如果 Agent 之间有 A2A 调用，trace_id 通过请求头传递。

### 关键指标

每个 Agent 至少要暴露以下指标：

| 指标 | 说明 | 意义 |
|------|------|------|
| 调用次数 | 一段时间内被调用次数 | 负载评估 |
| 成功率 | 成功/总调用 | 健康状态 |
| 平均延迟 | 从接受到返回的时间 | 性能监控 |
| Token 消耗 | 输入+输出 Token | 成本控制 |
| 错误分布 | 各类错误的频率 | 问题定位 |

### 日志结构化

不要只打文字日志。每个 Agent 的输出应该是结构化的 JSON，包含：agent_name、trace_id、input_summary、output_summary、latency_ms、token_count。

## 演进路线：从单体到多 Agent

正确的做法不是一开始就设计完美的多 Agent 系统，而是**从单体一步步演进**。

<p align="center">
  <img src="../../assets/12-multi-agent/multi-agent-evolution.svg" alt="从单体 Agent 到多 Agent 的演进路径" width="95%"/>
</p>

### 阶段 0：单体 Agent + MCP

```
Agent ←MCP→ 数据库 / API / 文件
```

一个 Agent 做所有事。通过 MCP 连接工具。这是起点。

### 阶段 1：Orchestrator + Worker（功能拆出）

```
Orchestrator → Worker Agent（专业功能）
    ↓ MCP
  工具
```

当单体 Agent 的 System Prompt 超过 2000 字，或工具列表超过 20 个时，考虑把专业功能拆成 Worker Agent。

### 阶段 2：Supervisor 加入（质量管控）

```
Supervisor → Worker Agent
    ↓          ↓
Orchestrator  tools
```

当输出质量不一致时，加入 Supervisor 做审核。

### 阶段 3：Pipeline 并行化（性能优化）

当某个 Worker 成为瓶颈时，拆成 Pipeline 多级并行处理。

### 阶段 4：Peer-to-Peer 去中心化（开放协作）

当系统需要与外部系统协作时，开放 A2A 接口。

### 不要跳阶段

**最常见的错误是直接从阶段 0 跳到阶段 4**。结果：Agent 之间通信混乱、边界模糊、调试噩梦。

每个阶段都有明确的触发条件——不满足条件就安心待在当前阶段。多 Agent 是解决复杂度的工程手段，不是最终目的。

## 总结

- **多 Agent 不是免费的**：延迟增加 2-3 倍、上下文碎片化、调试复杂度指数级上升
- **四种不该拆的场景**：任务简单、上下文高度共享、延迟敏感、团队规模小
- **错误传播四道防线**：输入校验、超时熔断、降级方案、输出验证
- **可观测性是刚需**：trace_id 贯穿全链路、结构化日志、关键指标监控
- **从单体开始逐步演进**：每个阶段有明确触发条件，不要跳跃。多 Agent 是手段，不是目的

> 学完 12 章，你已经掌握了多 Agent 系统的设计、开发和运维。下一章 [13 — 评测](../13-evaluation/README.md)——你的系统做出来了，但怎么知道它好不好？

## 参考链接

- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [LangGraph — Multi-Agent Systems](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [Martin Fowler — Microservices Trade-offs](https://martinfowler.com/articles/microservice-trade-offs.html)（多 Agent 的复杂度与微服务类似，设计原则可借鉴）
