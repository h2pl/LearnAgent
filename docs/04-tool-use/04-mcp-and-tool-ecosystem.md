# MCP 与工具生态

> MCP（Model Context Protocol）用一年时间从 Anthropic 的实验项目变成 AI 工具层的事实标准。2026 年，8,000+ 有效 Server、9700 万月 SDK 下载——它正在解决困扰行业多年的 N×M 工具集成问题。

## 目录

- [N×M 问题：工具集成的困境](#n×m-问题工具集成的困境)
- [MCP 是什么](#mcp-是什么)
- [三大核心原语：Tools、Resources、Prompts](#三大核心原语toolsresourcesprompts)
- [从"写一次"到"处处用"](#从写一次到处处用)
- [MCP 的工程实践](#mcp-的工程实践)
- [2026 年 MCP 生态现状](#2026-年-mcp-生态现状)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [多工具编排](./03-multi-tool-orchestration.md) 中，你了解了如何让多个工具协同工作。但所有工具都是自己写的——每新增一个外部能力（GitHub、Slack、数据库），你都要重新实现一套集成代码。这篇文章解决核心问题：**MCP 如何让你写一次工具，到处复用，把 N×M 的集成地狱变成 N+M 的简单加法**。

**Model Context Protocol（MCP）** 是 Anthropic 于 2024 年 11 月发布的开放标准，定义了 AI 应用如何连接外部工具和数据源。2025 年 12 月，Anthropic 将它捐赠给 Linux 基金会，成为 Agentic AI Foundation 的创始项目。到 2026 年中，MCP 已经是工具层的事实标准——Claude、ChatGPT、Cursor、Gemini、VS Code 都原生支持。

## N×M 问题：工具集成的困境

在 MCP 之前，工具集成是经典的 **N×M 噩梦**：

- N 个 AI 客户端（Claude、GPT、Gemini、Cursor...）
- M 个外部工具（GitHub、Slack、Postgres、Stripe...）
- 需要写 **N×M** 套适配代码

重复劳动的根源不只是"写很多代码"，而是**每个客户端的 Function Calling 格式不同**。Claude 用 `user` role + `tool_result` 消息块，GPT 用 `tool` role，Gemini 用 `functionResponse`——同样是"调用 GitHub API 搜索 issue"，你需要为三个客户端写三套格式适配，且每套都要处理错误、超时、认证。GitHub 的 API 没变，但对接层被重复写了 N 次，每次都可能引入不同的 Bug。

MCP 的思路是在 LLM 的 Function Calling 和外部工具之间插入一个**标准协议层**：Server 用 JSON-RPC 2.0 暴露标准接口，Client 负责把 JSON-RPC 转换为各平台原生格式。**你写一次 Server，任何 MCP 客户端都能用**。N+M 套代码，而不是 N×M。

## MCP 是什么

MCP 是一个运行在 JSON-RPC 2.0 之上的协议层，借鉴了 VS Code 的 Language Server Protocol（LSP）的设计。它定义了四个角色：

| 角色 | 职责 | 示例 |
|------|------|------|
| **Host** | 用户运行的应用 | Claude Desktop、Cursor、VS Code |
| **Client** | Host 内部的连接实例 | 与 Server 保持 1:1 会话 |
| **Server** | 暴露工具/资源/提示的服务 | GitHub Server、Postgres Server |
| **Gateway**（可选） | 路由、认证、审计层 | 企业级部署用 |

**传输方式**：本地用 **STDIO**（Server 作为 Host 的子进程），远程用 **Streamable HTTP**（2025-03 规范取代 SSE）。远程传输在 2025 年中支持 OAuth 2.1 后，企业部署才真正可行。

**一个极简的 MCP 服务器只有 12 行 Python**：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")

@mcp.tool()
def get_weather(city: str) -> str:
    """获取指定城市的当前天气。"""
    # 实际调用天气 API
    return f"{city}当前天气：多云，26°C"

if __name__ == "__main__":
    mcp.run()
```

把它配置到 Claude Desktop 的 `mcp.json` 里，Claude 立即就能调用 `get_weather`。把它配置到 Cursor 的 `mcp.json` 里，Cursor 也能用。**同一个 Server，零改动，跨客户端复用**。

## 三大核心原语：Tools、Resources、Prompts

MCP Server 暴露三种能力，不是只有工具调用：

### Tools（工具）

可调用函数，与 Function Calling 语义一致。这是 MCP 最常用的原语。

```python
@mcp.tool()
def search_github_issues(repo: str, query: str) -> list[dict]:
    """在指定 GitHub 仓库中搜索 issues。"""
    # 调用 GitHub API
    return [{"number": 123, "title": "Bug in auth", "state": "open"}]
```

### Resources（资源）

只读数据，模型可以读取但不能修改。Resource 不是工具调用，而是直接获取数据。

```python
@mcp.resource("file://docs/readme.md")
def get_readme() -> str:
    """返回项目的 README 文件内容。"""
    with open("README.md") as f:
        return f.read()
```

Resource 的优势是**零调用开销**：模型需要文档内容时，直接读取，不需要走一次"调用→执行→回传"的完整流程。

### Prompts（提示模板）

预定义的 Prompt 模板，用户可以直接调用。这不是给模型的，而是给终端用户的快捷方式。

```python
@mcp.prompt()
def code_review_prompt(code: str) -> str:
    """生成代码审查的提示模板。"""
    return f"请审查以下代码，检查潜在 Bug 和性能问题：\n\n{code}"
```

**两个常被忽略的设计**：

1. **Sampling**：Server 可以请求 Client 代它调用 LLM。这意味着 MCP Server 本身可以是 Agent——它遇到不确定的参数时，可以反问模型"这个参数应该填什么？"Server 不知道 Client 用的是什么模型，这是刻意的解耦。

2. **Roots**：Server 可以询问 Client"用户授权了哪些文件路径"。这是权限边界——Server 不能随意访问文件系统，只能看到用户明确授权的范围。

## 从"写一次"到"处处用"

MCP 的真正价值不是"少写代码"，而是**生态复用**。2026 年，modelcontextprotocol.io 的注册表已有数百个社区和厂商 Server：

| 类别 | 代表 Server | 用途 |
|------|------------|------|
| 代码平台 | GitHub、GitLab | 读仓库、提 PR、查 Issue |
| 数据库 | Postgres、SQLite、MongoDB | 查询、分析 |
| 协作工具 | Slack、Notion、Linear | 发消息、查任务 |
| 云服务 | Cloudflare、AWS、Vercel | 管理资源、查日志 |
| 支付 | Stripe | 查交易、退款 |

**使用方式**：不需要写任何集成代码。安装 Server（`npm install` 或 `pip install`），配置到客户端的 `mcp.json`，直接可用。

```json
// Claude Desktop 的 mcp.json 配置
{
    "mcpServers": {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
            }
        },
        "postgres": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/db"]
        }
    }
}
```

## MCP 的工程实践

生产环境的 MCP 不是那 12 行 Demo。从 Anthropic 和社区的最佳实践看，一个生产级 MCP Server 需要：

### 1. 认证与授权

本地 Server 依赖进程隔离，但远程 Server 必须做 OAuth 2.1。2025-06 规范加入的远程传输支持，是企业部署的前提。

### 2. 输入验证

Demo 中的 type hint 不等于安全。生产 Server 需要：
- 参数范围校验（如 `limit` 不能超过 1000）
- SQL 注入防护（数据库 Server 必须参数化查询）
- 权限检查（GitHub Server 不能让用户访问别人的私有仓库）

### 3. 错误处理

工具调用失败时，返回结构化的错误信息，让模型能据此判断"出了什么错"并调整下一次调用的参数。

```python
@mcp.tool()
def query_database(sql: str) -> str:
    try:
        result = db.execute(sql)
        return json.dumps(result)
    except DatabaseError as e:
        # 返回结构化错误，模型能据此修正查询
        return f"[ERROR] 数据库查询失败：{e.message}. 请检查表名和列名是否正确。"
```

### 4. 网关层（Gateway）

企业部署时，直接在 Host 和 Server 之间直连缺少集中管控。Gateway 层负责：
- **审计**：记录每个工具调用的输入输出
- **策略**：哪些工具可以调用、哪些参数被禁止
- **限流**：防止单个用户耗尽 Server 配额
- **安全扫描**：检查工具输入中是否包含提示注入攻击

## 2026 年 MCP 生态现状

| 指标 | 数据（2026年中） |
|------|----------------|
| 有效 Server | 8,060（注册表 16,950 条中去重后的有效项目，仅 40.9% 在 90 天内有更新） |
| 月 SDK 下载 | 约 9,700 万 |
| 支持的客户端 | Claude、ChatGPT、Cursor、Gemini、VS Code、Zed、Windsurf 等 |
| 协议版本 | 2025-11（Linux 基金会捐赠版） |
| 官方 SDK | Python、TypeScript |

> 数据来源：[A Measurement Study of Model Context Protocol](https://arxiv.org/abs/2509.25292)（arXiv:2509.25292），覆盖 6 个 MCP 注册表。

**一个值得注意的现象**：52% 的注册 Server 是"死亡状态"——只做了 12 行 Demo，没加认证、没做错误处理、没维护。这和 npm 包的生态类似：数量多，但生产可用的少。选择 Server 时，优先看官方维护的（Anthropic、OpenAI、社区核心团队）或 Star 数高的。

**MCP 与 Function Calling 的关系**：2026 年的主流架构是**两者共存**。LLM 底层仍然用 Function Calling（或 Tool Use）做运行时决策，MCP 是跨 LLM 的协议层。你写了一个 MCP Server，Claude 用它的 Tool Use 调用，GPT 用它的 Function Calling 调用，Gemini 用它的 Function Calling 调用——但你的 Server 代码只写一次。

## 总结

- **MCP 解决 N×M 问题**：写一次 Server，任何兼容客户端都能用。N+M 套代码替代 N×M 套适配。
- **三大原语**：Tools（可调用）、Resources（只读数据）、Prompts（模板）。不是只有工具调用。
- **Sampling 和 Roots 是关键设计**：Server 可以请求 Client 代调用 LLM，且只能访问用户授权的资源。
- **生产 Server 不等于 Demo**：需要认证、输入验证、错误处理、网关层。52% 的社区 Server 是死亡状态。
- **2026 年 MCP 是事实标准**：Claude、ChatGPT、Cursor、Gemini、VS Code 都原生支持，注册表有效 Server 超过 8,000 个。

> 掌握了工具调用，你的 Agent 已经能查数据、调 API、操作外部系统。但 Agent 怎么知道"什么时候该做什么事"？怎么自主规划多步任务？请继续阅读 [05 — Agent 循环](../05-agent-loop/README.md)，了解 Agent 的核心架构。

## 参考链接

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Servers Registry](https://github.com/modelcontextprotocol/servers)
- [Anthropic MCP Introduction](https://www.anthropic.com/news/model-context-protocol)
- [A Measurement Study of Model Context Protocol (arXiv:2509.25292)](https://arxiv.org/abs/2509.25292)
- [OpenAI Agents SDK MCP Support](https://github.com/openai/openai-agents-python)
- [Linux Foundation Agentic AI Foundation](https://www.linuxfoundation.org/press/press-release/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
