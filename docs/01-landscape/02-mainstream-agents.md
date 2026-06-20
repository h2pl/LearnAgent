# 2026 主流 Agent 全景

> 2026 年的 Agent 市场已经非常热闹，从编程助手到个人助理，每个品类解决不同的问题。本文带你快速浏览全貌，知道市场上有什么、各自擅长什么。

## 目录

- [为什么需要了解全景](#为什么需要了解全景)
- [编程 Agent](#编程-agent)
- [研究 Agent](#研究-agent)
- [浏览器/桌面 Agent](#浏览器桌面-agent)
- [自动化 Agent](#自动化-agent)
- [个人助理](#个人助理)
- [企业 Agent 平台](#企业-agent-平台)
- [开发框架：构建你自己的 Agent](#开发框架构建你自己的-agent)
- [怎么选？先看场景](#怎么选先看场景)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇[什么是 AI Agent](./01-what-is-agent.md)讲了 Agent 的本质，这篇来看看 2026 年市场上都有哪些主流产品。

这些产品能力其实都差不多——都能理解指令、调用工具、独立完成任务。真正的区别在于：**它们解决什么问题、在什么环境下工作**。

## 为什么需要了解全景

买锤子之前，先知道有哪些钉子。了解全景有两个目的：

1. **避免重复造轮子**——你想做的事，可能已经有现成产品
2. **知道自己要什么**——当你需要自己构建 Agent 时，知道行业标杆长什么样

注意：下面的产品信息截至 2026 年中。这个领域变化很快，具体价格和功能建议以官网为准。

---

## 编程 Agent

最成熟的品类。帮你写代码、改代码、理解代码库。

| 产品 | 一句话 | 适合谁 |
|------|--------|--------|
| **Claude Code** | 终端里的深度编程 Agent，能理解整个代码库 | 喜欢命令行的开发者 |
| **Cursor** | VS Code 改造的 AI IDE，编辑器内最流畅的体验 | 习惯 IDE 的开发者 |
| **Devin** | 云端全自主 Agent，给个 Issue 就能干活 | 需要后台自动开发的团队 |
| **GitHub Copilot** | GitHub 生态里最自然的代码补全 + Agent 模式 | GitHub 重度用户 |
| **Cline / Aider** | 开源方案，自带 API Key 就能用 | 想控制成本或数据隐私的开发者 |

**一句话选型**：终端党 → Claude Code，IDE 党 → Cursor，后台任务 → Devin。

---

## 研究 Agent

帮你做多步调研：搜索 → 阅读 → 交叉验证 → 写报告。2026 年增长最快的品类。

| 产品 | 一句话 | 适合谁 |
|------|--------|--------|
| **OpenAI Deep Research** | 50 步以上的深度自主调研 | 需要深度分析的研究者 |
| **Perplexity Pro** | 快速研究，来源透明，像升级版搜索引擎 | 日常快速查资料 |
| **Google Deep Research** | Gemini 驱动，免费可用 | 预算有限的用户 |
| **Manus Research** | 100+ 并行子 Agent 同时调研 | 需要广度的场景 |

**一句话选型**：深度 → Deep Research，速度 → Perplexity，广度 → Manus。

---

## 浏览器/桌面 Agent

直接操作屏幕，像人类一样点击和输入。**不需要 API 接口**，任何网页都能操作。

| 产品 | 一句话 | 适合谁 |
|------|--------|--------|
| **ChatGPT Operator** | 浏览器自动化，OpenAI 出品 | 需要浏览器自动化的用户 |
| **Claude Computer Use** | 桌面 + 浏览器都能操作 | 需要跨应用操作的场景 |
| **Browser Use** | 开源 Python SDK | 开发者想自己控制流程 |

**一句话选型**：桌面控制 → Computer Use，纯浏览器 → Operator，自建 → Browser Use。

---

## 自动化 Agent

把重复流程变成自动化工作流。低代码、可视化、预构建集成。

| 产品 | 一句话 | 适合谁 |
|------|--------|--------|
| **n8n** | 500+ 集成，AI Agent 节点，可自托管 | 开发者和技术团队 |
| **Zapier Agents** | 8000+ App 集成，门槛最低 | 非技术人员 |
| **Lindy** | AI 原生的可视化自动化流程 | 想让 AI 参与决策的运营人员 |

**一句话选型**：自托管 → n8n，集成最多 → Zapier，AI 原生 → Lindy。

---

## 个人助理

始终在线、跨平台、不断学习。运行在你自己的设备上，通过聊天应用与你交互。

| 产品 | 一句话 | 适合谁 |
|------|--------|--------|
| **OpenClaw** | 20+ 通道（微信/QQ/Telegram…），主动检查消息 | 国内用户，需要微信集成 |
| **Hermes Agent** | 200+ 模型自由切换，可编排子 Agent | 追求模型自由度的用户 |
| **Thoth** | 完全本地运行，数据不出设备 | 对隐私要求极高的用户 |

**一句话选型**：要微信 → OpenClaw，要模型自由 → Hermes，要本地 → Thoth。

---

## 企业 Agent 平台

嵌入企业系统的 Agent。安全、合规、可审计是基本要求。

| 平台 | 一句话 | 适合谁 |
|------|--------|--------|
| **Salesforce Agentforce** | Salesforce 生态内的 Hybrid Reasoning Agent | Salesforce 用户 |
| **MS Copilot Studio** | Teams/SharePoint/Outlook 无缝集成 | Microsoft 365 用户 |
| **Vertex AI Agent Builder** | GCP 原生的 Agent 构建平台 | Google Cloud 用户 |
| **Amazon Bedrock Agents** | AWS 原生的 Agent 构建平台 | AWS 用户 |

**一句话选型**：你绑定哪个生态，就选哪个平台。

---

## 开发框架：构建你自己的 Agent

以上是**产品**。如果你想自己构建 Agent 系统，看这里：

| 框架 | 一句话 |
|------|--------|
| **LangGraph** | 用状态机精确控制 Agent 的每一步跳转 |
| **CrewAI** | 给 Agent 分配角色，让它们分工协作 |
| **AutoGen** | 多 Agent 对话协作框架（Microsoft） |
| **OpenAI Agents SDK** | OpenAI 官方 Agent 构建工具包 |
| **Dify** | 可视化的低代码 AI 应用平台，内置 RAG |

框架不是产品的替代品。框架让你构建自定义系统，但需要自己部署维护。大多数场景优先用现成产品，框架留给定制需求。

---

## 怎么选？先看场景

| 你的角色 | 推荐 |
|----------|------|
| **开发者（写代码）** | Claude Code 或 Cursor |
| **开发者（研究技术方案）** | Perplexity 日常 + Deep Research 深挖 |
| **团队 Lead** | 上面两个 + Devin 处理后台任务 |
| **运营/业务人员** | Lindy 或 Zapier Agents |
| **创业者快速验证** | Manus + n8n |
| **需要个人助理** | OpenClaw（国内）或 Hermes（模型自由） |
| **企业 IT** | Agentforce（Salesforce）或 Copilot Studio（M365） |

---

## 总结

| 品类 | 一句话 | 典型产品 |
|------|--------|----------|
| **编程 Agent** | 帮你写代码 | Claude Code, Cursor, Devin |
| **研究 Agent** | 帮你查资料写报告 | Deep Research, Perplexity |
| **浏览器/桌面 Agent** | 帮你操作软件 | Operator, Computer Use |
| **自动化 Agent** | 帮你跑流程 | n8n, Zapier, Lindy |
| **个人助理** | 全天候在线助手 | OpenClaw, Hermes |
| **企业平台** | 嵌入企业系统的 Agent | Agentforce, Copilot Studio |
| **开发框架** | 让你自己造 Agent | LangGraph, CrewAI |

> **先想清楚要解决什么问题，再找对应的品类，最后选具体产品。** 品类选对了，产品之间没有本质差异。

接下来深入最成熟的品类——[Claude Code 编程 Agent](./03-claude-code.md)。

## 参考链接

- [Types of AI Agents: The Complete Guide (AgentsIndex, 2026)](https://agentsindex.ai/blog/types-of-ai-agents)
- [What Are AI Agents (AiAgents.computer, 2026)](https://aiagents.computer/what-are-ai-agents)
- [The 2026 Guide to AI Agents (IBM)](https://www.ibm.com/think/ai-agents)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
