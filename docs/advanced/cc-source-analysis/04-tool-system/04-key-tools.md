# 关键工具实现

> BashTool、FileEditTool 和 AgentTool 是 Claude Code 三个最核心的工具。BashTool 的 16 个文件承载了权限、安全、沙箱、Prompt 四大体系；FileEditTool 用 `replace_in_file` 避免了 AI 重写整个文件；AgentTool 把子 Agent 包装成"另一个工具调用"。

你好，我是江小湖。

前三篇介绍了工具系统的统一接口、执行流水线和并发调度。这一篇深入三个工具的设计取舍——它们的实现细节反映了 Claude Code 对安全、可靠性和可组合性的理解。

## 目录

- [BashTool：最复杂的工具](#bashtool最复杂的工具)
- [FileEditTool：精度优先于安全](#fileedittool精度优先于安全)
- [AgentTool：Agent 即工具](#agenttoolagent-即工具)
- [三类工具的设计对比](#三类工具的设计对比)
- [总结](#总结)
- [参考链接](#参考链接)

## BashTool：最复杂的工具

BashTool 是 Claude Code 里代码量最大的单一工具目录——16 个文件，总规模超过 40 万字符。它的复杂度来源于一个矛盾：Bash 是图灵完备的，没有显式 API 限制，任何安全策略都必须靠代码强制执行。

### 职责分工

| 文件 | 职责 | 规模 |
|------|------|------|
| `BashTool.tsx` | 工具接口实现、`call()`、进程管理 | 161KB |
| `bashPermissions.ts` | 权限规则匹配、模式过滤 | 101KB |
| `bashSecurity.ts` | 安全分类、危险命令检测 | 105KB |
| `readOnlyValidation.ts` | 只读模式命令验证 | 70KB |
| `pathValidation.ts` | 路径白名单/黑名单 | 45KB |
| `prompt.ts` | 动态生成工具描述 | 21KB |

BashTool 的 `call()` 方法不是简单的 `exec(command)`。它是一个完整的 Shell 会话生命周期管理：

1. 解析命令的 AST（`parseForSecurity`）
2. 用 AST 做安全分类——读/写/搜索/破坏性
3. 用 AST 做权限匹配——`Bash(git *:*)` 这类模式
4. 决定是否用沙箱（`shouldUseSandbox`）
5. 启动子进程，管理 stdin/stdout/stderr
6. 实时推送进度
7. 结果超过 30K 字符时，存到磁盘文件，只返回预览

### 安全分层的核心洞察

BashTool 的安全不是单一维度。它把"这个命令安全吗"拆成了三个独立判断：

- **isReadOnly**：这个命令会写文件吗？（`ls` = 是，`rm` = 否）
- **isConcurrencySafe**：这个命令能和其他命令同时跑吗？（`git status` = 是，`git commit` = 否）
- **isDestructive**：这个命令有不可逆后果吗？（`rm -rf` = 是，`cat` = 否）

这三个布尔值组合使用，而不是简单的一个"安全/不安全"标签。Plan 模式只允许 `isReadOnly: true`，并发调度看 `isConcurrencySafe`，权限提示看 `isDestructive`。

### Sed 编辑模式

BashTool 支持一个特殊模式——sed 编辑。当模型想做文件编辑但没有 `FileEditTool` 可用时（比如 Plan 模式限制），它可以通过 `sed` 命令改文件。BashTool 会检测 `sed` 命令并应用和 `FileEditTool` 同级别的安全检查。

### 幻象分类器优化

BashTool 的分类器检查是提前启动的（speculative check）。在权限系统的交互式对话框还在渲染的时候，分类器已经在对命令做安全分析了。等用户看到"是否允许"的弹窗时，分类结果通常已经就绪，减少了等待时间。

## FileEditTool：精度优先于安全

FileEditTool 是 Claude Code 的编辑器。和许多 AI 编辑器不同，它不重写整个文件——它用 `replace_in_file` 操作符做**精确替换**。

### 设计的核心取舍

| 方案 | 优点 | 缺点 |
|------|------|------|
| 重写整个文件 | 简单，不需要 diff | 大文件浪费 token；容易丢失手动修改 |
| 精确替换（CC 的方案） | 节省 token；不破坏手动修改 | 模型必须生成正确的 old_str |

Claude Code 选择了精确替换，因为它面向的是真实项目——文件可能有上千行，用户可能同时在 IDE 里手动编辑。重写整个文件会丢失手动的修改，也会浪费大量 token 在不变的代码上。

### 替换失败时的自愈

如果模型给的 `old_str` 在文件中找不到——比如文件在工具调用期间被用户手动修改了——FileEditTool 不会直接报错。它会：

1. 尝试模糊匹配（忽略空白差异）
2. 返回详细的错误消息，包含文件当前内容
3. 让模型根据最新内容重新制定替换方案

这个设计让 FileEditTool 在实际使用中非常可靠。即使用户在 AI 编辑时同时手动改代码，也不会出现"两个编辑冲突"的问题。

### 7 个文件的职责分工

除了核心的 `FileEditTool.ts`（21KB），还有 6 个配套文件：`types.ts` 定义数据结构，`utils.ts` 处理文本操作和 diff 算法，`prompt.ts` 向模型描述如何使用替换操作符，`constants.ts` 定义工具名和限制常量，以及 UI 渲染组件。

## AgentTool：Agent 即工具

AgentTool 是 Claude Code 最具哲学意义的工具。它把"启动一个子 Agent"包装成"调用一个工具"。

### 统一抽象的价值

从 Agent 循环的视角看，调用 AgentTool 和调用 BashTool 没有区别：

```
Agent 循环:
  → 模型输出 tool_use: { name: "Agent", args: { prompt: "分析数据库性能" } }
  → 工具执行层找到 AgentTool
  → AgentTool.call() 启动子 Agent
  → 子 Agent 跑完，返回结果
  → 结果塞回上下文
  → 模型继续决策
```

这种统一抽象带来了一个重要的好处：Agent 循环完全不需要知道子 Agent 的存在。它只是在处理一个"执行时间比较长、返回内容比较多"的工具调用。

### 子 Agent 的三种形态

AgentTool 支持三种执行形态：

1. **一次性（One-shot）**：立即执行，同步返回结果。用于简单的信息收集和单一任务。
2. **后台任务（Async）**：异步执行，通过 `TaskOutput` 工具获取结果。用于长时间运行的任务。
3. **Fork 模式**：在独立的 Git Worktree 中执行，不污染当前工作区。用于探索性任务。

### 上下文隔离

子 Agent 有独立的系统提示词、独立的消息历史、独立的工具权限。它和父 Agent 的通信只有两个通道：

- **输入**：父 Agent 传给 AgentTool 的 `prompt` 参数
- **输出**：子 Agent 返回的结果文本

这个设计很关键——如果子 Agent 和父 Agent 共享上下文，就会产生循环依赖：父 Agent 等待子 Agent，子 Agent 又要看父 Agent 的完整历史。上下文隔离打破了这个循环。

### Prompt 缓存共享

Fork 模式下的子 Agent 通过 `renderedSystemPrompt` 共享父 Agent 的系统提示词缓存。如果子 Agent 重新生成系统提示词（比如 GrowthBook 从 cold 变为 warm），就会导致缓存失效。共享冻结的提示词避免了这个问题。

## 三类工具的设计对比

| 维度 | BashTool | FileEditTool | AgentTool |
|------|----------|-------------|-----------|
| **复杂度来源** | 安全控制 | 可靠性 | 组合性 |
| **核心文件数** | 16 | 7 | 14 |
| **最主要的设计挑战** | 把图灵完备的 Bash 变成可控的工具 | 在 AI 编辑和手动编辑之间保持一致 | 把另一个 Agent 包装成无差别工具调用 |
| **失败处理** | 错误码 + 输出截断 | 模糊匹配 + 重新搜索 | 超时 + 部分结果返回 |
| **权限模型** | 三层安全判断 | 文件路径验证 | 子 Agent 隔离 |

三个工具面对的问题完全不同，但都遵守了同一个原则：**失败不会波及整个会话**。BashTool 的命令失败了，Agent 循环继续。FileEditTool 的替换失败了，模型再试一次。AgentTool 的子 Agent 超时了，部分结果仍然返回。

## 总结

- BashTool 用 16 个文件把图灵完备的 Bash 变成可控工具，安全判断拆为 isReadOnly/isConcurrencySafe/isDestructive 三个独立维度。
- FileEditTool 选择精确替换而非重写整个文件，以节省 token 并避免丢失手动修改，替换失败时支持模糊匹配自愈。
- AgentTool 把子 Agent 包装成"另一个工具调用"，让 Agent 循环完全不需要感知子 Agent 的存在。
- 三类工具的场景完全不同，但都遵守"失败不波及会话"的设计原则。
- 工具的设计取舍反映了 Claude Code 对安全、可靠性和可组合性的系统级思考。

> 下一篇：[CallModel 与 Sticky Latch](../05-llm-calling/01-callmodel.md)，看 Claude Code 如何管理 LLM 调用。

## 参考链接

- [Claude Code BashTool.tsx 源码](file:///E:/Projects/claude-code/src/tools/BashTool/BashTool.tsx)
- [Claude Code FileEditTool.ts 源码](file:///E:/Projects/claude-code/src/tools/FileEditTool/FileEditTool.ts)
- [Claude Code AgentTool.tsx 源码](file:///E:/Projects/claude-code/src/tools/AgentTool/AgentTool.tsx)
- [Claude Code 工具执行流水线](file:///E:/Projects/claude-code/src/services/tools/toolExecution.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
