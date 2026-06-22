# 三大框架对比：Claude Code vs Hermes vs OpenClaw

前两篇我们深入分析了 Claude Code 的架构，知道它用 51 万行代码构建了一个生产级 Agent 系统。但 Claude Code 不是唯一的选择。

2026 年，开源 Agent 框架已经形成了三足鼎立的局面：Claude Code、Hermes、OpenClaw。三个框架的设计哲学完全不同，适用的场景也完全不同。

这一篇，我们用真实数据对比这三个框架，看看它们各自的优势和劣势。不端水，直接说结论。

## 代码规模

先看代码量。

| 框架 | 代码行数 | 语言 | 文件数 |
|------|---------|------|--------|
| Claude Code | ~510K 行 | TypeScript | 1,884 文件 |
| Hermes | ~500K 行 | Python | 870-1,598 文件 |
| OpenClaw | ~430K 行 | TypeScript | - |

三个框架都是生产级规模，代码量都在 40-50 万行级别。Claude Code 略大，但差距不大。

但代码量的分布完全不同。

Claude Code 的 51 万行中，98.4% 是工程基础设施，AI 决策逻辑只占 1.6%。它的核心是一个 88 行的 while 循环，包裹着 40 万行的权限管理、上下文压缩、会话存储等工程代码。

Hermes 的 50 万行中，核心是 `run_agent.py`（约 10,700 行），其余是工具、平台适配、记忆系统。它的设计哲学是"自我进化"，强调让 Agent 越用越好。

OpenClaw 的 43 万行中，核心是平台集成层，支持 24 个消息平台（Slack、Discord、Telegram 等）。它的设计哲学是"连接一切"，强调让 Agent 能在任何平台上运行。

三个框架的代码量接近，但设计哲学完全不同。

## Agent 循环

Agent 循环是框架的心脏，决定了 Agent 怎么运行。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 核心循环 | `while(true)` + 7 种 transition | `run_conversation()` + 3 种 API mode | Polling loop + SQLite IPC |
| 状态管理 | 可变 State 对象，跨迭代携带 | 不可变配置 + 可变历史分离 | SQLite 持久化 + 内存快照 |
| 错误恢复 | **7 层恢复策略** | 重试 + fallback 模型切换 | 基础重试 |
| 流式处理 | StreamingToolExecutor 边收边跑 | 支持流式但无并发调度 | 无流式 |

Claude Code 的 Agent 循环最复杂，有 7 种不同的 `transition.reason`，每种原因对应不同的继续策略。当上下文快满时，循环会尝试不同的压缩策略（响应式压缩、自动压缩、微压缩、上下文折叠、裁剪），然后重试。这个设计让 Claude Code 能在长对话中保持稳定。

Hermes 的 Agent 循环相对简单，有 3 种 API mode（同步、异步、流式）。它的设计哲学是"简单可靠"，不追求复杂的错误恢复，而是通过重试和 fallback 来保证稳定性。

OpenClaw 的 Agent 循环最简单，就是一个 polling loop，从 SQLite 读取消息，调用模型，写回结果。它的设计哲学是"平台集成"，不追求循环的复杂性，而是追求平台的广泛性。

**结论**：Claude Code 的 Agent 循环最复杂，错误恢复最精细。Hermes 和 OpenClaw 的循环相对简单，但各有侧重。

## 工具系统

工具系统决定了 Agent 能做什么。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 工具数量 | 42 个内置 | 40+ 内置 | 100+ AgentSkills |
| 工具定义 | `Tool` 接口 + Zod Schema | Python 函数 + 装饰器 | SKILL.md 声明式 |
| 并发调度 | isConcurrencySafe 标注 + 并行/串行 | 线程池并发 | 串行 |
| 执行 Pipeline | 8 步（校验→Hook→权限→执行→Hook） | 3 步（校验→执行→结果） | 2 步（执行→结果） |
| 错误级联 | siblingAbortController 一刀切 | 无 | 无 |

Claude Code 的工具系统最复杂，有 8 步执行 Pipeline：校验输入 → 执行前置 Hook → 权限检查 → 执行工具 → 执行后置 Hook → 格式化结果 → 记录遥测 → 返回结果。每一步都有明确的职责，可以独立测试、独立优化。

Hermes 的工具系统相对简单，有 3 步执行 Pipeline：校验输入 → 执行工具 → 返回结果。它的设计哲学是"简单直接"，不追求复杂的 Pipeline，而是追求工具的易用性。

OpenClaw 的工具系统最简单，有 2 步执行 Pipeline：执行工具 → 返回结果。它的设计哲学是"平台集成"，不追求工具系统的复杂性，而是追求工具的广泛性（100+ AgentSkills）。

**结论**：Claude Code 的工具系统最复杂，执行 Pipeline 最精细。Hermes 和 OpenClaw 的工具系统相对简单，但各有侧重。

## 上下文管理

上下文管理决定了 Agent 能记住多少东西。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 压缩层数 | **5 层渐进式** | 1 层（>50% 触发） | 无自动压缩 |
| 关键阈值 | AUTOCOMPACT_BUFFER=13000 等精确配置 | 简单百分比 | 无 |
| CLAUDE.md 保护 | 永不删除特权 | 无 | 无 |
| 熔断机制 | MAX_CONSECUTIVE_FAILURES=3 | 无 | 无 |
| Prompt Cache | Sticky-on Latch + 14 个缓存断点 | 冻结快照模式 | 无 |

Claude Code 的上下文管理最复杂，有 5 层渐进式压缩机制：

1. Budget reduction — 削减工具输出的预览长度
2. Snip — 删掉会话前面已经没用的工具结果
3. Microcompact — 压缩特定段落
4. Context collapse — 把大段对话总结成摘要
5. Auto-compact — 全 session 总结，最后手段

系统在上下文用到 92% 的时候自动触发，从第 1 层开始往下试，能在便宜的层解决就不动贵的。这个设计的好处是：大部分时候前两层就能腾出足够空间，不需要动到代价最大的全 session 总结。

Hermes 的上下文管理相对简单，只有 1 层压缩，当上下文超过 50% 时触发。它的设计哲学是"简单可靠"，不追求复杂的压缩策略，而是追求压缩的稳定性。

OpenClaw 没有自动压缩机制。它的设计哲学是"平台集成"，不追求上下文管理的复杂性，而是追求平台的广泛性。

**结论**：Claude Code 的上下文管理最复杂，压缩策略最精细。Hermes 有基础压缩，OpenClaw 没有自动压缩。

## 记忆系统

记忆系统决定了 Agent 能学习多少东西。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 记忆层次 | 3 层（提取→会话→Dream） | 2 层（MEMORY.md + USER.md） | 全局/群组/会话 3 级 |
| 自我进化 | autoDream 后台反思 | **Skill 自动生成** | 无 |
| 记忆安全 | 路径不可信校验 | **注入扫描器** | 无 |
| 文件锁 | using 资源管理 | **fcntl/msvcrt 文件锁** | 无 |
| 新鲜度 | 时间戳 + 老化权重 | 无 | 无 |

这里需要纠正一个常见的误解。

很多人说 Hermes 的记忆系统很强大，但实际上 Hermes 的记忆系统很简陋，只有两个文件（MEMORY.md + USER.md），总共 1,300 token。

但 Hermes 有一个亮点：**Skill 自动生成**。每次完成任务后，Hermes 会自动把经验写成 SKILL.md 文件，下次遇到类似任务直接加载。实测第二次运行 token 消耗降低 17%。

这不是"记忆系统"，而是"学习循环"。Claude Code 的记忆系统更复杂（3 层 + autoDream + KAIROS 守护进程），但 Hermes 的 Skill 自动生成是独家设计。

OpenClaw 的记忆系统也相对简单，有全局/群组/会话 3 级记忆，但没有自我进化机制。它的设计哲学是"平台集成"，不追求记忆系统的复杂性，而是追求平台的广泛性。

**结论**：Claude Code 的记忆系统最复杂，有 3 层 + autoDream + KAIROS。Hermes 的记忆系统简陋，但有 Skill 自动生成的学习循环。OpenClaw 有基础记忆，但没有自我进化。

## 权限与安全

权限系统决定了 Agent 能做什么、不能做什么。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 权限模式 | **7 种 + 8 级优先级** | 基础 allow/deny | 容器隔离 |
| ML 分类器 | ✅ auto 模式 | ❌ | ❌ |
| Bash 安全 | 23 项检查 + 18 个屏蔽命令 | 基础沙箱 | OS 级容器隔离 |
| 防护层数 | 3 层（注册过滤→调用检查→交互询问） | 1 层 | 1 层（容器） |
| Prompt Injection | watchdog Agent 拦截 | 记忆注入扫描 | 无 |

Claude Code 的权限系统最复杂，有 7 种运行模式、8 级规则优先级、3 层防护结构。还有一个 ML 分类器在 auto 模式下自动判断安全性。

Hermes 的权限系统相对简单，只有基础的 allow/deny。它的设计哲学是"简单可靠"，不追求复杂的权限系统，而是追求权限的易用性。

OpenClaw 的权限系统最简单，只有 OS 级容器隔离。它的设计哲学是"平台集成"，不追求权限系统的复杂性，而是追求平台的广泛性。但 OS 级容器隔离在部署安全上更彻底。

**结论**：Claude Code 的权限系统最复杂，三层防护 + ML 分类器是业界最精细的权限设计。Hermes 有基础权限，OpenClaw 有 OS 级容器隔离。

## 扩展生态

扩展生态决定了 Agent 能集成多少东西。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 扩展机制 | 4 种（Hook/Skill/Plugin/MCP） | 2 种（Skill/MCP） | 2 种（Skill/MCP） |
| 成本分级 | 明确（零→低→中→高） | 无 | 无 |
| 平台集成 | CLI + IDE + SDK | **18+ 平台** | 24+ 平台 |
| 市场生态 | 无 | GitHub-backed Skill Hub | ClawHub 市场 |

Claude Code 有 4 种扩展机制：Hook（零成本）、Skill（低成本）、Plugin（中成本）、MCP（高成本）。每种机制有明确的成本分级，开发者可以根据需求选择合适的扩展方式。

Hermes 有 2 种扩展机制：Skill 和 MCP。它的亮点是 GitHub-backed Skill Hub，可以方便地分享和复用 Skill。

OpenClaw 有 2 种扩展机制：Skill 和 MCP。它的亮点是 ClawHub 市场，可以方便地分享和复用 AgentSkills。

**结论**：Claude Code 的扩展机制最丰富，有 4 种扩展方式 + 明确的成本分级。Hermes 和 OpenClaw 的扩展机制相对简单，但各有侧重。

## 启动性能

启动性能决定了用户体验。

| 维度 | Claude Code | Hermes | OpenClaw |
|------|------------|--------|----------|
| 冷启动 | **~135ms** | ~3-5s | 8-12s |
| 优化技巧 | import 间插入副作用 | 无 | 无 |
| Fast-path | `--version` 12ms 退出 | 无 | 无 |
| 内存占用 | 中等 | 中等 | **1GB+** |

Claude Code 的启动性能最好，冷启动约 135ms。它做了大量优化：Fast-path 分发、并行预取、延迟初始化。`--version` 命令甚至可以在 12ms 内退出。

Hermes 的启动性能中等，冷启动约 3-5s。它是 Python 应用，启动慢是语言特性，不是设计问题。

OpenClaw 的启动性能最差，冷启动 8-12s，内存占用 1GB+。它是 Python 应用，而且加载了大量依赖，启动慢是预期内的。

**结论**：Claude Code 的启动性能最好，做了大量优化。Hermes 和 OpenClaw 的启动性能中等和差，但都是 Python 应用，启动慢是语言特性。

## 综合评分

| 维度 | Claude Code | Hermes | OpenClaw |
|------|:-----------:|:------:|:--------:|
| Agent 循环 | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |
| 工具系统 | ★★★★★ | ★★★☆☆ | ★★★☆☆ |
| 上下文管理 | ★★★★★ | ★★☆☆☆ | ★☆☆☆☆ |
| 记忆系统 | ★★★★☆ | ★★★★☆ | ★★★☆☆ |
| 权限安全 | ★★★★★ | ★★☆☆☆ | ★★★☆☆ |
| 扩展生态 | ★★★★☆ | ★★★★☆ | ★★★★☆ |
| 启动性能 | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |
| **总分** | **38/40** | **26/40** | **20/40** |

**结论**：Claude Code 在工程化方面全面领先，Hermes 在记忆系统（学习循环）上有亮点，OpenClaw 在平台集成上有优势。

## 谁更值得学习

按学习目的分类：

| 你想学什么 | 学谁 | 原因 |
|-----------|------|------|
| **生产级 Agent 工程化** | Claude Code | 错误恢复、权限、压缩、缓存都是业界标杆 |
| **Agent 自我进化** | Hermes | Skill 自动生成是独家设计 |
| **多平台消息集成** | OpenClaw | 24+ 平台适配器的设计模式值得参考 |
| **OS 级安全隔离** | OpenClaw | 容器隔离比逻辑权限更彻底 |
| **设计哲学与价值观** | Claude Code | 唯一有正式文档的框架 |
| **快速上手做 Agent** | OpenClaw | 架构简单，适合理解基本概念 |

**我的建议**：

1. **最值得深读**：Claude Code — 工程化程度最高，每个模块都有可借鉴的设计
2. **最值得参考**：Hermes 的 Skill 自动生成 — 学习循环的最佳实践
3. **最不推荐**：OpenClaw — 平台集成广但技术含量低，记忆系统有缺陷（19.6s 召回延迟）

**一句话总结**：Claude Code 是"怎么做对"，Hermes 是"怎么做好"，OpenClaw 是"怎么做大"。

## 小结

三个框架各有侧重，没有绝对的"最好"。

Claude Code 在工程化方面全面领先，是生产级 Agent 的标杆。Hermes 在学习循环上有创新，是自我进化 Agent 的先锋。OpenClaw 在平台集成上有优势，是多平台 Agent 的标杆。

选择哪个框架，取决于你的需求。如果你想做生产级 Agent，学 Claude Code。如果你想做自我进化 Agent，学 Hermes。如果你想做多平台 Agent，学 OpenClaw。

但无论选择哪个框架，都要记住：**智能是模型给的，可用性是工程给的。**
