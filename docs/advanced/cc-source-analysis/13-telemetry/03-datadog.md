# Datadog 集成详解

> 171 处 `logEvent` 调用最终汇入一个 300 行的 Datadog 模块。它用白名单过滤事件、批量压缩网络请求、控制标签基数防止成本爆炸，还通过 GrowthBook 门控实现了远程开关。这些工程决策的背后是对"监控不能伤害产品"这一原则的坚守。

你好，我是江小湖。

[前两篇](./01-three-sinks.md) 讲了三层 Sink 的架构和类型级数据治理。整体设计清楚了，但 Datadog 这条管道的细节——事件怎么从内存进入网络、标签怎么构建、批量怎么刷新——还没展开。这篇就走进 `datadog.ts` 的 300 行代码，看 Claude Code 怎样把"告诉 Datadog 发生了什么"这件简单的事做到生产级可靠。

## 目录

- [Datadog 日志的结构](#datadog-日志的结构)
- [事件白名单的分类](#事件白名单的分类)
- [三层门控](#三层门控)
- [元数据组装与展平](#元数据组装与展平)
- [基数控制策略](#基数控制策略)
- [ddtags 构建与可搜索性](#ddtags-构建与可搜索性)
- [批量刷新机制](#批量刷新机制)
- [优雅关闭](#优雅关闭)
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
## Datadog 日志的结构

每条发往 Datadog 的日志是一个 `DatadogLog` 对象。理解它的结构是理解整个 Datadog 集成的基础：

```typescript
// services/analytics/datadog.ts

type DatadogLog = {
  ddsource: string    // 日志来源：'nodejs'
  ddtags: string      // 标签字符串：'event:tengu_init,platform:darwin,...'
  message: string     // 事件名：'tengu_init'
  service: string     // 服务名：'claude-code'
  hostname: string    // 主机名：'claude-code'
  [key: string]: unknown  // 额外字段（扁平化后的事件数据）
}
```

这五个固定字段是 Datadog 日志 API 的必填字段。`ddtags` 是最关键的——**它决定了事件在 Datadog 仪表盘中的可搜索性**。源码注释记录了一个重要的设计约束：

> event:\<name\> is prepended so the event name is searchable via the log search API — the `message` field (where eventName also lives) is a DD reserved field and is NOT queryable from dashboard widget queries or the aggregation API.

事件名同时出现在 `message` 字段和 `ddtags` 中。`message` 是 Datadog 的保留字段，在仪表盘查询和聚合 API 中**不可搜索**。因此必须把事件名编码为 `event:tengu_init` 放入 `ddtags`，才能在 Datadog 中按事件名过滤。

## 事件白名单的分类

Datadog 只接收白名单内的事件。`DATADOG_ALLOWED_EVENTS` 包含约 40 个事件，可分为几类：

```typescript
const DATADOG_ALLOWED_EVENTS = new Set([
  // 1. 生命周期事件
  'tengu_init',         // 初始化
  'tengu_started',      // 启动完成
  'tengu_cancel',       // 用户取消
  'tengu_exit',         // 退出

  // 2. API 交互
  'tengu_api_error',    // API 调用失败
  'tengu_api_success',  // API 调用成功
  'tengu_query_error',  // 查询错误

  // 3. 工具调用
  'tengu_tool_use_success',               // 工具调用成功
  'tengu_tool_use_error',                 // 工具调用失败
  'tengu_tool_use_granted_in_prompt_permanent',  // 永久授权
  'tengu_tool_use_granted_in_prompt_temporary',  // 临时授权
  'tengu_tool_use_rejected_in_prompt',           // 用户拒绝

  // 4. OAuth 认证
  'tengu_oauth_error',                    // OAuth 错误
  'tengu_oauth_success',                  // OAuth 成功
  'tengu_oauth_token_refresh_failure',    // Token 刷新失败
  'tengu_oauth_token_refresh_success',    // Token 刷新成功
  'tengu_oauth_token_refresh_lock_acquiring',  // 分布式锁获取中
  'tengu_oauth_token_refresh_lock_acquired',   // 分布式锁获取成功
  'tengu_oauth_token_refresh_lock_releasing',  // 分布式锁释放中
  'tengu_oauth_token_refresh_lock_released',   // 分布式锁已释放

  // 5. 异常捕获
  'tengu_uncaught_exception',     // 未捕获异常
  'tengu_unhandled_rejection',   // 未处理的 Promise 拒绝

  // 6. 功能开关
  'tengu_brief_mode_enabled',    // Brief 模式开启
  'tengu_brief_mode_toggled',    // Brief 模式切换
  'tengu_compact_failed',        // 上下文压缩失败
  'tengu_model_fallback_triggered',  // 模型降级

  // 7. IDE 连接（chrome_bridge 前缀）
  'chrome_bridge_connection_succeeded',
  'chrome_bridge_connection_failed',
  'chrome_bridge_disconnected',
  'chrome_bridge_tool_call_completed',
  'chrome_bridge_tool_call_error',
  'chrome_bridge_tool_call_started',
  'chrome_bridge_tool_call_timeout',

  // 8. 团队记忆同步
  'tengu_team_mem_sync_pull',     // 拉取团队记忆
  'tengu_team_mem_sync_push',    // 推送团队记忆
  'tengu_team_mem_sync_started', // 同步开始
  'tengu_team_mem_entries_capped', // 条目数超限
])
```

**白名单的设计逻辑**：Datadog 是面向运维告警的通道，不是全量数据分析管道（那是 1P 的职责）。所以白名单只包含**需要实时告警的事件**：启动失败、API 错误、工具异常、OAuth 故障。像 `tengu_tool_use_granted_in_prompt_permanent` 这种事件虽然不是错误，但它记录了用户授权行为——安全审计需要实时可见。

OAuth token 刷新相关的 8 个事件特别密集，反映了多实例部署中 token 刷新的分布式锁竞争是一个关键运维场景。

## 三层门控

事件到达 Datadog 需要通过三层检查。`trackDatadogEvent()` 按顺序执行：

```typescript
export async function trackDatadogEvent(
  eventName: string,
  properties: { [key: string]: boolean | number | undefined },
): Promise<void> {
  // 门控 1：只发送生产环境事件
  if (process.env.NODE_ENV !== 'production') return

  // 门控 2：第三方 Provider 不发送（Bedrock/Vertex/Foundry）
  if (getAPIProvider() !== 'firstParty') return

  // 门控 3：事件必须在白名单中
  if (!DATADOG_ALLOWED_EVENTS.has(eventName)) return

  // 门控 4：GrowthBook 远程开关（在 sink.ts 中检查）
  // 如果 shouldTrackDatadog() 返回 false，整个调用链不进入此函数
```

前两个门控是硬过滤——开发环境和第三方 Provider 的事件永远不会到达网络层。第三个门控是内容过滤——只有运维关心的事件才进入网络。第四个门控（在上一篇提到的 `sink.ts` 中）是远程开关——即使一切正常，Anthropic 也能通过 GrowthBook 随时关闭 Datadog 数据流。

**门控顺序**有性能考量：最廉价的检查（环境变量字符串比较）放前面，最昂贵的（网络请求和 GrowthBook 查询）放后面。大部分非生产事件在第一行就被拦回，不会触发后续任何逻辑。

## 元数据组装与展平

通过门控后，事件需要附加大量元数据才能进入 Datadog。`trackDatadogEvent()` 的核心逻辑是把三层数据合并为一个扁平结构：

```typescript
const metadata = await getEventMetadata({
  model: properties.model,
  betas: properties.betas,
})

// 解构 envContext，展平到顶层
const { envContext, ...restMetadata } = metadata
const allData: Record<string, unknown> = {
  ...restMetadata,    // session、model、userType 等
  ...envContext,      // platform、arch、version 等（展平到顶层）
  ...properties,      // 事件特定的属性
  userBucket: getUserBucket(),  // 用户分桶（隐私保护）
}
```

**为什么展平 envContext？** `getEventMetadata()` 返回的 `EventMetadata` 把环境信息嵌套在 `envContext` 对象中。但 Datadog 日志是扁平的 key-value 结构——嵌套对象在 Datadog 中只能作为 JSON 字符串存储，无法在查询中按字段过滤。展平后，每个环境字段（`platform`、`arch`、`version`）都成为独立的可查询属性。

展平之后还有几个转换步骤，每个都服务于特定目的。

## 基数控制策略

Datadog 按不同标签值的数量收费。如果一个字段的值空间太大（高基数），会导致标签爆炸。Claude Code 在 Datadog 层面做了三种基数控制：

```typescript
// 策略 1：MCP 工具名归一化
if (typeof allData.toolName === 'string' && allData.toolName.startsWith('mcp__')) {
  allData.toolName = 'mcp'  // mcp__slack__read_channel → mcp
}
```

上一篇在类型层面讲了 `sanitizeToolNameForAnalytics()` 做的更精细的脱敏（返回 `mcp_tool`）。Datadog 这里做的是**更激进**的归一化——直接变成 `mcp`。原因是 Datadog 对标签数量更敏感，1P 有更严格的 BigQuery Schema 约束。

```typescript
// 策略 2：模型名缩短（非 ant 用户）
if (process.env.USER_TYPE !== 'ant' && typeof allData.model === 'string') {
  const shortName = getCanonicalName(allData.model.replace(/\[1m]$/i, ''))
  allData.model = shortName in MODEL_COSTS ? shortName : 'other'
}
```

模型名可能有多个变体（`claude-sonnet-4-20250514`、`claude-sonnet-4-20250514[1m]`），`getCanonicalName()` 把它们归一化为规范名。不在 `MODEL_COSTS` 表中的模型统一替换为 `other`——未知名模型可能是内部测试版本，不应该产生新的标签值。

**注意 `USER_TYPE !== 'ant'` 的条件**：Anthropic 内部用户（`USER_TYPE === 'ant'`）可以看到原始模型名，用于调试。外部用户只看到规范名——这是同一套数据在不同受众下的差异化展示。

```typescript
// 策略 3：版本号截断
if (typeof allData.version === 'string') {
  allData.version = allData.version.replace(
    /^(\d+\.\d+\.\d+-dev\.\d{8})\.t\d+\.sha[a-f0-9]+$/,
    '$1',
  )
  // "2.0.53-dev.20251124.t173302.sha526cc6a" → "2.0.53-dev.20251124"
}
```

开发版本号包含构建时间戳（`t173302`）和 SHA 哈希（`sha526cc6a`），每个构建都不同。截断后只保留基础版本和日期——`2.0.53-dev.20251124` 在同一天的所有构建中共用同一个标签值。

还有第四种基数控制——用户分桶——值得单独说明。

## 用户分桶算法

```typescript
const NUM_USER_BUCKETS = 30

const getUserBucket = memoize((): number => {
  const userId = getOrCreateUserID()
  const hash = createHash('sha256').update(userId).digest('hex')
  return parseInt(hash.slice(0, 8), 16) % NUM_USER_BUCKETS
})
```

用户 ID 的 SHA256 哈希取前 8 个十六进制字符（32 位整数），对 30 取模，得到 0-29 的桶号。`memoize` 确保整个进程只计算一次。

**为什么用哈希分桶而不是直接计数？** 源码注释解释得很清楚：

> For alerting purposes, we want to alert on the number of users impacted by an issue, rather than the number of events — often a small number of users can generate a large number of events (e.g. due to retries). To approximate this without ruining cardinality by counting user IDs directly, we hash the user ID and assign it to one of a fixed number of buckets.

告警逻辑关心的是"多少用户受影响"，不是"多少事件被触发"。一个用户的重试可能产生数百条事件，如果按事件计数，单个用户就能触发误报。按用户分桶后，告警阈值可以设为"超过 5 个桶有错误"——近似于"超过 5 个用户受影响"。

30 个桶是一个工程权衡：太少（比如 10 个）精度不够，不同用户挤在同一个桶里；太多（比如 1000 个）又接近直接用用户 ID，失去基数控制的效果。30 个桶意味着约 3.3% 的统计精度——对于"是否值得告警"的判断足够了。

## ddtags 构建与可搜索性

`ddtags` 是 Datadog 日志中最关键的字段。它是一个逗号分隔的字符串，包含所有可搜索的标签：

```typescript
const TAG_FIELDS = [
  'arch', 'clientType', 'errorType', 'http_status_range', 'http_status',
  'kairosActive', 'model', 'platform', 'provider', 'skillMode',
  'subscriptionType', 'toolName', 'userBucket', 'userType', 'version',
  'versionBase',
]

const tags = [
  `event:${eventName}`,  // 事件名总是第一个标签
  ...TAG_FIELDS
    .filter(field => allDataRecord[field] !== undefined && allDataRecord[field] !== null)
    .map(field => `${camelToSnakeCase(field)}:${allDataRecord[field]}`),
]

const log: DatadogLog = {
  ddsource: 'nodejs',
  ddtags: tags.join(','),  // 'event:tengu_init,platform:darwin,arch:x64,...'
  message: eventName,
  service: 'claude-code',
  hostname: 'claude-code',
  env: process.env.USER_TYPE,
}
```

`TAG_FIELDS` 是一个精心挑选的列表——只有这些字段会成为 Datadog 标签。标签和普通字段的区别在于：标签可以被索引和搜索，但每个唯一标签值都会增加 Datadog 的计费。因此 `TAG_FIELDS` 只包含低基数字段（`platform`、`arch`、`version`），高基数字段（如 `sessionId`）只在日志体中作为普通字段存在。

字段名通过 `camelToSnakeCase()` 转换为 snake_case——Datadog 的最佳实践是 snake_case 标签名，和上一篇 1P 格式转换的策略一致。

```typescript
function camelToSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
}
// 'userBucket' → 'user_bucket'
// 'http_status_range' → 'http_status_range'（已经是 snake_case，不变）
```

除了标签，还有一个值得注意的字段转换——HTTP 状态码：

```typescript
// status → http_status + http_status_range
if (allData.status !== undefined && allData.status !== null) {
  const statusCode = String(allData.status)
  allData.http_status = statusCode  // "503"

  const firstDigit = statusCode.charAt(0)
  if (firstDigit >= '1' && firstDigit <= '5') {
    allData.http_status_range = `${firstDigit}xx`  // "5xx"
  }

  delete allData.status  // 删除原始字段
}
```

`status` 是 Datadog 的保留字段名——如果日志中直接出现 `status` 字段，Datadog 会把它当作自己的状态字段处理，而不是自定义属性。因此代码把 `status` 重命名为 `http_status`，同时生成一个 `http_status_range`（如 `5xx`）作为额外的标签维度。

`http_status_range` 被列入 `TAG_FIELDS`，这意味着可以在 Datadog 仪表盘中按状态码范围过滤——"所有 5xx 错误"这种查询在一秒内完成。

## 批量刷新机制

Datadog 不逐条发送日志，而是批量提交。核心机制由三个函数协作完成：

```typescript
let logBatch: DatadogLog[] = []
let flushTimer: NodeJS.Timeout | null = null

function scheduleFlush(): void {
  if (flushTimer) return  // 已有定时器 → 不重复调度

  flushTimer = setTimeout(() => {
    flushTimer = null
    void flushLogs()
  }, getFlushIntervalMs()).unref()  // .unref() 确保不阻止进程退出
}
```

`scheduleFlush()` 在每次事件入队后调用。如果已有定时器在跑，不做任何事——这意味着**从第一条事件到定时器触发之间，所有事件都积累在内存中**。15 秒的窗口内可能积累数十条事件，一次 HTTP 请求全部发出。

`flushLogs()` 是实际执行网络请求的函数：

```typescript
async function flushLogs(): Promise<void> {
  if (logBatch.length === 0) return

  const logsToSend = logBatch
  logBatch = []  // 先清空，防止发送期间的错误导致重复发送

  try {
    await axios.post(DATADOG_LOGS_ENDPOINT, logsToSend, {
      headers: {
        'Content-Type': 'application/json',
        'DD-API-KEY': DATADOG_CLIENT_TOKEN,
      },
      timeout: NETWORK_TIMEOUT_MS,  // 5 秒超时
    })
  } catch (error) {
    logError(error)  // 只记录错误，不重试
  }
}
```

**先清空再发送**的设计值得注意。`logBatch` 在发送前就被清空（`logBatch = []` 在 `axios.post` 之前执行）。这意味着发送期间产生的新事件会进入一个新的空数组，不会被这次请求包含，也不会被丢失——它们会在下一次刷新时发送。

发送失败时的处理是**fire-and-forget**：`catch` 块只调用 `logError()` 记录错误，不重试。上一篇讲了这是因为 Datadog 是 best-effort 通道——1P 才是有磁盘重试保障的可靠通道。如果 Datadog 发送失败，关键事件仍然通过 1P 到达 BigQuery，只是 Datadog 仪表盘上暂时看不到。

批量大小超过 100 条时触发**立即刷新**：

```typescript
logBatch.push(log)

if (logBatch.length >= MAX_BATCH_SIZE) {
  // 满 100 条 → 取消定时器，立即发送
  if (flushTimer) {
    clearTimeout(flushTimer)
    flushTimer = null
  }
  void flushLogs()
} else {
  scheduleFlush()  // 未满 → 确保有定时器在跑
}
```

这种"时间触发 + 容量触发"的双阈值设计是批量发送的标准模式。15 秒的延迟对于告警场景可接受，但如果 15 秒内积累了 100 条错误事件（比如大规模 API 故障），立即发送比等待定时器更有意义。

`setTimeout` 的 `.unref()` 调用是一个细节但重要的决定——它告诉 Node.js 事件循环，这个定时器不需要阻止进程退出。如果没有 `.unref()`，即使所有工作完成，进程也会等待 15 秒的定时器到期才能退出。

## 优雅关闭

进程退出前需要把内存中的日志刷出。`shutdownDatadog()` 负责这件事：

```typescript
export async function shutdownDatadog(): Promise<void> {
  if (flushTimer) {
    clearTimeout(flushTimer)
    flushTimer = null
  }
  await flushLogs()
}
```

源码注释解释了为什么需要主动调用它：

> Called from gracefulShutdown() before process.exit() since forceExit() prevents the beforeExit handler from firing.

`process.exit()` 会立即终止进程，不会等待异步操作完成。如果 `logBatch` 中还有未发送的日志，它们会随着进程退出而丢失。`gracefulShutdown()` 在调用 `forceExit()` 之前先 `await shutdownDatadog()`，确保最后一批日志被发出。

## 总结

- Datadog 的日志结构围绕 **`ddtags` 字段**构建可搜索性——事件名必须编码为 `event:<name>` 放入标签，因为 `message` 字段在 Datadog 查询中不可搜索。
- **事件白名单**约 40 个事件，聚焦于运维告警场景（生命周期、API 错误、工具异常、OAuth 竞争、未捕获异常），不做全量数据分析。
- **三层门控**（生产环境、第一方 Provider、白名单）加上 GrowthBook 远程开关，形成了四层过滤体系，保证只有正确的环境中的正确事件到达 Datadog。
- **基数控制**通过工具名归一化（`mcp`）、模型名缩短（规范名或 `other`）、版本号截断（去掉时间戳和 SHA）、用户分桶（30 桶 SHA256）四种策略控制标签数量。
- **批量刷新**采用 15 秒定时器 + 100 条满载双阈值，`setTimeout.unref()` 确保不阻止进程退出。
- **优雅关闭**在 `process.exit()` 前同步刷出内存日志，`shutdownDatadog()` 是最后一道保障。

> 下一篇将进入第 14 章——设计哲学，分析 Claude Code 在架构决策中的价值取舍和工程权衡。

## 参考链接

- [Claude Code Datadog 源码](file:///E:/Projects/external/claude-code/src/services/analytics/datadog.ts)
- [Datadog Logs API v2 文档](https://docs.datadoghq.com/api/latest/logs/)
- [Datadog 标签最佳实践](https://docs.datadoghq.com/getting_started/tagging/)
- [Node.js setTimeout.unref() 文档](https://nodejs.org/api/timers.html#timeoutunref)
- [GrowthBook Feature Gates](https://docs.growthbook.io/lib/js#feature-flags)
