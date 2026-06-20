# 多工具编排策略

> 当 Agent 拥有 10 个工具时，真正的挑战不是"有没有"，而是"怎么组合"。并行调用、链式依赖、结果聚合——多工具编排决定了 Agent 能处理的任务复杂度上限。

## 目录

- [从单工具到多工具](#从单工具到多工具)
- [并行调用：一次请求，多个动作](#并行调用一次请求多个动作)
- [链式依赖：工具间的接力](#链式依赖工具间的接力)
- [结果聚合与上下文管理](#结果聚合与上下文管理)
- [工具筛选：Token 效率的艺术](#工具筛选token-效率的艺术)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [工具 Schema 设计](./02-tool-schema-design.md) 中，你了解了如何让单个工具被精准调用。但真实场景很少只用一个工具——"查天气然后推荐穿搭"需要两个工具，"查订单然后发邮件通知"需要三个工具。这篇文章解决核心问题：**Agent 怎么同时管理多个工具，让它们协同完成复杂任务**。

**多工具编排** 是指 Agent 在面对需要多个外部能力的请求时，合理调度工具的执行顺序、处理并行与串行的关系、聚合多个工具的结果，最终生成连贯的回复。这是 Agent 从"简单助手"进化到"复杂代理"的分水岭。

## 从单工具到多工具

单工具场景的决策很简单：用户说"查天气"，模型调用 `get_weather`，结束。多工具场景的复杂度呈指数增长：

| 工具数量 | 可能的组合方式 | 决策复杂度 |
|---------|---------------|-----------|
| 1 | 1 | 低 |
| 2 | 并行 / 串行 2 种 | 中 |
| 3 | 并行 / 串行 / 混合，多种顺序 | 高 |
| 5+ | 排列组合爆炸 | 极高 |

模型本身不"规划"工具调用顺序。它基于参数编码的概率分布，在每一步决定"现在该调用什么"。真正的编排逻辑在你的代码里——你可以控制是否允许并行、是否强制串行、如何处理依赖关系。

## 并行调用：一次请求，多个动作

<img src="../../assets/05-tool-use/multi-tool-orchestration.svg" alt="多工具编排模式：并行调用、链式依赖、动态筛选" width="95%"/>

2024 年后，主流模型（GPT-4o、Claude 3.5+、Gemini 1.5+）都支持**原生并行工具调用**。模型在一次回复中输出多个工具调用请求，你的代码同时执行它们，大幅缩短总耗时。

```python
# 用户说："北京和上海今天天气怎么样？"
# 模型一次输出两个工具调用请求

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[{"role": "user", "content": "北京和上海今天天气怎么样？"}],
    tools=[weather_tool]
)

# response.tool_calls 包含两个独立的调用：
# call_1: get_weather(city="北京")
# call_2: get_weather(city="上海")
```

**并行调用的工程实现**：

```python
import asyncio
import openai

async def execute_tool_calls_parallel(tool_calls):
    """并行执行所有工具调用"""
    tasks = []
    for call in tool_calls:
        task = asyncio.create_task(
            execute_single_tool(call.function.name, 
                              json.loads(call.function.arguments))
        )
        tasks.append((call.id, task))
    
    results = {}
    for call_id, task in tasks:
        results[call_id] = await task
    
    return results

# 将结果按 tool_call_id 回传给模型
for call_id, result in results.items():
    messages.append({
        "role": "tool",
        "tool_call_id": call_id,
        "content": str(result)
    })
```

**并行调用的关键限制**：两个工具之间不能有依赖关系。如果工具 B 需要工具 A 的结果作为参数，就必须串行执行。SFT 训练数据中，参数可独立确定的工具对被标注为并行输出，有语义依赖的被标注为分步输出——参数编码了这种区分模式。

<p align="center">
  <img src="../../assets/05-tool-use/parallel-vs-serial.svg" alt="并行调用vs串行调用：无依赖任务并行执行，依赖任务按序接力" width="95%"/>
</p>

## 链式依赖：工具间的接力

链式调用是 Agent 的核心能力——工具 A 的结果作为工具 B 的输入，形成因果链。

```python
# 用户说："帮我查订单 12345 的物流，然后通知收件人"
# 第一步：查订单信息
# 第二步：用订单中的收件人邮箱发通知

# 第一轮：模型调用 get_order
response1 = client.chat.completions.create(...)
# tool_call: get_order(order_id="12345")
# result: {"recipient": "user@example.com", "status": "shipped", "tracking": "SF123456"}

# 将结果回传，模型看到收件人邮箱后，发起第二轮调用
messages.append({"role": "tool", "tool_call_id": "call_1", 
                "content": "订单 12345 已发货，收件人 user@example.com，物流单号 SF123456"})

# 第二轮：模型调用 send_email
response2 = client.chat.completions.create(...)
# tool_call: send_email(to="user@example.com", subject="订单发货通知", body="...")
```

**链式调用的两种模式**：

| 模式 | 控制方 | 适用场景 | 代码复杂度 |
|------|--------|----------|-----------|
| **模型驱动链** | 模型决定下一步调用什么 | 灵活的开放式任务 | 低 |
| **代码驱动链** | 你硬编码调用顺序 | 固定的业务流程 | 中 |

**模型驱动链**的实现是一个循环：调用模型 → 检查是否返回工具调用 → 执行 → 回传 → 重复。这个循环的完整架构在 [05 — Agent 循环](../06-agent-loop/README.md) 中展开。核心代码骨架如下：

```python
# 模型驱动链的核心循环
while True:
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=available_tools
    )
    
    if not response.tool_calls:
        break  # 模型直接回复，任务完成
    
    # 执行工具调用并回传结果
    for call in response.tool_calls:
        result = execute_tool(call)
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": str(result)
        })
```

## 结果聚合与上下文管理

多工具调用最大的隐形成本是**上下文膨胀**。每轮工具调用的结果都会被注入对话历史，10 轮调用后上下文可能从 1000 tokens 膨胀到 15000+ tokens。

**问题**：OpenAI GPT-4.1 的上下文窗口是 100 万 tokens，但输入 Token 按量计费。一个多工具 Agent 跑 20 轮，成本可能从 $0.01 涨到 $2.00。

**为什么上下文膨胀还影响准确率**：自注意力机制对上下文中的所有 Token 计算关联度。上下文越长，注意力权重越分散——与当前决策相关的关键信号（最新的用户请求和工具结果）被大量历史 Token 稀释。这就是"迷失在中间"现象（[LLM 的局限与工程对策](../02-llm-basics/05-limitations-and-countermeasures.md)中讲过）在多工具场景中的具体表现。

**三种压缩策略**：

1. **摘要回传**：不返回原始 JSON，返回精简摘要

```python
# ❌ 原始 JSON，占用 500+ tokens
{"status": "shipped", "tracking": "SF123456", "items": [{"id": "A1", "name": "手机壳", "price": 29.9}, ...]}

# ✅ 摘要，占用 50 tokens
"订单已发货，物流单号 SF123456，预计 2 天到达。包含 3 件商品，总价 127.5 元。"
```

2. **截断策略**：只保留最近 N 轮的工具结果

```python
# 保留最近 3 轮工具调用，更早的用摘要替代
MAX_TOOL_HISTORY = 3

if len(tool_messages) > MAX_TOOL_HISTORY:
    # 将旧工具结果替换为一句话摘要
    old_messages = tool_messages[:-MAX_TOOL_HISTORY]
    summary = f"[此前完成了 {len(old_messages)} 次工具调用，涉及 {extract_topics(old_messages)}]"
    messages = [msg for msg in messages if msg not in old_messages]
    messages.append({"role": "system", "content": summary})
```

3. **Prompt Caching**：2025-2026 年主流平台（OpenAI、Anthropic、Google）都支持 **Prompt Caching**，复用之前计算的 KV 张量，减少长上下文的开销和延迟。对于多轮工具调用的 Agent，固定部分（系统提示、工具定义）可以缓存，每轮只传输变化的对话内容。

| 平台 | 缓存折扣 | 适用场景 |
|------|---------|---------|
| OpenAI | 输入价格最高 90% 折扣（GPT-5.x），旧模型约 50% | 长系统提示、重复工具定义 |
| Anthropic | 输入价格 90% 折扣 | 多轮对话前缀、知识库文档 |
| Google | 阶梯定价 | 100k+ 上下文的长文档 |

## 工具筛选：Token 效率的艺术

向模型发送 20 个工具定义和发送 5 个工具定义，对成本和准确率都有显著影响。

**实测数据显示**：
- 工具数量从 5 个增加到 20 个，工具选择准确率从约 95% 下降到约 72%（下降约 23 个百分点）。增加到 30 个时进一步降至 53%
- 工具定义总 Token 数增加 3000+，每轮请求成本增加 $0.01-0.03

> 数据来源：[工具数量对 Function Calling 准确率的影响测试](https://blog.csdn.net/cmzznet/article/details/160215228)，覆盖 5-30 个工具场景。

**动态筛选策略**：根据用户输入的意图，只发送相关工具。

```python
def select_tools(user_input: str, all_tools: list) -> list:
    """根据用户输入，从工具库中筛选相关工具"""
    
    # 简单策略：关键词匹配
    keywords = extract_keywords(user_input)
    
    # 工具分类映射
    tool_categories = {
        "weather_tool": ["天气", "温度", "下雨"],
        "order_tool": ["订单", "购买", "快递"],
        "email_tool": ["邮件", "通知", "发送"]
    }
    
    selected = []
    for tool in all_tools:
        categories = tool_categories.get(tool["function"]["name"], [])
        if any(kw in keywords for kw in categories):
            selected.append(tool)
    
    # 保底：至少保留通用工具
    if not selected:
        return [general_tool]
    
    return selected
```

**更高级的策略**：用轻量模型（如 GPT-4.1-mini）做"工具路由"——先让轻量模型判断该用哪些工具，再把筛选后的工具集传给主力模型。路由成本是主力模型的 1/10，但能显著提升主力模型的准确率。

## 总结

- **多工具复杂度指数增长**：2 个工具有并行/串行 2 种模式，5 个工具的组合空间爆炸。编排逻辑在你的代码里，不在模型里。
- **并行调用加速无依赖任务**：模型原生支持一次输出多个工具调用，用 `asyncio` 并行执行，总耗时接近最慢的那个工具。
- **链式依赖必须串行**：模型驱动链用循环实现（调用→执行→回传→重复），适合开放式任务；代码驱动链硬编码顺序，适合固定流程。
- **上下文管理是多工具的隐形杀手**：每轮工具结果都注入历史，用摘要回传、截断策略、Prompt Caching 三种方式控制成本。
- **动态工具筛选提升准确率**：不要向模型发送无关工具。用关键词匹配或轻量模型路由，把工具集控制在 5-8 个以内。

> 掌握了多工具编排，你已经能让 Agent 执行复杂的组合任务。但每个工具都是自己写的，有没有一种方式，让 Agent 直接使用别人已经写好的工具？请继续阅读 [MCP 与工具生态](./04-mcp-and-tool-ecosystem.md)，了解 2026 年工具层的事实标准。

## 参考链接

- [OpenAI Parallel Function Calling](https://platform.openai.com/docs/guides/function-calling/parallel-function-calling)
- [Anthropic Tool Use Chaining](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview)
- [Prompt Caching Guide](https://platform.openai.com/docs/guides/prompt-caching)
- [BFCL Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [工具数量对 Function Calling 准确率的影响测试](https://blog.csdn.net/cmzznet/article/details/160215228)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
