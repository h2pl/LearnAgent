# 五层架构

> Claude Code 的 51 万行代码可以拆成五层：CLI 入口层、Agent 循环层、工具执行层、权限控制层和系统提示层。每一层职责单一，边界清晰。

你好，我是江小湖。

上一篇 [51 万行的真相](./01-overview.md) 讲到，Claude Code 的源码里 98% 以上都是工程基础设施。这一篇解决一个更具体的问题：**这 51 万行代码内部是怎么组织的？**

把代码按职责分层后，会得到一个清晰的五层结构。理解这个分层，就能在后续阅读每一章时知道"这段代码属于哪一层、解决什么问题"。

## 目录

- [CLI 入口层](#cli-入口层)
- [Agent 循环层](#agent-循环层)
- [工具执行层](#工具执行层)
- [权限控制层](#权限控制层)
- [系统提示层](#系统提示层)
- [层与层的数据流](#层与层的数据流)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/01-architecture-overview/comparison.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 01 配图</em>
</p>

## 整体分层

<p align="center">
  <img src="../../../../assets/cc-source-analysis/01-architecture-overview/five-layers.svg" alt="Claude Code 五层架构" width="90%"/>
  <br/>
  <em>Claude Code 五层架构：从入口到模型调用</em>
</p>

| 层级 | 主要文件/目录 | 核心职责 |
|------|--------------|----------|
| CLI 入口层 | `entrypoints/`, `main.tsx` | 解析命令、选择运行模式、启动优化 |
| Agent 循环层 | `query.ts`, `QueryEngine.ts` | while 循环驱动模型调用与工具执行 |
| 工具执行层 | `Tool.ts`, `tools/`, `toolExecution.ts` | 把模型的意图变成具体操作 |
| 权限控制层 | `utils/permissions/`, `permissions/` | 判断每个操作是否被允许 |
| 系统提示层 | `constants/prompts.ts` | 动态拼装给模型的指令和上下文 |

这五层从外到内，把"用户输入 → 模型决策 → 工具执行 → 结果返回"整个链路串了起来。

## CLI 入口层

CLI 入口层是用户看到的第一个界面。敲下 `claude` 后，第一个被调用的是 `entrypoints/cli.tsx`。

```typescript
// entrypoints/cli.tsx（简化）
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Fast-path：--version 命令零导入，直接退出
  if (args.length === 1 && args[0] === '--version') {
    console.log(`${MACRO.VERSION} (Claude Code)`);
    return; // 12ms 内完成
  }

  // 子命令分发：daemon / remote-control 各自加载所需模块
  if (args[0] === 'daemon') {
    const { daemonMain } = await import('../daemon/main.js');
    await daemonMain(args.slice(1));
    return;
  }

  // 默认路径：加载完整 REPL
  const { main: cliMain } = await import('../main.js');
  await cliMain();
}
```

入口层的设计原则是**能跳过就跳过**。`--version` 只需要打印一行版本号，没必要加载 51 万行代码。只有确认是 REPL 模式，才导入完整的 `main.tsx`。

入口层还做了一个关键优化：在 import 阶段并行启动慢操作。`main.tsx` 开头先启动 MDM 子进程和 Keychain 读取，然后再执行 180 多行 import。等 import 完成时，这些 I/O 操作也基本结束了，启动时间从 250ms 降到约 135ms。

## Agent 循环层

Agent 循环层是 Claude Code 的心脏，整个 Agent 的运行逻辑都在这里。

```typescript
// query.ts（核心逻辑简化）
while (true) {
  const response = await callModel(messages);

  if (response.tool_use) {
    const results = await runTools(response.tool_use);
    messages.push(...results);
  }

  if (response.stop_reason === 'end_turn') {
    break;
  }
}
```

没有复杂的 planner，没有显式状态机。模型读上下文，决定调用什么工具，观察结果，继续循环。整个过程由模型驱动。

但实际的 `query.ts` 有 1612 行，因为它要处理大量边界情况：

- `max_output_tokens` 截断时自动续写，最多 3 次
- 上下文快满时触发 5 种压缩策略
- 工具执行失败时通过 `siblingAbortController` 级联取消
- 记录 `transition.reason`，共有 7 种继续原因

循环层的状态用一个可变对象 `State` 跨迭代携带，包含消息历史、工具上下文、压缩追踪、轮次计数等字段。

## 工具执行层

工具执行层负责把模型的"调用意图"变成真正的操作。

```typescript
// Tool.ts（工具接口简化）
interface Tool {
  name: string;
  inputSchema: ZodSchema;
  prompt(): string;              // 向模型描述自己
  isReadOnly(): boolean;         // 是否只读
  isConcurrencySafe(): boolean;  // 是否可并发
  isDestructive(): boolean;      // 是否有破坏性
  call(input, context): Promise<ToolResult>;
}
```

Claude Code 内置了 42 个工具，从 `BashTool` 到 `EditTool` 到 `AgentTool`。每个工具都要告诉模型"我能做什么"，告诉权限系统"我有什么风险"，告诉 UI "我该怎么展示"。

工具执行层的核心流程包括：

1. 用 Zod Schema 校验模型输入
2. 调用权限层检查是否允许
3. 根据 `isConcurrencySafe()` 决定串行还是并行
4. 执行工具 `call()` 方法
5. 格式化结果，喂回模型

并发调度是工具层的关键优化。如果模型一次请求 3 个 `ReadTool`，工具层会并行执行，而不是串行等待。

## 权限控制层

权限控制层回答一个问题：**这个操作允许吗？**

它有三层防护结构：

1. **注册过滤**：被禁用的工具直接从模型视野里移除
2. **调用检查**：每次工具调用都按规则验证
3. **交互询问**：没有匹配规则时实时问用户

Claude Code 支持 7 种运行模式，8 级规则优先级。`auto` 模式还会用一个 ML 分类器自动判断操作是否安全，随着用户使用，分类器会越来越准，询问次数逐渐减少。

权限层的核心设计哲学是：**安全不应该是粗暴的全盘拦截，而是精确地只拦截那些真正需要人判断的操作。**

## 系统提示层

系统提示层是 Claude Code 的"说明书"。它告诉模型：你能用什么工具、不能做什么、应该怎么行为。

系统提示不是静态字符串，而是数百个提示碎片在运行时动态拼装。根据模式、工具和上下文的不同，注入不同的片段。

```typescript
// 系统提示词 = 多个碎片拼接
systemPrompt = [
  ...getBasePrompt(),           // 基础指令
  ...getSafetyRules(),          // 安全守则（约 5677 Token）
  ...getToolDescriptions(),     // 工具描述
  ...getProjectContext(),       // 项目上下文（CLAUDE.md）
  ...getModeSpecificRules(),    // 模式特定规则
  ...getUserPreferences(),      // 用户偏好
];
```

系统提示层还要保护 **Prompt Cache**。50-70K Token 的系统提示词缓存在服务器端，如果中途切换 header 导致提示词变化，缓存就失效了。Claude Code 用 **Sticky-on Latch** 机制，一旦启用某个 header 就保持开启，避免缓存失效。

## 层与层的数据流

五层架构不是孤立的，层与层之间有明确的数据流。

```
用户输入
  ↓
CLI 入口层（cli.tsx → main.tsx）
  ↓
Agent 循环层（query.ts）
  ↓
工具执行层（Tool.ts → toolExecution.ts）
  ↓
权限控制层（canUseTool()）
  ↓
系统提示层（prompts.ts）
  ↓
模型（API 调用）
  ↓
系统提示层（解析响应）
  ↓
权限控制层（检查结果）
  ↓
工具执行层（执行工具）
  ↓
Agent 循环层（更新状态）
  ↓
用户输出
```

每一层只关心自己的事。入口层不碰工具执行，循环层不碰权限判断，工具层不碰提示词拼装。边界清晰的好处是：每一层可以独立测试、独立优化、独立替换。

## 总结

- Claude Code 的代码按职责分为五层：CLI 入口层、Agent 循环层、工具执行层、权限控制层、系统提示层。
- CLI 入口层负责启动和模式分发，核心优化是 Fast-path 和并行预取。
- Agent 循环层是 while 循环，负责驱动模型调用和工具执行。
- 工具执行层负责把模型意图变成操作，并支持并发调度。
- 权限控制层有三层防护，7 种模式 + 8 级优先级 + ML 分类器。
- 系统提示层动态拼装提示词，并保护 Prompt Cache。
- 层与层之间职责单一、数据流清晰，这是 Claude Code 稳定性的架构基础。

> 下一篇：[三大框架对比](./03-comparison.md)，看看 Claude Code、Hermes、OpenClaw 各自适合学什么。

## 参考链接

- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Dive into Claude Code — MBZUAI/UCL 论文](https://arxiv.org/abs/2604.14228)
- [Claude Code Source Map Leak Analysis](https://arstechnica.com/ai/2026/03/claude-code-source-code-leak-technical-analysis/)
- [Claude Code System Prompt Engineering](https://simonwillison.net/2026/Mar/24/claude-code-system-prompt/)
