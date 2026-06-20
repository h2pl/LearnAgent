# Claude Code 编程 Agent

> Anthropic 的终端原生编程 Agent。在命令行里和你对话，直接操作文件和 Git。Anthropic 内部约 90% 的生产代码由它生成。133K GitHub Stars，SWE-bench Verified 72%。

## 目录

- [Claude Code 是什么](#claude-code-是什么)
- [核心能力](#核心能力)
- [它能做什么](#它能做什么)
- [什么人适合 / 不适合](#什么人适合--不适合)
- [扩展生态](#扩展生态)
- [使用成本](#使用成本)
- [和同类产品的对比](#和同类产品的对比)
- [快速上手](#快速上手)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在[全景概览](./02-mainstream-agents.md)中你看到了编程 Agent 这个品类。Claude Code 是目前这个品类里关注度最高的产品——它定义了"编程 Agent 应该是什么样"。

## Claude Code 是什么

Claude Code 是 Anthropic 开发的**终端原生编程 Agent**。它不是一个 IDE 插件，也不是 Web 聊天界面——它就是一个 CLI 工具，你在终端里运行它，它通过自然语言和你协作。

**一句话定位**：住在你命令行里的结对编程伙伴。

它在一个终端进程内完成全部工作：读取你的代码库 → 规划多步操作 → 调用文件/Git/Shell 工具 → 运行测试 → 迭代修复。你定义目标，它执行过程。

<img src="../../assets/01-landscape/claude-code-hero.jpg" alt="Claude Code 终端界面" width="100%"/>

## 核心能力

| 能力 | 说明 |
|------|------|
| **代码生成与修改** | 读写文件、跨模块改动、项目级重构 |
| **Bug 排查** | 接收错误日志，定位根因并修复 |
| **代码重构** | 跨文件重命名、提取公共逻辑、框架迁移 |
| **Git 工作流** | 自动 commit、开 PR、Code Review |
| **测试驱动** | 写代码 → 跑测试 → 读错误 → 修复，自动循环 |
| **子 Agent 委派** | 复杂任务拆成子任务并行执行，不膨胀主会话上下文 |
| **Dynamic Workflows** | 自动拆解任务，编排子 Agent 完成，最后合成结果 |
| **Web 搜索与获取** | 查文档、搜方案、读网页 |
| **MCP 扩展** | 通过 MCP 连接数据库、API、内部工具 |
| **Computer Use** | 在 CLI 内操作桌面应用（macOS） |

## 它能做什么

**日常编码**：描述需求，它生成代码并写入文件。支持新增功能、修改现有代码、补充单元测试。自动跑测试，失败就继续修直到通过。

**项目级重构**：比如"把这个模块从 JavaScript 迁移到 TypeScript"——它分析所有依赖，逐步迁移，确保编译和测试通过。适合几十到上百个文件的大改动。

**Bug 修复**：贴入完整错误栈或描述异常行为，它搜索相关代码，定位根因，给出修复方案并应用。你只需要 review 结果。

**Code Review**：给一个 PR diff，它逐文件审查：潜在 Bug、安全风险、性能问题、代码风格。可以在 CI 中自动触发。

**深度研究**：对于大型任务（如"实现一个新功能模块"），Dynamic Workflows 自动将任务拆解为多个子任务，委派子 Agent 并行调研和编码，最后合成一个完整实现。

**远程与异步**：通过 Remote Control 在手机上继续桌面会话。通过 Channels 接收 Telegram/Discord 消息让 Claude 自动处理。通过 Routines 设置定时任务。

## 什么人适合 / 不适合

**适合**：习惯命令行的全栈和后端开发者。需要深度代码分析和跨文件重构的场景。已经在用 Git CLI 的团队。

**不适合**：不熟悉命令行的前端设计师。只需要行级补全（应该用 Copilot）。完全 GUI 驱动的工作流（应选 Cursor）。

**一个常见模式**：很多开发者日常用 Cursor 写代码，遇到大重构或 Bug 时切到 Claude Code。两者互补，不冲突。

## 典型工作流程

一个典型的 Claude Code 使用流程：

1. **启动**：在项目目录下运行 `claude`，Claude 自动读取 `CLAUDE.md` 了解项目规范和架构
2. **描述任务**："给用户模块添加重置密码功能，包括发送邮件和 Token 校验"
3. **分析规划**：Claude 搜索代码库理解现有用户模块结构，规划修改范围
4. **执行**：创建新文件、修改现有文件、运行测试
5. **迭代**：测试失败则读取错误、修复、重新运行，直到通过
6. **提交**：`git diff` 审查改动，确认后自动 commit

整个过程持续几分钟到几十分钟，你不需要中断手头其他工作。需要决策时（比如 API 设计选择）Claude 会停下来问你。

<p align="center"><img src="../../assets/01-landscape/claude-code-workflow.svg" alt="Claude Code工作流" width="90%"/><br/><em>图：Claude Code 典型工作流——从启动到提交</em></p>

## 五种交互界面

Claude Code 不止 CLI 一个入口：

| 界面 | 适合场景 |
|------|----------|
| **终端 CLI** | 深度编码、重构，最完整的 Agent 体验 |
| **VS Code 扩展** | 在编辑器内使用，不离开 IDE |
| **JetBrains 扩展** | 在 IntelliJ/WebStorm 中使用 |
| **桌面 App** | macOS 原生 App，有 UI 管理 MCP 连接 |
| **Web 界面** | 手机上继续会话，远程控制桌面 Agent |

所有界面共享同一个引擎，CLAUDE.md、Skills、MCP 配置在所有界面中一致可用。

## Agent Teams 与协作

2026 年 Q1 引入的 **Agent Teams** 让多个 Claude Code 实例以对等模式协作。不同于子 Agent 委派的"主-从"模式，Agent Teams 是**对等通信**——每个 Agent 有自己的任务和上下文，通过共享任务列表和点对点消息协调。

适合场景：
- **多模块并行开发**：一个 Agent 改前端，另一个改后端，第三个写测试
- **大型代码库分析**：多个 Agent 各自分析一个模块，汇总结果
- **持续集成**：CI 中多个 Agent 并行执行 Code Review、测试、文档生成

Agent SDK 则让你用 API 控制 Claude Code 的完整能力——构建自定义的 CI/CD 流水线、自动化工作流、或者将 Claude Code 嵌入你自己的工具中。

## 扩展生态

Claude Code 的真正价值在于它的扩展体系，这四个机制让它从"一个好用的 CLI"变成"一个可以深度定制的工作平台"：

| 机制 | 作用 | 示例 |
|------|------|------|
| **CLAUDE.md** | 项目级持久上下文，每次启动自动加载 | 编码规范、架构决策、常用命令 |
| **Skills** | 可复用的工作流模板，用 `/` 命令触发 | `/review` Code Review、`/deploy` 部署 |
| **MCP** | 连接外部服务和工具的标准协议 | 查数据库、操作 Jira、读 Figma |
| **Hooks** | 在 Agent 动作前后自动执行脚本 | 每次编辑后自动格式化、commit 前跑 lint |

**Skills 系统**是最灵活的扩展。一个 Skill 是一个 Markdown 文件，包含知识、工作流或指令。可以手动调用（`/deploy`），也可以在相关时让 Claude 自动加载。Skills 还可以在隔离的子 Agent 上下文中运行，不膨胀主会话。

**MCP 生态**是连接外部世界的标准协议。支持的工具包括：Sentry（监控）、Linear（项目管理）、GitHub（代码托管）、PostgreSQL（数据库）、Playwright（浏览器自动化）、Cloudflare（云服务）等数百个 Server。MCP 工具定义使用延迟加载，只有调用时才占上下文。

**插件（Plugins）** 是打包层，将 Skills、Hooks、MCP Server 打包为可安装单元。可以跨项目复用，也可以分享给团队。

## 使用成本

| 方案 | 月费 | 说明 |
|------|------|------|
| **Pro** | $20/月 | 包含 Claude Opus 和 Sonnet 合理用量 |
| **Max** | $100/月 | 更高用量，适合高频使用 |

支持 macOS（完整体验）、Linux、Windows（CLI 可用）。

## 和同类产品的对比

| 维度 | Claude Code | Cursor | Devin | Codex CLI | Gemini CLI |
|------|------------|--------|-------|-----------|------------|
| **交互** | 终端 CLI | IDE 内嵌 | Web 异步 | 终端 CLI | 终端 CLI |
| **代码理解** | 最深（项目级） | 中（IDE 范围） | 中（沙箱） | 中（Sandbox） | 中 |
| **子 Agent** | 五层嵌套 + 动态编排 | 后台单 Agent | 单 Agent | 单 Agent | 单 Agent |
| **自主性** | 半自动 | 半自动 | 全自动 | 半自动 | 半自动 |
| **扩展生态** | Skills+MCP+Hooks+Plugins | 插件市场 | 有限 | MCP | 有限 |
| **价格** | $20-100/月 | $0-40/月 | $500/月 | API 按量 | 免费/API |
| **适合场景** | 深度编码/重构 | 日常编码 | 后台 Issue | 轻量编码 | 免费探索 |

## 快速上手

```bash
npm install -g @anthropic/claude-code
cd your-project
claude
```

启动后在终端对话，例如：
- "帮我写一个用户登录的 API 接口"
- "这个 Bug 是怎么回事"（贴错误日志）
- "把这个模块重构为异步模式"

首次使用引导配置 API Key。建议在项目根创建 `CLAUDE.md` 写入编码规范。

## 总结

- Claude Code 是终端原生的编程 Agent，核心优势在项目级代码理解和跨文件重构
- 扩展生态（Skills + MCP + Hooks + Plugins）是它的差异化护城河
- 和 Cursor、Devin 定位互补——终端党用 Claude Code，IDE 党用 Cursor，后台任务用 Devin
- CLAUDE.md 是每个项目应该创建的第一个文件

> 编程 Agent 只是生态的一部分。接下来看看个人 AI 助理——[OpenClaw 个人助理](./04-openclaw.md)。

## 参考链接

- [Claude Code 官方文档](https://code.claude.com/docs/en/)
- [Claude Code 功能概览](https://code.claude.com/docs/en/features-overview)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)
- [MCP 快速开始](https://code.claude.com/docs/en/mcp-quickstart)
- [SWE-bench Leaderboard](https://www.swebench.com/)
