# 2026 主流 Agent 全景

> 2026 年的 Agent 市场已从"所有产品都叫 Agent"走向专业分化。编程、研究、浏览器、个人助理——它们解决完全不同的问题。本文用"品类 × 能力级"双维框架帮你理清全局。

## 目录

- [为什么需要双维框架](#为什么需要双维框架)
- [能力级：L1-L5](#能力级l1-l5)
- [品类 1：编程 Agent](#品类-1编程-agent)
- [品类 2：研究 Agent](#品类-2研究-agent)
- [品类 3：浏览器/桌面 Agent](#品类-3浏览器桌面-agent)
- [品类 4：个人助理](#品类-4个人助理)
- [品类 5：通用自主 Agent](#品类-5通用自主-agent)
- [品类 6：工作流自动化](#品类-6工作流自动化)
- [品类 7：企业 Agent 平台](#品类-7企业-agent-平台)
- [开发框架：构建你自己的 Agent](#开发框架构建你自己的-agent)
- [选型指南](#选型指南)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在[什么是 AI Agent](./01-what-is-agent.md)中你建立了基本认知，这篇来看 2026 年的生态全貌——市场上有什么、怎么分类、怎么选。

## 为什么需要双维框架

同一款产品在不同配置下差异巨大。ChatGPT 可以是一个简单 Chatbot（L1），也可以是一个自主研究助手（L4）——能力完全不同。

所以需要两个维度来描述一个 Agent：

**横向——品类**：它解决什么问题（编程？研究？个人助理？）  
**纵向——能力级**：它有多自主（聊天式？工作流？自主执行？）

两个维度交叉，才能准确判断一个产品是否适合你的需求。

<img src="../../assets/01-landscape/landscape-map.png" alt="2026 AI Agent 全景图" width="100%"/>

## 能力级：L1-L5

参考 Lenny Rachitsky 和 presenc.ai 的 5 级框架：

| 级别 | 名称 | 特点 |
|------|------|------|
| **L1** | 聊天工具 | 对话 + 基本工具，Session 记忆，无规划 |
| **L2** | 工作流 | 按预设流程执行固定任务，状态机控制 |
| **L3** | 工具编排 | 动态选择工具完成目标，短时记忆 |
| **L4** | 自主执行 | 长周期规划（数小时到数天），多步推理 |
| **L5** | 多 Agent | 多个 Agent 协作，层级规划 |

L4 是 2026 年能力的活跃前沿。L5 多 Agent 仍处于研究前沿，预计 2027-2028 成熟。

---

## 品类 1：编程 Agent

最成熟的品类。辅助或替代开发者写代码。**差异化在于代码库理解和工具链集成**。

| 产品 | 能力级 | 形态 | 核心优势 | 价格 |
|------|--------|------|----------|------|
| **Claude Code** | L3-L4 | 终端 CLI | 深度代码库理解，子 Agent 委派 | $20-100/月 |
| **Cursor** | L3 | IDE（VS Code 分支） | 编辑器内最流畅的 Agent 体验 | $0-40/月 |
| **Devin** | L4 | 云平台 | 全自主 Issue→PR | $500/月 |
| **Codex CLI** | L3 | 终端 CLI | OpenAI 出品，Sandbox Agent | API 按量 |
| **Gemini CLI** | L3 | 终端 CLI | Google 出品，慷慨免费额 | 免费/API |
| **GitHub Copilot** | L2-L3 | IDE 插件 | GitHub 生态集成 | $19/月 |
| **Cline** | L3 | VS Code 扩展 | 开源，BYO API Key | 免费 |
| **Aider** | L3 | 终端 CLI | 极简结对，多 LLM | 免费 |

**选型核心**：终端党用 Claude Code，IDE 党用 Cursor，后台任务用 Devin。

---

## 品类 2：研究 Agent

2026 年增长最快的品类。接收研究问题，自动执行多步调研——搜索、阅读、交叉验证、撰写报告。

| 产品 | 能力级 | 核心优势 | 价格 |
|------|--------|----------|------|
| **OpenAI Deep Research** | L3-L4 | 50+ 步自主调研，深度优先 | $200/月 |
| **Perplexity Pro** | L2-L3 | 快速研究，来源透明 | $20/月 |
| **Google Deep Research** | L3 | Gemini 驱动，免费可用 | 免费/API |
| **Manus Research** | L4 | 100+ 并行调研子 Agent | $39/月 |

**选型核心**：深度优先 → Deep Research，速度优先 → Perplexity，并行广度 → Manus。

---

## 品类 3：浏览器/桌面 Agent

直接操作屏幕，模拟人类点击输入。**不需要 API，不需要集成**——像人类一样使用软件。

| 产品 | 能力级 | 核心优势 | 价格 |
|------|--------|----------|------|
| **ChatGPT Operator** | L3-L4 | OpenAI 出品，浏览器自动化 | $200/月 |
| **Claude Computer Use** | L3-L4 | 桌面 + 浏览器，远程委派 | $20-100/月 |
| **Browser Use** | L3 | 开源，Python SDK | 免费 |
| **TARS** | L3 | 开源开源，GUI 操作 | 免费 |

**选型核心**：桌面控制 → Computer Use，纯浏览器 → Operator，自建 → Browser Use。

---

## 品类 4：个人助理

始终在线、跨平台、不断学习。**运行在你自己的设备上，通过聊天应用与你交互**。

| 产品 | 能力级 | 核心优势 | 价格 |
|------|--------|----------|------|
| **OpenClaw** | L3-L4 | 20+ 通道（含微信/QQ），主动检查 | 免费开源 |
| **Hermes Agent** | L3-L4 | 200+ 模型自由，编码 Agent 编排 | 免费开源 |
| **Thoth** | L3 | 本地 Ollama 运行，数据主权 | 免费开源 |

**选型核心**：需要微信/QQ → OpenClaw。需要模型自由度 → Hermes。追求完全本地 → Thoth。

---

## 品类 5：通用自主 Agent

给一个目标，自主完成。**不预设工作流**，Agent 自己决定怎么做。

| 产品 | 能力级 | 核心优势 | 价格 |
|------|--------|----------|------|
| **Manus** | L4-L5 | 多 Agent 编排，100+ 并行子 Agent | $20-39/月 |
| **ChatGPT Agent** | L3-L4 | 浏览器操作，Git/Gmail 连接器 | $20-200/月 |

---

## 品类 6：工作流自动化

把业务流程变成可编排的工作流。**低代码、可视化、预构建集成**。

| 产品 | 能力级 | 核心优势 | 价格 |
|------|--------|----------|------|
| **n8n** | L2-L3 | 500+ 集成，AI Agent 节点，自托管 | 免费/$24-667/月 |
| **Lindy** | L2-L3 | 可视化构建，3000+ 集成 | $49.99/月起 |
| **Zapier Agents** | L2 | 8000+ App 集成 | $29.99/月起 |

**选型核心**：自托管 → n8n，最大化 App 集成 → Zapier，AI 原生 → Lindy。

---

## 品类 7：企业 Agent 平台

嵌入企业系统的 Agent 平台。**安全、合规、可审计**是核心要求。

| 平台 | 能力级 | 核心优势 | 定价 |
|------|--------|----------|------|
| **Salesforce Agentforce** | L3-L4 | Hybrid Reasoning，Salesforce 生态 | $2/对话 |
| **MS Copilot Studio** | L3 | Teams/SharePoint/Outlook 集成 | $200/Agent/月 |
| **Vertex AI Agent Builder** | L3 | GCP 原生 | 按量 |
| **Amazon Bedrock Agents** | L3 | AWS 原生 | 按量 |
| **扣子（Coze）** | L2-L3 | 字节系，零代码构建 | 免费/增值 |

**选型核心**：你先绑定哪个生态，就选哪个平台。

---

## 开发框架：构建你自己的 Agent

以上是**产品**。如果你想**自己构建** Agent 系统，需要用框架：

| 框架 | 类型 | 核心特性 | 开源 |
|------|------|----------|------|
| **LangGraph** | 状态机 | 精确控制 Agent 跳转逻辑 | 是 |
| **CrewAI** | 角色驱动 | 定义角色，分工协作 | 是 |
| **AutoGen** | 对话式 | 多 Agent 对话协作（Microsoft） | 是 |
| **OpenAI Agents SDK** | SDK | OpenAI 原生 Agent SDK | 是 |
| **Dify** | 低代码 | 可视化编排 + RAG | 是 |

**框架不是产品的替代品**。框架让你构建自定义系统，但需要自己部署维护。大多数场景优先用现成产品，框架留给定制需求。

---

## 选型指南

| 你的角色 | 推荐 |
|----------|------|
| **终端工程师** | Claude Code（深度）+ Cursor（日常） |
| **技术团队 Lead** | 上面两个 + Devin（后台）+ LangGraph（编排） |
| **研究者** | Deep Research（深度）+ Perplexity（快速） |
| **创业者（技术）** | Manus（原型）+ n8n（运营）+ Claude Code |
| **运营/业务人员** | Lindy 或 Zapier Agents |
| **需要个人助理** | OpenClaw（国内）或 Hermes（模型自由） |
| **企业 IT** | Agentforce（Salesforce）或 Copilot Studio（M365） |

---

<p align="center"><img src="../../assets/01-landscape/agent-classification-matrix.svg" alt="Agent品类能力级分类矩阵" width="90%"/><br/><em>图：7大品类 × 5级能力 双维分类矩阵</em></p>

## 总结

| 品类 | 一句话 | 能力级范围 | 典型产品 |
|------|--------|-----------|----------|
| **编程 Agent** | 辅助/替代你写代码 | L2-L4 | Claude Code, Cursor, Devin |
| **研究 Agent** | 自主调研写报告 | L2-L4 | Deep Research, Perplexity |
| **浏览器/桌面 Agent** | 操作屏幕像人类 | L3-L4 | Operator, Computer Use |
| **个人助理** | 始终在线，跨平台 | L3-L4 | OpenClaw, Hermes |
| **通用自主 Agent** | 给目标，自主完成 | L4-L5 | Manus, ChatGPT Agent |
| **工作流自动化** | 编排业务流程 | L2-L3 | n8n, Lindy |
| **企业平台** | 嵌入企业系统 | L3 | Agentforce, Copilot Studio |
| **开发框架** | 构建自定义 Agent | — | LangGraph, CrewAI |

> **选品类比选品牌重要，定能力级比定品类更关键**。先想清楚要解决什么问题、需要多自主，再看具体产品。

接下来深入最成熟的品类——[Claude Code 编程 Agent](./03-claude-code.md)。

## 参考链接

- [Types of AI Agents: The Complete Guide (AgentsIndex, 2026)](https://agentsindex.ai/blog/types-of-ai-agents)
- [AI Agent Taxonomy 2026 (Presenc AI)](https://presenc.ai/research/ai-agent-taxonomy-2026)
- [What Are AI Agents (AiAgents.computer, 2026)](https://aiagents.computer/what-are-ai-agents)
- [The 2026 Guide to AI Agents (IBM)](https://www.ibm.com/think/ai-agents)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
