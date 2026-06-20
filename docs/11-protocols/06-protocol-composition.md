# 协议组合与选型

> 前面四篇介绍了一堆协议——MCP、A2A、ACP、ANP、AG-UI、OAP、Skills、AGENTS.md。现在回到最实际的问题：我的 Agent 到底该用哪些？怎么组合？从 MVP 到生产怎么一步步加？

## 目录

- [选型三原则](#选型三原则)
- [分层采纳路线图](#分层采纳路线图)
- [常见组合模式](#常见组合模式)
- [选型决策树](#选型决策树)
- [MVP 到生产的演进路径](#mvp-到生产的演进路径)
- [OAP：是否值得关注](#oap是否值得关注)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。这一章前四篇介绍了完全不同的协议，你可能已经满脑子都是缩写词了。但你不需要全部用上。大多数 Agent 从 MCP 一个协议就能启动，然后按需逐步增加。本文就是来帮你做这个选择的。

## 选型三原则

### 1. 从最成熟的开始

这是最重要的原则。2026 年的协议列表中，成熟度差异很大：

| 协议 | 成熟度 | 开始用的风险 |
|------|--------|------------|
| **MCP** | 最高 | 几乎为零，已事实标准 |
| **A2A** | 高（v1.0 + 50+ 厂商） | 低 |
| **Skills** | 中等（多家支持但格式有差异） | 低（文件级别，零成本切换） |
| **ANP** | 中低（社区阶段） | 中等（API 可能变化） |
| **AG-UI** | 低（仍在早期，尚未收敛） | 高（可能在 2027 年被取代） |
| **OAP** | 极低（概念验证） | 高（不推荐现在用于生产） |

**建议**：MCP 可以直接上生产。A2A 可以用于新项目的多 Agent 设计。其他协议保持关注，等成熟再引入。

### 2. 按层解耦，各层独立选型

协议的互补性意味着你可以**各层独立选型**，不需要一次选完：

- 工具层：MCP ✓（不用想了）
- 通信层：需要跨 Agent 吗？→ A2A。不需要？→ 跳过
- 交互层：有富前端？→ 关注 AG-UI。纯 API？→ 跳过
- 商业层：涉及跨组织交易？→ 关注 OAP。不涉及？→ 跳过

每一层的选项变化不影响其他层的选型。

### 3. 不要为未来过度设计

2026 年的 Agent 技术还在快速演进，大多数团队还在"让第一个 Agent 稳定跑起来"的阶段。这种情况下，最常见的错误是：**一次性做了多 Agent 的协议设计，但核心 Agent 还没跑通**。

<p align="center">
  <img src="../../assets/11-protocols/protocol-evolution-path.svg" alt="协议采纳不应超前于业务阶段" width="90%"/>
</p>

## 分层采纳路线图

以下路线图来自 [arXiv 2505.02279](https://arxiv.org/abs/2505.02279) 的协议调研，结合行业实践做了调整：

### Phase 1：工具接入（你在这里）

| 协议 | MCP |
|------|-----|
| 场景 | Agent 需要调用数据库、API、文件系统 |
| 复杂度 | 极低，12 行 Python 启动 |
| 交付时间 | 1-2 天 |

### Phase 2：多 Agent 协作

| 协议 | A2A |
|------|-----|
| 场景 | Agent 需要拆分任务给子 Agent，或跨系统协作 |
| 复杂度 | 中等，需要设计 Agent 边界 |
| 前提条件 | 单体 Agent 已验证可行 |

### Phase 3：前端交互

| 协议 | AG-UI / A2UI |
|------|-------------|
| 场景 | Agent 输出需要实时流式渲染到前端 |
| 复杂度 | 中低，取决于前端框架 |
| 前提条件 | 已有前端应用 |

### Phase 4：跨组织商业

| 协议 | OAP |
|------|-----|
| 场景 | Agent 需要跨企业边界执行下单、支付、签约 |
| 复杂度 | 高，涉及身份、审计、合规 |
| 前提条件 | 有明确的跨组织合作需求 |

## 常见组合模式

以下是 2026 年实际生产中常见的协议组合：

### 模式 A：最小可行 Agent（MCP 仅此而已）

```
你的代码 → MCP Server → 数据库 / API
```

适合：个人项目、内部工具、快速原型。
不需要其他协议。MCP 已经够用，你可以用 Zero 到 MCP 启动。

### 模式 B：企业协作 Agent（MCP + A2A）

```
你的 Agent ←A2A→ 其他部门 Agent
    ↓ MCP
  数据库
```

适合：企业级多 Agent 系统。最常见的生产组合。A2A 让不同的团队可以独立开发自己的 Agent，然后通过 A2A 连接。

### 模式 C：前端交互 Agent（MCP + AG-UI）

```
用户 ←AG-UI/SSE→ 你的 Agent ←MCP→ 工具
```

适合：Chat 风格应用、Copilot 风格嵌入。Agent 在后台执行，但结果实时推送前端。

### 模式 D：全网 Agent（MCP + A2A + ANP + OAP）

```
Agent A ←A2A→ Agent B (企业内)
    ↓ ANP
跨组织发现
    ↓ OAP
商业交易
```

适合：开放的 Agent 市场、跨企业工作流。目前只有少数前沿团队走到这一步。

## 选型决策树

<p align="center">
  <img src="../../assets/11-protocols/protocol-decision-tree.svg" alt="协议选型决策树" width="90%"/>
</p>

```
你的 Agent 需要什么？
│
├── 调用外部工具？ → MCP（必选）
│
├── 其他 Agent 通信？
│   ├── 同一企业内部？ → A2A
│   ├── 跨企业边界？ → A2A + ANP
│   └── 不需要 → 跳过
│
├── 前端实时交互？
│   ├── 标准 React/Vue 前端？ → AG-UI
│   ├── Google 生态？ → A2UI
│   └── 纯 API / 后台 → 跳过
│
├── 商业交易？
│   ├── 跨组织交易？ → 关注 OAP
│   └── 不涉及 → 跳过
│
└── 任务流程管理？
    ├── 需要按需加载？ → Skills
    └── 不需要 → 跳过
```

**实际经验**：90% 的团队停在"路径 A"——只用 MCP。到"路径 B"（MCP + A2A）大概是 30%。到"路径 C"（加前端协议）大概 10%。到"路径 D"（全协议栈）少于 1%。**不要因为选项多而焦虑**。从 MCP 开始，按需向上走。

## MVP 到生产的演进路径

以下是一个实际的演进案例，展示一个 Agent 从零到生产的协议使用变化：

### 第 1-2 周：MVP（MCP 仅此而已）

```
Agent → 2 个 MCP Server（数据库 + 搜索 API）
```

功能：用户提问 → Agent 查数据库 → 返回结果。
不需要任何其他协议。

### 第 3-4 周：多工具（MCP 扩展）

```
Agent → 5 个 MCP Server（+ GitHub + Slack + 文件系统）
```

引入 Gateway 做认证和审计。

### 第 2-3 月：多 Agent（引入 A2A）

```
主 Agent ←A2A→ 搜索 Agent
    ↓ MCP              ↓ MCP
  核心工具             搜索 API
```

主 Agent 做决策，搜素 Agent 处理专业领域的查询。

### 第 4-6 月：前端交互（引入 AG-UI）

```
用户 ←AG-UI→ 主 Agent ←A2A→ 搜索 Agent
                ↓ MCP              ↓ MCP
              核心工具             搜素 API
```

Agent 的执行进度、中间结果实时流式呈现到前端网页。

### 半年后：商业部署（引入 OAP）

```
跨企业 → OAP 合约 → 你的 Agent ↔ 客户 Agent
```

当你的 Agent 需要向客户收费或签署协议时，引入 OAP。

## OAP：是否值得关注

OAP 在 2026 年是最新和最有野心的协议。它的 L0-L5 合规模型（从基本兼容到 SOC 2 认证）非常完整，但采纳度还很低。

| 时机 | 建议 |
|------|------|
| 现在（2026 中） | 关注，但不依赖。OAP 的很多概念（DID 身份、计费、审计）在生态中还未验证 |
| 2027 年展望 | 如果 Linux Foundation 接管治理，OAP 可能成为商业层的标准 |
| 适合的先行者 | 如果你的 Agent 涉及跨组织商业交易，OAP 值得小范围试点 |

## 总结

- **选型三原则**：从最成熟开始、各层独立选型、不要超前设计
- **MCP 是唯一必选项**：2026 年所有 Agent 都应该用 MCP 连接工具
- **A2A 是扩展首选**：需要多 Agent 协作时引入，成熟度高
- **其他协议按需引入**：ANP（去中心化）、AG-UI（前端）、OAP（商业）——等你有明确需求再说
- **90% 团队只用 MCP**，30% 加了 A2A，10% 到前端协议，1% 到全栈

> 下一章 [12 — 多 Agent](../12-multi-agent/README.md)，进入多 Agent 协作的世界——不是通过协议连接外部 Agent，而是在同一系统内设计多个 Agent 的协作架构。

## 参考链接

- [arXiv 2505.02279 — Phased Adoption Roadmap](https://arxiv.org/abs/2505.02279)
- [Google Developers Blog — Add protocols as you need them](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/)
- [VentureBeat — Layered Adoption Strategy (2026-06)](https://venturebeat.com/orchestration/mcp-solved-tool-calling-a2a-solved-coordination-what-solves-transport)
- [IBM — What Are AI Agent Protocols?](https://www.ibm.com/think/topics/ai-agent-protocols)
- [OAP Specification — L0-L5 Compliance Levels](https://github.com/openagentprotocol-OAP/oap-spec)
- [Zylos Research — Protocol Comparison (2026-02)](https://zylos.ai/research/2026-02-15-agent-to-agent-communication-protocols)
