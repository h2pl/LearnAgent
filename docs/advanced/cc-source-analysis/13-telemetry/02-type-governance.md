# 类型级数据治理

> Claude Code 用两个 `never` 类型在编译期锁死 PII 泄露路径：所有进入遥测的字符串都必须经过显式安全函数处理，否则 TypeScript 编译不过。这不是运行时检查，而是类型系统层面的架构约束。

你好，我是江小湖。

[上一篇](./01-three-sinks.md) 讲了三层 Sink 的架构：事件从 `logEvent()` 进入，经过采样后分发到 Datadog 和 1P。但有个问题没展开——这些事件里的数据是怎么保证不泄露用户隐私的？

Claude Code 处理的是用户的代码、文件路径、终端命令。这些内容如果原样上报，就是严重的隐私事故。源码中有一个 974 行的 `metadata.ts` 文件专门解决这个问题，它的核心武器不是运行时校验，而是一套**类型级约束体系**。

## 目录

- [never 类型的防御机制](#never-类型的防御机制)
- [工具名脱敏](#工具名脱敏)
- [工具输入截断](#工具输入截断)
- [文件扩展名提取](#文件扩展名提取)
- [Bash 命令解析](#bash-命令解析)
- [环境上下文采集](#环境上下文采集)
- [1P 格式转换与 Proto 约束](#1p-格式转换与-proto-约束)
- [进程指标采集](#进程指标采集)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/13-telemetry/telemetry-sinks.svg" alt="遥测架构" width="90%"/>
  <br/>
  <em>事件的分层分发：Analytics/OTLP/Metrics</em>
</p>



<p align="center">
  <img src="../../../../assets/cc-source-analysis/13-telemetry/second.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 13-telemetry 配图</em>
</p>
## never 类型的防御机制

`metadata.ts` 的第 57 行定义了一个奇怪的类型：

```typescript
// services/analytics/index.ts

export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never
```

这个类型名长达 57 个字符，是整个 Claude Code 代码库中最长的类型名。它被定义为 `never`——TypeScript 中不可能持有任何值的类型。

**为什么用 `never`？** 因为所有进入遥测系统的字符串值最终都需要标注返回类型。如果返回 `string`，开发者可能直接把用户代码、文件路径塞进去。但返回 `never` 后，唯一的赋值方式是**显式类型断言**：

```typescript
// 唯一合法的写法——必须写 as 断言
return toolName as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
```

这个断言相当于开发者签了一份"合同"：**我确认这个字符串不包含代码片段、文件路径或其他敏感信息**。断言的名字本身就是审计清单——code review 时搜索这个超长类型名，就能找到所有需要检查的赋值点。

源码中还有第二个 `never` 类型，用于不同的隐私级别：

```typescript
// services/analytics/index.ts

export type AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED = never
```

这个类型标记的是**允许包含 PII 的值**，但它们只能通过 `_PROTO_*` 前缀的键进入 payload，最终只到达 1P 的特权 BigQuery 表。上一篇讲到的 `stripProtoFields` 会在 Datadog 发送前剥离这些键。

两个 `never` 形成了双通道设计：

| 类型 | 含义 | 允许的内容 | 到达的 Sink |
|------|------|-----------|------------|
| `..._NOT_CODE_OR_FILEPATHS` | 已验证不含敏感数据 | 工具名、文件扩展名、环境信息 | Datadog + 1P |
| `..._PII_TAGGED` | PII 已标记，走特权通道 | MCP 服务器名、工具详情 | 仅 1P（Datadog 被 strip） |

**架构意图**：不是在运行时拦截敏感数据，而是在类型层面让"忘记脱敏"变成编译错误。任何新增的遥测字段，如果忘记走安全函数，TypeScript 编译器会报错——因为 `never` 不能直接赋值给 `string`。

## 工具名脱敏

`sanitizeToolNameForAnalytics()` 是最简单的安全函数，也是理解整套体系的入口：

```typescript
// services/analytics/metadata.ts

export function sanitizeToolNameForAnalytics(
  toolName: string,
): AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS {
  if (toolName.startsWith('mcp__')) {
    return 'mcp_tool' as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
  }
  return toolName as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
}
```

MCP 工具名遵循 `mcp__<server>__<tool>` 格式，比如 `mcp__slack__read_channel`。这个名称暴露了用户安装了 Slack MCP 服务器——属于 PII-medium 级别。函数把所有 MCP 工具统一替换为 `mcp_tool`，而内置工具（Bash、Read、Write 等）的原名是公开信息，可以安全记录。

但有些场景需要记录更细粒度的 MCP 信息。`mcpToolDetailsForAnalytics()` 提供了条件放行：

```typescript
export function mcpToolDetailsForAnalytics(
  toolName: string,
  mcpServerType: string | undefined,
  mcpServerBaseUrl: string | undefined,
): { mcpServerName?: ...; mcpToolName?: ... } {
  const details = extractMcpToolDetails(toolName)
  if (!details) return {}

  // 放行条件：内置 MCP 或已验证的安全来源
  if (
    !BUILTIN_MCP_SERVER_NAMES.has(details.serverName) &&
    !isAnalyticsToolDetailsLoggingEnabled(mcpServerType, mcpServerBaseUrl)
  ) {
    return {}  // 不满足条件 → 脱敏
  }
  return { mcpServerName: details.serverName, mcpToolName: details.mcpToolName }
}
```

**三个放行条件**，满足任一即可记录详细 MCP 名称：

```typescript
export function isAnalyticsToolDetailsLoggingEnabled(
  mcpServerType: string | undefined,
  mcpServerBaseUrl: string | undefined,
): boolean {
  // 条件 1：Cowork 模式（内部 Agent 协作，无 ZDR 概念）
  if (process.env.CLAUDE_CODE_ENTRYPOINT === 'local-agent') return true
  // 条件 2：claude.ai 代理的 MCP（官方维护的列表）
  if (mcpServerType === 'claudeai-proxy') return true
  // 条件 3：URL 匹配官方 MCP 注册表
  if (mcpServerBaseUrl && isOfficialMcpUrl(mcpServerBaseUrl)) return true
  return false
}
```

用户自己配置的私有 MCP（比如指向内网服务的 `http://internal.company.com:3000/mcp`）永远不满足条件，工具名始终被替换为 `mcp_tool`。

## 工具输入截断

工具名是低风险字段，而工具的**输入参数**可能包含用户代码、文件路径、甚至 API 密钥。`extractToolInputForTelemetry()` 用多层截断控制风险：

```typescript
// services/analytics/metadata.ts

const TOOL_INPUT_STRING_TRUNCATE_AT = 512   // 超过 512 字符的字符串触发截断
const TOOL_INPUT_STRING_TRUNCATE_TO = 128   // 截断到 128 字符
const TOOL_INPUT_MAX_JSON_CHARS = 4 * 1024  // 最终 JSON 不超过 4KB
const TOOL_INPUT_MAX_COLLECTION_ITEMS = 20   // 数组/对象最多 20 个元素
const TOOL_INPUT_MAX_DEPTH = 2               // 嵌套深度最多 2 层
```

截断逻辑 `truncateToolInputValue()` 递归处理任意结构的输入：

```typescript
function truncateToolInputValue(value: unknown, depth = 0): unknown {
  if (typeof value === 'string') {
    if (value.length > TOOL_INPUT_STRING_TRUNCATE_AT) {
      // "很长的代码..." → "前128字符…[5200 chars]"
      return `${value.slice(0, TOOL_INPUT_STRING_TRUNCATE_TO)}…[${value.length} chars]`
    }
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean' ||
      value === null || value === undefined) {
    return value  // 原始类型直接保留
  }
  if (depth >= TOOL_INPUT_MAX_DEPTH) {
    return '<nested>'  // 超过 2 层嵌套 → 占位符
  }
  if (Array.isArray(value)) {
    const mapped = value
      .slice(0, TOOL_INPUT_MAX_COLLECTION_ITEMS)  // 只取前 20 个
      .map(v => truncateToolInputValue(v, depth + 1))
    if (value.length > TOOL_INPUT_MAX_COLLECTION_ITEMS) {
      mapped.push(`…[${value.length} items]`)  // 标记被截断
    }
    return mapped
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      // 跳过内部标记键（以 _ 开头）
      .filter(([k]) => !k.startsWith('_'))
    // ... 同样截断到 20 个键，递归处理值
  }
}
```

**设计要点**：截断不是丢弃——字符串末尾标注原始长度（`…[5200 chars]`），数组末尾标注原始元素数（`…[150 items]`）。这让分析师知道截断了多少，可以估算原始数据的规模。

这个函数只在 `OTEL_LOG_TOOL_DETAILS=1` 时启用：

```typescript
export function extractToolInputForTelemetry(input: unknown): string | undefined {
  if (!isToolDetailsLoggingEnabled()) return undefined  // 默认关闭
  const truncated = truncateToolInputValue(input)
  let json = jsonStringify(truncated)
  if (json.length > TOOL_INPUT_MAX_JSON_CHARS) {
    json = json.slice(0, TOOL_INPUT_MAX_JSON_CHARS) + '…[truncated]'
  }
  return json
}
```

默认关闭是一个有意识的选择：只有在需要调试特定工具行为时才打开，避免日常运行中的数据泄露风险。

## 文件扩展名提取

文件扩展名是低敏感度但有高分析价值的字段。`getFileExtensionForAnalytics()` 从文件路径中提取扩展名，同时做了安全处理：

```typescript
const MAX_FILE_EXTENSION_LENGTH = 10

export function getFileExtensionForAnalytics(
  filePath: string,
): AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS | undefined {
  const ext = extname(filePath).toLowerCase()
  if (!ext || ext === '.') return undefined

  const extension = ext.slice(1)  // 去掉点号：".ts" → "ts"
  if (extension.length > MAX_FILE_EXTENSION_LENGTH) {
    return 'other'  // 超长扩展名 → 归类为 other
  }
  return extension as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
}
```

**为什么要限制长度？** 哈希化文件名（如 `key-hash-abcd-123-456`）的"扩展名"实际上是哈希值的一部分，可能泄露文件内容特征。超过 10 个字符的扩展名一律替换为 `other`，既保护隐私又控制了 Datadog 的标签基数。

## Bash 命令解析

Bash 工具是 Claude Code 最常用的工具之一，命令中可能包含文件路径。`getFileExtensionsFromBashCommand()` 从 Bash 命令中提取操作文件的扩展名，但不记录文件名本身：

```typescript
const FILE_COMMANDS = new Set([
  'rm', 'mv', 'cp', 'touch', 'mkdir', 'chmod', 'chown',
  'cat', 'head', 'tail', 'sort', 'stat', 'diff', 'wc',
  'grep', 'rg', 'sed',
])

// 按复合操作符拆分：&&、||、;、|
const COMPOUND_OPERATOR_REGEX = /\s*(?:&&|\|\||[;|])\s*/
```

函数按复合操作符拆分命令，再对每个子命令按空白拆分 token，最后从非 flag 参数中提取扩展名：

```typescript
export function getFileExtensionsFromBashCommand(
  command: string,
  simulatedSedEditFilePath?: string,
): AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS | undefined {
  if (!command.includes('.') && !simulatedSedEditFilePath) return undefined

  let result: string | undefined
  const seen = new Set<string>()

  for (const subcmd of command.split(COMPOUND_OPERATOR_REGEX)) {
    const tokens = subcmd.split(WHITESPACE_REGEX)
    const baseCmd = lastPathComponent(tokens[0])
    if (!FILE_COMMANDS.has(baseCmd)) continue  // 非文件操作命令 → 跳过

    for (let i = 1; i < tokens.length; i++) {
      if (tokens[i].charCodeAt(0) === 45) continue  // 跳过 flag（- 开头）
      const ext = getFileExtensionForAnalytics(tokens[i])
      if (ext && !seen.has(ext)) {
        seen.add(ext)
        result = result ? result + ',' + ext : ext
      }
    }
  }
  return result as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
}
```

比如命令 `cat README.md && cp config.ts backup/ && npm install`，提取结果是 `md,ts`。`npm install` 不在 `FILE_COMMANDS` 中，被跳过。

**设计取舍**：这是一种 best-effort 解析，不做完整 shell 语法分析（不处理引号、变量替换、子 shell）。源码注释解释了原因：grep 的正则模式和 sed 脚本不太可能被误判为文件扩展名，所以简单拆分够用。代价是边缘情况（如带空格的文件名）会解析不准，但对于统计分析来说完全可接受。

## 环境上下文采集

每个遥测事件都会附带一份环境上下文（`EnvContext`），帮助分析师理解事件发生的运行环境。这是整个 metadata 模块中字段最多的类型：

```typescript
export type EnvContext = {
  platform: string          // 统一化平台：darwin / win32 / linux
  platformRaw: string       // 原始 process.platform（含 freebsd 等）
  arch: string              // CPU 架构
  nodeVersion: string       // Node.js 版本
  terminal: string | null   // 终端类型
  packageManagers: string   // 检测到的包管理器：npm,yarn,pnpm
  runtimes: string           // 检测到的运行时：node,bun,deno
  isRunningWithBun: boolean  // 是否在 Bun 运行时中
  isCi: boolean             // 是否在 CI 环境
  isClaubbit: boolean       // 是否为 Claubbit 模式
  isClaudeCodeRemote: boolean  // 是否远程运行
  isLocalAgentMode: boolean    // 是否本地 Agent 模式
  isConductor: boolean        // 是否 Conductor 模式
  remoteEnvironmentType?: string
  coworkerType?: string       // 协作 Agent 类型
  claudeCodeContainerId?: string
  claudeCodeRemoteSessionId?: string
  tags?: string               // 自定义标签
  isGithubAction: boolean     // GitHub Actions 环境
  isClaudeCodeAction: boolean // Claude Code Action
  isClaudeAiAuth: boolean     // claude.ai 认证用户
  version: string             // Claude Code 版本号
  versionBase?: string        // 基础版本号（去掉构建后缀）
  buildTime: string           // 构建时间
  deploymentEnvironment: string
  wslVersion?: string         // WSL 版本
  linuxDistroId?: string      // Linux 发行版 ID
  linuxDistroVersion?: string
  linuxKernel?: string
  vcs?: string                // 版本控制系统：git,hg,svn
}
```

**采集策略**：`buildEnvContext()` 被 `memoize` 包裹，整个会话只执行一次。它用 `Promise.all` 并行采集四个需要异步检测的信息（包管理器、运行时、Linux 发行版、VCS），然后构建一个不可变的上下文对象：

```typescript
const buildEnvContext = memoize(async (): Promise<EnvContext> => {
  const [packageManagers, runtimes, linuxDistroInfo, vcs] = await Promise.all([
    env.getPackageManagers(),
    env.getRuntimes(),
    getLinuxDistroInfo(),
    detectVcs(),
  ])
  return { /* ... */ }
})
```

值得注意的是 `platformRaw` 字段的存在。`getHostPlatformForAnalytics()` 会把 freebsd、openbsd 等小众平台归入 linux，但 `platformRaw` 保留 `process.platform` 原始值。注释说："getHostPlatformForAnalytics() buckets those into 'linux'; here we want the truth"——在 BigQuery 分析时需要看到真实的平台分布。

有些字段受到 feature flag 保护，防止在外部构建版本中泄露内部信息：

```typescript
// coworkerType 字段受 feature flag 保护
...(feature('COWORKER_TYPE_TELEMETRY')
  ? process.env.CLAUDE_CODE_COWORKER_TYPE
    ? { coworkerType: process.env.CLAUDE_CODE_COWORKER_TYPE }
    : {}
  : {}),
```

GitHub Actions 相关字段只在 `GITHUB_ACTIONS=true` 时才采集，避免非 CI 环境产生无意义的空值。

## 1P 格式转换与 Proto 约束

环境上下文采集完毕后，需要转换为 1P（First Party）要求的格式。`to1PEventFormat()` 承担这个职责，把所有 camelCase 字段转为 snake_case：

```typescript
export function to1PEventFormat(
  metadata: EventMetadata,
  userMetadata: CoreUserData,
  additionalMetadata: Record<string, unknown> = {},
): FirstPartyEventLoggingMetadata {
  const { envContext, processMetrics, rh, kairosActive, ...coreFields } = metadata

  // env 的类型是 proto 生成的 EnvironmentMetadata
  // 不是手写的 interface
  const env: EnvironmentMetadata = {
    platform: envContext.platform,
    platform_raw: envContext.platformRaw,
    arch: envContext.arch,
    // ... 全部 snake_case
  }
```

**关键约束**：`env` 变量的类型标注为 `EnvironmentMetadata`，这不是手写的 TypeScript interface，而是由 Protocol Buffer 生成的类型。这意味着如果代码里多写了一个 proto 没定义的字段，TypeScript 会报编译错误。

源码注释记录了这条规则的血泪史：

```
IMPORTANT: env is typed as the proto-generated EnvironmentMetadata so that
adding a field here that the proto doesn't define is a compile error. The
generated toJSON() serializer silently drops unknown keys — a hand-written
parallel type previously let #11318, #13924, #19448, and coworker_type all
ship fields that never reached BQ.
```

曾有四个字段（包括 `coworker_type`）因为使用了手写类型而非 proto 生成的类型，导致 `toJSON()` 序列化器静默丢弃了它们——数据写入代码正常运行，但数据从未到达 BigQuery。

**教训**：手写类型提供了"类型安全"的假象——TypeScript 编译通过不代表数据链路完整。Proto 生成的类型把 schema 约束推到编译期，让"数据链路断裂"变成编译错误而非线上事故。

`to1PEventFormat()` 的返回值结构精确映射 proto schema 的三层组织：

```typescript
return {
  env,           // → proto EnvironmentMetadata（BigQuery 独立列）
  ...(processMetrics && {
    process: Buffer.from(jsonStringify(processMetrics)).toString('base64'),
    // process 指标 base64 编码后存储
  }),
  ...(auth && { auth }),  // → proto PublicApiAuth（account_uuid + org_uuid）
  core,          // → proto 顶层字段（session_id, model 等）
  additional: {   // → proto additional_metadata（JSON blob）
    ...(rh && { rh }),                    // 仓库哈希
    ...(kairosActive && { is_assistant_mode: true }),
    ...(skillMode && { skill_mode: skillMode }),
    ...(observerMode && { observer_mode: observer_mode }),
    ...additionalMetadata,
  },
}
```

注意 `auth` 字段只填充 UUID（`account_uuid` 和 `organization_uuid`），注释明确说"account_id is intentionally omitted"——数字 ID 可能在不同系统间冲突，UUID 才是全球唯一的安全标识。

## 进程指标采集

每个事件还附带一份进程级指标（`ProcessMetrics`），用于监控 Claude Code 自身的资源消耗：

```typescript
export type ProcessMetrics = {
  uptime: number              // 进程运行时长（秒）
  rss: number                 // 常驻内存集大小
  heapTotal: number           // V8 堆总大小
  heapUsed: number            // V8 堆已用大小
  external: number             // C++ 对象内存
  arrayBuffers: number         // ArrayBuffer 内存
  constrainedMemory: number | undefined  // 系统内存限制
  cpuUsage: NodeJS.CpuUsage   // CPU 时间（用户态 + 内核态）
  cpuPercent: number | undefined  // CPU 占比百分比
}
```

CPU 百分比的计算用增量法——两次调用之间 CPU 时间差除以墙钟时间差：

```typescript
function buildProcessMetrics(): ProcessMetrics | undefined {
  try {
    const mem = process.memoryUsage()
    const cpu = process.cpuUsage()
    const now = Date.now()

    let cpuPercent: number | undefined
    if (prevCpuUsage && prevWallTimeMs) {
      const wallDeltaMs = now - prevWallTimeMs
      if (wallDeltaMs > 0) {
        const userDeltaUs = cpu.user - prevCpuUsage.user
        const systemDeltaUs = cpu.system - prevCpuUsage.system
        // CPU 时间增量（微秒）/ 墙钟时间增量（微秒）× 100
        cpuPercent = ((userDeltaUs + systemDeltaUs) / (wallDeltaMs * 1000)) * 100
      }
    }
    prevCpuUsage = cpu
    prevWallTimeMs = now
    return { /* ... */ }
  } catch {
    return undefined
  }
}
```

**全局变量设计**：`prevCpuUsage` 和 `prevWallTimeMs` 是模块级变量（注释说"inherently process-global"），和 `datadog.ts` 中的批量刷新计时器是同一模式。这是因为 CPU 百分比天然是进程级别的指标——多个事件共享同一个基准值。

进程指标最终被 JSON 序列化后 Base64 编码，存储在 1P 事件的 `process` 字段中。这不是一个独立的分析维度，而是附加的诊断信息——当某个事件触发错误时，可以检查当时的内存和 CPU 状态，判断是否是资源压力导致的问题。

## 总结

- Claude Code 的遥测数据治理采用**类型驱动**策略：两个 `never` 类型在编译期锁死未脱敏数据的注入路径，强制每个安全函数的返回值都经过显式断言。
- **工具名脱敏**把 MCP 工具统一为 `mcp_tool`，仅在三个安全条件满足时才记录详细的 MCP 服务器名和工具名。
- **工具输入截断**用五条参数（128 字符、4KB JSON、20 元素、2 层深度）递归裁剪，同时保留原始规模标记供分析使用。
- **文件扩展名**和 **Bash 命令解析**提取低敏感度的结构信息（扩展名类型、操作命令类型），而非文件名或命令内容本身。
- **环境上下文**采集 40+ 个字段描述运行环境，用 `memoize` 确保只采集一次，部分字段受 feature flag 保护。
- **1P 格式转换**严格映射 proto 生成的类型，用手写类型曾导致四个字段静默丢失的历史教训解释了为什么 proto 类型约束不可省略。

> 下一篇：[Datadog 集成详解](./03-datadog.md)，深入 Datadog 批量发送的时序设计、基数控制的工程权衡，以及调试工具的使用。

## 参考链接

- [Claude Code Analytics 源码](file:///E:/Projects/external/claude-code/src/services/analytics/metadata.ts)
- [TypeScript never 类型文档](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#the-never-type)
- [Protocol Buffers Schema 指南](https://protobuf.dev/overview/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [OWASP: Data Minimization](https://owasp.org/www-project-top-ten/)
