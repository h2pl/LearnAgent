# 角色设计与任务分解

> 架构模式决定了 Agent 之间怎么组织。但一个更棘手的问题是：**Agent 的边界划在哪里**？怎么拆任务才不会让 Agent 互相踩脚、重复劳动或推诿扯皮？

## 目录

- [Agent 边界划分原则](#agent-边界划分原则)
- [任务分解策略](#任务分解策略)
- [意图路由](#意图路由)
- [冲突处理](#冲突处理)
- [一个完整案例：边界设计过程](#一个完整案例边界设计过程)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇文章确定了架构模式，但在写代码之前还有一件更重要的事：**决定每个 Agent 做什么、不做什么**。这个决定做错了，后面所有代码都是错的。

本文从三个角度讲角色设计：边界划分（怎么切）、任务分解（怎么拆）、冲突处理（碰了怎么办）。

## Agent 边界划分原则

### 原则一：按职责拆分，不是按功能拆分

一个常见的错误是按"数据访问"、"计算"、"展示"这种技术功能切 Agent。正确的做法是按**职责和上下文**来切。

| ❌ 按功能切 | ✅ 按职责切 |
|-----------|-----------|
| 数据库 Agent | 用户管理 Agent（它需要查数据库） |
| 计算 Agent | 报表生成 Agent（它需要计算+查数据库） |
| API Agent | 搜索 Agent（它需要调外部 API） |

**按功能切的 Agent 是"工具"，不是"角色"**。工具应该通过 MCP 暴露，不要做成 Agent。Agent 应该有独立的决策能力和完整的任务上下文。

### 原则二：每个 Agent 有独立的知识域

两个 Agent 需要大量共享知识（同一个数据库、同一套业务规则），说明它们应该合并。Agent 之间的知识依赖越少，系统越稳定。

### 原则三：通信成本 < 合并收益

拆 Agent 是有成本的——每次通信都有延迟、序列化开销和可能失败的风险。一个简单的判断标准：**如果两个 Agent 之间有超过 30% 的交互是"把数据从 A 传给 B 做简单转换"，那就应该合并**。

<p align="center">
  <img src="../../assets/12-multi-agent/role-boundary-decision.svg" alt="Agent 边界划分决策：合并 vs 拆分" width="90%"/>
</p>

## 任务分解策略

确定了 Agent 的边界，下一步是把用户请求分解为可执行的任务序列。

### 策略一：静态分解（规则驱动）

适用于流程固定的任务。用 if-else 或决策表把任务类型映射到处理 Agent。

```python
TASK_ROUTING = {
    "bug_report": ["意图分类 Agent", "Bug 分析 Agent", "修复方案 Agent"],
    "feature_request": ["意图分类 Agent", "产品分析 Agent", "技术评估 Agent"],
    "data_query": ["意图分类 Agent", "数据查询 Agent"],
}
```

### 策略二：动态分解（LLM 驱动）

适用于开放式的复杂任务。让 LLM（通常是 Orchestrator）自主决定怎么拆。

```python
async def dynamic_decompose(user_request: str):
    # Orchestrator 用 LLM 拆分任务
    plan = await orchestrator_llm.invoke(
        f"将以下请求拆解为可执行的子任务列表，每个子任务标注负责的 Agent：\n{user_request}"
    )
    for task in plan["tasks"]:
        result = await agents[task["agent"]].execute(task)
        task["result"] = result
    return await orchestrator_llm.synthesize(plan)
```

动态分解灵活但不可控。推荐的做法是**混合模式**：先走静态路由匹配，匹配不到再走动态分解。

### 策略三：分层分解

用户请求 → 一级 Agent（Orchestrator）→ 二级 Agent（专业领域）→ 三级 Agent（具体执行）。层次越深，职责越细。

```python
# 第一层：Orchestrator 理解意图
# 第二层：领域 Agent 制定方案
# 第三层：执行 Agent 调用工具
```

适合大型系统。每个层级的 Agent 数量控制在 5 个以内，超过就该考虑加层。

## 意图路由

任务分解的前提是**正确理解用户想要什么**。意图路由就是"把用户请求分给对的 Agent"。

### 方法一：关键词+规则

```python
def route_intent(query: str) -> str:
    if any(kw in query for kw in ["bug", "错误", "异常", "修复"]):
        return "tech_support"
    if any(kw in query for kw in ["价格", "购买", "订阅"]):
        return "sales"
    return "general"
```

简单、可解释、零成本。但覆盖不全，组合关键词场景容易漏。

### 方法二：Embedding 相似度

把 Agent 的能力描述和用户请求都转为向量，算相似度：

```python
from openai import embeddings

query_vec = embeddings.embed(user_request)
agent_scores = {
    name: cosine_similarity(query_vec, agent_embedding)
    for name, agent_embedding in agents.items()
}
best_agent = max(agent_scores, key=agent_scores.get)
```

比规则灵活，但需要 Embedding 模型和预计算 Agent 向量。

### 方法三：LLM 分类（推荐）

```python
async def route_intent_llm(query: str) -> str:
    agents_desc = [
        {"name": "tech_support", "description": "处理技术问题、Bug 报告"},
        {"name": "sales", "description": "处理价格、购买、订阅相关"},
        {"name": "general", "description": "其他通用咨询"},
    ]
    response = await llm.invoke(
        f"根据用户请求，选择最合适的处理 Agent：{json.dumps(agents_desc)}\n用户：{query}"
    )
    return response.content.strip()
```

**推荐理由**：准确率最高、易于维护（改描述文本就行）、能处理边界情况（"这个既像 Bug 又像咨询"）。缺点是每次路由都调用一次 LLM，带来一定的延迟和成本。

<p align="center">
  <img src="../../assets/12-multi-agent/intent-routing-comparison.svg" alt="意图路由三种方法对比：关键词+规则、Embedding相似度、LLM分类" width="90%"/>
  <br/><em>图：三种意图路由方法的适用场景与混合策略</em>
</p>

## 冲突处理

多 Agent 系统最常见的三类冲突：

### 1. 资源竞争

两个 Agent 同时调用同一个 MCP Server。解决方案：**MCP Gateway 限流 + 公平队列调度**。Gateway 层面做并发控制和优先级排序。

### 2. 知识不一致

Agent A 认为数据是 X，Agent B 认为数据是 Y。解决方案：**单写多读 + 事实层**。所有 Agent 从一个共享事实层读数据，只有被授权的 Agent 能写。事实层可以是数据库、共享内存或 MCP Resource。

### 3. 决策冲突

Agent A 说"应该用方案一"，Agent B 说"方案二更好"。解决方案：**仲裁 Agent**。让另一个中立的 Agent（Supervisor）做最终裁定。或者使用"提交时协商"模式——Agent 先各自行动，在最终输出合并时由 Supervisor 裁决。

## 一个完整案例：边界设计过程

假设你要为技术咨询公司设计一套多 Agent 系统：

### 第一步：识别职责域

- 技术问题解答
- 代码审查
- 架构方案设计
- 文档编写
- 客户沟通

### 第二步：做边界决策

按**原则一**：职责拆分，不是功能拆分。

```
❌ 错的：代码 Agent（负责所有代码相关）
✅ 对的：代码审查 Agent（职责：审查代码质量）、故障分析 Agent（职责：排查线上问题）

虽然都涉及代码，但它们的上下文、知识域、决策逻辑完全不同。
```

按**原则三**：通信成本评估。

代码审查 Agent 审查完后需要把结果发给文档 Agent 写报告。两者之间传递的是结构化审查意见（几百字节），不是大块数据——通信成本低，适合保持独立。

### 第三步：任务分解 + 路由

```
用户请求 → 意图路由（LLM 分类）
  ├── 技术咨询 → 故障分析 Agent → 代码审查 Agent（如果需要）→ 文档 Agent
  ├── 架构咨询 → 架构 Agent → 文档 Agent
  └── 常规咨询 → 通用 Agent
```

### 第四步：定义冲突策略

故障分析 Agent 和架构 Agent 可能都对同一个系统有不同看法——一个关注稳定性，一个关注可扩展性。仲裁策略：交给 Supervisor Agent 做综合判断，输出兼顾两方面的方案。

## 总结

- **边界划分三原则**：按职责（不是功能）拆分、独立知识域、通信成本 < 合并收益
- **任务分解三策略**：静态规则（固定流程）、LLM 动态（开放任务）、分层（大型系统）
- **意图路由三种方法**：关键词规则（最简单）、Embedding 相似度（灵活）、LLM 分类（最推荐）
- **三类冲突**：资源竞争（Gateway 限流）、知识不一致（共享事实层）、决策冲突（仲裁 Agent）

> 下一篇 [CrewAI 实战：研究团队](./03-crewai-research-team.md)——用 CrewAI 框架搭建一个多角色协作的研究团队，看角色设计和任务分解在实际代码中怎么落地。

## 参考链接

- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [LangGraph — Agent Architectures](https://langchain-ai.github.io/langgraph/concepts/agent_architectures/)
