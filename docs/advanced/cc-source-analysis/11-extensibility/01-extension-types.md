# 四种扩展方式对比：Claude Code 如何从工具变成平台

> Claude Code 不是封闭系统。它提供了四种扩展方式——Hook、Skill、Plugin、MCP——每种有不同的成本和适用场景。这四种方式不是竞争关系，而是**成本梯度**：从改一行代码到接一套生态，总有一款适合你。

你好，我是江小湖。

上一章 [权限系统](../10-permissions/README.md) 讲到 Claude Code 如何把危险操作锁在笼子里。但一个只有笼子的系统太封闭了——要让 Claude Code 真正好用，它需要**扩展能力**。让开发者和用户在不修改核心代码的情况下，自定义行为、添加功能、连接外部工具。

Claude Code 提供了四种扩展方式，它们的成本从低到高排列：

| 扩展方式 | 开发成本 | 运行成本 | 隔离程度 | 适用场景 |
|----------|----------|----------|----------|----------|
| **Hook** | 最低 | 最低 | 无（共享进程） | 修改行为细节 |
| **Skill** | 低 | 低 | 无（共享进程） | 添加可复用工作流 |
| **Plugin** | 中 | 中 | 进程隔离 | 打包完整功能模块 |
| **MCP** | 高 | 高 | 网络隔离 | 连接外部工具生态 |

四种方式不是替代关系，而是**互补关系**。Hook 改细节，Skill 加工作流，Plugin 包功能，MCP 接生态。

## 目录

- [Hook：修改行为的钩子点](#hook修改行为的钩子点)
- [Skill：可复用的工作流](#skill可复用的工作流)
- [Plugin：打包的功能模块](#plugin打包的功能模块)
- [MCP：连接外部工具生态](#mcp连接外部工具生态)
- [四种方式的选型策略](#四种方式的选型策略)
- [扩展的加载机制](#扩展的加载机制)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/11-extensibility/extension-types.svg" alt="四种扩展对比" width="90%"/>
  <br/>
  <em>Hook → Skill → Plugin → MCP</em>
</p>

<p align="center">
  <img src="../../../../assets/cc-source-analysis/11-extensibility/mcp-architecture.svg" alt="MCP 协议" width="90%"/>
  <br/>
  <em>Client-Server 双向通信</em>
</p>


## Hook：修改行为的钩子点

Hook 是成本最低的扩展方式。它允许在 Claude Code 的特定执行点**注入自定义逻辑**——不需要创建新文件，不需要启动新进程，只需要声明一个钩子函数。

```typescript
// Hook 注册（简化版）
interface Hook {
  name: string;
  point: HookPoint;
  handler: HookHandler;
  priority: number; // 钩子优先级，多个钩子时的执行顺序
}

// Claude Code 内置的钩子点
enum HookPoint {
  PRE_TOOL_CALL = 'pre_tool_call',       // 工具调用前
  POST_TOOL_CALL = 'post_tool_call',     // 工具调用后
  PRE_MODEL_CALL = 'pre_model_call',     // 模型调用前
  POST_MODEL_CALL = 'post_model_call',   // 模型调用后
  PRE_COMPACT = 'pre_compact',           // 上下文压缩前
  POST_COMPACT = 'post_compact',         // 上下文压缩后
  SESSION_START = 'session_start',       // 会话开始时
  SESSION_END = 'session_end',           // 会话结束时
}

// 注册一个 Hook
function registerHook(hook: Hook): void {
  const hooks = getHooksForPoint(hook.point);
  hooks.push(hook);
  hooks.sort((a, b) => a.priority - b.priority); // 按优先级排序
}
```

**Hook 的特点**：

1. **零成本**：Hook 是函数级别的注入，没有额外的进程、网络或文件开销。

2. **同步执行**：Hook 在 Claude Code 的主线程同步执行，可以修改传入的参数或阻止操作。

3. **无隔离**：Hook 运行在 Claude Code 的进程中，共享内存和权限。这意味着 Hook 可以做任何事（包括危险操作），但也意味着 Hook 的 bug 会影响整个系统。

**典型用例**：

```typescript
// 用例 1：在工具调用前记录日志
registerHook({
  name: 'log_tool_calls',
  point: HookPoint.PRE_TOOL_CALL,
  priority: 100,
  handler: (tool, args) => {
    console.log(`[HOOK] Tool call: ${tool.name}(${JSON.stringify(args)})`);
    return { modified: false }; // 不修改，只记录
  },
});

// 用例 2：在上下文压缩前添加自定义压缩规则
registerHook({
  name: 'custom_compact_rule',
  point: HookPoint.PRE_COMPACT,
  priority: 50,
  handler: (context) => {
    // 保留所有包含 "TODO" 的消息，不压缩
    const protectedMessages = context.messages.filter(m => 
      m.content.includes('TODO')
    );
    return { modified: true, protectedMessages };
  },
});

// 用例 3：在会话开始时加载自定义配置
registerHook({
  name: 'load_custom_config',
  point: HookPoint.SESSION_START,
  priority: 10,
  handler: (session) => {
    const customConfig = loadConfig('.claude/custom.json');
    session.mergeConfig(customConfig);
    return { modified: true };
  },
});
```

**Hook 的局限性**：
- 只能修改已有的钩子点，不能新增钩子点
- 无隔离，Hook 的 bug 会影响整个系统
- 不适合添加复杂的独立功能

## Skill：可复用的工作流

Skill 是 Claude Code 的**官方推荐扩展方式**。它是一个声明式的、可复用的工作流定义，描述了"如何完成一类任务"。

```typescript
// Skill 定义（简化版）
interface Skill {
  name: string;           // Skill 名称，如 "react-component"
  version: string;        // 语义化版本
  description: string;    // 描述
  
  // 触发条件
  triggers: SkillTrigger[];
  
  // 工作流定义
  workflow: WorkflowStep[];
  
  // 工具列表（这个 Skill 需要的工具）
  tools: string[];
  
  // 提示词模板
  promptTemplates: Record<string, string>;
}

interface SkillTrigger {
  type: 'command' | 'pattern' | 'intent';
  value: string;
}

interface WorkflowStep {
  id: string;
  action: 'read' | 'write' | 'execute' | 'ask' | 'call';
  target?: string;        // 操作目标
  condition?: string;     // 执行条件
  next?: string[];        // 下一步
}
```

**Skill 的声明式定义**：

```yaml
# skill.yaml: React 组件开发 Skill
name: react-component
version: 1.0.0
description: 标准化的 React 组件开发流程

triggers:
  - type: command
    value: "/react-component"
  - type: pattern
    value: "创建.*React.*组件"

workflow:
  - id: check-project
    action: read
    target: "package.json"
    next: [check-typescript]
  
  - id: check-typescript
    action: read
    target: "tsconfig.json"
    condition: "file.exists"
    next: [create-component]
  
  - id: create-component
    action: write
    target: "src/components/{name}.tsx"
    next: [create-styles]
  
  - id: create-styles
    action: write
    target: "src/components/{name}.module.css"
    next: [create-test]
  
  - id: create-test
    action: write
    target: "src/components/{name}.test.tsx"
    next: [update-index]
  
  - id: update-index
    action: read
    target: "src/components/index.ts"
    next: []

tools:
  - read_file
  - edit_file
  - create_file

promptTemplates:
  component: |
    创建 React 组件 {name}，遵循以下规范：
    - 使用 TypeScript
    - 使用 CSS Modules
    - 包含基本测试
    - 导出默认组件
```

**Skill 的特点**：

1. **声明式**：Skill 描述"做什么"，而不是"怎么做"。具体执行由 Claude Code 的引擎处理。

2. **可复用**：一个 Skill 可以在多个项目中使用，也可以分享给其他用户。

3. **触发灵活**：可以通过命令（`/react-component`）、模式匹配（"创建 React 组件"）或意图识别触发。

4. **与工具集成**：Skill 不创建新工具，而是组合已有工具。它定义的是工作流，不是功能。

**Skill vs Hook**：

| 维度 | Hook | Skill |
|------|------|-------|
| 形式 | 函数代码 | 声明式 YAML/JSON |
| 成本 | 低（写函数） | 中（定义工作流） |
| 复用性 | 低（绑定到特定代码） | 高（独立文件） |
| 隔离 | 无 | 无 |
| 适用 | 修改行为 | 定义流程 |

## Plugin：打包的功能模块

Plugin 是 Claude Code 的**重量级扩展方式**。它是一个完整的、自包含的功能模块，有自己的进程、权限和生命周期。

```typescript
// Plugin 定义（简化版）
interface Plugin {
  name: string;
  version: string;
  entry: string;           // 入口文件
  
  // 权限声明
  permissions: PluginPermission[];
  
  // 生命周期钩子
  lifecycle: {
    onLoad: () => Promise<void>;
    onUnload: () => Promise<void>;
  };
  
  // 提供的工具
  tools: ToolDefinition[];
  
  // 提供的命令
  commands: CommandDefinition[];
}

interface PluginPermission {
  type: 'file' | 'network' | 'process' | 'ui';
  scope: string;
  readonly: boolean;
}
```

**Plugin 的隔离机制**：

Plugin 与 Claude Code 主进程**隔离运行**，通过 IPC 通信：

```typescript
// Plugin 进程通信（简化版）
class PluginManager {
  private plugins = new Map<string, PluginProcess>();
  
  async loadPlugin(pluginPath: string): Promise<void> {
    const plugin = await loadPluginManifest(pluginPath);
    
    // 验证权限声明
    await validatePermissions(plugin.permissions);
    
    // 启动独立进程
    const process = spawn('node', [plugin.entry], {
      stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
      env: { 
        ...process.env,
        CLAUDE_PLUGIN_ID: plugin.name,
        CLAUDE_PLUGIN_VERSION: plugin.version,
      },
    });
    
    // 建立 IPC 通道
    process.on('message', (msg: PluginMessage) => {
      this.handlePluginMessage(plugin.name, msg);
    });
    
    this.plugins.set(plugin.name, { process, manifest: plugin });
    
    // 调用生命周期钩子
    await this.sendMessage(plugin.name, { type: 'load' });
  }
}
```

**Plugin 的隔离维度**：

| 维度 | 隔离方式 | 说明 |
|------|----------|------|
| **进程** | 独立 Node.js 进程 | Plugin 崩溃不影响主进程 |
| **内存** | 独立 V8 堆 | 不共享内存，防止内存泄漏 |
| **权限** | 声明式权限 | Plugin 只能访问声明的权限 |
| **文件** | 沙箱路径 | 只能访问插件目录和声明的目录 |
| **网络** | 白名单 | 只能访问声明的域名/IP |

**Plugin 的适用场景**：

- **复杂功能**：如自定义语言支持、IDE 集成、版本控制增强
- **第三方服务**：如连接 Jira、Slack、GitHub 的插件
- **UI 扩展**：如自定义主题、自定义面板、自定义快捷键
- **安全敏感**：如处理凭据、加密操作的插件（需要隔离）

**Plugin 的成本**：

- **开发成本**：需要遵循 Plugin API，定义权限，处理 IPC
- **运行成本**：额外进程，额外内存，IPC 通信开销
- **维护成本**：版本兼容性、依赖管理、安全更新

## MCP：连接外部工具生态

MCP（Model Context Protocol）是 Anthropic 推出的**开放标准协议**，用于连接 Claude 与外部工具。它不是 Claude Code 特有的扩展方式，而是整个 Claude 生态的扩展接口。

```typescript
// MCP Server 接口（简化版）
interface MCPServer {
  name: string;
  version: string;
  
  // 工具列表
  tools: MCPToolDefinition[];
  
  // 调用工具
  callTool(name: string, args: unknown): Promise<MCPToolResult>;
  
  // 资源列表
  resources: MCPResourceDefinition[];
  
  // 读取资源
  readResource(uri: string): Promise<MCPResource>;
  
  // 提示词模板
  prompts: MCPPromptDefinition[];
}

interface MCPToolDefinition {
  name: string;
  description: string;
  inputSchema: JSONSchema;  // JSON Schema 输入验证
}
```

**MCP 的架构**：

```
Claude Code (MCP Client)
        |
        | MCP Protocol (JSON-RPC over stdio/HTTP/SSE)
        |
    [MCP Server 1] —— 本地文件系统工具
    [MCP Server 2] —— 数据库查询工具
    [MCP Server 3] —— GitHub API 工具
    [MCP Server 4] —— 浏览器自动化工具
```

**MCP 的特点**：

1. **协议标准化**：MCP 是开放标准，任何遵循协议的 Server 都可以接入任何 MCP Client（不局限于 Claude Code）。

2. **语言无关**：MCP Server 可以用任何语言编写（Python、Go、Rust 等），只要实现 MCP 协议即可。

3. **动态发现**：Claude Code 启动时，扫描配置目录中的 MCP Server，动态加载和发现工具。

4. **工具级隔离**：每个 MCP Server 是一个独立进程，与 Claude Code 通过 stdio/HTTP/SSE 通信。

**MCP 的配置**：

```json
// .claude/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${env.GITHUB_TOKEN}"
      }
    },
    "sqlite": {
      "command": "uvx",
      "args": ["-y", "mcp-server-sqlite", "--db-path", "/path/to/data.db"]
    }
  }
}
```

**MCP 的适用场景**：

- **连接外部服务**：如 GitHub、Slack、Jira、Notion 等
- **专用工具**：如数据库查询、API 测试、文档生成等
- **企业集成**：如内部系统、私有 API、数据仓库等
- **跨语言生态**：如用 Python 写的数据分析工具，用 Go 写的性能分析工具

**MCP 的成本**：

- **开发成本**：需要实现 MCP 协议，定义 JSON Schema，处理协议通信
- **运行成本**：每个 MCP Server 是一个独立进程，有额外的启动和通信开销
- **维护成本**：需要处理协议版本兼容、Server 的健康检查、错误恢复

## 四种方式的选型策略

如何选择扩展方式？Claude Code 的选型策略是一个**决策树**：

```
你想做什么？
    |
    ├─ 修改某个已有行为？
    │      └─ 使用 Hook（最低成本）
    │
    ├─ 定义一个可复用的工作流？
    │      └─ 使用 Skill（中等成本，高复用）
    │
    ├─ 添加一个复杂功能模块？
    │      └─ 使用 Plugin（高成本，强隔离）
    │
    ├─ 连接外部工具或服务？
    │      └─ 使用 MCP（最高成本，跨生态）
    │
    └─ 不确定？
           └─ 从 Skill 开始，不够再升级
```

**实际选型案例**：

| 需求 | 选型 | 原因 |
|------|------|------|
| "在工具调用前记录日志" | Hook | 只需修改一个行为点 |
| "标准化 React 组件创建流程" | Skill | 可复用工作流，团队共享 |
| "添加自定义代码审查工具" | Plugin | 需要独立进程和 UI |
| "连接 GitHub Issue 管理" | MCP | 连接外部服务，用标准协议 |
| "在会话开始时加载团队配置" | Hook | 简单，不需要隔离 |
| "自定义代码格式化规则" | Skill | 可复用，不需要隔离 |

**组合使用**：四种方式不是互斥的。一个复杂的扩展方案可能同时使用多种方式：

```
企业内部 Claude Code 扩展方案：

├── Hook
│   ├── 会话开始时加载企业 SSO 配置
│   └── 工具调用前记录审计日志
│
├── Skill
│   ├── "创建微服务" 标准化流程
│   ├── "代码审查清单" 检查流程
│   └── "部署到 K8s" 发布流程
│
├── Plugin
│   ├── 企业内部 IDE 集成
│   └── 自定义代码分析工具
│
└── MCP
    ├── GitHub Enterprise 集成
    ├── Jira 工单管理
    └── 内部数据仓库查询
```

## 扩展的加载机制

Claude Code 在启动时加载扩展，加载顺序和优先级很重要：

```typescript
// 扩展加载机制（简化版）
async function loadExtensions(): Promise<ExtensionLoadResult> {
  const result: ExtensionLoadResult = {
    hooks: [],
    skills: [],
    plugins: [],
    mcpServers: [],
  };
  
  // 1. 加载 Hooks（最先，因为其他扩展可能依赖 Hook）
  const hookFiles = await glob('.claude/hooks/*.js');
  for (const file of hookFiles) {
    const hook = await import(file);
    registerHook(hook.default);
    result.hooks.push(hook.default.name);
  }
  
  // 2. 加载 Skills
  const skillFiles = await glob('.claude/skills/*/skill.yaml');
  for (const file of skillFiles) {
    const skill = await loadSkill(file);
    registerSkill(skill);
    result.skills.push(skill.name);
  }
  
  // 3. 加载 Plugins（在 Skills 之后，因为 Plugin 可能使用 Skill）
  const pluginFiles = await glob('.claude/plugins/*/plugin.json');
  for (const file of pluginFiles) {
    await pluginManager.loadPlugin(path.dirname(file));
    result.plugins.push(file);
  }
  
  // 4. 加载 MCP Servers（最后，因为 MCP 可能依赖前面的扩展）
  const mcpConfig = await loadMCPConfig('.claude/mcp.json');
  for (const [name, server] of Object.entries(mcpConfig.mcpServers)) {
    await mcpClient.connect(name, server);
    result.mcpServers.push(name);
  }
  
  return result;
}
```

**加载顺序**：

1. **Hooks 先加载**：因为其他扩展可能注册自己的 Hook（如 Skill 在触发时记录日志）。

2. **Skills 其次**：Skills 是基础工作流，Plugin 和 MCP 可能依赖它们。

3. **Plugins 然后**：Plugin 是独立功能模块，可能使用 Skill 和 Hook。

4. **MCP Servers 最后**：MCP 是外部连接，依赖前面的基础扩展。

**加载失败的处理**：

- **Hook 加载失败**：跳过该 Hook，记录警告，继续加载其他扩展。
- **Skill 加载失败**：跳过该 Skill，记录警告，继续加载其他扩展。
- **Plugin 加载失败**：跳过该 Plugin，记录错误，继续加载其他扩展。Plugin 的隔离保证了一个 Plugin 的失败不影响其他 Plugin。
- **MCP Server 加载失败**：标记为离线，记录错误，定期重连。MCP Server 的独立性保证了一个 Server 的失败不影响其他 Server。

## 总结

- Claude Code 提供四种扩展方式，构成**成本梯度**：Hook（最低）→ Skill（中低）→ Plugin（中）→ MCP（高）。
- **Hook** 修改已有行为的钩子点，零成本、同步执行、无隔离，适合细节调整。
- **Skill** 定义可复用工作流，声明式 YAML、触发灵活，适合标准化流程。
- **Plugin** 打包完整功能模块，进程隔离、权限声明，适合复杂功能和安全敏感操作。
- **MCP** 连接外部工具生态，开放标准、语言无关，适合跨服务集成。
- 四种方式可以**组合使用**，加载顺序是 Hook → Skill → Plugin → MCP。
- 选型策略：修改行为用 Hook，定义流程用 Skill，复杂功能用 Plugin，外部服务用 MCP。

> 下一篇：[Skill 系统](./02-skills.md)，深入拆解 Claude Code 的 Skill 注册、加载和执行机制。

## 参考链接

- [Claude Code 扩展系统源码](file:///E:/Projects/claude-code/src/extensions/)
- [Claude Code Skill 系统](file:///E:/Projects/claude-code/src/skills/)
- [MCP 官方文档](https://modelcontextprotocol.io/)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
