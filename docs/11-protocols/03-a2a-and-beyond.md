# A2A 与 Agent 通信协议

> MCP 解决的是 Agent 与工具的垂直集成。但 Agent 之间怎么通信？A2A、ACP、ANP 三个协议覆盖了从企业协作到去中心化发现的全谱系。本文讲清楚它们的定位和用法。

## 目录

- [垂直集成 vs 水平协作](#垂直集成-vs-水平协作)
- [A2A：跨企业 Agent 协作](#a2a跨企业-agent-协作)
- [ACP：有状态协作与并入 A2A](#acp有状态协作与并入-a2a)
- [ANP：去中心化 Agent 网络](#anp去中心化-agent-网络)
- [三协议对比与选型](#三协议对比与选型)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面讲了 MCP，它让 Agent 通过标准化方式调用工具，属于 **垂直集成**——Agent 向下连接到数据库、API、文件系统。但你的 Agent 不可能一个人做完所有事：它需要向另一个 Agent 查数据、让专门的 Agent 处理图像、把耗时任务托管给后台服务。这就是 **水平协作**——Agent 之间如何找到对方、理解对方能做什么、委托任务并拿到结果。

本文覆盖三个水平层协议：**A2A**（企业协作，已被广泛采纳）、**ACP**（IBM 的方案，已并入 A2A）、**ANP**（去中心化网络，面向开放互联网）。

## 垂直集成 vs 水平协作

先搞清楚这两个概念的区别：

<p align="center">
  <img src="../../assets/11-protocols/vertical-vs-horizontal.svg" alt="垂直集成（MCP）vs 水平协作（A2A/ANP）" width="90%"/>
</p>

| 维度 | 垂直集成 | 水平协作 |
|------|---------|---------|
| **方向** | Agent → 工具 | Agent ↔ Agent |
| **典型协议** | MCP | A2A、ACP、ANP |
| **主机关系** | 同一系统（Client-Server） | 跨系统（Peer-to-Peer） |
| **任务复杂度** | 单次调用 | 多步委托，生命周期管理 |
| **身份** | 配置固定（无需发现） | 动态发现（Agent Card / DID） |

**一个 Agent 同时做两件事**：用 MCP 调用工具获取数据，用 A2A 把分析结果发给另一个 Agent 做可视化。这两个协议不是二选一，而是搭档。

## A2A：跨企业 Agent 协作

A2A（Agent-to-Agent Protocol）由 Google 于 2025 年 4 月发布，2025 年 6 月捐赠给 Linux Foundation，2026 年初达到 v1.0。它是目前水平层采纳最广泛的协议，50+ 厂商发布时即表态支持。

### 核心概念：Agent Card

每个 A2A Agent 在 `/.well-known/agent-card.json` 发布一个 JSON 文件，描述自己的能力：

```json
{
  "name": "数据分析-Agent",
  "description": "处理数据查询和报表生成",
  "capabilities": {
    "skills": ["数据查询", "趋势分析", "报表导出"]
  },
  "endpoints": [
    {
      "url": "https://analytics.example.com/a2a",
      "type": "sse"
    }
  ],
  "authentication": {
    "schemes": ["bearer"]
  }
}
```

**Agent Card 是 A2A 的入口**。调用方根据 Card 判断"这个 Agent 能不能做我要的事"，然后通过它声明的 endpoint 发起通信。Card 可以动态更新，Agent 下线或能力变更时自动失效。

### 任务生命周期

A2A 定义了标准的任务状态机。一个委托任务从创建到完成遵循以下流程：

```
┌─────────┐
│ pending │── 任务已创建，等待 Agent 接手
└────┬────┘
     ▼
┌─────────┐
│ working │── Agent 正在执行
└────┬────┘
     ├────────────────────┐
     ▼                    ▼
┌──────────┐   ┌──────────────────┐
│completed │   │ input-required   │── Agent 需要更多信息
└──────────┘   └──────────────────┘
     │                    │
     ▼                    ▼
┌───────┐       继续 working（收到新输入后）
│ failed│
└───────┘
```

**input-required 是 A2A 的关键设计**。它让 Agent 可以向调用方请求更多信息——比如"你要查哪个月的数据？"。这让协作可以双向交互，而不是一次性的"发指令→等结果"。

### 三种交互模式

A2A 支持三种模式，对应不同的延迟要求：

- **同步（Synchronous）**：请求发出后立即返回结果。适用于低延迟场景，如查天气、翻译文本
- **流式（Streaming）**：通过 SSE 实时推送进度和中间结果。适用于长任务，如生成报告、批量处理
- **异步（Asynchronous）**：后台执行，完成后通过回调通知。适用于耗时任务，如每周一次的报表生成

### 实际用法

在 Google ADK 中，调用一个 A2A Agent 只需要几行配置：

```python
from google.adk import RemoteA2aAgent

analytics_agent = RemoteA2aAgent(
    agent_card_url="https://analytics.example.com/.well-known/agent-card.json",
    auth_token="xxx"
)

result = await analytics_agent.send_task(
    task="查询上季度各产品线的收入趋势",
    mode="streaming"
)
```

ADK 的 `RemoteA2aAgent` 每次只路由到一个远程 Agent。如果需要同时查询多个 Agent（如价格、质量、物流），官方推荐直接用 `a2a-sdk` 库。

## ACP：有状态协作与并入 A2A

ACP（Agent Communication Protocol）由 IBM Research 于 2025 年 3 月发布，基于 BeeAI 框架。它的设计理念和 A2A 有明显差异：

| 维度 | A2A（v0.x） | ACP |
|------|------------|-----|
| **设计哲学** | 轻量委托，Agent 保持黑盒 | 有状态协作，Agent 内部可观察 |
| **消息格式** | JSON-RPC | Multipart MIME |
| **状态管理** | 任务级生命周期 | 会话级状态持久化 |
| **异步模式** | 回调可见 | 原生异步优先，内置消息队列 |
| **运行时** | 协议层无关 | BeeAI 框架集成 |

**2025 年 8 月，IBM 和 Google 宣布 ACP 并入 A2A**。ACP 的状态管理、异步消息、多部分消息格式等设计被吸收进 A2A v1.0 规范。实际效果是：你不需要在 A2A 和 ACP 之间做选择——A2A v1.0 已经包含了 ACP 的核心价值。

这对开发者意味着：**学 A2A 就够了**。如果你在用 BeeAI 框架，BeeAI 也会支持 A2A v1.0。

## ANP：去中心化 Agent 网络

ANP（Agent Network Protocol）由社区工作组开发，目标是做 "Agent 世界的 HTTP"——不依赖中心注册表，任何 Agent 都能找到和信任其他 Agent。

### 核心设计

ANP 有三层架构：

- **身份层**：使用 W3C Decentralized Identifiers（DIDs），`did:wba` 方法基于 HTTPS 和 DNS，不需要区块链。每个 Agent 拥有一个唯一且可验证的身份
- **发现层**：Agent 用 JSON-LD 图描述自己的能力，使用 schema.org 词汇。不需要中心注册表，Agent 通过 DID 解析直接获取对方的能力描述
- **传输层**：基于 HTTPS，支持端到端加密

```json
{
  "@context": ["https://schema.org", "https://agent-network-protocol.io/context"],
  "id": "did:wba:agent.example.com:agent-1",
  "type": "SoftwareAgent",
  "name": "数据爬虫 Agent",
  "capability": [
    {
      "type": "Action",
      "name": "WebScrape",
      "description": "抓取指定 URL 的内容"
    }
  ],
  "endpoint": "https://agent.example.com/anp"
}
```

### ANP 的适用场景

| 场景 | ANP 优势 | A2A 优势 |
|------|---------|---------|
| 企业内部 Agent 协作 | — | Agent Card + 企业级管控 |
| 跨企业合作伙伴 | DID 身份验证 | 需要双方信任 Agent Card |
| 开放市场的发现 | JSON-LD 语义搜索 | Agent Card 静态注册 |
| 去中心化/自治 Agent | 原生支持 | 不支持 |

**ANP 和 A2A 不是竞争关系**。多个行业分析（Zylos、OSSA）建议：ANP 做身份和发现，A2A 做任务委托。ANP 解决"怎么找到你、怎么信任你"，A2A 解决"找到了之后怎么协作"。

## 三协议对比与选型

<p align="center">
  <img src="../../assets/11-protocols/agent-communication-comparison.svg" alt="A2A/ACP/ANP 三协议对比" width="90%"/>
</p>

| 协议 | 一句话 | 采纳程度 | 适合谁 |
|------|--------|---------|-------|
| **A2A** | 企业按需选择"让它干" | 高，50+ 厂商 | 大多数 Agent 开发者 |
| **ACP** | 已并入 A2A | — | 历史知识，无需单独学 |
| **ANP** | 开放互联网的 Agent 身份与发现 | 社区阶段 | 去中心化/跨组织场景 |

**建议**：从 A2A 开始。它最成熟、文档最全、厂商支持最多。如果将来需要跨组织的开放 Agent 网络，再引入 ANP。

## 总结

- **垂直集成 vs 水平协作**：MCP 管工具（向下），A2A/ANP 管 Agent 间通信（横向），两者互补
- **A2A 是企业协作的事实标准**：Agent Card 做能力声明、标准任务生命周期、三种交互模式、50+ 厂商背书
- **ACP 已并入 A2A**：IBM 的 ACP 在 2025-08 正式合并，A2A v1.0 吸收了其有状态协作设计
- **ANP 面向去中心化**：W3C DIDs + JSON-LD，解决开放互联网上的 Agent 身份与发现
- **选型建议**：A2A 起步，需要跨组织发现时加 ANP

> 下一篇 [A2A 实战：多 Agent 协作实现](./04-a2a-in-practice.md)——从概念到代码，用 A2A SDK 搭建一个真正的多 Agent 协作系统。

## 参考链接

- [A2A Specification (v1.0)](https://github.com/google/A2A)
- [Google ADK — RemoteA2aAgent](https://google.github.io/adk/)
- [IBM — ACP Joins A2A (2025-08)](https://www.ibm.com/research/blog/agent-communication-protocol)
- [ANP Specification](https://github.com/Agent-Network-Protocol)
- [W3C Decentralized Identifiers (DIDs)](https://www.w3.org/TR/did-core/)
- [OSSA Survey: Agent Communication Protocols 2026](https://openstandardagents.org/research/agent-communication-protocol-survey/)
- [Linux Foundation — Agentic AI Foundation](https://agentic.ai/)
