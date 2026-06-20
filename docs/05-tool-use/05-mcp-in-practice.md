# MCP 实战全流程

> 前一篇介绍了 MCP 的概念和生态，本文动手：从装 SDK、写 Server、测 Inspector、配客户端到远程部署，一条龙走完 MCP 开发全流程。

## 目录

- [前置阅读](#前置阅读)
- [环境准备](#环境准备)
- [第一步：脚手架——最小 MCP Server](#第一步脚手架最小-mcp-server)
- [第二步：测试——MCP Inspector 调试](#第二步测试mcp-inspector-调试)
- [第三步：集成——配置到客户端](#第三步集成配置到客户端)
- [第四步：进阶——完整的生产级 Server](#第四步进阶完整的生产级-server)
- [第五步：远程部署——Streamable HTTP 模式](#第五步远程部署streamable-http-模式)
- [完整案例：GitHub Issue 管理器](#完整案例github-issue-管理器)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [MCP 与工具生态](./04-mcp-and-tool-ecosystem.md) 中，你了解了 MCP 的架构（Host/Client/Server/Gateway）和三大原语（Tools/Resources/Prompts）。但只看概念是学不会的——本文带你动手从零搭建一个完整的 MCP Server，经过调试、本地配置、远程部署，再到一个生产级的真实案例。

本文使用 **MCP Python SDK**（Linux Foundation 维护的官方 SDK，2025-11 规范版）。

## 前置阅读

本文假设你已经了解 MCP 的基础概念：Host/Client/Server 四层架构、三大原语（Tools/Resources/Prompts）、JSON-RPC 2.0 传输。如果还没读过，先看 [MCP 与工具生态](./04-mcp-and-tool-ecosystem.md) 前四节。

## 环境准备

MCP SDK 支持通过 pip 安装，Python 3.10+ 即可：

```bash
pip install mcp  # 官方 MCP Python SDK
```

验证安装：

```python
from mcp.server.fastmcp import FastMCP
print("FastMCP 可用")   # 只用这行验证 SDK 就绪
```

## 第一步：脚手架——最小 MCP Server

以下代码创建一个 16 行的 MCP Server，暴露一个工具和一个资源：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-first-server")

@mcp.tool()
def add(a: int, b: int) -> int:
    """两数相加。"""
    return a + b

@mcp.resource("hello://world")
def hello_resource() -> str:
    """返回问候语。"""
    return "Hello, MCP!"

if __name__ == "__main__":
    mcp.run()
```

保存为 `server.py`，运行：

```bash
python server.py
```

你会在终端看到输出：`MCP server running with stdio transport`。这意味着 Server 已在 STDIO 模式下运行。STDIO 模式是本地开发的标准方式——Server 作为客户端子进程启动，通过标准输入输出通信。

这个模式对命令行不友好，但从客户端的角度看完全无感。

## 第二步：测试——MCP Inspector 调试

MCP 官方提供了一个图形化调试工具 —— **MCP Inspector**。它可以通过 npx 直接运行，不需要安装：

```bash
npx @modelcontextprotocol/inspector python server.py
```

打开浏览器访问 `http://localhost:5173`，你会看到一个交互式调试界面：

<p align="center">
  <img src="../../assets/05-tool-use/mcp-inspector.svg" alt="MCP Inspector 调试界面：工具/资源/提示的交互式测试" width="95%"/>
</p>

Inspector 的核心功能：

- **Tools 面板**：列出所有工具，填写参数，点击调用，查看 JSON-RPC 请求/响应全文
- **Resources 面板**：列出所有资源 URI，点击读取，查看返回数据
- **Prompts 面板**：列出所有提示模板，查看参数和内容
- **请求日志**：每次调用的 JSON-RPC 原始报文，用于调试协议问题

你可以在 Inspector 中点击 `add` 工具，填入 `a=3, b=5`，点击调用，立即看到返回 `8`。

## 第三步：集成——配置到客户端

### Claude Desktop

在 Claude Desktop 的配置文件中添加：

```json
{
  "mcpServers": {
    "my-first-server": {
      "command": "python",
      "args": ["C:/path/to/server.py"]
    }
  }
}
```

配置文件位置：macOS 在 `~/Library/Application Support/Claude/claude_desktop_config.json`，Windows 在 `%APPDATA%\Claude\claude_desktop_config.json`。

重启 Claude Desktop，你可以问："帮我算一下 12345 + 67890"，Claude 会调用你的 `add` 工具并返回结果。

### Cursor

Cursor 的 MCP 配置在项目级 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "my-first-server": {
      "command": "python",
      "args": ["C:/path/to/server.py"]
    }
  }
}
```

### VS Code

VS Code 在 2026 年初原生支持 MCP，配置方式相同，位置在 `.vscode/mcp.json`。

## 第四步：进阶——完整的生产级 Server

Demo 够了。一个生产级 MCP Server 需要什么？

### 1. 输入验证

```python
from pydantic import BaseModel, Field

class QueryParams(BaseModel):
    sql: str = Field(..., max_length=500, description="SQL 查询语句")
    limit: int = Field(default=100, ge=1, le=10000, description="最大返回行数")

@mcp.tool()
def query_database(params: QueryParams) -> str:
    """执行数据库查询。"""
    if "drop" in params.sql.lower() or "delete" in params.sql.lower():
        raise ValueError("不允许执行修改操作")
    return execute_safe_query(params.sql, params.limit)
```

`pydantic` 帮你在参数到达处理函数之前完成类型校验和范围检查。

### 2. 结构化错误返回

```python
@mcp.tool()
def fetch_user(user_id: int) -> dict:
    """根据用户 ID 获取用户信息。"""
    user = db.get_user(user_id)
    if not user:
        # 返回结构化错误，模型能据此修正下一次调用
        return {"error": "用户不存在", "code": "NOT_FOUND", "suggestion": f"请检查用户 ID 是否正确，有效范围 1-{db.max_id()}"}
    return user
```

**关键**：返回结构化错误信息，而不是抛异常。模型接到异常不知道"出了什么错"，但接受到结构化的错误对象，它能判断下一步怎么做。

### 3. 自动提示（Prompts）

Prompts 是 MCP 中最被低估的原语。它可以让用户在客户端中一键执行预设任务：

```python
@mcp.prompt()
def analyze_sales(year: int, month: int) -> str:
    """销售分析提示模板。"""
    return f"请分析 {year} 年 {month} 月的销售数据，重点关注：\n1. 各产品线收入\n2. 环比增长\n3. 异常订单"

@mcp.prompt()
def debug_error(error_code: str) -> str:
    """错误排查提示模板。"""
    return f"系统返回了错误代码 {error_code}，请逐步排查：\n1. 查看相关日志\n2. 检查配置\n3. 提出修复方案"
```

### 4. 生命周期钩子

```python
@mcp.on_startup
def startup():
    print("Server 启动，初始化数据库连接")
    db.connect()

@mcp.on_shutdown
def shutdown():
    print("Server 关闭，释放资源")
    db.disconnect()
```

## 第五步：远程部署——Streamable HTTP 模式

本地 STDIO 模式只能在单机上用。要让 MCP Server 作为远程服务运行，需要用 **Streamable HTTP 传输**（2025-03 规范引入）。

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("remote-server")

@mcp.tool()
def search_docs(query: str) -> str:
    """搜索文档。"""
    return f"关于「{query}」的结果..."

# 以 HTTP 模式启动
if __name__ == "__main__":
    mcp.run(transport="sse")  # SSE 模式启动
```

启动后，用类似 uvicorn 的方式运行（FastMCP 底层使用 Starlette）：

```bash
python remote_server.py --transport sse --host 0.0.0.0 --port 8000
```

现在 Server 监听在 `http://0.0.0.0:8000/sse`，任何 MCP 客户端都可以通过 HTTP 连接它。

配置到远程客户端时（例如 Claude Desktop 连远程 Server），使用 Streamable HTTP 配置：

```json
{
  "mcpServers": {
    "remote-server": {
      "url": "http://your-server.com:8000/sse"
    }
  }
}
```

### 远程部署注意事项

**认证**：远程 Server 必须配置认证。推荐 OAuth 2.1（2025-06 规范支持）：

```python
from mcp.server.auth import OAuthMiddleware

app = OAuthMiddleware(
    app=mcp.app,
    token_url="https://auth.example.com/token",
    client_id="mcp-server-1"
)
```

**HTTPS**：生产环境必须用 HTTPS，避免中间人攻击。可以用 Nginx 反向代理 + Let's Encrypt，或者用 Cloudflare Tunnel。

**健康检查**：暴露 `/health` 端点给 Gateway 或负载均衡器轮询。

## 完整案例：GitHub Issue 管理器

以下是一个完整的 MCP Server，提供 GitHub Issue 的增删查改能力。它展示了生产 Server 应有的组织方式。

```python
# github_issue_server.py
import os
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("github-issue-manager")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"

# ──────── 工具 - 查询 Issue ────────

class SearchParams(BaseModel):
    repo: str = Field(..., description="仓库名，格式 owner/repo")
    query: str = Field(default="", description="搜索关键词")
    state: str = Field(default="open", pattern="^(open|closed|all)$")

@mcp.tool()
def search_issues(params: SearchParams) -> str:
    """在指定仓库中搜索 Issues。"""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    url = f"{GITHUB_API}/repos/{params.repo}/issues"
    resp = httpx.get(url, headers=headers, params={
        "q": params.query, "state": params.state
    })
    if resp.status_code != 200:
        return f"[ERROR] 查询失败：{resp.json().get('message', '未知错误')}。请检查仓库名和 Token。"
    issues = resp.json()
    return "\n".join(
        f"- #{i['number']} {i['title']} ({i['state']})"
        for i in issues[:10]
    )

# ──────── 工具 - 创建 Issue ────────

class CreateParams(BaseModel):
    repo: str = Field(..., description="仓库名，格式 owner/repo")
    title: str = Field(..., max_length=256)
    body: str = Field(default="", description="Issue 正文")

@mcp.tool()
def create_issue(params: CreateParams) -> str:
    """在指定仓库中创建一个新 Issue。"""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    url = f"{GITHUB_API}/repos/{params.repo}/issues"
    resp = httpx.post(url, headers=headers, json={
        "title": params.title, "body": params.body
    })
    if resp.status_code == 201:
        data = resp.json()
        return f"Issue #{data['number']} 创建成功：{data['html_url']}"
    return f"[ERROR] 创建失败：{resp.json().get('message', '未知错误')}"

# ──────── 资源 - 当前配置状态 ────────

@mcp.resource("config://status")
def config_status() -> str:
    """返回当前 Server 配置状态。"""
    repos = os.environ.get("ALLOWED_REPOS", "h2pl/*")
    return f"Token 状态：{'已配置' if GITHUB_TOKEN else '未配置'}\n允许的仓库：{repos}"

# ──────── 提示模板 ────────

@mcp.prompt()
def bug_report_template() -> str:
    """提交 Bug Issue 的模板。"""
    return """请协助创建一个 Bug Issue：

## Bug 描述
（描述问题现象）

## 复现步骤
1.
2.
3.

## 期望行为
（描述应该是什么结果）

## 实际行为
（描述实际是什么结果）

## 环境
- OS：
- 版本："""

# ──────── 启动 ────────

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("警告：未设置 GITHUB_TOKEN 环境变量")
    mcp.run()
```

使用方式：

```bash
# 本地运行
export GITHUB_TOKEN=ghp_xxx
python github_issue_server.py
```

通过 MCP Inspector 测试后，配置到 Claude Desktop：

```json
{
  "mcpServers": {
    "github-issue": {
      "command": "python",
      "args": ["C:/path/to/github_issue_server.py"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx",
        "ALLOWED_REPOS": "h2pl/*"
      }
    }
  }
}
```

现在你可以在 Claude Desktop 中对 Claude 说："帮我查一下 h2pl/AgentDevGuide 仓库中标签为 bug 的 open issue"，Claude 会调用 `search_issues` 工具，实时查询 GitHub API 返回结果。

<p align="center">
  <img src="../../assets/05-tool-use/mcp-deployment-flow.svg" alt="MCP部署全流程：脚手架→测试→集成→增强→远程部署，五步走通" width="95%"/>
</p>

## 总结

- **MCP 实战五步走**：脚手架 → Inspector 测试 → 客户端集成 → 生产级增强 → 远程部署
- **FastMCP 让开发极其简单**：装饰器模式定义 Tools/Resources/Prompts，16 行跑起来
- **生产 Server 的关键**：pydantic 输入验证、结构化错误返回、生命周期钩子、认证
- **远程部署用 Streamable HTTP**：`mcp.run(transport="sse")` 一行切换，但需要 HTTPS + 认证
- **GitHub Issue 管理器是真实模板**：一个 80 行的 Server 覆盖了完整的工作流

> 恭喜你，工具调用全部掌握。接下来，Agent 怎么知道"什么时候该做什么事"？怎么自主规划多步任务？请继续阅读 [05 — Agent 循环](../06-agent-loop/README.md)，了解 Agent 的核心架构。

## 参考链接

- [MCP Python SDK — FastMCP 文档](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Inspector — 调试工具](https://github.com/modelcontextprotocol/inspector)
- [MCP Specification — Streamable HTTP](https://spec.modelcontextprotocol.io/)
- [FastMCP Examples — GitHub](https://github.com/jlowin/fastmcp)
- [Claude Desktop — MCP 配置](https://docs.anthropic.com/en/docs/claude-dektop/mcp)
- [Cursor — MCP 集成](https://docs.cursor.com/context/model-context-protocol)
