# OpenClaw 个人助理

> 2026 年增长最快的开源项目（379K Stars），AI 项目第一。不是 Chatbot，不是编程 Copilot——是一个运行在你设备上、通过聊天应用与你交互的**个人 AI 助理**。始终在线、跨平台、记住一切。

## 目录

- [OpenClaw 是什么](#openclaw-是什么)
- [核心能力](#核心能力)
- [它能做什么](#它能做什么)
- [Skills 与生态](#skills-与生态)
- [部署方式](#部署方式)
- [和 Hermes Agent 的对比](#和-hermes-agent-的对比)
- [快速上手](#快速上手)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在[全景概览](./02-mainstream-agents.md)中你看到了个人助理这个品类。OpenClaw 是这个品类的代表——379K Stars，AI 开源项目第一。

## OpenClaw 是什么

OpenClaw 是一个**本地优先的个人 AI 助理框架**。你在自己设备上运行一个 Gateway 进程，连接聊天应用（Telegram、WhatsApp、微信等），它就变成了一个始终在线的 AI 助理。

**一句话定位**：一个 AI 助理，住在你的设备上，通过你已有的聊天应用和你交流。

它不是编码 Agent（虽然也能写代码），不是 Chatbot（不止被动回答），而是一个**主动的、跨平台的、不断学习的个人助理**。它运行在你自己的硬件上，数据不离开你的网络。

## 核心能力

| 能力 | 说明 |
|------|------|
| **跨平台聊天** | WhatsApp、Telegram、Discord、Slack、Signal、iMessage、微信、QQ 等 20+ 平台 |
| **持久记忆** | 记住偏好、项目、历史对话，跨 Session 不丢失，可查看编辑 |
| **主动检查（Heartbeat）** | 定时检查关心的信息，有事通知你，没事不打扰 |
| **定时任务（Cron）** | 自然语言定义"每天早上报摘要""每周一生成周报" |
| **语音交互** | 语音唤醒、语音消息收发（macOS/iOS/Android） |
| **浏览器自动化** | 操作网页、填表、提取数据 |
| **代码执行** | 运行 Python/JS/Shell 代码，安装的依赖跨重启保留 |
| **文件管理** | 读写文件、处理上传文档、管理目录 |
| **Live Canvas** | Agent 驱动的可视化工作空间，实时交互 |
| **图像处理** | 图片分析、生成、OCR |
| **多 Agent 路由** | 不同通道/联系人路由到不同的 Agent 实例 |

## 它能做什么

<img src="../../assets/00-landscape/openclaw-telegram-pr.jpg" alt="OpenClaw Telegram 聊天界面" width="80%"/>

**跨平台个人助理**：在 Telegram 上安排日程，到点了 WhatsApp 提醒你。所有聊天应用由同一个 Agent 管理，上下文互通。消息、图片、文档、语音——多模态全支持。

**多 Agent 路由**：这是 OpenClaw 一个容易被忽视但实用的能力。你可以配置多个 Agent 实例，不同通道路由到不同 Agent。比如 Telegram 上跑一个"工作助手"处理日程和邮件，Discord 上跑一个"运维机器人"监控服务器，WhatsApp 上跑一个"生活助理"管购物清单。它们共享记忆基础设施但会话完全隔离。

**移动端体验**：iOS/Android App 支持配对、语音唤醒、相机拍照分析、屏幕录制。你可以对着手机说"帮我看一下这个服务器的状态"，OpenClaw 自动唤醒、SSH 到服务器、返回结果。这在路上或在另一个房间时非常方便——不需要打开电脑。

**信息管理**：整理文件、归档邮件、管理笔记。记忆是存储在本地文件，你可以直接打开查看和修改。内置向量记忆层，语义检索无需外部数据库。

**自动化任务**：设置定时任务——每天早上 9 点报天气和日程、每月初生成项目报告、监控服务器状态异常时通知你。支持 Cron 表达式和自然语言。

**知识助手**：接入你的文档库，基于 RAG 回答项目、技术、流程问题。长期使用越来越了解你的工作习惯。

**系统管理**：通过 Skills 管理服务器、数据库、部署流程。社区有大量 DevOps 相关 Skills 可直接使用。

**硬件控制**：连接 Home Assistant 控制智能家居——"关灯""调温度"直接执行。

**研究辅助**：Web 搜索 + 浏览器自动化 + 代码执行，读取网页、分析数据、生成报告。

**开发者工具**：接入 GitHub、GitLab、Linear 等。PR Review、Issue 管理、CI 监控都可以通过聊天完成。

## Skills 与生态

<img src="../../assets/00-landscape/openclaw-agents-ui.jpg" alt="OpenClaw 多 Agent 管理界面" width="100%"/>

OpenClaw 的扩展由三个层次构成：

| 层次 | 说明 | 示例 |
|------|------|------|
| **Tools（工具）** | Agent 可调用的原子功能 | `exec` 执行命令、`browser` 控制浏览器、`web_search` 搜索 |
| **Skills（技能）** | Markdown 指令包，教会 Agent 如何工作 | 邮件技能、日历技能、部署工作流 |
| **Plugins（插件）** | 打包的新运行时能力 | 新聊天通道、新模型供应商、新工具集 |

**ClawHub**（社区技能市场）已有 **2300+ Skills**，涵盖 CI/CD 修复、招聘流程、内容创作、DevOps、金融分析等类别。Skills 用自然语言编写，不需要写代码——就是一份 Markdown 文档告诉 Agent 怎么做。

**支持 35+ 模型供应商**：Anthropic、OpenAI、Google、DeepSeek，以及 Ollama/vLLM/SGLang 等本地部署方案。

**媒体生成**：内置图像生成和视频生成能力，通过 Skills 可调用。

## 社区实战

以下是社区中真实使用 OpenClaw 的案例（来自官方 Showcase 和公开分享）：

| 角色 | 配置 | 做了什么 |
|------|------|----------|
| **独立开发者** | 4 Agent（战略/编码/营销/分析）+ 共享记忆 | 24/7 运营一个 SaaS，通过 Telegram 沟通 |
| **创作者** | Codex + 图像模型 + 浏览器 Skills | 5 天搭建自媒体内容流水线 |
| **运维工程师** | Supabase + Gmail Skills + Cron | 每天自动读邮件、创建 Todo、存入数据库 |
| **技术创业者** | 语音唤醒 + Claude Code | 走路时通过语音启动编码任务 |

核心模式：**OpenClaw 是编排层，不是替代品**。它不取代你现有的工具，而是把 Telegram、GitHub、Gmail、Coding Agent 等串起来，统一通过聊天应用控制。

## 部署方式

| 方式 | 适合场景 |
|------|----------|
| **桌面（macOS/Linux/Windows）** | 个人日常使用，开箱即用 |
| **服务器（VPS）** | 7×24 在线，多人使用 |
| **Raspberry Pi / NAS** | 低功耗长期运行 |
| **Mobile Nodes（iOS/Android）** | 配对后远程控制，支持语音和相机 |

配套的 macOS 菜单栏 App、Windows Hub、iOS/Android App 让管理更便捷。

## 和 Hermes Agent 的对比

OpenClaw 和 Hermes Agent 常放在一起比较，它们是同类产品的两个代表：

| 维度 | OpenClaw | Hermes Agent |
|------|----------|--------------|
| **Stars** | 379K | 197K |
| **语言** | TypeScript | Python |
| **消息通道** | 20+（含微信/QQ） | 6+ |
| **模型支持** | 35+ 供应商 | 200+ 模型（OpenRouter） |
| **扩展方式** | Skills + Plugins | Skills + MCP |
| **独特优势** | 通道覆盖最广、主动检查（Heartbeat）、记忆透明可编辑 | 模型自由最高、编码 Agent 编排、自动技能创建 |
| **适合人群** | 需多平台覆盖，尤其需要微信/QQ | Python 生态，需模型自由度 |

**选型建议**：需要微信/QQ 通道 → OpenClaw。需要模型自由度和编码 Agent 编排 → Hermes。两者记忆和助理能力都很成熟。

## 快速上手

```bash
npm install -g openclaw@latest
openclaw gateway start
```

运行后走 Onboard 向导：连接聊天账号、配置模型供应商、选择 Skills。几分钟内就能开始使用。

## 总结

- OpenClaw 是本地优先的个人 AI 助理，核心优势在 20+ 消息通道覆盖（含微信/QQ）
- Heartbeat 主动检查 + Cron 定时任务让它不止被动应答，还能主动工作
- ClawHub Skills 生态（2300+）让它通过自然语言即可扩展
- 数据完全在本地，不依赖云服务

> 个人助理的另一个选择——[Hermes Agent 开源 Agent](./05-hermes-agent.md)，在模型自由度和编码编排上各有侧重。

## 参考链接

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw 官方文档](https://docs.openclaw.ai/)
- [OpenClaw Skills 指南 (DigitalOcean)](https://www.digitalocean.com/resources/articles/what-are-openclaw-skills)
- [ClawHub](https://clawhub.com)
