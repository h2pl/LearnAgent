# 记忆框架与巩固策略

> 前三篇讲了记忆的原理和手写实现。这篇解决三个进阶问题：长期记忆有哪些类型？什么时候该用框架而不是自己写？怎么让记忆系统自我进化——自动提取、更新、遗忘？

## 目录

- [长期记忆的三种类型](#长期记忆的三种类型)
- [记忆巩固：从对话到知识](#记忆巩固从对话到知识)
- [框架一：Mem0 — 极简记忆层](#框架一mem0--极简记忆层)
- [框架二：Letta — Agent 自主记忆](#框架二letta--agent-自主记忆)
- [框架三：Zep — 企业级记忆数据库](#框架三zep--企业级记忆数据库)
- [框架四：Cognee — 知识图谱记忆](#框架四cognee--知识图谱记忆)
- [四大框架对比与选型](#四大框架对比与选型)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前三篇文章覆盖了 [Agent 记忆三层模型](./01-memory-layers.md)、[存储与检索](./02-memory-storage-retrieval.md)、[跨会话实践](./03-cross-session-memory.md)。这篇和下一篇是记忆管理的**收官二连弹**：

1. **本篇（理论）**：长期记忆分类 + 记忆巩固 + 四大框架的设计理念与选型
2. **[下一篇（实战）](./05-frameworks-hands-on.md)**：四大框架的完整 Quick Start 代码 + 生产配置 + 组合使用

## 长期记忆的三种类型

认知科学把人类长期记忆分为三类，Agent 的记忆系统也应该做同样的区分：

| 类型 | 人类类比 | Agent 场景 | 存储内容 | 检索方式 |
|------|---------|-----------|---------|---------|
| **语义记忆** (Semantic) | "地球围绕太阳转" | 用户偏好、产品知识 | 事实、概念、关系 | 语义相似度检索 |
| **情景记忆** (Episodic) | "去年夏天去了北京" | 上次对话的决策、出错经历 | 具体事件、时间戳 | 时间 + 语义混合检索 |
| **程序记忆** (Procedural) | "骑自行车不会忘" | Agent 的行为规则、工作流 | 操作规则、Few-shot 示例 | 直接加载到系统提示 |

### 为什么区分很重要？

不区分的后果：**所有记忆都走同一条路（向量检索），但不同类型的最优检索方式不同**。

```python
# ❌ 不区分：所有记忆塞进同一个向量数据库
memory.store("用户喜欢深色模式", type="fact")        # 语义记忆
memory.store("2024-06-15 用户修改了配置文件", type="event")  # 情景记忆
memory.store("代码修改前必须运行测试", type="rule")    # 程序记忆

# ✅ 区分后：每种记忆用最合适的存储和检索
class TypedMemory:
    """按类型分治的记忆系统"""

    def __init__(self, vector_db, kv_store, rules_file):
        self.semantic = vector_db      # 语义记忆 → 向量DB（语义检索）
        self.episodic = vector_db      # 情景记忆 → 向量DB（时间+语义）
        self.procedural = kv_store     # 程序记忆 → KV存储（直接加载）

    def store(self, content: str, memory_type: str, metadata: dict = None):
        meta = metadata or {}
        meta["type"] = memory_type
        meta["created_at"] = datetime.now().isoformat()

        if memory_type == "procedural":
            # 程序记忆：直接写入规则文件，每次会话启动时加载
            self.procedural.set(meta.get("rule_key", "default"), content)
        elif memory_type == "episodic":
            # 情景记忆：向量化 + 时间戳元数据
            meta["timestamp"] = datetime.now().timestamp()
            self.episodic.add(content, metadata=meta)
        else:
            # 语义记忆：向量化，不带时间约束
            self.semantic.add(content, metadata=meta)

    def retrieve(self, query: str, memory_type: str = None, top_k: int = 5):
        """按类型选择检索策略"""
        if memory_type == "procedural":
            # 程序记忆：全量加载（通常不超过几十条）
            return self.procedural.get_all()

        filters = {}
        if memory_type:
            filters["type"] = memory_type

        if memory_type == "episodic":
            # 情景记忆：时间衰减加权（最近的更重要）
            results = self.episodic.search(query, top_k=top_k * 2, filter=filters)
            return self._time_weighted_sort(results)
        else:
            # 语义记忆：纯相似度检索
            return self.semantic.search(query, top_k=top_k, filter=filters)

    def _time_weighted_sort(self, results, decay_factor=0.95):
        """时间衰减：越旧的记忆权重越低"""
        now = datetime.now().timestamp()
        for r in results:
            age_hours = (now - r.metadata.get("timestamp", now)) / 3600
            r.score *= decay_factor ** (age_hours / 24)  # 每天衰减 5%
        return sorted(results, key=lambda x: x.score, reverse=True)[:5]
```

### 三种记忆的典型内容

| 语义记忆 | 情景记忆 | 程序记忆 |
|---------|---------|---------|
| 用户偏好 Python | 2024-06-15 部署失败了 3 次 | 代码修改前必须运行测试 |
| 项目用 PostgreSQL | 上次讨论决定用 Redis 缓存 | 回复用户时先确认需求 |
| 团队成员有 Alice 和 Bob | 用户昨天问了关于 Docker 的问题 | 遇到 API 错误先重试 2 次 |
| 服务部署在 AWS us-east-1 | 上次重构花了 3 天 | 不要删除用户的原始数据 |

## 记忆巩固：从对话到知识

**记忆巩固**是指从原始对话中提取有价值的结构化记忆，决定什么值得记、什么时候更新、什么时候遗忘。这是记忆系统从"能用"到"好用"的关键跃迁。

### 提取策略：什么值得记？

不是所有对话都值得变成记忆。核心判断标准：

```
值得记 ✓                          不值得记 ✗
────────────────────              ────────────────────
用户表达明确偏好                    闲聊、寒暄
做出了重要技术决策                   临时性的问题（"几点了"）
提供了可复用的事实                   已经存在于记忆中的信息
纠正了 Agent 的错误                  一次性的操作指令
分享了长期有效的约束                  即将过时的临时信息
```

用 LLM 自动提取：

```python
def extract_memories(conversation: list[dict], llm) -> list[dict]:
    """从对话中提取值得记忆的信息"""

    extract_prompt = f"""分析以下对话，提取值得长期记住的信息。

分类规则：
- semantic: 事实、偏好、知识（长期有效）
- episodic: 具体事件、决策过程（带时间意义）
- procedural: 行为规则、操作流程（指导未来行为）

只提取满足以下条件的信息：
1. 长期有效（不是临时性的）
2. 不在已有记忆中
3. 对未来的对话有帮助

对话：
{json.dumps(conversation, ensure_ascii=False, indent=2)}

输出 JSON 数组，每条包含：
- content: 记忆内容（简洁的一句话）
- type: semantic | episodic | procedural
- importance: 1-5（5 最重要）
- reason: 为什么值得记住"""

    response = llm.chat(extract_prompt)
    memories = json.loads(response)

    # 过滤低重要性记忆（importance < 3 不存）
    return [m for m in memories if m["importance"] >= 3]
```

### 更新策略：去重与合并

记忆不是一次写入就不管了。新记忆可能与旧记忆冲突或重复：

```python
def consolidate_memory(new_memory: dict, memory_system) -> str:
    """记忆巩固：去重、更新、合并"""

    # 1. 检索相似旧记忆
    similar = memory_system.retrieve(
        new_memory["content"],
        memory_type=new_memory["type"],
        top_k=3,
        threshold=0.85  # 相似度阈值
    )

    if not similar:
        # 没有相似记忆 → 直接写入
        memory_system.store(**new_memory)
        return "created"

    # 2. 用 LLM 判断：更新、合并还是跳过
    judge_prompt = f"""比较新旧记忆，决定操作：

新记忆：{new_memory['content']}
旧记忆：{[m.content for m in similar]}

操作选项：
- UPDATE: 新记忆更新/替换旧记忆（如"用户喜欢浅色"→"用户喜欢深色"）
- MERGE: 新旧记忆合并为更完整的信息
- SKIP: 新记忆已被旧记忆覆盖，不需要存
- CREATE: 虽然相似但是不同的信息，都保留

输出：{{"action": "UPDATE|MERGE|SKIP|CREATE", "content": "最终记忆内容", "old_ids": ["要替换的旧记忆ID"]}}"""

    decision = json.loads(llm.chat(judge_prompt))

    if decision["action"] == "SKIP":
        return "skipped"
    elif decision["action"] == "UPDATE":
        for old_id in decision.get("old_ids", []):
            memory_system.delete(old_id)
        memory_system.store(decision["content"], new_memory["type"])
        return "updated"
    elif decision["action"] == "MERGE":
        for old_id in decision.get("old_ids", []):
            memory_system.delete(old_id)
        memory_system.store(decision["content"], new_memory["type"])
        return "merged"
    else:
        memory_system.store(**new_memory)
        return "created"
```

### 遗忘策略：主动淘汰

记忆不是越多越好。过多低价值记忆会污染检索结果：

```python
def memory_maintenance(memory_system, max_memories=500, min_age_days=30):
    """定期记忆维护"""

    all_memories = memory_system.get_all()

    # 1. 删除过期记忆（超过 min_age_days 且未被引用）
    now = datetime.now()
    for mem in all_memories:
        age = (now - mem.created_at).days
        if age > min_age_days and mem.access_count == 0:
            memory_system.delete(mem.id)

    # 2. 容量控制：按重要性排序，保留 top N
    remaining = memory_system.get_all()
    if len(remaining) > max_memories:
        # 按 importance × recency 排序
        scored = []
        for mem in remaining:
            age_days = (now - mem.created_at).days
            recency_score = max(0.1, 1.0 - age_days / 365)
            final_score = mem.importance * recency_score
            scored.append((mem, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # 删除低分记忆
        for mem, _ in scored[max_memories:]:
            memory_system.delete(mem.id)
```

<p align="center">
  <img src="../../assets/09-memory-management/memory-consolidation.svg" alt="记忆巩固机制" width="90%"/>
  <br/>
  <em>图：记忆巩固三阶段 — 提取/整合/遗忘，输出三类结构化知识</em>
</p>

## 框架一：Mem0 — 极简记忆层

**Mem0 是 2025-2026 年最流行的轻量级记忆方案**。它在应用逻辑和向量数据库之间建立了一个智能中间层，核心思路是"事实提取（Fact Extraction）"——不存原始对话，而是用 LLM 将对话自动提炼为离散的事实条目。

### 核心理念

```
原始对话："我叫张三，我喜欢用 Python 做后端，上周把项目部署到了 AWS"
               ↓ LLM 自动事实提取
记忆条目：
  - { "fact": "用户叫张三", "type": "semantic" }
  - { "fact": "喜欢用 Python 做后端开发", "type": "semantic" }
  - { "fact": "项目部署在 AWS", "type": "semantic", "date": "2026-06-XX" }
```

**关键特征**：

| 维度 | 说明 |
|------|------|
| **自主管理** | 开发者控制记忆的存取时机，不是 Agent 自主决策 |
| **去重合并** | 新记忆写入时自动检测与旧记忆的关系，自动 UPDATE/MERGE/SKIP |
| **延迟** | p95 < 100ms，适合实时对话 |
| **集成复杂度** | 极低——5 行代码即可给 Agent 加上记忆 |
| **Token 节省** | 论文数据显示 90%+ — 因为记忆是浓缩的事实，不是原始对话 |

- **快速集成**：已经用了 LangChain 等框架，想低成本加记忆层
- **不适用**：需要 Agent 自主决定"什么该记、什么该忘"的场景 — 这种场景适合 Letta

> Mem0 的完整 Quick Start 代码和生产配置见 [下一篇实战篇](./05-frameworks-hands-on.md#mem05-行代码给-agent-加记忆)。

## 框架二：Letta — Agent 自主记忆

**Letta（前身 MemGPT）的设计哲学与其他框架完全不同**。它不把记忆当作"开发者管理的数据库"，而是**让 Agent 像操作系统管理内存一样，自主管理自己的记忆**。

### 核心理念：LLM 作为操作系统

Letta 的核心论文《MemGPT: Towards LLMs as Operating Systems》提出了一个类比：

```
操作系统                        Letta Agent
──────────                      ────────────
物理内存（RAM）    ←→   核心记忆（Core Memory）— 始终在上下文窗口
硬盘存储（HDD）    ←→   存档记忆（Archival Memory）— 可随时换入换出
内存管理（MMU）    ←→   Agent 自主决策：什么留在核心、什么归档
```

**关键特征**：

| 维度 | 说明 |
|------|------|
| **自主管理** | **是**——Agent 自己判断哪些信息重要、哪些可以遗忘 |
| **记忆结构** | 两段式：`human` 块（关于用户的记忆）+ `persona` 块（Agent 自身设定） |
| **记忆块** | 支持多 block：`human`、`persona`、`project_context`、`conversation_summary` |
| **存储后端** | SQLite + 向量 DB（可选 Pinecone/Qdrant） |
| **学习曲线** | 高——需要理解 OS 范式和自主记忆管理的概念 |

- **需要记忆自进化的系统**：不希望每次都由开发者手动搞记忆提取和更新
- **不适用**：简单的偏好记忆（< 50 条）— Letta 的学习曲线和架构复杂度不值得

> Letta 的完整 Quick Start 代码和记忆管理流程图见 [下一篇实战篇](./05-frameworks-hands-on.md#letta创建自主记忆的-agent)。

## 框架三：Zep — 企业级记忆数据库

**Zep 是专为生产环境设计的企业级记忆服务器**。它不像 Mem0 那样做"事实提取"，也不像 Letta 那样让 Agent 自主管理，而是走**时序感知 + 自动摘要 + 知识图谱**的路线。

### 核心理念

Zep 的核心差异化能力是**时间维度感知**：

```
普通向量搜索：
  搜索 "用户的技术栈" → 返回历史上所有提到技术栈的消息
  → 结果矛盾："Java"、 "学Python"、"现在用Go" —— 不知道哪个是最新的

Zep 的时间知识图谱（Temporal Knowledge Graph）：
  搜索 "用户的技术栈" →
    2025-03: Java（后端开发）
    2025-09: Python（开始学习）
    2026-01: Go（当前主力）  ← 最新状态
  → 理解状态演进，不返回冲突答案
```

**关键特征**：

| 维度 | 说明 |
|------|------|
| **核心能力** | 时间知识图谱（Temporal Knowledge Graph）——理解信息随时间的演进 |
| **记忆类型** | 对话摘要 + 事实提取 + 实体关系 + 时间线 |
| **存储后端** | PostgreSQL + 向量 DB + 图存储（Graphiti 引擎） |
| **自主管理** | 部分——自动摘要和实体提取是自动的，检索策略由开发者控制 |
| **集成支持** | 原生 LangChain、LangGraph、OpenAI Agents SDK 适配器 |

- **状态演进追踪**：需要知道"用户从什么时候开始变了"的场景
- **不适用**：原型验证、学习阶段 — Zep 需要部署服务器，比 Mem0 重得多

> Zep 的完整 Quick Start 代码（含跨会话检索和时间演进）见 [下一篇实战篇](./05-frameworks-hands-on.md#zep企业级时序记忆)。

## 框架四：Cognee — 知识图谱记忆

**Cognee 是最"重"的记忆方案，也是最适合知识密集型场景的方案**。它实现了 **GraphRAG**——将非结构化文本转化为结构化的知识图谱，让 Agent 能做跨文档的复杂逻辑推理。

### 核心理念

Cognee 解决的是普通向量搜索搞不定的问题：

```
向量搜索能回答的：
  "PostgreSQL 支持哪些索引类型？"
  → 找与问题最相似的文档段落

图搜索能回答的（Cognee 的能力）：
  "根据去年的三次技术评审会议纪要，导致迁移失败的核心决策链是什么？"
  → 需要跨 3 份文档，追踪 A 决策 → B 结果 → C 调整的因果链
  → 向量搜索做不到，图谱遍历可以
```

**关键特征**：

| 维度 | 说明 |
|------|------|
| **核心能力** | GraphRAG — 文档 → 实体提取 → 知识图谱 → 图谱增强检索 |
| **流水线** | `add()` 添加数据 → `cognify()` 构建图谱 → `search()` 图谱检索 |
| **存储后端** | 图DB（Ladybug/Kuzu）+ 向量 DB（LanceDB/PGVector） |
| **自主管理** | Pipeline 驱动——数据处理是自动的，检索策略由开发者控制 |
| **学习曲线** | 高——需要理解图模型（节点/边/属性）和 GraphRAG 概念 |

- **任何需要"跨文档推理"的场景**：不是找相关段落，而是找因果链
- **不适用**：简单 Agent 应用、客服系统 — Cognee 的 cognify 流水线延迟高（10-60 秒），不适合实时对话

> Cognee 的完整 Quick Start 代码和 GraphRAG 流水线详解见 [下一篇实战篇](./05-frameworks-hands-on.md#cognee知识图谱记忆实战)。

## 四大框架对比与选型

### 横向对比表

| 维度 | Mem0 | Letta | Zep | Cognee |
|------|------|-------|-----|--------|
| **核心理念** | 极简记忆层，事实提取 | Agent 自主管理（OS 范式） | 时序感知 + 自动摘要 | 知识图谱 + GraphRAG |
| **记忆类型** | 语义 + 情景 | 核心记忆 + 存档记忆 | 对话摘要 + 事实 + 时间线 | 实体 + 关系 + 时间线 |
| **存储后端** | 向量DB + 图DB | SQLite + 向量DB | PostgreSQL + 向量DB + 图存储 | 图DB（Ladybug）+ 向量DB |
| **自主管理** | ✗（开发者控制） | ✓（Agent 自己决定存取） | 半自动（摘要/提取自动） | ✗（Pipeline 驱动） |
| **事实提取** | 写入时自动 LLM 提取 | Agent 自主提取 | 服务端自动提取 | cognify() 批量提取 |
| **时间感知** | ✗ | 弱（靠 Agent 自主） | ✓（时间知识图谱） | ✓（时间线 + 事件关联） |
| **跨文档推理** | ✗ | ✗ | 弱（实体关联） | ✓（图遍历因果链） |
| **多用户隔离** | user_id 隔离 | Agent 级隔离 | session_id + user_id | 租户隔离 |
| **Token 节省** | 90%+ (事实浓缩) | 中等（自主记忆换页） | 70%+ (自动摘要) | 中等 |
| **延迟** | p95 < 100ms | 200-500ms | 100-300ms | 200-500ms (cognify 10-60s) |
| **学习曲线** | 低 | 高 | 中 | 高 |
| **集成复杂度** | 极低（5行代码） | 中（API 模式） | 中（需部署或 Cloud） | 高（需理解图模型） |
| **最适场景** | 通用 Agent、快速上线 | 长期自主 Agent | 企业客服、状态演化 | 知识密集、跨文档推理 |

### 选型决策树

```
你的场景是什么？
│
├── 快速上线、原型验证、通用场景 → Mem0
│   理由：5行代码，API最简单，延迟最低。
│   选 Mem0 时确认：Agent 不需要自主决定记什么
│
├── Agent 需长期自主运行（数周~数月） → Letta
│   理由：Agent 自己管理记忆生命周期的能力是其他框架不具备的。
│   选 Letta 时确认：团队能接受它的学习曲线和架构复杂度
│
├── 企业级对话系统 / 客服 / SaaS → Zep
│   理由：原生时间感知 + 自动摘要 + 多用户隔离 + 大厂级稳定性。
│   选 Zep 时确认：需要部署服务器或使用 Cloud 服务，不是本地几行代码能跑
│
└── 知识密集型 / 跨文档推理 → Cognee
    理由：GraphRAG 的因果链追踪是向量搜索做不到的。
    选 Cognee 时确认：不需要实时响应，可以接受 cognify 的批处理延迟
```

<p align="center">
  <img src="../../assets/09-memory-management/framework-comparison.svg" alt="四大记忆框架对比矩阵" width="90%"/>
  <br/>
  <em>图：Mem0/Letta/Zep/Cognee 核心维度对比与选型路径</em>
</p>

### 什么时候不用框架？

| 场景 | 推荐 |
|------|------|
| 原型验证、学习阶段 | 手写实现（前 3 篇的方案） |
| 简单偏好记录（< 50 条记忆） | 手写 KV 存储 |
| 需要深度定制记忆逻辑 | 手写核心 + 框架做存储层 |
| 生产环境、多用户、大量记忆 | 用框架 |

## 总结

- **三种长期记忆各有用处**：语义记忆存事实（向量检索）、情景记忆存事件（时间+语义检索）、程序记忆存规则（直接加载）。不要把所有记忆塞进同一个向量库。
- **记忆巩固是"好用"的关键**：自动提取（LLM 从对话中识别值得记的信息）、去重合并（新旧记忆冲突时智能处理）、主动遗忘（淘汰低价值记忆）。
- **Mem0 是通用首选**：极简 API，事实提取 + 自动去重，适合 80% 的 Agent 场景。缺点是自主性弱——存取时机完全由开发者控制。
- **Letta 是自主王者**：Agent 自己决定什么该记、什么该忘，仿 OS 的内存管理范式。适合长期自主 Agent，但学习曲线高。
- **Zep 是时序专家**：时间知识图谱 + 自动摘要 + 企业级稳定性。适合客服和对话系统，能正确追踪状态演进。
- **Cognee 是推理利器**：GraphRAG 实现跨文档因果链追踪。适合法律、金融、医疗等知识密集型场景。代价是延迟高。
- **四种方案可组合使用**：Mem0 + Zep（事实 + 时序）、Letta + Cognee（自主 + 推理），原型用 Mem0 规模化后切 Zep。

> 这篇文章覆盖了记忆管理的基础理论和四种框架的设计理念。下一篇文章 [记忆框架实战](./05-frameworks-hands-on.md) 将逐一给出四个框架的可运行代码——从 pip install 到生产配置，一步不落。

## 参考链接

- [Mem0 官方文档](https://docs.mem0.ai/) — 通用记忆层，API 最简洁
- [Letta 官方文档](https://docs.letta.com/) — Agent 自主记忆，OS 范式
- [Letta (MemGPT) 论文](https://arxiv.org/abs/2310.08560) — "LLM as Operating Systems" 开创性工作
- [Zep 文档](https://help.getzep.com/) — 时序感知的记忆框架，企业级稳定性
- [Cognee GitHub](https://github.com/topoteretes/cognee) — 知识图谱驱动的记忆系统
- [2026 AI 智能体内存系统深度对比](https://explore.n1n.ai/zh/blog/2026-nian-ai-zhinengti-neicun-xitong-shendu-duibi-2026-04-23) — Mem0 vs Zep vs Letta vs Cognee
- [Graphlit: AI Agent Memory 框架调研](https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks) — 2026 年最全面的框架对比
