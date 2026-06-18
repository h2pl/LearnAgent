# 架构设计与 API 服务化

> 13 章的知识，最终凝结为一个可部署的 Agent 系统。架构设计决定系统的天花板，API 服务化决定系统的可访问性。

## 目录

- [架构设计原则](#架构设计原则)
- [参考架构](#参考架构)
- [Agent 核心引擎](#agent-核心引擎)
- [API 层设计](#api-层设计)
- [流式响应 (SSE)](#流式响应-sse)
- [状态管理](#状态管理)
- [扩展性设计](#扩展性设计)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。欢迎来到最后一章。前 13 章我们走过了从 LLM 基础到 Agent 安全的全过程。**现在，是时候把这些知识变成一个真正可部署的系统了。**

本文从架构设计和 API 层切入——这是 Agent 服务化最核心的两个决策点。

## 架构设计原则

### 分层分离

一个生产级 Agent 系统应该至少分为四层：

```
用户界面层 (UI/API) — 与用户交互的入口
    │
编排层 (Orchestration) — Agent 逻辑、任务调度、状态管理
    │
能力层 (Capabilities) — LLM、工具、检索、记忆
    │
基础设施层 (Infrastructure) — 存储、缓存、计算
```

每层独立部署、独立扩展、独立演进。**下层不依赖上层**——能力层不知道编排层的存在。

### 无状态优先

Agent 的核心执行引擎应该是无状态的——所有状态存储在外部：

- **对话历史** → 数据库 / Redis
- **记忆** → 持久化存储（向量数据库 + 关系型数据库）
- **会话状态** → 缓存 (Redis) 或数据库
- **配置** → 配置文件或配置中心

为什么？无状态意味着可以水平扩展、滚动更新、快速恢复。**状态越少，运维越简单。**

### 优雅降级

任何外部依赖都可能不可用。系统应该设计降级策略：

```
LLM 服务不可用 → 切换到备用模型 / 返回缓存结果
向量数据库不可用 → 切换到关键词搜索 / 返回兜底回答
工具 API 不可用 → 告知用户该功能暂时无法使用
```

**每个外部调用都要有 fallback 和 timeout。**

## 参考架构

<p align="center">
  <img src="../../assets/14-ship-to-prod/agent-architecture.svg" alt="Agent 系统参考架构" width="95%"/>
</p>

```
┌─────────────────────────────────────────────────────┐
│                    API Gateway                        │
│    REST (同步)    │    WebSocket/SSE (流式)          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                Agent Orchestrator                     │
│  意图识别 → 上下文组装 → 工具调度 → 响应生成          │
│  (LangGraph / CrewAI / 自研引擎)                     │
└────┬─────────┬──────────┬──────────┬────────────────┘
     │         │          │          │
┌────▼──┐ ┌───▼────┐ ┌───▼───┐ ┌───▼────────┐
│ LLM   │ │ Tools  │ │Retrieval│ │   Memory   │
│ 池    │ │ 池     │ │  池    │ │   池       │
├───────┤ ├────────┤ ├────────┤ ├────────────┤
│GPT-4o │ │查询订单│ │ 向量搜 │ │  对话历史   │
│Claude │ │发送邮件│ │ 全文搜 │ │  用户画像   │
│ ……    │ │ ……     │ │ ……    │ │  长期记忆   │
└───────┘ └────────┘ └────────┘ └────────────┘
```

## Agent 核心引擎

### 执行循环

Agent 的核心是一个循环：

```python
async def agent_loop(request: UserRequest) -> AsyncGenerator[Event, None]:
    """Agent 主执行循环"""
    context = await build_context(request)
    
    while not should_stop(context):
        # 1. 调用 LLM 获取下一步决策
        response = await llm_call(context)
        
        # 2. 处理工具调用
        if response.has_tool_calls:
            for tool_call in response.tool_calls:
                result = await execute_tool(tool_call)
                context.add_tool_result(result)
                yield Event("tool_result", tool_call.name, result)
            continue
        
        # 3. 生成最终回复
        yield Event("response", response.text)
        break
```

### 事件驱动

推荐使用事件驱动架构。每个 Agent 步骤发出事件，外部可以订阅这些事件：

```python
@dataclass
class AgentEvent:
    type: str          # "llm_call" | "tool_call" | "error" | "response"
    data: Any
    timestamp: float
    trace_id: str
```

事件可以用于：前端实时显示进度、审计日志、性能监控、故障调试。

### 错误处理

每个外部调用都要有完整的错误处理链：

```python
async def safe_llm_call(context, max_retries=3):
    """带重试和降级的 LLM 调用"""
    for attempt in range(max_retries):
        try:
            return await primary_llm(context)
        except RateLimitError:
            if attempt == max_retries - 1:
                return await fallback_llm(context)  # 切换模型
            await asyncio.sleep(2 ** attempt)  # 指数退避
        except TimeoutError:
            continue  # 重试
        except APIError as e:
            if e.is_transient:
                continue
            raise  # 非临时错误，直接抛出
```

## API 层设计

### 同步 API (REST)

适合非实时交互——用户发出请求，等待最终结果。

```
POST /api/v1/agent/chat
Content-Type: application/json

{
  "user_id": "usr_123",
  "session_id": "sess_456",
  "message": "帮我查一下最近的订单",
  "stream": false
}

→ 响应:
{
  "session_id": "sess_456",
  "response": "您最近的订单是 ORD-789，已于 6 月 15 日送达",
  "tool_calls": [
    {"tool": "query_order", "params": {"user_id": "usr_123"}, "result": {...}}
  ],
  "metadata": {
    "latency_ms": 2340,
    "tokens_used": 1250,
    "model": "gpt-4o"
  }
}
```

### API 设计原则

**版本化**。API 从一开始就加版本号：

```
/v1/agent/chat    # 稳定版本
/v2/agent/chat    # 试验版本
```

**幂等性**。关键操作（如支付、取消订单）提供 `idempotency_key`，防止重复执行：

```json
{
  "idempotency_key": "unique_req_001",
  "action": "cancel_order",
  "order_id": "ORD-789"
}
```

**限流**。API 网关层做限流，按用户/API Key 维度：

```
每个用户: 30 请求/分钟
全局: 1000 请求/分钟
流式连接: 10 并发/用户
```

**响应格式统一**。所有 API 响应使用统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "request_id": "req_abc123"
}
```

## 流式响应 (SSE)

Agent 的思考过程往往是多步的，用户不希望等待全部完成才看到结果。**流式响应是生产级 Agent 的标配**。

### Server-Sent Events (SSE)

SSE 是推荐的首选方案——比 WebSocket 更简单，浏览器原生支持：

```
POST /api/v1/agent/chat/stream

→ SSE 流:
data: {"type": "status", "content": "正在分析您的问题..."}
data: {"type": "tool_call", "tool": "query_order", "params": {...}}
data: {"type": "tool_result", "tool": "query_order", "result": {...}}
data: {"type": "thinking", "content": "根据查询结果..."}
data: {"type": "text", "content": "您最近的订单是"}
data: {"type": "text", "content": " ORD-789"}
data: {"type": "done", "content": ""}
```

### 心跳

长时间运行的 Agent 需要心跳机制：

```
data: {"type": "heartbeat", "timestamp": 1718700000}
```

### 中断

用户应该可以中断正在运行的 Agent：

```
POST /api/v1/agent/sess_456/cancel
→ Agent 终止当前执行，返回已完成的上下文
```

## 状态管理

### 会话管理

```
Session: {
  id: "sess_456",
  user_id: "usr_123",
  agent_id: "customer-service",
  messages: [...],         // 对话历史
  context: {...},          // Agent 上下文
  status: "active" | "waiting_approval" | "completed" | "cancelled",
  created_at: "...",
  updated_at: "...",
  expires_at: "..."        // TTL
}
```

会话应该设置 TTL（Time To Live），过期自动清理：

```
活跃会话: 24 小时
已完成会话: 7 天
审批中会话: 1 小时
```

### 上下文管理

**不是所有对话历史都需要喂给 LLM**。上下文管理策略：

```
短期上下文: 最近 10 轮对话 + 系统 prompt（始终在上下文中）
中期上下文: 最近 20 轮对话摘要（超出短期时使用）
长期上下文: 用户画像 + 长期记忆（按需注入）
```

## 扩展性设计

### 水平扩展

Agent 引擎是无状态的，因此可以水平扩展：

```
Load Balancer
  ├── Agent Instance 1
  ├── Agent Instance 2
  ├── Agent Instance 3
  └── Agent Instance N (自动扩缩容)
```

每个实例处理独立的请求，通过 Redis 共享会话数据和缓存。

### 异步任务队列

对于耗时操作（如批量处理、定时任务），使用消息队列：

```
API 请求 → 消息队列 (RabbitMQ/Redis Streams) → Worker 处理
```

### 插件机制

工具应该是可插拔的，新工具上线无需重启服务：

```python
class ToolPlugin(ABC):
    @abstractmethod
    async def execute(self, params: dict) -> ToolResult: ...
    
    @abstractmethod
    def get_schema(self) -> dict: ...  # 返回 JSON Schema

# 新工具只需实现 ToolPlugin 接口，注册即可使用
register_tool("query_order", QueryOrderTool())
```

## 总结

架构设计和 API 服务化是 Agent 从 demo 到生产的第一步。核心要点：

- **分层分离**：UI、编排、能力、基础设施四层独立
- **无状态引擎**：所有状态存在外部，实现水平扩展
- **流式响应**：SSE 是 Agent 交互的标配
- **错误处理**：每个外部调用都有重试和降级策略

**下一篇**：部署方案——Docker 容器化、CI/CD 流水线、环境管理。

## 参考链接

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Microsoft — Agent Architecture Best Practices](https://learn.microsoft.com/en-us/ai/playbook/technology-guidance/generative-ai/)
- [Anthropic — Building Production Agents](https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns)
- [12-Factor App](https://12factor.net/)
