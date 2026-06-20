# 跨会话记忆实践

> 理论讲完了，这篇全是实战。从零构建一个带记忆的 Agent：记忆初始化、会话中读写、会话结束时提取归档、新会话开始时检索注入——完整代码，可直接运行。

## 目录

- [整体架构](#整体架构)
- [记忆初始化：新会话的第一件事](#记忆初始化新会话的第一件事)
- [会话中的记忆读写](#会话中的记忆读写)
- [会话结束：记忆提取与归档](#会话结束记忆提取与归档)
- [新会话开始：记忆检索与注入](#新会话开始记忆检索与注入)
- [生产环境的注意事项](#生产环境的注意事项)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前两篇文章讲了 [Agent 记忆三层模型](./01-memory-layers.md) 和 [记忆存储与检索](./02-memory-storage-retrieval.md) 的原理。这篇文章把它们全部落地：**用 Python 实现一个完整的记忆系统，覆盖会话全生命周期**。读完本文，你将拥有一个"越用越聪明"的 Agent。

## 整体架构

一个带记忆的 Agent 会话流程分为四个阶段：

```
1. 会话开始 → 识别用户 → 检索长期记忆 → 注入上下文
2. 对话进行中 → 短期记忆自动累积 → 工作记忆跟踪任务状态
3. 会话结束 → 从对话中提取有价值信息 → 归档到长期记忆
4. 下次会话 → 回到第 1 步，但 Agent 已经"记住"了你
```

<p align="center">
  <img src="../../assets/09-memory-management/cross-session-lifecycle.svg" alt="跨会话记忆生命周期" width="90%"/>
  <br/>
  <em>图：四个阶段形成记忆闭环 — 初始化/对话/结束/持久化</em>
</p>

完整代码结构：

```python
import chromadb
import json
from openai import OpenAI
from datetime import datetime

client = OpenAI()

class MemoryAgent:
    """带三层记忆的 Agent"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.vector_db = chromadb.PersistentClient(path="./memory_db")
        self.memories = self.vector_db.get_or_create_collection("memories")
        
        # 短期记忆：对话历史
        self.messages = []
        # 工作记忆：任务状态
        self.working_memory = {}
    
    def start_session(self):
        """阶段 1：新会话开始，加载长期记忆"""
        pass  # 下文实现
    
    def chat(self, user_input: str) -> str:
        """阶段 2：对话进行中"""
        pass  # 下文实现
    
    def end_session(self):
        """阶段 3：会话结束，提取并归档"""
        pass  # 下文实现
```

## 记忆初始化：新会话的第一件事

新会话开始时，Agent 应该先加载用户的长期记忆，注入到系统提示中：

```python
def start_session(self):
    """新会话开始：识别用户 → 检索长期记忆 → 构建系统提示"""
    
    # 1. 检索与用户相关的长期记忆
    user_memories = self.memories.query(
        query_texts=[f"用户 {self.user_id} 的偏好和项目信息"],
        n_results=10,
        where={"user_id": self.user_id}
    )
    
    # 2. 构建记忆上下文
    memory_context = ""
    if user_memories["documents"][0]:
        memory_context = "以下是你从历史对话中了解到的关于用户的信息：\n"
        for doc in user_memories["documents"][0]:
            memory_context += f"- {doc}\n"
    
    # 3. 构建系统提示（长期记忆注入）
    system_prompt = f"""你是一个智能助手。

{memory_context}

当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

请基于你对用户的了解，提供个性化的回答。如果不确定用户的偏好，正常回答即可。"""
    
    # 4. 初始化短期记忆
    self.messages = [{"role": "system", "content": system_prompt}]
    self.working_memory = {}
    
    return system_prompt
```

**关键设计**：

- 系统提示中明确告诉 Agent "以下是你从历史中了解到的"——这让 Agent 知道自己有记忆，行为更自然
- 检索用 `user_id` 过滤，避免加载其他用户的记忆
- 记忆条目用列表格式，便于 LLM 逐条理解

## 会话中的记忆读写

对话进行中，短期记忆自动累积（每轮对话加入 messages），工作记忆跟踪任务状态：

```python
def chat(self, user_input: str) -> str:
    """对话进行中：短期记忆 + 工作记忆 + 实时记忆检索"""
    
    # 1. 用户输入加入短期记忆
    self.messages.append({"role": "user", "content": user_input})
    
    # 2. 实时检索：如果用户提到了历史话题，动态加载相关记忆
    if self._needs_memory_lookup(user_input):
        relevant = self.memories.query(
            query_texts=[user_input],
            n_results=3,
            where={"user_id": self.user_id}
        )
        if relevant["documents"][0]:
            # 将相关记忆作为 system 消息注入
            memory_note = "相关历史记忆：\n" + "\n".join(
                f"- {doc}" for doc in relevant["documents"][0]
            )
            self.messages.append({"role": "system", "content": memory_note})
    
    # 3. 调用 LLM
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=self.messages
    )
    
    assistant_msg = response.choices[0].message.content
    self.messages.append({"role": "assistant", "content": assistant_msg})
    
    return assistant_msg

def _needs_memory_lookup(self, user_input: str) -> bool:
    """判断是否需要动态检索长期记忆"""
    # 简单策略：包含"上次""以前""之前""我记得"等关键词时触发
    trigger_words = ["上次", "以前", "之前", "我记得", "你说过", "我的项目"]
    return any(word in user_input for word in trigger_words)
```

**实时检索的价值**：不是每次对话都需要长期记忆。只有当用户提到历史相关话题时，才动态加载——节省 Token、减少噪声。

## 会话结束：记忆提取与归档

会话结束时，从对话中提取有价值的信息写入长期记忆：

```python
def end_session(self):
    """会话结束：从对话中提取有价值的信息，归档到长期记忆"""
    
    # 用 LLM 从对话中提取值得记住的信息
    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" 
        for m in self.messages 
        if m['role'] != 'system'
    )
    
    extraction = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{
            "role": "system",
            "content": """从以下对话中提取值得长期记住的信息。
            
提取规则：
- 用户明确告知的个人信息（姓名、角色、偏好）
- 项目的技术细节（技术栈、部署方式）
- 重要的决策或纠正
- 不要提取临时的技术问题或一次性请求

返回 JSON 数组，每项包含：
- content: 记忆内容（一句话概括）
- type: 类型（preference/fact/correction/decision）
- importance: 重要程度（high/medium/low）

如果没有值得提取的信息，返回空数组 []。"""
        }, {
            "role": "user", 
            "content": conversation_text
        }]
    )
    
    memories_to_store = json.loads(extraction.choices[0].message.content)
    
    for mem in memories_to_store:
        self.memories.add(
            ids=[f"mem_{self.user_id}_{datetime.now().timestamp()}"],
            documents=[mem["content"]],
            metadatas=[{
                "user_id": self.user_id,
                "type": mem["type"],
                "importance": mem["importance"],
                "created_at": datetime.now().isoformat()
            }]
        )
    
    return len(memories_to_store)  # 返回提取的记忆条数
```

**提取策略的关键**：

- 用 LLM 判断"什么值得记"，而不是什么都存
- 区分信息类型（偏好/事实/纠正/决策），便于后续按类型检索
- 标注重要程度，让检索时能优先返回高重要度的记忆

<p align="center">
  <img src="../../assets/09-memory-management/memory-update-flow.svg" alt="记忆更新决策流程" width="90%"/>
  <br/>
  <em>图：记忆更新决策 — 新信息经过提取→去重→冲突检测→合并/替换</em>
</p>

## 新会话开始：记忆检索与注入

下次会话开始时，Agent 自动加载之前积累的记忆：

```python
# 完整使用示例

# === 第一次会话 ===
agent = MemoryAgent(user_id="zhangsan")
agent.start_session()

agent.chat("我叫张三，是个后端工程师，主要用 TypeScript")
# → "你好张三！TypeScript 是个很好的选择..."

agent.chat("我的项目部署在 AWS，用的 PostgreSQL")
# → "了解，AWS + PostgreSQL 是很常见的组合..."

agent.end_session()
# → 提取了 3 条记忆：姓名/角色、语言偏好、部署信息

# === 第二次会话（隔天）===
agent2 = MemoryAgent(user_id="zhangsan")
system_prompt = agent2.start_session()
# → 系统提示中自动包含：
#   "- 用户叫张三，是后端工程师"
#   "- 偏好 TypeScript 开发"
#   "- 项目部署在 AWS，使用 PostgreSQL"

response = agent2.chat("帮我写一个数据库连接的工具函数")
# → Agent 自动用 TypeScript + PostgreSQL 来写，不需要用户再次说明！
```

**这就是记忆的价值**：用户不需要每次重复相同的信息，Agent 越用越了解用户。

## 生产环境的注意事项

从 Demo 到生产，还需要考虑以下问题：

### 1. 记忆隔离与安全

```python
# 每个用户的记忆必须严格隔离
# 检索时必须带 user_id 过滤，防止记忆泄露
results = self.memories.query(
    query_texts=[query],
    where={"user_id": self.user_id},  # 必须有！
    n_results=5
)
```

### 2. 记忆容量控制

```python
def get_memory_stats(self) -> dict:
    """监控记忆使用量"""
    all_memories = self.memories.get(where={"user_id": self.user_id})
    return {
        "total_memories": len(all_memories["ids"]),
        "by_type": self._count_by_type(all_memories["metadatas"]),
        "oldest_memory": self._get_oldest(all_memories["metadatas"]),
    }

# 当记忆超过阈值时，清理低重要度的旧记忆
def prune_memories(self, max_count: int = 200):
    """保持记忆数量在合理范围内"""
    stats = self.get_memory_stats()
    if stats["total_memories"] > max_count:
        # 删除低重要度的旧记忆
        low_importance = self.memories.get(
            where={"$and": [
                {"user_id": self.user_id},
                {"importance": "low"}
            ]}
        )
        # 按时间排序，删除最早的
        # ...
```

### 3. 记忆注入的 Token 预算

```python
def inject_memories(self, max_tokens: int = 500):
    """控制注入上下文的记忆总量"""
    memories = self.memories.query(
        query_texts=[self._latest_user_message()],
        n_results=10,
        where={"user_id": self.user_id}
    )
    
    injected = []
    total_tokens = 0
    
    for doc in memories["documents"][0]:
        doc_tokens = len(doc) // 4  # 粗略估算
        if total_tokens + doc_tokens > max_tokens:
            break
        injected.append(doc)
        total_tokens += doc_tokens
    
    return injected
```

### 4. 现有框架的记忆方案

如果你用框架开发，可以直接用框架内置的记忆功能：

| 框架 | 记忆方案 | 适合场景 |
|------|---------|---------|
| **LangGraph** | Checkpoint（状态持久化） | 多轮对话、中断恢复 |
| **Letta (MemGPT)** | 三层记忆内置 | 需要长期记忆的生产 Agent |
| **Mem0** | 记忆层中间件 | 任意框架的记忆增强 |
| **OpenAI Agents SDK** | 无内置记忆，自行实现 | 灵活度最高 |

**建议**：如果你已经在用 LangGraph，先用 Checkpoint 解决短期记忆和工作记忆。需要跨会话长期记忆时，接入 Mem0 或自建向量库。

## 总结

- **完整的记忆 Agent 有四个阶段**：初始化（加载记忆）→ 对话（短期累积 + 实时检索）→ 结束（提取归档）→ 下次初始化（记忆生效）。
- **会话开始时的记忆注入是关键**：系统提示中包含用户的历史偏好，Agent 才能表现出"记住你"的效果。
- **会话结束时的记忆提取决定质量**：用 LLM 判断"什么值得记"，区分类型和重要程度，不是什么都存。
- **生产环境必须关注**：用户记忆隔离（安全）、记忆容量控制（不超过 200 条）、注入 Token 预算（不超过 500 tokens）。
- **框架能加速开发**：LangGraph Checkpoint 解决短期/工作记忆，Mem0 解决长期记忆，不需要全部自己写。

> 你已经手写实现了一个完整的记忆 Agent。但手写方案能覆盖的场景有限——生产环境需要更成熟的框架。下一篇 [记忆框架与选型](./04-memory-frameworks.md) 带你了解 Mem0、Letta、Zep、Cognee 四大主流方案，以及什么时候该用框架、什么时候该自己写。

## 参考链接

- [Mem0 — Memory Layer for AI Applications](https://github.com/mem0ai/mem0)
- [Letta (MemGPT) — Stateful Agent Framework](https://github.com/letta-ai/letta)
- [LangGraph — Memory & Persistence](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [Anthropic — Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [ChromaDB — Getting Started](https://docs.trychroma.com/docs/overview/getting-started)
