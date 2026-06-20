# 扩展协议全景

> 2025 到 2026 年，Agent 协议从各自为政走向分层共存。本文梳理 MCP、A2A、ACP、ANP、AG-UI、OAP 等协议的定位与关系，帮你建立完整的协议认知地图。

## 目录

- [Agent 的碎片化困境](#agent-的碎片化困境)
- [协议分层模型](#协议分层模型)
- [垂直层：Agent 连接工具](#垂直层agent-连接工具)
- [水平层：Agent 间通信](#水平层agent-间通信)
- [交互层：Agent 连接用户](#交互层agent-连接用户)
- [商业与契约层](#商业与契约层)
- [2026 协议格局：互补而非竞争](#2026-协议格局互补而非竞争)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。从 [工具调用](../05-tool-use/01-tool-calling-mechanism.md) 到 [Agent 框架概述与选型](../10-framework/01-framework-overview.md)，你的 Agent 已经具备了完整的执行能力。但这里有一个隐性问题：所有工具和交互都绑定在特定的模型和实现上——换个客户端就得重写集成，换个厂商就得重新适配。

**扩展协议** 就是来解决这个问题的。它们定义了一套标准的"连接方式"，让 Agent 可以跨平台调用工具、跨系统协作、跨前端呈现结果。2025-2026 年，Agent 协议领域爆发了 MCP、A2A、ACP、ANP、AG-UI、OAP 等多个标准——看起来碎片化严重，但其实每一层都有清晰的定位。

读完本文，你将理解这些协议的分层结构、各自的定位、以及 2026 年的行业共识。

## Agent 的碎片化困境

在协议爆发之前，每个 Agent 都是一个**孤岛**：

<p align="center">
  <img src="../../assets/11-protocols/protocol-fragmentation.svg" alt="无协议时的 Agent 孤岛困境" width="90%"/>
</p>

- **工具绑定**：换一个客户端（Claude → GPT），所有工具集成重写
- **厂商锁定**：换个平台（Google → Anthropic），Agent 通信机制完全不同
- **前端耦合**：Agent 的输出格式与前端渲染逻辑深度绑定
- **重复劳动**：每个新的 Agent 项目都要重复实现一遍工具调用、状态同步、认证鉴权

这个问题在 2025 年达到顶峰。厂商各自推出自己的集成方案，但彼此不兼容。开发者面临的是 **N×M×K 问题**——N 个客户端、M 个工具、K 个厂商，需要写 N×M×K 套代码。

**协议的爆发不是竞争，而是各层"填空"**。每个协议解决一个问题面，合在一起覆盖了 Agent 交互的完整链路。

## 协议分层模型

2026 年，行业共识已经形成：Agent 协议按 **交互方向** 分为三层，外加一个**跨层契约层**：

<p align="center">
  <img src="../../assets/11-protocols/protocol-layers.svg" alt="Agent 协议分层模型：垂直层、水平层、交互层、商业层" width="90%"/>
</p>

| 层 | 交互方向 | 核心协议 | 解决什么问题 |
|-----|---------|---------|-------------|
| **垂直层** | Agent → 工具 | MCP | 标准化工具调用和数据获取 |
| **水平层** | Agent ↔ Agent | A2A / ACP / ANP | 跨 Agent 的任务委托与协作 |
| **交互层** | Agent → 前端 | AG-UI / A2UI | Agent 向用户界面流式输出 |
| **商业层**（跨层）| 全域 | OAP / UCP / AP2 | 计费、身份、审计、合规 |

**关键认知**：这些协议不是竞争关系，而是互补关系。一个生产级 Agent 通常会同时使用 MCP（连工具）+ A2A（连其他 Agent）+ AG-UI（连前端）+ OAP（做合规）。

## 垂直层：Agent 连接工具

### MCP（Model Context Protocol）

MCP 是 2026 年工具集成层的**事实标准**。由 Anthropic 于 2024 年 11 月发布，2025 年 12 月捐赠给 Linux 基金会。到 2026 年中，生态数据如下：

- **10,000+** 有效公共 Server
- **1.64 亿** 月 Python SDK 下载量
- **原生支持**：Claude、ChatGPT、Cursor、Gemini、VS Code、Zed、Windsurf

MCP 定义了四个角色：**Host**（用户应用）、**Client**（连接实例）、**Server**（暴露工具/资源/Prompt 的服务）、**Gateway**（可选的企业级路由层）。传输方式支持 STDIO（本地）和 Streamable HTTP（远程）。

实现细节在 [MCP 与工具生态](../05-tool-use/04-mcp-and-tool-ecosystem.md) 中已有详细讲解，本章不再重复。第 02 篇会从协议治理和企业部署的角度做深入分析。

## 水平层：Agent 间通信

水平层的协议最多，也最容易混淆。2026 年实际上是三个协议覆盖了 Agent 间通信的不同场景：

### A2A（Agent-to-Agent Protocol）

由 Google 于 2025 年 4 月发布，2025 年 6 月捐赠给 Linux Foundation。目标是**跨厂商**的 Agent 任务委托。核心概念是 **Agent Card**——每个 Agent 发布一个 JSON 文件描述自己的能力，其他 Agent 通过 Agent Card 发现和调用。

A2A 定义了三种交互模式：**同步**（即时返回）、**流式**（SSE 实时推送）、**异步**（后台执行，回调通知）。任务有标准的生命周期状态：pending → working → completed / failed / input-required。

发布时有 50+ 厂商背书（Salesforce、SAP、ServiceNow、MongoDB 等）。2026 年达到 v1.0，是水平层采纳最广的协议。

### ACP（Agent Communication Protocol）

由 IBM Research 于 2025 年 3 月发布，基于 BeeAI 框架。它的设计理念是 **REST 原生 + 有状态消息**。与 A2A 的偏轻量委托不同，ACP 支持多部分 MIME 消息、会话状态管理和长时运行任务。

**2025 年 8 月，IBM 和 Google 宣布 ACP 并入 A2A**，统一在 Linux Foundation 下治理。ACP 的状态管理和异步通信概念被吸收进 A2A v1.0 规范。因此 2026 年的实际建议是：直接用 A2A，ACP 的增量价值已经被继承。

### ANP（Agent Network Protocol）

由社区工作组开发的去中心化协议。它的目标是做 "Agent 世界的 HTTP"——不依赖任何中心注册表，而是用 **W3C Decentralized Identifiers（DIDs）** 做 Agent 身份，用 **JSON-LD** 描述能力。

ANP 适合跨组织的开放的 Agent 网络。A2A 适合企业内部的 Agent 协作，ANP 适合跨企业边界的发现与通信。两者可以组合使用：ANP 做身份和发现，A2A 做任务委托。

| 协议 | 发起方 | 治理 | 发现机制 | 适合场景 |
|------|--------|------|---------|---------|
| **A2A** | Google | Linux Foundation | Agent Card（.well-known） | 企业跨厂商协作 |
| **ACP** | IBM | 已并入 A2A | REST 端点 | — |
| **ANP** | 社区 | 社区 | W3C DIDs + JSON-LD | 去中心化开放网络 |

## 交互层：Agent 连接用户

Agent 的输出最终要呈现给用户。传统方式是用模板渲染，但 Agent 的响应是动态的、流式的、甚至包含交互组件。**AG-UI（Agent-User Interface Protocol）** 由 CopilotKit 于 2025 年提出，定义了 Agent 向前端流式输出的标准格式。

AG-UI 的核心思路：Agent 的输出不是纯文本，而是一系列 **事件流**——文本块、卡片、图表、表单、确认对话框。前端按事件类型渲染对应组件，无需为每个 Agent 写定制适配层。

<p align="center">
  <img src="../../assets/11-protocols/protocol-interaction-layer.svg" alt="AG-UI 让 Agent 输出与前端解耦" width="90%"/>
</p>

Google 也在 2026 年初推出了 **A2UI（Agent-to-User Interface）**，与 AG-UI 定位类似。两者的差异在于：AG-UI 偏重框架集成（React/Vue），A2UI 偏重协议规范。

对大多数开发者来说，理解"有一层协议专门处理 Agent 到前端的输出标准化"就够了。具体选哪个取决于前端框架——CopilotKit 用户选 AG-UI，Google ADK 用户选 A2UI。

## 商业与契约层

这是 2026 年最新出现的一层。当 Agent 需要执行**跨组织的商业操作**（下单、支付、签约）时，协议需要覆盖身份、计费、审计、合规等非技术需求。

### OAP（Open Agent Protocol）

OAP 是 2026 年野心最大的协议。它定义了一个**完整的 Agent 互操作栈**，覆盖身份（DIDs）、能力描述、结构化调用、定价与计费、多方协作、保密性执行、防篡改审计。OAP 提出了 L0-L5 六级合规模型：

| 级别 | 定义 | 要求 |
|------|------|------|
| L0 | 兼容 | 基本 MCP/A2A 映射 |
| L1 | 可发现 | 完整 Manifest，机器可验证 |
| L2 | 可计费 | 定价、认证、订阅、退款 |
| L3 | 可信 | 审计日志、数据策略、多方审核 |
| L4 | 协作 | 多 Agent 协调、冲突解决 |
| L5 | 认证 | 外部 SOC 2 / ISO 审计 + 三方验证 |

### UCP 与 AP2

**UCP（Universal Commerce Protocol）** 由 Google 提出，专注于电商场景——下单、查询库存、物流跟踪。**AP2（Agent Payment Protocol）** 专注于 Agent 自主支付——用加密签名的授权令（Mandate）证明支付意图和执行授权。

这两个协议对大多数 Agent 开发者来说属于"用到再看"的范畴。如果你的 Agent 涉及商业交易，可以关注 OAP 作为统一方案，它已经覆盖了 UCP 和 AP2 的能力范围。

## 2026 协议格局：互补而非竞争

以下是 2026 年中 Agent 协议格局的完整映射：

<p align="center">
  <img src="../../assets/11-protocols/protocol-landscape-2026.svg" alt="2026 年 Agent 协议全景格局" width="90%"/>
</p>

从多个行业调研（OSSA、Zylos、VentureBeat、arXiv 2505.02279）中可以看到一致的结论：

- **MCP 已在工具层胜出**。10k+ Server、1.64 亿月下载、全客户端支持，没有悬念
- **A2A 在企业协作层领先**。50+ 厂商背书、ACP 合并、Linux Foundation 治理
- **ANP 是去中心化层的未来方向**。目前还在社区阶段，适合有长期去中心化需求的团队
- **AG-UI / A2UI 还在早期**。前端交互协议尚未收敛，2026 年以集成方案为主
- **OAP 是商业层的统一尝试**。L0-L5 模型有吸引力，但采纳还停留在概念验证阶段

**最重要的建议**：不要选一个协议。选一个**协议栈**。最务实的起点是 **MCP + A2A**，它们覆盖了 80% 的场景。等业务需要时再扩展其他协议。

## 总结

- **碎片化困境驱动协议爆发**：N×M×K 问题催生了 MCP、A2A、ACP、ANP、AG-UI、OAP 等多个标准
- **协议分三层 + 商业层**：垂直层（MCP，工具集成）、水平层（A2A/ACP/ANP，Agent 通信）、交互层（AG-UI/A2UI，前端输出）、商业层（OAP，计费与合规）
- **MCP 和 A2A 是 2026 年最成熟的选择**：MCP 在工具层已是事实标准，A2A 在企业协作层领先
- **协议是互补而非竞争**：生产环境使用多协议组合，每个协议解决一个特定问题
- **开始建议**：MCP + A2A 起步，按需扩展

> 协议全景已了然于胸。下一篇 [MCP 深入](./02-mcp-in-depth.md)——从协议治理和企业部署的角度，深入理解 MCP 的内部机制和最佳实践。

## 参考链接

- [OSSA — Survey: Agent Communication Protocols in 2026](https://openstandardagents.org/research/agent-communication-protocol-survey/)
- [Google Developers Blog — Developer's Guide to AI Agent Protocols (2026-03)](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/)
- [arXiv 2505.02279 — A Survey of Agent Interoperability Protocols](https://arxiv.org/abs/2505.02279)
- [VentureBeat — MCP solved tool calling. A2A solved coordination (2026-06)](https://venturebeat.com/orchestration/mcp-solved-tool-calling-a2a-solved-coordination-what-solves-transport)
- [Zylos Research — Comparing Communication Standards (2026-03)](https://zylos.ai/research/2026-03-05-multi-agent-communication-protocols-comparison)
- [IBM — What Are AI Agent Protocols?](https://www.ibm.com/think/topics/ai-agent-protocols)
- [OAP Specification](https://github.com/openagentprotocol-OAP/oap-spec)
- [MCP Specification](https://modelcontextprotocol.io/)
- [A2A Specification](https://github.com/google/A2A)
- [ANP Specification](https://github.com/Agent-Network-Protocol)
