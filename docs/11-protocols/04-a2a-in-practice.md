# A2A 实战：多 Agent 协作实现

> 前一篇讲了 A2A 的概念和设计，本文实战——从装 SDK、写 Agent Card、实现 A2A Server，到完整的跨 Agent 任务委托。所有代码可运行，适合边读边练。

## 目录

- [前置阅读](#前置阅读)
- [环境准备：安装 A2A SDK](#环境准备安装-a2a-sdk)
- [第一步：创建 Agent Card](#第一步创建-agent-card)
- [第二步：实现 A2A Agent Server](#第二步实现-a2a-agent-server)
- [第三步：Agent 客户端调用](#第三步agent-客户端调用)
- [三种交互模式](#三种交互模式)
- [一个完整案例：多 Agent 协作系统](#一个完整案例多-agent-协作系统)
- [生产化注意事项](#生产化注意事项)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [A2A 与 Agent 通信协议](./03-a2a-and-beyond.md) 中，你了解了 A2A 的核心概念：Agent Card 做能力声明、任务生命周期管理、三种交互模式。现在是动手时间——本文带你从零搭建一个基于 A2A 的多 Agent 协作系统。

本文使用 **Google ADK 的 A2A SDK**（2026 年初发布，Linux Foundation 治理），Python 版本。所有代码基于 A2A v1.0 规范。

## 前置阅读

本文假设你已经了解 A2A 的基本概念。如果还没读过，建议先看 [A2A 与 Agent 通信协议](./03-a2a-and-beyond.md)，了解 Agent Card、任务生命周期、同步/流式/异步三种模式。本文直接在此基础上写代码。

## 环境准备：安装 A2A SDK

A2A SDK 作为 Google ADK 的一部分发布，也可以单独安装：

```bash
pip install google-adk          # 完整 ADK（含 A2A 支持）
pip install a2a-sdk             # 或仅 A2A SDK 独立包
```

验证安装：

```python
from a2a import A2AServer, A2AClient, AgentCard
print("A2A SDK ready")
```

## 第一步：创建 Agent Card

Agent Card 是 A2A 的"名片"——它告诉其他 Agent "你是谁、能做什么、怎么调用你"。

```python
from a2a import AgentCard, Skill, Endpoint, AuthScheme

# 创建一个 Agent Card，描述一个"数据分析 Agent"
card = AgentCard(
    name="data-analyst",
    description="查询数据库并生成数据报表",
    skills=[
        Skill(
            name="sql_query",
            description="执行 SQL 查询，返回结构化结果"
        ),
        Skill(
            name="report_generate",
            description="根据查询结果生成 Markdown 格式报表"
        ),
    ],
    endpoints=[
        Endpoint(
            url="http://localhost:8001/a2a",
            type="sse"      # 支持 SSE 流式传输
        )
    ],
    authentication=AuthScheme(schemes=["bearer"])
)
```

实际部署时，Agent Card 也会作为 JSON 文件发布到 `/.well-known/agent-card.json`：

```python
import json

with open("agent-card.json", "w") as f:
    json.dump(card.to_dict(), f, indent=2)
```

生成的 JSON 文件可以直接放到 Web 服务器的 `/.well-known/` 路径下，其他 Agent 通过标准 URL 自动发现。

## 第二步：实现 A2A Agent Server

A2A Server 的核心是接收和响应来自其他 Agent 的**任务（Task）**请求。

以下是一个最小可运行的 A2A Server：

```python
from a2a import A2AServer, Task, TaskStatus, Message, TextPart

# 定义任务处理函数
async def handle_task(task: Task) -> Task:
    # 从任务中提取用户需求
    user_query = task.message.parts[0].text

    # 执行分析（这里用简单示例）
    if "查" in user_query:
        result = f"查询结果：上月销售额 1,280,000 元，环比增长 12.5%"
    else:
        result = f"收到任务：{user_query}"

    # 返回结果
    task.status = TaskStatus.COMPLETED
    task.response = Message(parts=[TextPart(text=result)])
    return task

# 启动 Server
server = A2AServer(
    host="localhost",
    port=8001,
    card_path="agent-card.json",
    task_handler=handle_task
)

server.run()
```

这段代码只有 28 行。启动后，其他 Agent 可以通过 A2A 协议连接到 `http://localhost:8001/a2a` 并委托任务。

## 第三步：Agent 客户端调用

其他 Agent（或你的应用）通过 `A2AClient` 发起任务委托：

```python
from a2a import A2AClient, Task, Message, TextPart

async def call_analyst_agent():
    # 创建客户端，连接到数据分析 Agent
    client = A2AClient(
        server_url="http://localhost:8001",
        agent_card_url="http://localhost:8001/.well-known/agent-card.json"
    )

    # 委托任务
    task = Task(
        message=Message(parts=[TextPart(text="查一下上个月的销售数据")])
    )

    result = await client.send_task(task)

    print(f"任务状态：{result.status}")
    print(f"结果：{result.response.parts[0].text}")
```

**调用的关键流程**：客户端先通过 Agent Card URL 获取 Agent 的能力声明（它能不能做 SQL 查询？），确认能力匹配后再发起任务委托。如果能力不匹配，客户端可以在发起调用前就给出"这个 Agent 做不了"的反馈。

## 三种交互模式

A2A 支持三种模式，用 `mode` 参数切换：

<p align="center">
  <img src="../../assets/11-protocols/a2a-interaction-modes.svg" alt="A2A 三种交互模式：同步/流式/异步" width="90%"/>
</p>

### 同步模式：即时返回

适合低延迟场景，如查天气、翻译、简单计算。

```python
result = await client.send_task(
    task=Task(message=Message(parts=[TextPart(text="1 美元等于多少人民币？")])),
    mode="sync"  # 默认模式
)
```

**同步模式的特点**：请求发出后，连接保持打开，直到收到完整结果。超时默认 30 秒。

### 流式模式：SSE 实时推送

适合耗时任务，中间结果实时可见。

```python
# Server 端需要把任务处理改为生成器
async def handle_task_streaming(task: Task):
    # 逐步生成中间结果
    yield TaskUpdate(status=TaskStatus.WORKING, message="正在查询数据库...")
    await asyncio.sleep(1)

    yield TaskUpdate(status=TaskStatus.WORKING, message="已查到 1,280 条记录，正在分析...")
    await asyncio.sleep(2)

    yield TaskUpdate(
        status=TaskStatus.COMPLETED,
        message=Message(parts=[TextPart(text="分析完成，上月销售额 1,280,000 元")]
    )
```

```python
# 客户端通过 SSE 接收流式更新
async for update in client.send_task_streaming(
    task=Task(message=Message(parts=[TextPart(text="分析销售数据")]))
):
    print(f"进度：{update.message.text}")
```

### 异步模式：后台执行 + 回调

适合耗时很长的任务，Agent 接受任务后立即返回，完成后回调通知。

```python
# 客户端发起异步任务
result = await client.send_task(
    task=Task(message=Message(parts=[TextPart(text="生成季度报表，明天早上 8 点前完成")])),
    mode="async",
    callback_url="http://my-agent/callback"  # 完成后回调地址
)

print(f"任务已接受，ID：{result.task_id}")
# 客户端可以去做其他事，等待回调
```

```python
# Server 端的回调处理
@app.post("/a2a/callback")
async def handle_callback(task_result: dict):
    task_id = task_result["task_id"]
    status = task_result["status"]
    print(f"任务 {task_id} 已完成，状态：{status}")
    # 通知用户或触发后续流程
```

## 一个完整案例：多 Agent 协作系统

以下展示一个真实的多 Agent 协作场景：**用户提问 → 主 Agent 拆解任务 → 分发给子 Agent → 汇总结果**。

<p align="center">
  <img src="../../assets/11-protocols/a2a-multi-agent-system.svg" alt="多 Agent 协作系统架构：主 Agent 分发任务给搜索和分析 Agent" width="90%"/>
</p>

### 定义子 Agent

先创建两个子 Agent，每个独立运行在各自的进程中：

```python
# 文件：search_agent.py（搜索 Agent）
from a2a import A2AServer, Task, TaskStatus, Message, TextPart

async def search_handler(task: Task) -> Task:
    query = task.message.parts[0].text
    # 模拟网络搜索
    results = f"搜索「{query}」的结果：\n1. 官方文档：docs.example.com\n2. 技术博客：blog.example.com\n3. Stack Overflow: stackoverflow.com/q/12345"
    task.status = TaskStatus.COMPLETED
    task.response = Message(parts=[TextPart(text=results)])
    return task

server = A2AServer(host="localhost", port=9001,
    card_path="search-agent-card.json",
    task_handler=search_handler)
server.run()
```

```python
# 文件：report_agent.py（报表 Agent）
from a2a import A2AServer, Task, TaskStatus, Message, TextPart

async def report_handler(task: Task) -> Task:
    data = task.message.parts[0].text
    report = f"# 分析报告\n\n{data}\n\n**结论**：基于以上数据，建议进一步优化。"
    task.status = TaskStatus.COMPLETED
    task.response = Message(parts=[TextPart(text=report)])
    return task

server = A2AServer(host="localhost", port=9002,
    card_path="report-agent-card.json",
    task_handler=report_handler)
server.run()
```

### 主 Agent 编排

主 Agent 接收用户请求，决定调用哪些子 Agent，然后汇总结果：

```python
# 文件：orchestrator.py（主 Agent）
from a2a import A2AClient, Task, Message, TextPart
import asyncio

async def orchestrate(user_request: str):
    # 连接到子 Agent
    search_client = A2AClient(
        server_url="http://localhost:9001",
        agent_card_url="http://localhost:9001/.well-known/agent-card.json"
    )
    report_client = A2AClient(
        server_url="http://localhost:9002",
        agent_card_url="http://localhost:9002/.well-known/agent-card.json"
    )

    # 步骤 1：让搜索 Agent 查找资料
    print("[主 Agent] 正在搜索资料...")
    search_result = await search_client.send_task(
        Task(message=Message(parts=[TextPart(text=user_request)]))
    )

    # 步骤 2：将搜索结果传给报表 Agent 生成报告
    print("[主 Agent] 正在生成报告...")
    report_result = await report_client.send_task(
        Task(message=Message(parts=[
            TextPart(text=f"基于以下信息生成分析报告：\n{search_result.response.parts[0].text}")
        ]))
    )

    # 步骤 3：合并返回给用户
    final_response = f"**搜索结果**：\n{search_result.response.parts[0].text}\n\n**分析报告**：\n{report_result.response.parts[0].text}"
    return final_response

# 执行
result = asyncio.run(orchestrate("2026 年 MCP 协议最新进展"))
print(result)
```

### 运行流程

```bash
# 终端 1：启动搜索 Agent
python search_agent.py

# 终端 2：启动报表 Agent
python report_agent.py

# 终端 3：启动主 Agent 执行
python orchestrator.py
```

主 Agent 会依次调用两个子 Agent，将搜索 Agent 的结果作为输入传给报表 Agent，最终返回整合后的报告。

## 生产化注意事项

以上 Demo 可以直接跑起来，但用于生产还需要补充几个环节：

### 1. 认证与授权

A2A v1.0 支持多种认证方案，推荐用 OAuth 2.0 或 mTLS：

```python
from a2a.auth import BearerAuth

# 客户端配置认证
client = A2AClient(
    server_url="http://localhost:9001",
    auth=BearerAuth(token="your-api-token")
)
```

### 2. Agent 发现优化

小型场景可以用固定 URL，但大型系统应该引入注册中心：

```python
from a2a.discovery import RegistryClient

# 从中心注册表发现 Agent
registry = RegistryClient(registry_url="http://registry.internal/agents")
analyst_agents = await registry.find_agents(capability="data_analysis")

for agent in analyst_agents:
    card = await agent.get_card()
    print(f"发现 Agent：{card.name}，能力：{card.skills}")
```

### 3. 任务超时与重试

```python
from a2a import RetryPolicy

client = A2AClient(
    server_url="http://localhost:9001",
    retry=RetryPolicy(max_retries=3, backoff=2.0),  # 最多重试 3 次，指数退避
    timeout=60.0  # 同步模式超时
)
```

### 4. 日志与追踪

```python
import logging
logging.basicConfig(level=logging.INFO)

# 完整记录每次 A2A 调用的请求/响应
client.enable_logging()  # 开启详细日志
```

### 5. 健康检查与负载均衡

生产环境中子 Agent 可能不可用。A2A 规范推荐 Server 暴露 `/health` 端点，主 Agent 定期检查：

```python
# Server 端
@app.get("/health")
async def health():
    return {"status": "ok", "uptime": time.time() - start_time}
```

## 总结

- **A2A 实战三步走**：创建 Agent Card（能力声明）→ 实现 A2A Server（任务处理）→ 客户端调用（任务委托）
- **三种交互模式对应不同场景**：同步（低延迟）、流式（长任务进度）、异步（后台执行）
- **多 Agent 编排模式**：主 Agent 拆解任务、分发到子 Agent、汇总结果——这是 A2A 最常用的模式
- **生产化补充**：认证（OAuth/mTLS）、发现（注册中心）、重试（指数退避）、健康检查
- **所有代码可运行**：三个 Python 文件即可启动一个完整的多 Agent 协作系统

> 下一篇 [轻量级约定：Skills 与 AGENTS.md](./05-lightweight-conventions.md)——除了正式的通信协议，还有一套轻量级的"约定"在 Agent 生态中广泛使用。

## 参考链接

- [Google ADK — A2A Python SDK](https://google.github.io/adk/)
- [A2A Specification v1.0 — Task Lifecycle](https://github.com/google/A2A)
- [A2A — Agent Card Specification](https://github.com/google/A2A/blob/main/spec/agent-card.md)
- [A2A — Authentication & Security](https://github.com/google/A2A/blob/main/spec/auth.md)
- [Google Developers Blog — A2A Practical Guide (2026-03)](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/)
