# 全链路追踪实现

> 设计原则定好了，选好了工具，下一步是落地——怎么在 Agent 代码中埋点、Span 怎么设计、Trace ID 怎么穿透每一层、采样和存储怎么配置。

## 目录

- [埋点模式](#埋点模式)
- [Span 设计](#span-设计)
- [Trace ID 传播](#trace-id-传播)
- [流式响应下的追踪](#流式响应下的追踪)
- [采样策略配置](#采样策略配置)
- [存储与保留](#存储与保留)
- [数据集市：把 Trace 当成数据仓库](#数据集市把-trace-当成数据仓库)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇文章规划了 Agent 可观测性的设计原则和工具选型。本文把这些原则翻译成代码——从装饰器插桩到 Span 设计到采样配置，覆盖一个生产级追踪系统的全部实现细节。

## 埋点模式

有三种埋点方式，从易到难。

### 模式一：装饰器插桩（推荐起点）

最简洁的方式，适合大多数团队。框架不强制，用一个自定义装饰器完成所有追踪：

```python
from functools import wraps
from my_tracer import Tracer

tracer = Tracer(service="agent-engine")

def trace_agent(agent_func):
    @wraps(agent_func)
    def wrapper(user_input: str, **kwargs):
        with tracer.trace("agent_episode") as span:
            span.set_attribute("user_input", user_input)
            try:
                result = agent_func(user_input, **kwargs)
                span.set_attribute("status", "success")
                return result
            except Exception as e:
                span.set_attribute("status", "error")
                span.set_attribute("error", str(e))
                raise
    return wrapper

@trace_agent
def my_agent(user_input: str):
    # Agent 业务逻辑
    pass
```

对于每个子调用，再封装一个追踪函数：

```python
def traced_llm_call(prompt: str, model: str) -> str:
    with tracer.trace("llm_call") as span:
        span.set_attribute("model", model)
        span.set_attribute("input_tokens", len(prompt))
        response = actual_llm_call(prompt, model)
        span.set_attribute("output_tokens", len(response))
        span.set_attribute("status", "success")
        return response

def traced_tool_call(tool_name: str, params: dict) -> Any:
    with tracer.trace("tool_call") as span:
        span.set_attribute("tool", tool_name)
        span.set_attribute("params", json.dumps(params))
        result = actual_tool_call(tool_name, params)
        span.set_attribute("result", json.dumps(result))
        return result
```

### 模式二：中间件插桩（适合框架）

如果 Agent 基于某个框架（LangGraph、CrewAI 等），用中间件自动拦截请求。以 FastAPI 为例，加上 Stripe 风格的请求 ID 中间件：

```python
from fastapi import Request
import uuid

@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    with tracer.trace("http_request", trace_id=trace_id) as span:
        span.set_attribute("method", request.method)
        span.set_attribute("path", request.url.path)
        response = await call_next(request)
        span.set_attribute("status_code", response.status_code)
        response.headers["X-Trace-Id"] = trace_id
        return response
```

### 模式三：手动插桩（适合定制需求）

最灵活也最重的方式。只有在对追踪粒度有特殊要求时才需要——比如需要追踪 Agent 内部一个循环中的每一次迭代：

```python
with tracer.trace("agent_loop") as loop_span:
    for i in range(max_steps):
        with tracer.trace("step", {"step_index": i}) as step_span:
            observation = observe(environment)
            action = think(observation)
            step_span.set_attribute("action", action)
```

### 推荐路径

```
从模式一开始 → 如果用了框架转模式二 → 特殊场景补模式三
```

不要一开始就设计一个完美的追踪系统。先跑通一条完整 Trace，再逐步补充细节。

## Span 设计

Span 设计决定了你后续能怎么查询和分析数据。设计不好的 Span，数据量再大也榨不出信息。

### 层次结构

一个 Agent Trace 的 Span 应该有三层：

```
Trace (agent_episode) ← 一次完整交互
├── Span (step_1)     ← Agent 循环的一轮
│   ├── Span (llm_call)     ← LLM 调用
│   ├── Span (tool_call)    ← 工具调用
│   └── Span (retrieval)    ← 检索
├── Span (step_2)
│   ├── Span (llm_call)
│   └── Span (tool_call)
└── Span (final_response)  ← 最终响应
```

不要平铺所有 Span。层次结构让你能回答不同粒度的问题——"这个请求整体多慢"（Trace 级别）、"哪一轮最慢"（Step 级别）、"LLM 调用本身多慢"（Span 级别）。

### Span 命名规范

命名决定了你在查询时的分组能力。统一的命名规范 + 合理的标签 (Tag) 设计 = 可聚合的追踪数据。

```
格式: {操作类型}.{领域}.{具体操作}

llm_call.chat.completion      ← LLM 聊天调用
tool_call.order.query         ← 订单查询工具
tool_call.order.cancel        ← 订单取消工具
retrieval.vector.search       ← 向量检索
agent.decision.intent         ← 意图识别决策
```

Agent 框架层应该提供一套默认的命名规范，让所有 Agent 的 Trace 遵循同样的命名体系。

### 关键属性

每个 Span 至少应该包含：

| 属性 | 说明 | 是否必需 |
|------|------|---------|
| `type` | llm_call / tool_call / retrieval / decision | 必需 |
| `status` | success / error / timeout | 必需 |
| `duration_ms` | 耗时 | 必需 |
| `input` | 输入（完整或摘要） | 必需 |
| `output` | 输出（完整或摘要） | 必需 |
| `error.message` | 错误信息（如果有） | 失败时必需 |

LLM Span 额外包含：
- `llm.model` — 模型名
- `llm.input_tokens` / `llm.output_tokens`
- `llm.temperature` / `llm.top_p`

工具 Span 额外包含：
- `tool.name`
- `tool.params` — 序列化后的完整参数

## Trace ID 传播

Trace ID 需要穿透的层级比传统分布式系统更多：

```
用户请求 → API 网关 → Agent 引擎 → LLM SDK → 模型 API
                                    → 工具 SDK → 外部 API
                                    → 检索 SDK → 向量数据库
```

### 透传方式

**HTTP Header**：对外部 API 用 `X-Trace-Id` 或 `Traceparent`（W3C 标准）头传递。

**SDK 参数**：对 LLM API（OpenAI、Anthropic），通过 `user` 字段或额外参数传入。这些平台会在日志中保留该字段，回查时能通过 Trace ID 关联。

```python
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    user=trace_id  # 通过 user 字段传递
)
```

**自定义 Headers**：对工具 API，在 HTTP 请求中加入自定义头。

**日志上下文**：在应用代码中，将 Trace ID 注入日志上下文，自动附加到每条日志记录。

### 客户端传入

如果客户端主动传入 `X-Trace-Id`，服务端应该信任并使用这个 ID（而不是重新生成）。这能让用户端和服务端的追踪关联起来——用户说"刚才那次请求"，你和他用的是同一个 Trace ID。

如果客户端不传，服务端在入口处生成。

```python
@app.middleware("http")
async def trace_middleware(request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    with tracer.trace("http_request", trace_id=trace_id):
        ...
```

## 流式响应下的追踪

Agent 经常使用流式响应（SSE/WebSocket）——Token 一个接一个地返回，而不是一次性输出。这对追踪提出了额外要求。

### 问题：完成前的状态不确定

在流式响应过程中，Trace 还没有结束。你需要：
1. 在响应开始时创建一个 Trace（分配 Trace ID）
2. 在流式传输过程中持续更新 Span（累计 token 数、捕获错误）
3. 在流结束后才 Finalize 整个 Trace

### 实现模式

```python
async def streaming_agent(user_input: str):
    with tracer.trace("agent_episode") as trace_span:
        # 分配 Trace ID，立即返回给客户端
        yield {"type": "trace_id", "value": trace_span.trace_id}

        # Agent 执行循环
        for step in agent_loop(user_input):
            with tracer.trace("step") as step_span:
                result = await execute_step(step)
                step_span.set_attribute("action", result.action)

                # 流式输出中间结果
                yield {"type": "step", "data": result}

                # 每步完成后立即发送该步的 Span
                yield {"type": "span", "data": step_span.export()}

        # 最终 Span
        trace_span.set_attribute("status", "success")
        yield {"type": "trace_end", "data": trace_span.export()}
```

关键点：**不要在流结束后才发送 Trace 数据**。每步完成后立即发送该步的 Span。这样即使在流中断的情况下，你至少能看到"到哪一步为止是成功的"。

### 断流检测

流式连接可能意外中断。追踪系统需要处理"不完整的 Trace"：

```
Trace 状态:
  - completed: 正常完成
  - incomplete: 流中断（有部分 Span，缺少最终响应）
  - error: 显式错误结束
```

不完整的 Trace 也有价值——它告诉你用户在哪里"放弃"了。这也是一种质量信号。

## 采样策略配置

采样是控制存储成本的主要手段。但采样策略直接影响你排查问题的能力。

### 策略类型

**头部采样 (Head-based)**：在请求入口处决定是否采样。实现简单，但会错过了"事后发现这个请求很重要"的挽回机会。

**尾部采样 (Tail-based)**：请求完成后，根据特征决定是否保留。可以实现"所有错误请求都保留"，但实现复杂，需要缓冲。

**混合采样**：推荐方案。头部采样做常规降噪，尾部采样补充重要场景。

### 推荐配置

```python
sampler = HybridSampler(
    head={
        "default": 0.05,              # 正常请求 5%
        "path:/api/experiment": 1.0,  # 新接口全量
    },
    tail={
        "status:error": 1.0,          # 错误请求 100%
        "duration > 10s": 0.5,        # 慢请求 50%
        "user_tier:premium": 1.0,     # 高价值用户全量
    },
    max_traces_per_minute=1000        # 硬上限
)
```

**对于生产环境，建议：错误 100%、尾部延迟 > P99 的 50%、普通请求 1-5%。**

### 采样一致性

如果 Agent 请求涉及多个微服务，各服务的采样决策必须一致。要么都采样，要么都不采样。不一致的采样会产生"孤儿 Span"——有子 Span 没有父 Span，无法组成完整的 Trace。

解决方案：Trace ID 的哈希值决定是否采样。所有服务用同一个哈希函数，对同一个 Trace ID 做出一致的采样决策。

```python
def should_sample(trace_id: str, rate: float = 0.1) -> bool:
    hash_val = int(hashlib.md5(trace_id.encode()).hexdigest(), 16)
    return (hash_val % 10000) / 10000 < rate
```

## 存储与保留

追踪数据量可能非常大。一个 Agent 每天 10 万请求，平均每个请求产生 10 个 Span、每个 Span 2KB——每天 2GB 数据。保留 30 天就是 60GB。

### 分层存储

```
热存储 (7 天): 全量 Span，支持实时查询
温存储 (30 天): 全量 Span，支持查询（可能有少许延迟）
冷存储 (90 天): 仅保留失败请求 + 评测相关的 Trace（评测用例应保留更久，回溯回归分析）
归档 (1 年+): 仅保留 Trace 的摘要（状态、耗时、错误码、token 数），丢弃原始 input/output
```

这要求在数据入库时就给每条 Trace 打上标记——"是否属于评测集"、"是否包含失败"。

### 数据保留策略

```yaml
retention:
  hot:
    duration: 7d
    includes: all spans
  warm:
    duration: 30d
    includes: all spans
  cold:
    duration: 90d
    includes:
      - status == "error"
      - eval_set == true
      - eval_score < 0.5
  archive:
    duration: 365d
    includes: summary only (no input/output)
```

## 数据集市：把 Trace 当成数据仓库

追踪数据不只是排查问题时才用的——它本身就是一个结构化的数据集。把 Trace 数据定期导入分析型数据库，可以做传统可观测性做不到的事情：

**用户行为分析**。Trace 数据包含了用户的完整交互序列。按维度聚合 Tokens/Cost/Error rate——知道哪个用户、哪个功能消耗最多。

**评测集自动生成**。从 Trace 中提取"用户重复提问"的请求（隐式反馈负样本），自动补充到评测集。

**回归分析**。当发布新版本后，对比新旧版本的 Trace 分布。P95 延迟变了多少、工具调用分布是否有偏移、失败模式是否有变化。

这不是必须的——不是每个团队都需要数据集市。但如果你已经积累了数月的 Trace 数据，它就是一座金矿。

## 总结

全链路追踪是 Agent 可观测性的核心。把它落地需要关注四个层面：

埋点用装饰器（最简洁）→ Span 设计分三层（Episode/Step/Action）→ Trace ID 穿透每一层 → 采样用混合策略（错误 100%，普通抽样）→ 存储分温冷（7 天热 + 归档摘要）。

**流式响应**需要每步完成后立即发送 Span，而不是等到响应结束。**数据集市**把 Trace 数据变成分析金矿——但不是每个团队都需要。

**下一篇**：[性能分析与优化](03-performance-analysis.md)——有了 Trace 数据，怎么找到性能瓶颈。

## 参考链接

- [OpenTelemetry Sampling](https://opentelemetry.io/docs/concepts/sampling/)
- [Tail-Based Sampling in LangFuse](https://langfuse.com/docs/tracing-features/tail-sampling)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [OpenAI — Using the `user` Parameter](https://platform.openai.com/docs/guides/safety-best-practices/end-user-ids)
- [Honeycomb — Sampling for LLM Traces](https://www.honeycomb.io/blog/sampling-llm-traces)
