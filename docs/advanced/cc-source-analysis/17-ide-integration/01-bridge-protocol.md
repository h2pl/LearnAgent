# Bridge 协议：Agent 如何"走出"终端

> `src/bridge/` 有 31 个文件、4000+ 行代码，支撑着 Claude Code 最核心的扩展能力——Remote Control 和 IDE 集成。它用一套 JSON 协议让手机、Web、VS Code 都能接入同一个 Agent 会话。

你好，我是江小湖。

上一章 [终端 UI 框架](../16-terminal-ui/README.md) 讲了 React + Ink 如何在终端渲染界面。但 Agent 的能力不应该被困在终端里——用户在手机上也应该能继续之前的任务，在 VS Code 里也应该能直接调用 Agent。

Bridge 就是实现这一切的协议层。

## 目录

- [Bridge 的四个角色](#bridge-的四个角色)
- [协议栈：从 WebSocket 到 SDK 消息](#协议栈从-websocket-到-sdk-消息)
- [消息生命周期](#消息生命周期)
- [Bridge Safe：远程命令的防火墙](#bridge-safe远程命令的防火墙)
- [Work Secret：安全握手](#work-secret安全握手)
- [会话模型：Bridge 如何跨设备同步](#会话模型bridge-如何跨设备同步)
- [总结](#总结)
- [参考链接](#参考链接)

## Bridge 的四个角色

```text
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Mobile/Web   │─────▶│ Bridge API   │─────▶│ Local Agent  │
│ Client       │      │ (claude.ai)  │      │ Process      │
└──────────────┘      └──────────────┘      └──────────────┘
                              │                      │
                              ▼                      ▼
                       ┌──────────────┐      ┌──────────────┐
                       │ Auth & JWT   │      │ IDE Extension│
                       │ (OAuth)      │      │ (VS Code/JB) │
                       └──────────────┘      └──────────────┘
```

| 角色 | 职责 | 关键文件 |
|------|------|---------|
| Mobile/Web Client | 用户交互界面，发送消息、接收响应 | claude.ai 前端、iOS/Android App |
| Bridge API Server | 消息路由、会话管理、JWT 签发 | claude.ai 后端服务 |
| Local Agent Process | 执行 Agent 逻辑、管理工具调用 | `bridgeMain.ts`、`replBridge.ts` |
| IDE Extension | 文件编辑同步、光标位置、选区传递 | VS Code / JetBrains 扩展 |

## 协议栈：从 WebSocket 到 SDK 消息

Bridge 协议分两层：

### 传输层

```typescript
// bridge/replBridgeTransport.ts — 两种传输模式
const V1_TRANSPORT = 'polling'       // 轮询：每 N 秒拉取新消息
const V2_TRANSPORT = 'websocket'     // WebSocket：双向实时通信
```

V1 使用 HTTP 轮询（简单但延迟高），V2 使用 WebSocket（低延迟但需要持久连接）。两种模式共享相同的上层协议。

### 应用层：SDK Message

所有应用层消息遵循统一的 `SDKMessage` 类型：

```typescript
// bridge/bridgeMessaging.ts

// 入站消息（客户端 → Agent）
type SDKMessage =
  | { type: 'user_message', content: string }       // 用户输入
  | { type: 'tool_approval', approved: boolean }     // 工具审批
  | { type: 'control_request', ... }                 // 客户端控制请求
  | { type: 'slash_command', command: string }       // 远程 slash 命令

// 出站消息（Agent → 客户端）
type BridgeOutput =
  | { type: 'text', content: string }                // 文本响应
  | { type: 'tool_use', toolName: string, args: any } // 工具调用通知
  | { type: 'tool_result', ... }                     // 工具结果
  | { type: 'thinking', content: string }            // 推理过程
```

## 消息生命周期

一次远程消息的完整旅程：

```text
[1] Mobile: 用户输入 "fix the login bug"
      │
      ▼ WebSocket (or HTTP poll)
[2] Bridge API Server: 路由到正确的 session
      │
      ▼ JWT-认证的 WebSocket
[3] replBridge.ts: 接收到 user_message
      │
      ▼ handleIngressMessage()
[4] bridgeMessaging.ts: 解析 → 校验 → 排入队列
      │
      ▼ enqueue()
[5] handlePromptSubmit: 和本地输入完全相同的处理路径
      │
      ▼ processUserInput → query() → tool execution
[6] replBridge.ts: 每个 tool_use 通知客户端
      │
      ▼ 每次文本生成流式推送给客户端
[7] Mobile: 实时显示 Agent 的工作进度
```

### 关键设计：echo 去重

Bridge 必须处理一个微妙的问题：Agent 生成的文本同时出现在 stdout 和 Bridge 输出中。如果两者都发回客户端，客户端会看到重复消息。

```typescript
// bridgeMessaging.ts — echo 去重
const BoundedUUIDSet = ... // 跟踪已发送的消息 UUID
// 每条消息带唯一 UUID，客户端用 UUID 去重
```

## Bridge Safe：远程命令的防火墙

并非所有 slash 命令都能从远程安全执行（详见 [15-命令生命周期](../15-cli-commands/02-lifecycle.md#bridge-safe远程命令的防火墙)）：

```typescript
// 三类命令的 Bridge 安全等级
if (cmd.type === 'local-jsx') return false  // Ink UI → 本地独占
if (cmd.type === 'prompt') return true       // 纯文本 → 安全
return BRIDGE_SAFE_COMMANDS.has(cmd)          // local 类型 → 白名单
```

`skipSlashCommands` flag 确保远程客户端发送的 `/exit` 不会杀死本地 session。

## Work Secret：安全握手

Bridge 的认证不是简单的 API Key——它使用三阶段握手：

```typescript
// bridge/types.ts — WorkSecret 结构

type WorkSecret = {
  version: number
  session_ingress_token: string          // 一次性会话令牌
  api_base_url: string                   // Bridge API 地址
  sources: Array<{
    type: string
    git_info?: { repo: string; ref?: string; token?: string }
  }>
  auth: Array<{ type: string; token: string }>
  environment_variables?: Record<string, string>
  use_code_sessions?: boolean            // CCR v2 兼容标志
}
```

### 三阶段握手

1. **Work Poll**：Agent 启动后在 `bridgeMain.ts` 中轮询 `claim_work` 端点，等待"工作"
2. **Work Received**：服务器返回 `WorkResponse`，包含 `WorkSecret` 和 `WorkData`
3. **Session Ingress**：Agent 用 `session_ingress_token` 建立 WebSocket 连接，开始收发消息

```typescript
// bridge/bridgeMain.ts — 工作轮询循环
while (!shutdown) {
  const work = await pollForWork(client, lastPollTime)
  if (work) {
    const session = await spawnSession(work)
    // session 持续运行直到完成/失败
  }
  await sleep(pollInterval)
}
```

这种设计让 Agent 进程可以提前启动、在后台等待工作——不需要用户提前知道 session ID。

## 会话模型：Bridge 如何跨设备同步

### Bridge Session 的状态机

```text
[CREATED] → [CONNECTED] → [ACTIVE] → [COMPLETED/FAILED]
                 │             │
                 ▼             ▼
           [DISCONNECTED]  [INTERRUPTED]
           (可重连)        (用户取消)
```

`SessionDoneStatus` 定义了四种终态：

```typescript
type SessionDoneStatus = 'completed' | 'failed' | 'interrupted'
```

### Session Activity 流

客户端通过 `session activity` 流实时看到 Agent 的工作：

```typescript
type SessionActivity = {
  type: 'tool_start' | 'text' | 'result' | 'error'
  summary: string    // e.g. "Editing src/foo.ts", "Reading package.json"
  timestamp: number
}
```

这被渲染成客户端的 Activity Feed——用户在手机上看到："正在读取 package.json → 正在编辑 src/foo.ts → 测试通过 ✓"。

### 超时与清理

```typescript
const DEFAULT_SESSION_TIMEOUT_MS = 24 * 60 * 60 * 1000  // 24 小时
```

Session 超时后自动清理。`registerCleanup` 注册的清理函数在进程退出时关闭所有活跃的 Bridge 连接。

## 总结

Bridge 协议是 Claude Code"走出终端"的关键基础设施：

1. **四角色架构**——Mobile/Web Client、Bridge API Server、Local Agent Process、IDE Extension，通过统一的 SDKMessage 协议通信
2. **双传输模式**——HTTP Polling（V1）和 WebSocket（V2）共享相同的应用层协议
3. **消息生命周期**——从远程客户端到 Agent 再到工具执行，和本地消息走相同的 `handlePromptSubmit` 路径
4. **Bridge Safe 防火墙**——local-jsx 命令（Ink UI）默认阻止，prompt 命令（纯文本）默认允许，local 命令需要白名单
5. **Work Secret 三阶段握手**——Poll → Receive → Ingress，Agent 可以提前启动等待工作
6. **跨设备同步**——Session Activity 流让所有客户端看到 Agent 的实时工作状态

Bridge 的存在意味着 Claude Code 不是一个"终端工具"——它是一个可以被嵌入到任何客户端的 **Agent 后端服务**。VS Code 扩展、手机 App、Web Dashboard——它们都是同一个 Bridge 协议的不同客户端。

---

> 至此，**Claude Code 源码解析系列全部 17 章、52 篇文章完成**。从 [01 — 整体架构](../01-architecture-overview/README.md) 的层次化设计，到本章的 Bridge 协议，我们完整遍历了 Claude Code 从启动到退出的每一层代码。

> 建议回到 [01 — 整体架构](../01-architecture-overview/README.md) 以俯瞰视角重新串一遍全局——当你理解了每一个模块的细节后，再看整体架构会有完全不同的体会。

> 我是江小湖，感谢阅读。

## 参考链接

- `src/bridge/types.ts` — Bridge 协议类型定义（10KB）
- `src/bridge/replBridge.ts` — Bridge 连接管理（102KB，2400 行）
- `src/bridge/bridgeMain.ts` — Bridge 主循环与 work polling（118KB，3000 行）
- `src/bridge/bridgeMessaging.ts` — 消息解析、去重、校验（16KB）
- `src/bridge/replBridgeTransport.ts` — WebSocket/轮询双传输（15KB）
- `src/utils/ide.ts` — IDE 集成工具（VS Code / JetBrains，48KB）
- `src/commands.ts` — BRIDGE_SAFE_COMMANDS 和 isBridgeSafeCommand
