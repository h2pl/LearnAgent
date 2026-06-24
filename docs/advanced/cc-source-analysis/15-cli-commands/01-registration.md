# 命令注册与分发：40+ slash 命令如何"和平共处"

> `commands.ts` 有 755 行，管理着 40+ 内置命令、动态加载的 Skills、Plugin 命令和 MCP Skills。但它不只是一个大数组——它用三层过滤（来源汇聚 → 可用性检查 → 启用开关）+ memoize 缓存，确保命令的加载和过滤既快又准确。

你好，我是江小湖。

上一章 [设计哲学](../14-design-philosophy/README.md) 讲了 Claude Code 的价值观和工程取舍。一个清晰的例子就是 `/commit` 命令——每个 commit message 都经过 Undercover Mode 的安全检查。而 `/commit` 只是 40+ slash 命令中的一个。

本文拆解 Claude Code 的命令注册和分发系统，看它是如何让不同来源的几十个命令和平共处的。

## 目录

- [命令的四层来源](#命令的四层来源)
- [Command 类型系统](#command-类型系统)
- [注册流程：从导入到汇聚](#注册流程从导入到汇聚)
- [过滤链：三层关卡的协同](#过滤链三层关卡的协同)
- [缓存策略](#缓存策略)
- [动态发现](#动态发现)
- [总结](#总结)
- [参考链接](#参考链接)

## 命令的四层来源

Claude Code 的命令来自四个完全不同的目录和加载机制：

```text
1. 内置命令 (built-in)     — commands.ts 硬编码导入，如 /commit /init /compact
2. Skills 目录 (skills)     — ~/.claude/skills/ 或项目 .claude/skills/
3. 插件命令 (plugin)        — MCP 插件提供的命令
4. 动态 Skills (dynamic)    — 运行中由 Agent 创建的 skills
```

这四层在 `commands.ts` 的 `loadAllCommands()` 中汇聚：

```typescript
const loadAllCommands = memoize(async (cwd: string): Promise<Command[]> => {
  const [
    { skillDirCommands, pluginSkills, bundledSkills, builtinPluginSkills },
    pluginCommands,
    workflowCommands,
  ] = await Promise.all([
    getSkills(cwd),         // Skills 目录 + Plugin Skills + Bundled + Builtin
    getPluginCommands(),    // 插件命令
    getWorkflowCommands ? getWorkflowCommands(cwd) : Promise.resolve([]),
  ])

  return [
    ...bundledSkills,           // 最高优先级：内置 Skills
    ...builtinPluginSkills,     // 内置插件 Skills
    ...skillDirCommands,        // 用户项目 Skills
    ...workflowCommands,        // Workflow 脚本
    ...pluginCommands,          // MCP 插件命令
    ...pluginSkills,            // 插件提供的 Skills
    ...COMMANDS(),              // 最后：内置命令（优先级最低）
  ]
})
```

**优先级设计**：数组末尾的命令在重名时覆盖前面的。所以用户项目 Skills 可以覆盖内置命令的同名实现——后加载者胜。

## Command 类型系统

`types/command.ts` 定义了两种主要命令类型：

### PromptCommand（提示词型命令）

```typescript
type PromptCommand = {
  type: 'prompt'
  progressMessage: string         // 执行时显示的进度信息
  contentLength: number           // 提示词长度（用于 token 预估）
  argNames?: string[]             // 参数名列表
  allowedTools?: string[]         // 限用的工具白名单
  model?: string                  // 指定模型
  source: 'builtin' | 'mcp' | 'plugin' | 'bundled'
  disableNonInteractive?: boolean // 非交互模式下禁用
  hooks?: HooksSettings           // 执行时的 Hook
  context?: 'inline' | 'fork'     // 内联执行 vs 子 Agent
  agent?: string                  // fork 时用的 agent 类型
  paths?: string[]                // 文件路径触发条件
  getPromptForCommand(            // 核心：生成提示词的函数
    args: string,
    context: ToolUseContext,
  ): Promise<ContentBlockParam[]>
}
```

### LocalJSXCommand（React/Ink 型命令）

```typescript
type LocalJSXCommand = {
  type: 'local-jsx'
  load: () => Promise<LocalJSXCommandModule>  // 懒加载
}
```

以 `/init` 为例——它需要展示表单、交互式菜单，所以用了 React/Ink 的 `local-jsx` 类型。

## 注册流程：从导入到汇聚

### 第一步：静态导入（内置命令）

`commands.ts` 的顶部是 120 行 import 语句。每个命令模块独立导入：

```typescript
import addDir from './commands/add-dir/index.js'
import commit from './commands/commit.js'
import compact from './commands/compact/index.js'
import doctor from './commands/doctor/index.js'
import init from './commands/init.js'
// ... 40+ 个导入
```

### 第二步：条件导入（Feature-flagged 命令）

```typescript
const buddy = feature('BUDDY')
  ? require('./commands/buddy/index.js').default
  : null

const proactive =
  feature('PROACTIVE') || feature('KAIROS')
    ? require('./commands/proactive.js').default
    : null
```

这些 `require()` 调用会被 Bun 做 Dead Code Elimination——外部构建中，`feature('BUDDY')` 永远返回 `false`，整个 `require('./commands/buddy/index.js')` 就被从产物中移除了。

### 第三步：惰性导入（insights 的 113KB 模块）

`/insights` 命令生成会话分析报告，它的模块有 119KB（3200 行）。不能在每个启动中都加载这个重量级模块：

```typescript
const usageReport: Command = {
  type: 'prompt',
  name: 'insights',
  description: 'Generate a report analyzing your Claude Code sessions',
  source: 'builtin',
  async getPromptForCommand(args, context) {
    const real = (await import('./commands/insights.js')).default
    if (real.type !== 'prompt') throw new Error('unreachable')
    return real.getPromptForCommand(args, context)
  },
}
```

`import('./commands/insights.js')` 是动态 import——直到用户真的输入 `/insights` 才会加载这个 119KB 的模块。

### 第四步：内部命令隔离

Anthropic 内部有 29 个命令不能暴露给外部用户。它们被集中放在 `INTERNAL_ONLY_COMMANDS` 数组里：

```typescript
export const INTERNAL_ONLY_COMMANDS = [
  backfillSessions,
  breakCache,
  bughunter,
  commit,
  commitPushPr,
  ctx_viz,
  goodClaude,
  // ... 共 29 个内部命令
].filter(Boolean)

// 在 COMMANDS() 的最后：
...(process.env.USER_TYPE === 'ant' && !process.env.IS_DEMO
  ? INTERNAL_ONLY_COMMANDS
  : []),
```

因为 `USER_TYPE` 是 Bun 构建时常量，外部构建中 `USER_TYPE === 'ant'` 条件永远不会成立，这 29 个命令被 DCE 完全消除。

## 过滤链：三层关卡的协同

汇聚后的命令列表不是直接返回的。经过三道过滤：

### 过滤 1：availability（可用性检查）

```typescript
export function meetsAvailabilityRequirement(cmd: Command): boolean {
  if (!cmd.availability) return true  // 无声明 → 默认可用
  for (const a of cmd.availability) {
    switch (a) {
      case 'claude-ai':
        if (isClaudeAISubscriber()) return true
        break
      case 'console':
        if (!isClaudeAISubscriber() &&
            !isUsing3PServices() &&
            isFirstPartyAnthropicBaseUrl())
          return true
        break
    }
  }
  return false
}
```

`availability: ['claude-ai', 'console']` 表示这个命令只对 claude.ai 订阅者或控制台 API key 用户显示。Bedrock/Vertex 用户看不到它。

### 过滤 2：isEnabled（Feature Flag 检查）

```typescript
export function isCommandEnabled(cmd: CommandBase): boolean {
  return cmd.isEnabled?.() ?? true  // 默认启用
}
```

每个命令可以有自己的 `isEnabled` 函数，里面可能是 GrowthBook A/B 实验、环境变量检查或功能门控。

### 过滤 3：动态去重

```typescript
export async function getCommands(cwd: string): Promise<Command[]> {
  const allCommands = await loadAllCommands(cwd)
  const dynamicSkills = getDynamicSkills()

  const baseCommands = allCommands.filter(
    _ => meetsAvailabilityRequirement(_) && isCommandEnabled(_),
  )

  // 动态 skills 只添加不重复的
  const baseCommandNames = new Set(baseCommands.map(c => c.name))
  const uniqueDynamicSkills = dynamicSkills.filter(
    s => !baseCommandNames.has(s.name) &&
         meetsAvailabilityRequirement(s) &&
         isCommandEnabled(s),
  )
  // ...
}
```

动态 Skills（运行时创建的）在去重检查后才插入列表中。**插入位置**在 Plugin Skills 之后、Built-in Commands 之前——保证动态 Skills 可以覆盖 Plugin Skills，但不会意外覆盖内置命令。

## 缓存策略

命令系统用了两层 memoize：

```typescript
const loadAllCommands = memoize(async (cwd: string): Promise<Command[]>) => { ... }
const COMMANDS = memoize((): Command[] => [ ... ])
```

`loadAllCommands` **按 cwd 缓存**——切换项目目录时会重新加载。`COMMANDS` 是全局缓存——内置命令列表不变。

`getCommands()` 不在 memoize 内，但 `loadAllCommands` 的缓存让它很快：

```typescript
// 每次调用都执行 availability + isEnabled 检查
// 但 loadAllCommands 只在第一个调用时真正执行 I/O
export async function getCommands(cwd: string): Promise<Command[]> {
  const allCommands = await loadAllCommands(cwd)  // 有缓存
  // ... availability + isEnabled 过滤（纯 CPU，快速）
}
```

这个设计让 auth 状态变化（如 `/login`）能立即反映在命令列表里——不需要清缓存。

## 动态发现

### SkillTool：模型可调用命令的发现

`getSkillToolCommands` 从所有命令中过滤出**模型可以直接调用的**：

```typescript
export const getSkillToolCommands = memoize(async (cwd: string) => {
  const allCommands = await getCommands(cwd)
  return allCommands.filter(
    cmd =>
      cmd.type === 'prompt' &&
      !cmd.disableModelInvocation &&
      cmd.source !== 'builtin' &&
      (cmd.loadedFrom === 'bundled' ||
        cmd.loadedFrom === 'skills' ||
        cmd.loadedFrom === 'commands_DEPRECATED' ||
        cmd.hasUserSpecifiedDescription ||
        cmd.whenToUse),
  )
})
```

关键过滤条件：**必须显式声明描述（`hasUserSpecifiedDescription` 或 `whenToUse`）**。没有描述的 Skill 被视为"未完成"，不会暴露给模型调用。

### MCP Skills 的特殊路径

MCP 命令来自外部 MCP Server，不走 `getCommands()` 的过滤链。而是通过 `getMcpSkillCommands()` 单独获取：

```typescript
export function getMcpSkillCommands(
  mcpCommands: readonly Command[],
): readonly Command[] {
  if (feature('MCP_SKILLS')) {
    return mcpCommands.filter(
      cmd =>
        cmd.type === 'prompt' &&
        cmd.loadedFrom === 'mcp' &&
        !cmd.disableModelInvocation,
    )
  }
  return []
}
```

MCP Skills 必须在 `MCP_SKILLS` feature flag 开启时才可用。这为外部 MCP Skills 提供了另一层安全控制。

## 总结

Claude Code 的命令注册系统看似简单——就是一个大数组加几层过滤。但设计中的几个关键决策值得注意：

1. **四层来源、统一接口**——内置命令、Skills 目录、Plugin 命令、动态 Skills 都用相同的 `Command` 类型，使过滤和显示逻辑完全复用
2. **后加载胜出**——数组末尾的同名命令覆盖前面的，让用户自定义 Skills 无缝覆盖内置行为
3. **缓存 + 实时检查分层**——昂贵的 I/O（文件扫描）在 memoize 内，轻量的 auth/feature flag 检查每次重算
4. **DCE 保护**——内部命令、feature-flagged 命令在外部构建中被 Bun 的 Dead Code Elimination 移除
5. **惰性加载**——119KB 的 `/insights` 模块只在真实调用时加载

这些设计让 40+ 命令的管理保持了可预测性：性能瓶颈在缓存、权限控制在过滤、可扩展性在统一接口。

下一篇文章 [命令生命周期](./02-lifecycle.md) 将继续深入，看命令从解析到执行的完整流程。

## 参考链接

- `src/commands.ts` — 命令注册和分发的总入口（755 行）
- `src/types/command.ts` — Command 类型定义（218 行）
- `src/commands/init.ts` — `/init` 命令（21217 字节，包含新旧两版提示词）
- `src/commands/commit.ts` — `/commit` 命令（含 Undercover 检查）
- `src/utils/slashCommandParsing.ts` — Slash 命令解析工具
- [How Claude Code Builds a System Prompt](https://www.dbreunig.com/2026/04/04/how-claude-code-builds-a-system-prompt.html) — dbreunig 的系统提示词可视化分析（外部参考）
- [Inside Claude Code: Architecture Deep Dive](https://zainhas.github.io/blog/2026/inside-claude-code-architecture/) — Zain Hasan 的架构全景图
- [Dive into Claude Code (arxiv)](https://arxiv.org/html/2604.14228v1) — VILA-Lab 的学术级源码分析
