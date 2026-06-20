# 记忆框架实战：四大方案 Quick Start

> 上一篇讲了四种框架的设计理念和选型决策。这篇是动手篇——每个框架配完整可运行的 Quick Start 代码，从安装到检索，一步不落。

## 目录

- [Mem0：5 行代码给 Agent 加记忆](#mem05-行代码给-agent-加记忆)
- [Letta：创建自主记忆的 Agent](#letta创建自主记忆的-agent)
- [Zep：企业级时序记忆](#zep企业级时序记忆)
- [Cognee：知识图谱记忆实战](#cognee知识图谱记忆实战)
- [四大框架组合使用](#四大框架组合使用)
- [生产环境记忆治理](#生产环境记忆治理)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇文章 [记忆框架与巩固策略](./04-memory-frameworks.md) 介绍了三种长期记忆类型、记忆巩固机制，以及 Mem0、Letta、Zep、Cognee 四种框架的设计理念和选型决策树。这篇文章是动手篇——每个框架都有完整的可运行代码示例，从安装到生产配置。

> **阅读建议**：如果你还没看上一篇，建议先了解四种框架的核心理念和选型依据，再回来看这篇代码实战。

## Mem0：5 行代码给 Agent 加记忆

### Quick Start

```python
# pip install mem0ai
from mem0 import Memory

# ========== 1. 初始化 ==========
# 默认使用内存存储（开发测试用），生产环境换 Qdrant/Pinecone
memory = Memory()

# ========== 2. 写入记忆（自动事实提取 + 去重） ==========
memory.add(
    "我叫张三，7年Java后端开发经验，现在转型做AI Agent开发。"
    "项目部署在AWS us-east-1，数据库用PostgreSQL。",
    user_id="zhangsan"
)
# Mem0 内部自动调用 LLM 提取事实：
# → "用户叫张三"
# → "7年Java后端经验，转型AI Agent"
# → "项目部署在AWS us-east-1"
# → "数据库用PostgreSQL"

# ========== 3. 语义检索 ==========
results = memory.search("张三用什么数据库？", user_id="zhangsan")
for r in results:
    print(f"{r['memory']} (相似度: {r['score']:.2f})")
# → 数据库用PostgreSQL (相似度: 0.94)

# ========== 4. 自动更新（去重合并） ==========
memory.add("我把数据库从 PostgreSQL 迁移到 MySQL 8.0 了",
           user_id="zhangsan")
# Mem0 自动检测到与旧记忆冲突，自动执行 UPDATE：
# 旧："数据库用PostgreSQL" → 新："数据库用MySQL 8.0"

# ========== 5. 获取所有记忆 ==========
all_mems = memory.get_all(user_id="zhangsan")
print(f"共 {len(all_mems)} 条记忆")
```

<p align="center">
  <img src="../../assets/09-memory-management/mem0-quickstart-flow.svg" alt="Mem0 Quick Start 流程图" width="90%"/>
  <br/>
  <em>图：Mem0 五步集成 — 安装/初始化/写入/检索/自动更新</em>
</p>

### 生产配置

```python
from mem0 import Memory

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "agent_memories"
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4.1-mini",  # 用轻量模型提取记忆，省钱
            "temperature": 0
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small"  # 记忆用 small 模型够用
        }
    },
    "history_db_path": "./memory_history.db"
}

memory = Memory.from_config(config)
```

### 适合谁？

- **原型验证**：5 行代码加上记忆，快速跑通概念
- **个人助手**：用户偏好少、记忆量不大（< 10K 条）
- **快速集成**：已经用了 LangChain 等框架，想低成本加记忆层
- **不适合**：需要 Agent 自主决定"什么该记、什么该忘"的场景

## Letta：创建自主记忆的 Agent

### Quick Start

```python
# pip install letta-client
from letta_client import Letta
import os

client = Letta(api_key=os.getenv("LETTA_API_KEY"))

# ========== 1. 创建带记忆的 Agent ==========
agent = client.agents.create(
    model="openai/gpt-5.2",
    # memory_blocks 定义 Agent 的初始记忆结构
    memory_blocks=[
        {
            "label": "human",
            "value": (
                "Name: 张三。背景: 7年Java后端开发，现转型AI Agent开发。"
                "技术栈: Python, PostgreSQL, Docker, AWS。"
                "项目: 正在开发Agent运维工具链（agent-configs、WriteFlow）。"
            )
        },
        {
            "label": "persona",
            "value": (
                "我是张三的编程助手。我熟悉Java和Python生态，"
                "偏好简洁直接的代码风格，讨厌过度设计。"
                "在提建议前会先确认用户的实际需求。"
            )
        }
    ],
    # Agent 可用的工具
    tools=["web_search", "fetch_webpage"]
)
print(f"Agent 创建成功，ID: {agent.id}")

# ========== 2. 发送消息（Agent 自主管理记忆） ==========
response = client.agents.messages.create(
    agent_id=agent.id,
    input="帮我查一下LangGraph最新版本，我想升级项目的依赖"
)

# 此时 Agent 内部发生了：
# 1. 检索 core memory 中关于"项目依赖"的信息
# 2. 调用 web_search 搜索 LangGraph 版本
# 3. 结合搜索结果和用户记忆，给出针对性的建议
# 4. 自主决定是否将"LangGraph版本信息"写入 archival memory

for msg in response.messages:
    print(f"[{msg.role}]: {msg.content}")

# ========== 3. 查看 Agent 的记忆状态 ==========
agent_state = client.agents.retrieve(agent.id)
for block in agent_state.memory.blocks:
    print(f"--- {block.label} ---")
    print(block.value[:200])
```

### Letta 记忆的自主管理过程

```
会话开始
  │
  ▼
[核心记忆] ── 始终在上下文窗口 ── 用户信息 + Agent设定 + 当前任务
  │
  ▼ Agent 执行过程中
[存档记忆] ← agent 自主写入 ─ 有长期价值的事实、决策、学到的知识
  │
  ▼ 上下文窗口快满时
[记忆换页] ─ Agent 自主决策：把不常用的核心记忆归档，把相关的存档记忆换入
  │
  ▼ 会话结束
[记忆持久化] ── 所有记忆块持久化到 SQLite + 向量 DB
```

### 适合谁？

- **长期自主运行的 Agent**：需要跨越数周甚至数月持续学习
- **复杂任务场景**：Agent 需要自己判断什么信息值得长期记住
- **需要记忆自进化的系统**：不希望每次都由开发者手动搞记忆提取和更新
- **不适合**：简单的偏好记忆（< 50 条）

## Zep：企业级时序记忆

### Quick Start

```python
# pip install zep-cloud
from zep_cloud import Zep
from zep_cloud.types import Message

client = Zep(api_key="YOUR_ZEP_API_KEY")

# ========== 1. 创建用户 ==========
client.user.add(
    user_id="zhangsan",
    email="zhangsan@example.com",
    metadata={"role": "developer", "team": "platform"}
)

# ========== 2. 创建会话并添加对话 ==========
session = client.memory.add_session(
    session_id="session_001",
    user_id="zhangsan",
)

messages = [
    Message(role="user", content="我叫张三，7年Java后端经验，现在想学AI Agent开发。"),
    Message(role="assistant", content="你好张三！你有丰富的后端经验，转型会很快。建议从LangChain开始。"),
    Message(role="user", content="好的，我们项目用的Python和PostgreSQL，部署在AWS上。"),
    Message(role="assistant", content="这些技术栈都和Agent开发很配！"),
]

client.memory.add(
    session_id="session_001",
    messages=messages,
)
# Zep 在后台自动：
# 1. 生成对话摘要
# 2. 提取实体（张三、Java、Python、PostgreSQL、AWS）
# 3. 建立实体间的关系
# 4. 生成时间线

# ========== 3. 添加新事实（时间演进） ==========
# 一周后，用户更新了状态
session2 = client.memory.add_session(
    session_id="session_002",
    user_id="zhangsan",
)
client.memory.add(
    session_id="session_002",
    messages=[
        Message(role="user",
                content="我已经学完LangChain，现在用LangGraph做复杂Agent编排。"),
    ],
)
# Zep 自动更新时间知识图谱：
# 技能演进：Java(2022-2026) → Python(2025-) → LangChain(2026-01) → LangGraph(2026-06)

# ========== 4. 跨会话检索（带时间感知） ==========
results = client.memory.search(
    session_id="session_002",
    query="张三的技术栈演进",
    min_score=0.7,
    limit=5,
)

for r in results:
    print(f"[{r.fact.created_at.date()}] {r.fact.content}")
# → [2026-01-15] 7年Java后端经验
# → [2026-01-15] 开始学习AI Agent开发
# → [2026-06-18] 已学完LangChain，现在用LangGraph做复杂Agent编排

# ========== 5. 搜索知识图谱中的实体 ==========
graph_results = client.graph.search(
    user_id="zhangsan",
    query="张三使用的技术",
)
```

### Zep 的自动摘要（Token 节省 75%）

Zep 的一个重要能力是**自动上下文摘要**。当对话历史过长时，它会自动压缩旧消息：

```
原始对话（20 轮，约 8000 tokens）
  → Zep 自动摘要（约 2000 tokens）
  → Token 节省 ~75%

摘要保留的内容：
  ✓ 关键事实和决策
  ✓ 实体和关系
  ✓ 时间线信息
  ✗ 闲聊和寒暄
  ✗ 重复信息
```

### 适合谁？

- **客服 / 对话式 AI**：用户跨多天、跨多会话交流，需要追踪长期状态
- **企业级 SaaS**：多用户隔离、高并发、时序分析
- **状态演进追踪**：需要知道"用户从什么时候开始变了"的场景
- **不适合**：原型验证、学习阶段

## Cognee：知识图谱记忆实战

### Quick Start

```python
# pip install cognee
import cognee
import asyncio

async def main():
    # ========== 1. 初始化（内置内存模式，生产换 PostgreSQL） ==========
    await cognee.prune.prune_data()
    await cognee.prune.prune_system()

    # ========== 2. 添加数据 ==========
    # 支持文本、文件、URL
    await cognee.add("""
    项目迁移复盘会议纪要（2026-03-15）

    参与人：张三（后端负责人）、李四（架构师）、王五（DBA）

    背景：PostgreSQL 15 → MySQL 8.0 迁移

    决策过程：
    1. 张三提议用 pt-online-schema-change 做在线迁移
    2. 李四指出 pt-osc 不支持跨数据库类型，建议改 pg_dump → mysql 转换
    3. 王五测试后发现 pg_dump 方案有约 5% 的数据精度丢失
    4. 最终决定：停止迁移，等待 MySQL 9.0 原生 JSONB 支持后再评估

    未解决问题：旧数据的 JSONB 查询语法不兼容
    """)

    await cognee.add("""
    第二次评估会议纪要（2026-06-10）

    参与人：张三、李四

    MySQL 9.0 已发布，原生 JSONB 支持完善。
    李四做了兼容性测试，通过率从之前的 85% 提升到 97%。
    决定：下月初启动第二轮迁移试点。
    """)

    # ========== 3. 构建知识图谱（GraphRAG 核心） ==========
    # cognify() 自动执行：
    # - 分块（chunking）
    # - 实体提取（Person: 张三、李四、王五, Project: 数据库迁移...）
    # - 关系抽取（张三 → proposed → pt-osc方案, 李四 → rejected → pt-osc方案）
    # - 图谱构建（节点和边）
    print("正在构建知识图谱...")
    await cognee.cognify()
    print("知识图谱构建完成！")

    # ========== 4. 图谱增强搜索 ==========
    results = await cognee.search(
        "数据库迁移失败的原因是什么？最终决定是什么？"
    )
    for r in results:
        print(f"[相关性: {r.score}] {r.content[:200]}...")

    # → 返回结果会追踪因果链：
    #   pt-osc 不支持跨库 → pg_dump 精度丢失 → 暂停迁移 → MySQL 9.0 → 重新启动

asyncio.run(main())
```

### Cognee 的 GraphRAG 流水线

```
文档/文本
    │
    ▼ add()
[分块 Chunking] ─ 将长文档拆分为可管理的片段
    │
    ▼ cognify()
[实体提取] ─ LLM 提取：人名、项目名、技术名词、决策、日期
    │
    ▼
[关系抽取] ─ LLM 判断实体间的关系：proposed、rejected、depends_on
    │
    ▼
[图谱构建] ─ 节点（实体）+ 边（关系）+ 属性 → 存储到图数据库
    │
    ▼ search()
[图谱检索] ─ 向量相似度 + 图遍历（1-hop → 2-hop 扩展）
    │
    ▼
[增强回答] ─ 将图谱上下文注入 LLM，生成带因果关系的回答
```

### 适合谁？

- **法律 / 合规分析**：跨数百份合同追踪条款变更和责任链
- **金融投研**：跨多份财报和研报，提取因果关系和趋势
- **医疗知识管理**：症状→诊断→治疗的因果路径
- **任何需要"跨文档推理"的场景**
- **不适合**：简单 Agent 应用、客服系统（cognify 延迟高，10-60 秒）

## 四大框架组合使用

四种框架不是互斥的——很多生产系统会组合使用：

```
Mem0（轻量事实层） + Zep（时序对话层）
  → 用户偏好用 Mem0，对话历史和状态演进用 Zep

Letta（Agent 自主层） + Cognee（知识检索层）
  → Agent 自主管理操作记忆，需要深度知识推理时调 Cognee

Mem0（快速启动） → Zep（规模化后迁移）
  → 典型演进路径：原型用 Mem0，成规模后切 Zep
```

## 生产环境记忆治理

### 记忆隔离

多用户场景下，记忆必须严格隔离：

```python
# ✓ 正确：用户级隔离
memory.add(user_preference, user_id="alice", agent_id="assistant")
memory.search(query, user_id="alice", agent_id="assistant")

# ✗ 错误：没有隔离，A 的记忆泄露给 B
memory.add(user_preference)  # 没有 user_id！
```

### 记忆质量监控

```python
class MemoryMonitor:
    """记忆系统健康度监控"""

    def __init__(self, memory_system):
        self.memory = memory_system

    def health_report(self):
        all_mems = self.memory.get_all()
        total = len(all_mems)

        return {
            "total_memories": total,
            "by_type": {
                "semantic": sum(1 for m in all_mems if m.type == "semantic"),
                "episodic": sum(1 for m in all_mems if m.type == "episodic"),
                "procedural": sum(1 for m in all_mems if m.type == "procedural"),
            },
            "avg_access_count": sum(m.access_count for m in all_mems) / max(total, 1),
            "stale_memories": sum(1 for m in all_mems if m.access_count == 0),
            "high_importance": sum(1 for m in all_mems if m.importance >= 4),
        }

    def detect_conflicts(self):
        """检测记忆冲突（同一主题有矛盾信息）"""
        # 按主题聚类，检查同簇内是否有矛盾
        clusters = self._cluster_by_topic(self.memory.get_all())
        conflicts = []
        for cluster in clusters:
            if len(cluster) > 1:
                # 用 LLM 检测簇内是否有矛盾
                if llm.detect_contradiction([m.content for m in cluster]):
                    conflicts.append(cluster)
        return conflicts
```

<p align="center">
  <img src="../../assets/09-memory-management/production-config.svg" alt="生产环境记忆配置决策树" width="90%"/>
  <br/>
  <em>图：从规模评估到框架/存储/检索策略的完整决策路径</em>
</p>

### 容量与成本预估

| 记忆规模 | 向量DB 存储 | Embedding 成本/月 | 检索延迟 | 建议 |
|---------|-----------|------------------|---------|------|
| < 1K 条 | < 10MB | < $0.1 | < 10ms | 手写实现或 Mem0 默认配置 |
| 1K-10K 条 | 10-100MB | $0.1-1 | 10-30ms | Mem0 + Qdrant |
| 10K-100K 条 | 100MB-1GB | $1-10 | 30-100ms | Mem0/Letta + 专用向量集群 |
| > 100K 条 | > 1GB | > $10 | 100-500ms | Cognee + 图索引加速 |

## 总结

- **Mem0 最快上手**：5 行代码，自动事实提取和去重。生产环境配 Qdrant + 轻量 LLM（如 gpt-4.1-mini）。
- **Letta 最自主**：Agent 自己管理 core memory 和 archival memory，OS 范式的记忆换页。适合需要长期自运行的场景。
- **Zep 最懂时间**：时间知识图谱追踪状态演进，自动摘要省 75% Token。企业管理后台或客服系统首选。
- **Cognee 最善推理**：GraphRAG 追踪因果链，cognify 批处理构建图谱。法律、金融、医疗等知识密集型场景首选。
- **生产环境三条铁律**：隔离（user_id 不能省）、监控（定期健康报告）、容量控制（< 500 条主动淘汰）。

> 记忆管理的旅程到这里就完结了。你学会了原理（三层模型）、手写实现（存储与检索）、框架选型（理论篇）和实战落地（本篇）。接下来进入 [10 — 框架与编排](../10-framework/README.md)，用 LangGraph 等框架把 Agent 的全部能力串联成生产级系统。

## 参考链接

- [Mem0 官方文档](https://docs.mem0.ai/) — 通用记忆层，5 行代码集成
- [Letta 官方文档](https://docs.letta.com/) — Agent 自主记忆
- [Letta Python SDK (PyPI)](https://pypi.org/project/letta-client/) — pip install letta-client
- [Zep 文档](https://help.getzep.com/) — 时序记忆，企业级
- [Zep Python SDK](https://pypi.org/project/zep-cloud/) — pip install zep-cloud
- [Cognee GitHub](https://github.com/topoteretes/cognee) — GraphRAG 记忆系统
- [2026 AI 智能体内存系统深度对比](https://explore.n1n.ai/zh/blog/2026-nian-ai-zhinengti-neicun-xitong-shendu-duibi-2026-04-23) — Mem0 vs Zep vs Letta vs Cognee
