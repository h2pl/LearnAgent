# Skills 与 AGENTS.md

> MCP 和 A2A 是正式协议——有规范文档、有标准化治理、有版本号。但在这些正式协议之外，Agent 生态中还有一套更轻量的"约定"：Skills 描述"遇到某类任务怎么做"，AGENTS.md 声明"我能做什么"。它们没有协议层那么严谨，但胜在简单、直接、零依赖。

## 目录

- [为什么需要轻量级约定](#为什么需要轻量级约定)
- [AGENTS.md：Agent 能力声明](#agentsmdagent-能力声明)
- [Skills：可复用的知识包](#skills可复用的知识包)
- [实践案例：本项目的 skills/ 目录](#实践案例本项目的-skills-目录)
- [厂商 Skills 实现对比](#厂商-skills-实现对比)
- [Skills vs MCP vs AGENTS.md](#skills-vs-mcp-vs-agentsmd)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面讲了三篇"正式协议"——它们有完整的规范文档、标准化的治理流程、严谨的版本号。但 Agent 生态中还有一类更轻量的东西：**约定**。没有官方机构管理，不需要实现传输层，一个 Markdown 文件加几行 YAML 就能工作。

本文讲两个最流行的轻量级约定：**AGENTS.md** 和 **Skills**。它们不像 MCP 那样能解决 N×M 问题，但在"一个 Agent 如何描述自己"和"遇到特定任务该怎么做"这两个问题上，它们是最实用的方案。

## 为什么需要轻量级约定

正式协议解决的是"跨系统互操作"问题——你的 Agent 和我的 Agent 需要交换数据，那我们就需要一个共同的传输协议和消息格式。这类问题**必须标准化**才有意义。

但还有另一类问题：**Agent 本身"认识自己"和"组织自己"**。你的 Agent 需要知道自己能做什么（能力声明），需要在特定任务触发时加载正确的流程模板（工作流）。这些问题不需要跨系统标准化，只需要一个**可读的人机约定**。

轻量级约定的特点：

- **零依赖**：不需要 SDK，不需要协议解析器，纯文本文件
- **易调试**：人可以直接阅读和编辑，没有中间层
- **快速迭代**：改一个 Markdown 文件就是"协议升级"

## AGENTS.md：Agent 能力声明

AGENTS.md 的概念最初由 Anthropic 在 2025 年初提出，作为 Claude Code 的 `AGENTS.md` 规范。它的核心思路：

在项目根目录放一个 `AGENTS.md` 文件，描述这个项目对 Agent 有哪些期望。包括：使用的技术栈、项目结构约定、推荐的工作流程、常见任务的处理方式。

```markdown
# AGENTS.md — 项目 Agent 协作指南

## 技术栈
- Python 3.14 + FastAPI 后端
- React 19 + TypeScript 前端
- PostgreSQL 16 数据库

## 项目结构
- `src/api/` — API 路由定义
- `src/services/` — 业务逻辑
- `src/models/` — 数据模型

## 开发工作流
1. 修改前先运行 `make test` 确保现有测试通过
2. 为新功能编写测试，位置在 `tests/`
3. 提交前运行 `make lint` 检查代码风格
```

**AGENTS.md 的核心价值不是告诉 Agent "有哪些文件"，而是告诉 Agent "在这个项目中该怎么工作"**。一个正确的 AGENTS.md 能让 Agent 显著减少无效的文件搜索和试探性操作。

不过，AGENTS.md 的采纳度在 2026 年不算高。主要问题：**没有标准格式**。Anthropic、Cursor、Copilot 各有一套推荐格式，彼此不兼容。Agent 读到一个 AGENTS.md，需要自己解析它是否遵循了自己的习惯。这导致了"写了也未必有效"的局面。

到了 2026 年中，AGENTS.md 更多被理解为**项目的 Agent 配置文件**，而不是一个严格意义上的协议。每个厂商用自己的格式（Claude Code 的 `.claude/`、Cursor 的 `.cursorrules`、GitHub Copilot 的 `.github/copilot-instructions.md`），AGENTS.md 作为文件的通用文件名保留，但内容格式因客户端而异。

## Skills：可复用的知识包

Skills 是比 AGENTS.md 更有生命力的约定。它的核心概念是：**把特定任务的执行流程打包成一个粒度可控的知识包，Agent 按需加载**。

一个 Skill 通常包含两部分：

```
skill-name/
├── skill-name.md     # 主体内容（YAML frontmatter + Markdown）
└── ...               # 辅助文件
```

### Skill 文件格式

Skill 文件使用 YAML frontmatter + Markdown 结构：

```yaml
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true
allowed-tools: >
  Bash(git *) Bash(docker *) Bash(kubectl *)
---
```

```markdown
# Deploy Workflow

执行生产部署的标准化步骤。

1. 运行 `make test` 确保测试通过
2. 运行 `make build` 构建 Docker 镜像
3. 运行 `make push` 推送镜像到仓库
4. 运行 `kubectl apply -f k8s/` 更新 Kubernetes 部署
```

**frontmatter 定义了 Skill 的元数据**——什么时候触发、需要什么工具权限、是否隔离执行。Markdown 正文定义了实际的工作流步骤。

### Skills 的关键设计

<p align="center">
  <img src="../../assets/11-protocols/skills-architecture.svg" alt="Skills 的结构化格式与触发机制" width="90%"/>
</p>

- **按需加载，不污染上下文**：Skill 只在匹配任务时才被加载，不会占用日常对话的上下文窗口
- **可嵌套，可隔离**：`context: fork` 让 Skill 在独立的子 Agent 环境中执行，与主会话完全隔离
- **工具权限粒度控制**：`allowed-tools` 和 `disallowed-tools` 控制 Skill 可以做什么、不能做什么
- **模型覆盖**：`model` 和 `effort` 字段允许为特定任务指定不同的模型或推理强度

## 实践案例：本项目的 skills/ 目录

在本文所属的 [multi-agent-manager](https://github.com/h2pl/multi-agent-manager) 项目中，`skills/` 目录就是一个实际的 Skills 应用案例：

```
skills/
├── README.md              # Skills 目录说明
├── skills-spec.md          # YAML frontmatter 规范
├── matplotlib-figures/     # 自动生成 Matplotlib 图表的 Skill
└── wechat-mp/              # 公众号发布工作流的 Skill
```

**将知识文件和 Skill 文件分开管理**——纯静态知识放 `knowledge/`（无 frontmatter，每次会话默认读取），可执行工作流放 `skills/`（YAML frontmatter + Markdown，按需加载）。这种分离的好处：Agent 不会在每次对话中都加载几十个 Skill 的 frontmatter，只在任务触发时才读对应的 Skill。

## 厂商 Skills 实现对比

不同厂商的 Skills 实现有细微差异：

| 厂商 | 实现名称 | 文件格式 | 触发方式 | 核心差异 |
|------|---------|---------|---------|---------|
| **Anthropic (Claude Code)** | Skills | YAML + Markdown | 自动匹配 `/skill-name` 手动调用 | 最早的 Skills 实现，ecosystem最大 |
| **GitHub Copilot** | Copilot Instructions | `.github/copilot-instructions.md` | 自动注入 | 偏静态指令，无动态触发 |
| **Cursor** | .cursorrules | `.cursorrules` 文件 | 项目级自动生效 | 全局规则，不支持按任务加载 |
| **本项目** | skills/ | YAML + Markdown (skills-spec) | 按任务关键词匹配 | 参考 Claude Code 规范，兼容多 Agent |

**趋势**：2026 年 Skills 的格式正在收敛。`description` + `when_to_use` 驱动自动匹配、`context: fork` 支持子 Agent 隔离执行、`allowed-tools` 做精细权限控制——这些设计出自 Claude Code，但 Cursor 和 Copilot 也在跟进。如果你的项目要引入 Skills，建议直接使用 Claude Code 兼容的 frontmatter 格式，确保多客户端可用。

## Skills vs MCP vs AGENTS.md

这三个概念很容易混淆。以下表格从多个维度厘清差异：

<p align="center">
  <img src="../../assets/11-protocols/conventions-comparison.svg" alt="Skills / MCP / AGENTS.md 三个维度的对比" width="90%"/>
</p>

| 维度 | AGENTS.md | Skills | MCP |
|------|-----------|--------|-----|
| **定位** | "在这个项目里怎么做" | "这个任务怎么做" | "怎么调用外部工具" |
| **粒度** | 项目级 | 任务级 | 工具级 |
| **触发方式** | 自动注入（项目打开时） | 按需加载（任务匹配时） | 动态调用（模型决策时） |
| **执行** | 被动（Agent 自行解析） | 主动（Agent 按步骤执行） | 主动（Client→Server RPC） |
| **传输** | 无（文件读取） | 无（上下文注入） | STDIO / HTTP |
| **可变性** | 静态（项目配置） | 静态（可更新） | 动态（运行时调用） |
| **是否需要协议层** | 否 | 否 | 是（JSON-RPC） |

**一个 Agent 可能同时用到三者**：AGENTS.md 告诉它在项目中遵循的规则，一个匹配的 Skill 提供具体任务的执行步骤，执行过程中通过 MCP 调用外部工具。

## 总结

- **轻量级约定填补了正式协议的空白**：AGENTS.md 和 Skills 不需要传输层和规范治理，靠文件格式约定就能工作
- **AGENTS.md 尚未统一**：各厂商格式不兼容，2026 年更推荐用厂商特定的配置文件（.claude/、.cursorrules）
- **Skills 是最实用的轻量级约定**：YAML frontmatter + Markdown，按需加载，权限控制，已有多厂商支持
- **本项目 skills/ 是真实案例**：知识/技能分离管理、多 Agent 兼容的 frontmatter 规范
- **三者互补**：AGENTS.md 管项目规则，Skills 管任务流程，MCP 管工具调用

> 下一篇 [协议组合与选型](./06-protocol-composition.md)——学完全部协议后，回到最实际的问题：什么时候用什么、怎么组合、怎么落地。

## 参考链接

- [Claude Code — Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Claude Code — AGENTS.md](https://docs.anthropic.com/en/docs/claude-code/agents)
- [GitHub Copilot — Copilot Instructions](https://docs.github.com/en/copilot/customizing-copilot)
- [Cursor — .cursorrules](https://docs.cursor.com/context/rules-for-ai)
- [本项目 skills-spec.md](https://github.com/h2pl/multi-agent-manager/blob/main/skills/skills-spec.md)
