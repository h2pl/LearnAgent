# MCP 集成：Claude Code 如何连接外部工具生态

> MCP（Model Context Protocol）不是 Claude Code 独有的扩展方式，而是 Anthropic 推出的**开放标准**。它定义了一套通用的协议，让任何遵循协议的 Server 都可以接入任何 MCP Client。Claude Code 是 MCP Client 的一个实现——它通过 MCP 连接文件系统、数据库、GitHub、浏览器等外部工具，把"一个编程助手"变成"一个可以操作整个数字世界的入口"。

你好，我是江小湖。

上一篇 [Skill 系统](./02-skills.md) 讲到 Skill 是 Claude Code 内部的"可复用工作流"。但 Skill 只能组合 Claude Code 已有的工具——如果用户需要连接外部服务（如 GitHub、Jira、Slack），Skill 做不到。这时候就需要 **MCP**。

MCP 的核心思想是：**不要让每个 LLM 应用都重新发明工具连接**。与其让 Claude Code、Cursor、Zed 各自实现一套 GitHub 集成，不如定义一个标准协议，GitHub 实现一次，所有应用都能用。

## 目录

- [MCP 的协议设计](#mcp-的协议设计)
- [Client-Server 架构](#client-server-架构)
- [工具发现与动态加载](#工具发现与动态加载)
- [Claude Code 的 MCP 集成](#claude-code-的-mcp-集成)
- [配置管理与多 Server 调度](#配置管理与多-server-调度)
- [MCP 的局限与替代方案](#mcp-的局限与替代方案)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/11-extensibility/mcp-architecture.svg" alt="MCP 协议" width="90%"/>
  <br/>
  <em>Client-Server 双向通信</em>
</p>

<p align="center">
  <img src="../../../../assets/cc-source-analysis/11-extensibility/extension-types.svg" alt="四种扩展对比" width="90%"/>
  <br/>
  <em>Hook → Skill → Plugin → MCP</em>
</p>


## MCP 的协议设计

MCP 是一个基于 **JSON-RPC 2.0** 的协议，通信方式支持 stdio、HTTP 和 Server-Sent Events (SSE)。协议定义了三种核心原语：

| 原语 | 说明 | 示例 |
|------|------|------|
| **Tools** | 可执行的操作 | `read_file`、`query_database`、`create_issue` |
| **Resources** | 可读的数据源 | `file://`、`db://`、`api://` |
| **Prompts** | 可复用的提示词模板 | "代码审查清单"、"Bug 报告模板" |

**协议分层**：

```
应用层（Claude Code / Cursor / Zed）
        |
        | MCP Client SDK
        |
传输层（stdio / HTTP / SSE）
        |
        | JSON-RPC 2.0
        |
服务层（MCP Server）
        |
        | 具体实现（文件系统、数据库、API）
```

**为什么选择 JSON-RPC 2.0**：
- **简单**：比 gRPC 简单，比 REST 更结构化
- **双向**：支持 Server 向 Client 推送通知（如资源变更）
- **已有生态**：很多语言和框架都支持 JSON-RPC

**通信方式的选择**：

| 方式 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| **stdio** | 本地 Server | 零配置，进程内通信 | 只能本地 |
| **HTTP** | 远程 Server | 跨网络，可负载均衡 | 需要配置 URL |
| **SSE** | 实时推送 | Server 主动推送更新 | 单向（Client 不能通过 SSE 发送请求） |

Claude Code 主要使用 **stdio** 方式——因为大部分 MCP Server 是本地工具（如文件系统、数据库）。

## Client-Server 架构

MCP 的架构是经典的 Client-Server 模式，但有两个特点：

1. **Client 是 LLM 应用**（Claude Code），不是用户浏览器
2. **Server 是工具提供者**（文件系统、数据库、API），不是 Web 服务器

```typescript
// MCP Client 接口（简化版）
interface MCPClient {
  // 连接 Server
  connect(serverConfig: ServerConfig): Promise<void>;
  
  // 发现工具
  listTools(): Promise<ToolDefinition[]>;
  
  // 调用工具
  callTool(name: string, args: unknown): Promise<ToolResult>;
  
  // 发现资源
  listResources(): Promise<ResourceDefinition[]>;
  
  // 读取资源
  readResource(uri: string): Promise<Resource>;
  
  // 发现提示词
  listPrompts(): Promise<PromptDefinition[]>;
  
  // 获取提示词
  getPrompt(name: string, args?: unknown): Promise<Prompt>;
  
  // 断开连接
  disconnect(): Promise<void>;
}

// MCP Server 接口（简化版）
interface MCPServer {
  // 初始化
  initialize(): Promise<ServerCapabilities>;
  
  // 处理工具调用
  handleCallTool(name: string, args: unknown): Promise<ToolResult>;
  
  // 处理资源读取
  handleReadResource(uri: string): Promise<Resource>;
  
  // 处理提示词获取
  handleGetPrompt(name: string, args?: unknown): Promise<Prompt>;
}
```

**MCP Server 的示例**：文件系统 Server

```typescript
// 文件系统 MCP Server（简化版）
class FilesystemServer implements MCPServer {
  async initialize(): Promise<ServerCapabilities> {
    return {
      tools: [
        {
          name: 'read_file',
          description: '读取文件内容',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string', description: '文件路径' },
            },
            required: ['path'],
          },
        },
        {
          name: 'write_file',
          description: '写入文件内容',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string' },
              content: { type: 'string' },
            },
            required: ['path', 'content'],
          },
        },
        {
          name: 'list_directory',
          description: '列出目录内容',
          inputSchema: {
            type: 'object',
            properties: {
              path: { type: 'string' },
            },
            required: ['path'],
          },
        },
      ],
      resources: [
        {
          uri: 'file://',
          name: '本地文件系统',
          mimeType: 'application/octet-stream',
        },
      ],
    };
  }
  
  async handleCallTool(name: string, args: unknown): Promise<ToolResult> {
    switch (name) {
      case 'read_file':
        const { path } = args as { path: string };
        const content = await fs.readFile(path, 'utf-8');
        return { content: [{ type: 'text', text: content }] };
      
      case 'write_file':
        const { path: writePath, content: writeContent } = args as { path: string; content: string };
        await fs.writeFile(writePath, writeContent, 'utf-8');
        return { content: [{ type: 'text', text: 'File written successfully' }] };
      
      case 'list_directory':
        const { path: dirPath } = args as { path: string };
        const entries = await fs.readdir(dirPath, { withFileTypes: true });
        return { content: [{ type: 'text', text: entries.map(e => e.name).join('\n') }] };
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  }
}
```

**Server 的启动方式**：

```bash
# 文件系统 Server（通过 npx 启动）
npx -y @modelcontextprotocol/server-filesystem /home/user/projects

# 数据库 Server（通过 uvx 启动）
uvx -y mcp-server-sqlite --db-path /path/to/data.db

# GitHub Server（需要环境变量）
env GITHUB_PERSONAL_ACCESS_TOKEN=xxx npx -y @modelcontextprotocol/server-github
```

Server 启动后，通过 stdio 与 Client 通信。Client 发送 JSON-RPC 请求，Server 返回 JSON-RPC 响应。

## 工具发现与动态加载

MCP 的核心价值之一是**动态发现**——Claude Code 不需要预先知道 Server 提供什么工具，而是在连接时动态获取：

```typescript
// 工具发现与动态加载（简化版）
class MCPClientImpl implements MCPClient {
  private servers = new Map<string, ServerConnection>();
  private toolRegistry = new Map<string, ToolRegistration>();
  
  async connect(name: string, config: ServerConfig): Promise<void> {
    // 1. 启动 Server 进程
    const process = spawn(config.command, config.args, {
      env: { ...process.env, ...config.env },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    
    // 2. 建立 JSON-RPC 连接
    const rpc = new JSONRPCConnection(process.stdin, process.stdout);
    
    // 3. 发送初始化请求
    const capabilities = await rpc.sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: { tools: {}, resources: {}, prompts: {} },
    });
    
    // 4. 发现工具
    const tools = await rpc.sendRequest('tools/list', {});
    for (const tool of tools.tools) {
      this.toolRegistry.set(tool.name, {
        server: name,
        definition: tool,
      });
    }
    
    // 5. 发送 initialized 通知
    await rpc.sendNotification('initialized', {});
    
    this.servers.set(name, { process, rpc, capabilities });
  }
  
  async callTool(name: string, args: unknown): Promise<ToolResult> {
    const registration = this.toolRegistry.get(name);
    if (!registration) {
      throw new Error(`Unknown tool: ${name}`);
    }
    
    const server = this.servers.get(registration.server);
    if (!server) {
      throw new Error(`Server ${registration.server} not connected`);
    }
    
    return await server.rpc.sendRequest('tools/call', {
      name,
      arguments: args,
    });
  }
}
```

**动态发现的意义**：

1. **零配置扩展**：Claude Code 不需要为每个 MCP Server 写适配代码。只要 Server 遵循协议，Claude Code 自动发现和使用它的工具。

2. **热插拔**：可以在会话中动态连接新的 MCP Server，不需要重启 Claude Code。

3. **工具去重**：如果多个 Server 提供同名工具，Claude Code 可以通过命名空间区分（如 `filesystem/read_file` vs `github/read_file`）。

**工具命名空间**：

```typescript
// 工具命名空间（简化版）
function resolveToolName(
  serverName: string,
  toolName: string
): string {
  // 如果工具名已包含命名空间，直接使用
  if (toolName.includes('/')) return toolName;
  
  // 否则，添加 Server 名称作为前缀
  return `${serverName}/${toolName}`;
}

// 示例
resolveToolName('filesystem', 'read_file'); // → "filesystem/read_file"
resolveToolName('github', 'create_issue');  // → "github/create_issue"
resolveToolName('github', 'github/read_file'); // → "github/read_file"（已包含命名空间）
```

命名空间防止了不同 Server 的工具名冲突。用户可以通过完整名称调用特定 Server 的工具。

## Claude Code 的 MCP 集成

Claude Code 不是"支持 MCP"这么简单，而是深度集成了 MCP 的三种原语：

### 1. Tools 集成

MCP Tools 被映射到 Claude Code 的工具系统：

```typescript
// MCP Tools 映射（简化版）
async function registerMCPTools(client: MCPClient): Promise<void> {
  const tools = await client.listTools();
  
  for (const toolDef of tools) {
    // 创建 Tool 包装器
    const tool = buildTool({
      name: `mcp/${client.serverName}/${toolDef.name}`,
      description: toolDef.description,
      parameters: toolDef.inputSchema,
      handler: async (args: unknown) => {
        return await client.callTool(toolDef.name, args);
      },
    });
    
    // 注册到 Claude Code 的工具系统
    registerTool(tool);
  }
}
```

**映射后的效果**：
- MCP Server 的 `read_file` 工具变成了 Claude Code 的 `mcp/filesystem/read_file` 工具
- 模型在生成工具调用时，可以直接调用这个工具
- 工具的执行结果被注入到对话上下文中，与内置工具完全一致

### 2. Resources 集成

MCP Resources 被映射到 Claude Code 的上下文系统：

```typescript
// MCP Resources 映射（简化版）
async function injectMCPResources(
  client: MCPClient,
  context: MessageContext
): Promise<void> {
  const resources = await client.listResources();
  
  for (const resource of resources) {
    // 读取资源内容
    const content = await client.readResource(resource.uri);
    
    // 注入到系统提示词中
    context.addSystemMessage({
      role: 'system',
      content: `Resource: ${resource.name}\n${content}`,
    });
  }
}
```

**Resources 的典型用法**：
- **文件系统资源**：把项目目录结构注入上下文，让模型知道代码库的组织
- **数据库资源**：把数据库 Schema 注入上下文，让模型知道表结构
- **API 资源**：把 API 文档注入上下文，让模型知道接口定义

### 3. Prompts 集成

MCP Prompts 被映射到 Claude Code 的提示词系统：

```typescript
// MCP Prompts 映射（简化版）
async function registerMCPPrompts(client: MCPClient): Promise<void> {
  const prompts = await client.listPrompts();
  
  for (const prompt of prompts) {
    // 注册为 Claude Code 的预定义提示词
    registerPromptTemplate({
      name: `mcp/${client.serverName}/${prompt.name}`,
      template: async (args?: unknown) => {
        return await client.getPrompt(prompt.name, args);
      },
    });
  }
}
```

**Prompts 的典型用法**：
- **代码审查清单**：MCP Server 提供标准的审查提示词模板
- **Bug 报告模板**：MCP Server 提供 Bug 描述的格式模板
- **API 调用模板**：MCP Server 提供调用特定 API 的提示词模板

## 配置管理与多 Server 调度

Claude Code 通过配置文件管理 MCP Server：

```json
// .claude/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"],
      "env": {},
      "disabled": false,
      "timeout": 30000
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${env.GITHUB_TOKEN}"
      },
      "disabled": false,
      "timeout": 10000
    },
    "sqlite": {
      "command": "uvx",
      "args": ["-y", "mcp-server-sqlite", "--db-path", "/path/to/data.db"],
      "env": {},
      "disabled": true
    }
  }
}
```

**配置项**：

| 项 | 说明 | 必填 |
|----|------|------|
| `command` | 启动命令 | 是 |
| `args` | 命令参数 | 是 |
| `env` | 环境变量 | 否 |
| `disabled` | 是否禁用 | 否（默认 false） |
| `timeout` | 调用超时（ms） | 否（默认 30000） |

**环境变量替换**：`env` 中的值支持 `${env.VAR_NAME}` 语法，从系统环境变量读取。这避免了在配置文件中硬编码敏感信息（如 API token）。

**多 Server 调度**：当多个 MCP Server 提供同名工具时，Claude Code 的调度策略：

```typescript
// 多 Server 工具调度（简化版）
async function resolveToolCall(
  toolName: string,
  args: unknown
): Promise<ToolResult> {
  // 1. 检查是否包含命名空间
  if (toolName.includes('/')) {
    const [serverName, actualToolName] = toolName.split('/', 2);
    const server = mcpClient.getServer(serverName);
    return await server.callTool(actualToolName, args);
  }
  
  // 2. 没有命名空间，查找所有 Server
  const candidates = mcpClient.findServersWithTool(toolName);
  
  if (candidates.length === 0) {
    throw new Error(`No MCP server provides tool: ${toolName}`);
  }
  
  if (candidates.length === 1) {
    return await candidates[0].callTool(toolName, args);
  }
  
  // 3. 多个 Server 提供同名工具，选择优先级最高的
  const selected = candidates.sort((a, b) => b.priority - a.priority)[0];
  return await selected.callTool(toolName, args);
}
```

**调度策略**：
1. **显式命名空间**：如果工具名包含命名空间（如 `filesystem/read_file`），直接路由到对应 Server。
2. **唯一匹配**：如果只有一个 Server 提供该工具，直接使用。
3. **优先级选择**：如果多个 Server 提供同名工具，按优先级选择。项目级 Server 优先级高于用户级，用户级高于内置级。

## MCP 的局限与替代方案

MCP 不是银弹，它有明确的局限：

| 局限 | 说明 | 替代方案 |
|------|------|----------|
| **启动延迟** | 每个 Server 是独立进程，启动需要 1-3 秒 | 长连接复用，或使用 Plugin 替代 |
| **通信开销** | stdio/HTTP 通信有序列化开销 | 使用本地 Hook 或 Skill 替代 |
| **单点故障** | 某个 Server 崩溃不影响其他，但会影响对应工具 | 健康检查 + 自动重连 |
| **协议限制** | 只支持 Tools/Resources/Prompts 三种原语 | 使用 Plugin 实现更复杂的交互 |
| **版本兼容** | Server 和 Client 的协议版本必须兼容 | 版本协商机制 |

**MCP vs Plugin 的选型**：

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 连接外部 API（GitHub、Slack） | MCP | 标准化，可复用 |
| 本地工具集成（文件系统、数据库） | MCP | 已有现成 Server |
| 复杂 UI 扩展 | Plugin | MCP 不支持 UI |
| 高性能要求（毫秒级响应） | Hook/Skill | MCP 有通信开销 |
| 需要自定义协议 | Plugin | MCP 协议限制 |

**MCP 的未来**：MCP 还在快速发展中，未来可能增加：
- **Streaming**：支持流式响应（如长文本生成）
- **Authentication**：内置认证机制（OAuth、API Key）
- **Batching**：支持批量调用，减少通信开销
- **Subscribing**：支持资源变更订阅（Server 主动推送更新）

## 总结

- MCP 是**开放标准协议**，基于 JSON-RPC 2.0，支持 stdio/HTTP/SSE 三种通信方式。
- 三种核心原语：**Tools**（可执行操作）、**Resources**（可读数据源）、**Prompts**（可复用提示词）。
- **动态发现**是 MCP 的核心价值——Claude Code 不需要预先写适配代码，连接时自动发现工具。
- **命名空间**防止工具名冲突，**多 Server 调度**按优先级选择同名工具。
- **深度集成**：MCP Tools 映射到工具系统、Resources 映射到上下文、Prompts 映射到提示词系统。
- **配置管理**通过 `.claude/mcp.json`，支持环境变量替换、超时设置、禁用开关。
- MCP 不是银弹，有启动延迟、通信开销、协议限制等局限，复杂场景用 Plugin 替代。

> 学完本章后，请继续阅读 [12 — 会话持久化](../12-session-persistence/README.md)，看长任务如何断点续传。

## 参考链接

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP 协议规范](https://spec.modelcontextprotocol.io/)
- [Claude Code MCP 集成源码](file:///E:/Projects/claude-code/src/mcp/)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
