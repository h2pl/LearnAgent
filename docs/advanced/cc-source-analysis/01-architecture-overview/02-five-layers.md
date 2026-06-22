# 五层架构

上一篇我们看了 Claude Code 的代码地图，知道 51 万行代码里 98.4% 是工程基础设施。这一篇我们深入看看这些工程代码是怎么组织的。

Claude Code 的架构可以分成五层，从外到内依次是：CLI 入口层、Agent 循环层、工具执行层、权限控制层、系统提示层。每一层都有明确的职责，层与层之间的边界清晰得像是用尺子量出来的。

```
┌─────────────────────────────────────────┐
│         CLI 入口层 (entrypoints/)        │
│  cli.tsx → main.tsx → launchRepl()      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Agent 循环层 (query.ts)            │
│  while(true) { callModel → runTools }   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      工具执行层 (tools/)                │
│  Tool.ts → toolExecution.ts → 42 工具   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      权限控制层 (permissions/)          │
│  canUseTool() → 7 种模式 → ML 分类器    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      系统提示层 (prompts.ts)            │
│  53KB 动态提示词 + 缓存冻结             │
└─────────────────────────────────────────┘
```

这个分层不是随便画的。每一层都解决一个独立的问题：入口层解决"怎么启动"，循环层解决"怎么跑"，工具层解决"怎么执行"，权限层解决"怎么安全"，提示层解决"怎么告诉模型它能干什么"。

## 第一层：CLI 入口层

入口层是用户看到的第一个界面。你在终端里敲 `claude`，第一个被调用的不是 `main.tsx`，而是 `entrypoints/cli.tsx`。

```typescript
// entrypoints/cli.tsx
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Fast-path for --version: 零导入，直接退出
  if (args.length === 1 && (args[0] === '--version' || args[0] === '-v')) {
    console.log(`${MACRO.VERSION} (Claude Code)`);
    return; // 12ms 完成
  }

  // Fast-path for 各种子命令
  if (args[0] === 'daemon') {
    const { daemonMain } = await import('../daemon/main.js');
    await daemonMain(args.slice(1));
    return;
  }

  if (args[0] === 'remote-control' || args[0] === 'rc') {
    const { bridgeMain } = await import('../bridge/bridgeMain.js');
    await bridgeMain(args.slice(1));
    return;
  }

  // 都不匹配，才加载完整 CLI
  const { main: cliMain } = await import('../main.js');
  await cliMain();
}
```

入口层的设计原则是：**能跳过就跳过**。

`--version` 命令只需要打印版本号，不需要加载 51 万行代码。`cli.tsx` 检测到这个命令后，零导入，直接打印退出，12ms 完成。

子命令（如 `daemon`、`remote-control`）也只加载自己需要的模块。只有检测到是交互式 REPL，才加载完整的 `main.tsx`。

这个设计让 Claude Code 的启动速度做到了极致。用户敲下 `claude` 到看到 REPL 界面，整个流程被压缩到约 135ms。

入口层还做了一个关键优化：**并行预取**。

```typescript
// main.tsx 顶部 - 这 3 行必须在所有 import 之前
import { profileCheckpoint } from './utils/startupProfiler.js';
profileCheckpoint('main_tsx_entry');

import { startMdmRawRead } from './utils/settings/mdm/rawRead.js';
startMdmRawRead(); // 启动 MDM 子进程（plutil/reg query）

import { startKeychainPrefetch } from './utils/secureStorage/keychainPrefetch.js';
startKeychainPrefetch(); // 启动 macOS Keychain 读取

// 然后才开始 ~180 行 import
import { Command as CommanderCommand } from '@commander-js/extra-typings';
import chalk from 'chalk';
import React from 'react';
// ... 180+ 行 import
```

MDM 子进程和 Keychain 读取都是慢操作（分别需要 ~50ms 和 ~65ms）。如果不做优化，启动时间 = import 时间 + MDM 时间 + Keychain 时间 ≈ 135ms + 50ms + 65ms = 250ms。

但 `cli.tsx` 在 import 之前就启动了这两个操作，让它们与 ~180 行 import **并行进行**。import 完成时，预取也完成了，几乎零等待。启动时间从 250ms 降到 135ms，接近减半。

入口层的工作到这里结束。它把控制权交给 `main.tsx`，由 `main.tsx` 初始化 Commander、解析命令行参数、加载配置，然后进入 Agent 循环层。

## 第二层：Agent 循环层

Agent 循环层是 Claude Code 的心脏。整个 Agent 的运行逻辑都在这里。

```typescript
// query.ts - 简化版
while (true) {
  // 1. 调用模型
  const response = await callModel(messages);
  
  // 2. 执行模型请求的工具
  if (response.tool_use) {
    const results = await runTools(response.tool_use);
    messages.push(...results);
  }
  
  // 3. 判断是否继续
  if (response.stop_reason === 'end_turn') {
    break;
  }
}
```

没有复杂的 planner，没有状态机，没有多步编排图。模型读上下文，决定下一步干什么，调工具，观察结果，继续走。整个过程是完全由模型驱动的，它自己决定什么时候停下来，什么时候再跑一轮。

但实际的 `query.ts` 有 1612 行，远比这个简化版复杂。因为循环层要处理很多边界情况。

比如，当 LLM 的输出因 `max_output_tokens` 被截断时，循环不会直接结束，而是自动续写，最多重试 3 次。这保证了长回答不会被意外切断。

```typescript
// query.ts - State 类型
type State = {
  messages: Message[]                    // 对话历史
  toolUseContext: ToolUseContext         // 工具执行上下文
  autoCompactTracking: ...               // 自动压缩追踪
  maxOutputTokensRecoveryCount: number   // 输出截断恢复计数 (≤3)
  hasAttemptedReactiveCompact: boolean   // 是否尝试过响应式压缩
  turnCount: number                      // 当前轮次
  transition: Continue | undefined       // 上次循环的继续原因
}
```

循环状态是一个可变对象，跨迭代携带。每次循环都会更新这个状态，下一次循环可以读到上一次的结果。

循环层还要处理 7 种不同的 `transition.reason`，每种原因对应不同的继续策略：

- `next_turn` — 正常继续
- `reactive_compact_retry` — 响应式压缩后重试
- `auto_compact_retry` — 自动压缩后重试
- `micro_compact_retry` — 微压缩后重试
- `context_collapse_retry` — 上下文折叠后重试
- `snip_retry` — 裁剪后重试
- `budget_reduction_retry` — 预算削减后重试

这 7 种原因对应了 5 层压缩机制。当上下文快满时，循环会尝试不同的压缩策略，然后重试。这个逻辑不在循环层实现，但循环层要协调它们。

循环层的工作是"让 Agent 跑起来"。它调用模型，执行工具，处理边界情况，决定什么时候继续、什么时候停止。但具体怎么执行工具、怎么保证安全，是下面两层的事。

## 第三层：工具执行层

工具执行层负责把模型的"我想用这个工具"变成真正的操作。

```typescript
// Tool.ts - 工具接口
interface Tool {
  name: string;
  inputSchema: ZodSchema;
  call(input, context): Promise<ToolResult>;
  
  // 元数据
  prompt(): string;              // 向模型描述自己
  isReadOnly(): boolean;         // 是否只读
  isConcurrencySafe(): boolean;  // 能否并发
  isDestructive(): boolean;      // 是否有破坏性
  
  // 权限
  checkPermissions(): PermissionResult;
}
```

工具不是简单的函数，而是带权限、描述、UI 的完整对象。每个工具都要告诉模型"我能做什么"，告诉权限系统"我有什么风险"，告诉 UI "我长什么样"。

Claude Code 有 42 个内置工具，从 `BashTool`（执行命令）到 `EditTool`（编辑文件）到 `AgentTool`（启动子 Agent）。每个工具都实现了 `Tool` 接口。

工具执行层的核心是 `toolExecution.ts`，它负责：

1. **校验输入**：用 Zod Schema 检查模型给的参数是否合法
2. **权限检查**：调用权限控制层，问"这个操作允许吗"
3. **执行工具**：调用工具的 `call` 方法
4. **处理结果**：把结果格式化，喂回给模型

工具执行层还有一个关键设计：**并发调度**。

```typescript
// Tool.ts - 并发安全标记
interface Tool {
  isConcurrencySafe(): boolean;  // 能否并发
}
```

有些工具可以并发执行（如多个 `ReadTool`），有些不能（如 `BashTool` 可能修改文件）。工具执行层根据这个标记决定哪些工具可以并行、哪些必须串行。

并发调度让工具执行更快。如果模型一次请求了 3 个 `ReadTool`，工具执行层会同时执行它们，而不是串行等待。

工具执行层的工作是"让工具跑起来"。它校验输入、检查权限、执行工具、处理结果。但具体怎么判断"这个操作是否安全"，是下一层的事。

## 第四层：权限控制层

权限控制层是 Claude Code 的安全屏障。它的职责是回答一个问题：**这个操作允许吗？**

```typescript
// 三层防护结构
// 第 1 层：工具注册过滤
// 被禁的工具直接从模型视野里移除，模型连看都看不到

// 第 2 层：单次调用检查
// 每次工具调用都根据工具名、参数、工作目录做规则验证

// 第 3 层：交互式询问
// 没有匹配规则时实时问用户，用户的回答变成当前 session 的规则
```

三层防护，层层递进。

第一层在工具注册时就过滤掉被禁的工具。如果某个工具被禁用，模型根本看不到它，也就不会调用它。这是最彻底的拦截。

第二层在每次工具调用时做规则验证。规则可以基于工具名、参数、工作目录等多个维度。比如可以设置"允许 `ReadTool` 读取 `/tmp` 目录，但禁止读取 `/etc` 目录"。

第三层是最后防线。如果没有匹配的规则，就实时问用户。用户的回答会变成当前 session 的规则，下次遇到同样的操作就不再询问。

权限控制层还支持 7 种运行模式：

- `default` — 只对高风险操作询问
- `auto` — ML 分类器自动判断
- `plan` — 只读模式，不执行任何修改
- `bypassPermissions` — 完全信任，用于沙箱环境
- 还有 3 种模式用于特殊场景

8 级规则优先级确保规则的冲突能被正确解决：

```
Policy（全局策略）> User（用户配置）> Project（项目配置）> Local（本地配置）
> CLI flag > cliArg > command > session
```

权限控制层的设计哲学是：**安全不应该是粗暴的全部拦截，而是精确地只拦那些真正需要人判断的操作。**

`auto` 模式是权限控制层最复杂的部分。它用一个 ML 分类器自动判断"这个操作是否安全"。分类器根据工具名、参数、工作目录等多个特征做预测，输出"允许"或"拒绝"。

ML 分类器的训练数据来自用户的历史决策。当用户在第三层回答"允许"或"拒绝"时，这个决策会被记录下来，用于训练分类器。随着用户的使用，分类器会越来越准确，询问的次数会越来越少。

权限控制层的工作是"让操作安全"。它判断每个操作是否允许，处理规则冲突，用 ML 分类器减少询问次数。但具体怎么告诉模型"你能干什么"，是下一层的事。

## 第五层：系统提示层

系统提示层是 Claude Code 的"说明书"。它告诉模型：你能用什么工具、你不能做什么、你应该怎么行为。

```typescript
// 系统提示词 = 数百个碎片动态拼装
systemPrompt = [
  ...getBasePrompt(),           // 基础指令
  ...getSafetyRules(),          // 安全守则（~5677 token）
  ...getToolDescriptions(),     // 工具描述
  ...getProjectContext(),       // 项目上下文（CLAUDE.md）
  ...getModeSpecificRules(),    // 模式特定规则
  ...getUserPreferences(),      // 用户偏好
];
```

Claude Code 的系统提示不是一个静态的字符串，而是数百个提示碎片在运行时动态拼装。根据模式、工具和上下文的不同，注入不同的提示片段。

光是安全守则就有约 5,677 个 token——相当于两万字的行为规范，每次对话都带进去。

系统提示层的核心挑战是**缓存**。

50-70K token 的系统提示词被缓存在服务器端。如果两次请求的系统提示词完全一样，服务器可以直接返回缓存的结果，节省大量计算。

但如果中途修改了系统提示词（比如切换了权限模式、加载了新的 CLAUDE.md），缓存就失效了，下次请求需要重新计算。重新计算的成本是 12 倍。

系统提示层设计了 **Sticky-on Latch** 机制来保护缓存。

```typescript
// bootstrap/state.ts - Sticky-on Latch 字段
type State = {
  // 一旦启用 auto mode，就保持发送 header
  afkModeHeaderLatched: boolean | null;
  
  // 一旦启用 fast mode，就保持发送 header
  fastModeHeaderLatched: boolean | null;
  
  // 一旦启用 cached microcompact，就保持发送 header
  cacheEditingHeaderLatched: boolean | null;
};
```

这些字段初始为 `null`，一旦设为 `true`，就保持 `true`。即使中途切换模式（如 Shift+Tab 切换 auto mode），header 也保持发送。这样服务器端的提示缓存就不会因为 header 变化而失效。

系统提示层还要处理 **DYNAMIC_BOUNDARY** 概念。

系统提示词分为两部分：静态部分（基础指令、安全守则）和动态部分（工具描述、项目上下文）。静态部分可以缓存，动态部分每次都要重新计算。

DYNAMIC_BOUNDARY 是静态和动态的分界线。分界线以上的内容可以缓存，分界线以下的内容每次都变。系统提示层要确保分界线的位置正确，避免动态内容污染静态缓存。

系统提示层的工作是"告诉模型它能干什么"。它动态拼装提示词、保护缓存、处理静态和动态的边界。

## 层与层之间的数据流

五层架构不是孤立的，层与层之间有明确的数据流。

用户输入从入口层进入，经过循环层、工具层、权限层、提示层，最终到达模型。模型的输出从提示层返回，经过权限层、工具层、循环层，最终到达用户。

```
用户输入
  ↓
入口层（cli.tsx → main.tsx）
  ↓
循环层（query.ts）
  ↓
工具层（Tool.ts → toolExecution.ts）
  ↓
权限层（canUseTool()）
  ↓
提示层（prompts.ts）
  ↓
模型（API 调用）
  ↓
提示层（解析响应）
  ↓
权限层（检查结果）
  ↓
工具层（执行工具）
  ↓
循环层（更新状态）
  ↓
用户输出
```

每一层都只做自己的事，不越界。入口层不关心工具怎么执行，循环层不关心权限怎么判断，工具层不关心提示词怎么拼装。

这种分层设计让 Claude Code 的代码结构清晰、职责明确。每一层都可以独立测试、独立优化、独立替换。

## 小结

Claude Code 的五层架构，从外到内依次是：CLI 入口层、Agent 循环层、工具执行层、权限控制层、系统提示层。

每一层都解决一个独立的问题：入口层解决"怎么启动"，循环层解决"怎么跑"，工具层解决"怎么执行"，权限层解决"怎么安全"，提示层解决"怎么告诉模型它能干什么"。

层与层之间的边界清晰，数据流明确。每一层都只做自己的事，不越界。

这种分层设计让 Claude Code 的 51 万行代码结构清晰、职责明确。每一层都可以独立测试、独立优化、独立替换。

下一章，我们看看 Claude Code 和其他 Agent 框架的对比，看看它的架构有什么优势和劣势。
