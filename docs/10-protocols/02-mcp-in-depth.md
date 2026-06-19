# MCP 深入

> MCP 在工具层的胜利已成定局，但大多数人只看到了它"写一次处处用"的表层价值。本文从协议深度切入：MCP 的治理结构、版本演进路线、企业级部署模式和它与 Function Calling 的真实关系。

## 目录

- [前置阅读](#前置阅读)
- [从实验项目到行业标准](#从实验项目到行业标准)
- [协议治理：Linux Foundation 接手后](#协议治理linux-foundation-接手后)
- [版本演进时间线](#版本演进时间线)
- [企业级部署：Gateway 模式](#企业级部署gateway-模式)
- [MCP vs Function Calling](#mcp-vs-function-calling)
- [生态数据可信度](#生态数据可信度)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [MCP 与工具生态](../04-tool-use/04-mcp-and-tool-ecosystem.md) 中，你已经了解了 MCP 的核心概念：四层架构（Host/Client/Server/Gateway）、三大原语（Tools/Resources/Prompts）、以及 12 行 Python 写一个极简 Server。那篇文章的角度是"工具标准化"——从开发者的实操视角出发。

本文换一个角度：**协议本身**。MCP 只是一个协议规范，但让它真正"跑起来"的，是治理结构、版本策略、生产部署模式和生态数据背后的取舍。

## 前置阅读

本文假设你已经了解 MCP 的基础概念。如果你还没读过，建议先看 [MCP 与工具生态](../04-tool-use/04-mcp-and-tool-ecosystem.md)，了解四大角色、三大原语和基本用法。本文将直接在此基础上展开。

## 从实验项目到行业标准

MCP 的演进速度在开放标准中相当罕见。以下是关键里程碑：

<p align="center">
  <img src="../../assets/10-protocols/mcp-evolution-timeline.svg" alt="MCP 版本演进时间线：2024.11 → 2026 中" width="90%"/>
</p>

| 时间 | 事件 | 意义 |
|------|------|------|
| 2024-11 | Anthropic 开源 MCP 规范 | 最初只是 Claude Desktop 的附属能力 |
| 2025-03 | 发布 Streamable HTTP 传输 | 从本地 stdio 扩展到远程调用 |
| 2025-06 | 支持 OAuth 2.1 | 企业远程部署的安全前提 |
| 2025-08 | ChatGPT、Cursor 原生支持 | MCP 走出 Anthropic 生态 |
| 2025-12 | 捐赠给 Linux Foundation | 成为 Agentic AI Foundation 创始项目 |
| 2026-04 | 月 SDK 下载达 1.64 亿 | 生态成熟度确认 |
| 2026-06 | 规范 2025-11 版稳定 | 10k+ 有效 Server，多厂商支持 |

**关键转折点是 2025-06 的 OAuth 2.1 支持**。在此之前，MCP 主要运行在 stdio 模式——Agent 和工具在同一台机器上。这对个人开发者够用，但企业不可能把数据库凭证放在 Agent 的配置文件中。OAuth 2.1 让远程 Server 有了规范的安全处理方式，企业部署才真正可行。

## 协议治理：Linux Foundation 接手后

2025 年 12 月，Anthropic 将 MCP 捐赠给 Linux Foundation 的 Agentic AI Foundation（AAIF）。这对协议的长远健康很重要：

- **厂商中立**：规范修订不再由单一厂商控制。AAIF 的治理委员会包括 Anthropic、OpenAI、Google、Microsoft 等
- **兼容性保障**：版本升级必须有明确的向后兼容策略。2025-11 版规范引入了 feature detection 机制
- **SDK 维护**：官方的 Python 和 TypeScript SDK 由 AAIF 社区维护，不再依赖 Anthropic 的发布节奏

**对开发者的实际影响**：你不用担心 MCP 被 Anthropic 私有化改造，也不用担心版本碎片化。AAIF 的治理模式借鉴了 Kubernetes（CNCF）和 GraphQL（Linux Foundation）的经验，功能演进和长期稳定性可以兼顾。

## 版本演进时间线

MCP 的版本号采用 **发布日期命名**（如 2025-11），而不是语义化版本。这与其他协议（A2A 用 v1.0）不同。

| 版本 | 发布日期 | 主要变更 |
|------|---------|---------|
| 2024-11 | 2024-11-25 | 初始规范，仅 STDIO 传输，基础 Tool/Resource/Prompt 原语 |
| 2025-03 | 2025-03-18 | Streamable HTTP 传输，Roots 原语（文件路径授权） |
| 2025-06 | 2025-06-12 | OAuth 2.1 支持，Sampling 原语（Server 请求 Client 代调用 LLM） |
| 2025-11 | 2025-12-01 | Gateway 规范，Feature Detection，错误代码标准化 |

**重要**：所有这些版本都向后兼容。2024-11 的 Server 在 2025-11 的 Client 上仍然能运行，只是无法使用新特性。Feature Detection 让 Server 和 Client 在握手时协商能力集，确保兼容性和功能升级可以并行推进。

## 企业级部署：Gateway 模式

Demo 级的 MCP 部署是 Client 直连 Server。但在企业环境中，这种模式有安全风险：**每个 Client 直接接触所有 Server，没有集中管控点**。

Gateway 模式解决的就是这个问题：

<p align="center">
  <img src="../../assets/10-protocols/mcp-gateway-architecture.svg" alt="MCP Gateway 企业部署架构" width="90%"/>
</p>

Gateway 作为中间层，承担四个职责：

- **认证与授权**：验证 Client 身份，判断是否有权调用特定 Server。2025-11 规范中，Gateway 可以截获 `roots` 请求来限制文件路径访问
- **审计日志**：记录每次工具调用的请求/响应/耗时。这对 SOC 2 等合规审计是必需的
- **流量控制**：限制单个 Client 的并发和频率，防止资源耗尽
- **安全扫描**：检查工具输入中的提示注入攻击

2025-11 规范正式加入了 Gateway 概念，但不是强制要求。小型团队可以直接 Client→Server，到需要集中管控时再引入 Gateway。**社区已有两个开源 Gateway 实现**：[mcp-gateway](https://github.com/punkpeye/mcp-gateway)（Node.js）和 [mcp-proxy](https://github.com/sparfenyuk/mcp-proxy)（Python）。

## MCP vs Function Calling

这是一个常见的混淆点：**MCP 和 Function Calling（或 Tool Use）到底是什么关系？**

| 维度 | Function Calling | MCP |
|------|-----------------|-----|
| **层级** | LLM 原生能力 | 协议层 |
| **作用域** | 单个模型 | 跨模型/跨客户端 |
| **Server 形态** | 无（直接代码调用） | 独立进程或远程服务 |
| **复用性** | 绑定模型 | 一次编写，处处运行 |
| **传输** | 内存函数调用 | STDIO / HTTP |

**2026 年的主流架构是两者共存**。当 Agent 调用一个工具时，底层决策仍然是 Function Calling——LLM 收到工具定义（JSON Schema），决定调用哪个、传入什么参数。MCP 在上层提供了一套标准化的工作流：Server 注册工具定义 → Client 转换为模型原生格式 → 模型调用 → Client 路由到对应 Server。

一个典型的调用链路是这样的：

```
模型 ←Tool Use→ Server Client ←JSON-RPC→ MCP Server ←API→ 外部工具
```

模型不需要知道 MCP 的存在。它只是"调用了一个函数"。MCP 的 Client 负责把它变成 JSON-RPC 请求发到对应 Server。反过来，Server 也不需要知道模型是谁——它只处理 JSON-RPC。

**这就是 MCP 的价值所在**：模型和工具完全解耦。你把 MCP Server 从 Claude Desktop 配置到 Cursor，底层从 Tool Use 切换到了 Function Calling，但 Server 不动。

## 生态数据可信度

MCP 的生态数据经常被引用，但需要分清楚哪些是"注册数量"、哪些是"真正可用"。

2026 年的数据如下：

| 指标 | 数据 | 说明 |
|------|------|------|
| MCP 注册表条目 | 约 16,950 | modelcontextprotocol.io 注册表 + 爬虫汇总 |
| 有效 Server | 8,060 | 去重后 90 天内有更新的项目 |
| 月 SDK 下载 | 9,700 万（2025-12）→ 1.64 亿（2026-04） | Python + TypeScript SDK 合计 |
| 死亡 Server 比例 | 约 52% | 一次性 Demo 或无人维护 |

数据主要来自 [arXiv 2509.25292](https://arxiv.org/abs/2509.25292)，一项覆盖 6 个 MCP 注册表的系统测量。**关键发现**：8,060 个有效 Server 意味着生态已经足够丰富，但 52% 的死亡率说明挑选 Server 时需要谨慎——优先选官方维护的（Anthropic 官方、社区核心团队）或 Star 数高的。

## 总结

- **MCP 的演进速度极快**：从 2024-11 的实验项目到 2026 年的行业标准，只用了 18 个月
- **Linux Foundation 治理保证了厂商中立**：版本兼容性和功能演进可以兼顾
- **Gateway 是企业级部署的关键**：认证、审计、限流、安全扫描——小型团队直连，大团队引入 Gateway
- **MCP 与 Function Calling 共存**：MCP 是协议层，Function Calling 是 LLM 原生能力，两者不冲突
- **生态数据需要辨别**：52% 的注册 Server 是死亡状态，选 Server 优先看维护状态

> 下一篇 [A2A 与 Agent 通信协议](./03-a2a-and-beyond.md)——从 MCP 的垂直集成到水平协作，了解 Agent 之间如何通信和协作。

## 参考链接

- [MCP Specification (2025-11)](https://spec.modelcontextprotocol.io/)
- [Anthropic — MCP Donation to Linux Foundation (2025-12)](https://www.anthropic.com/news/model-context-protocol)
- [arXiv 2509.25292 — A Measurement Study of MCP](https://arxiv.org/abs/2509.25292)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [mcp-gateway (Open Source)](https://github.com/punkpeye/mcp-gateway)
- [mcp-proxy (Open Source)](https://github.com/sparfenyuk/mcp-proxy)
