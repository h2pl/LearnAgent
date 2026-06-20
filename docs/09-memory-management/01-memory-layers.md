# Agent 记忆三层模型

> 没有记忆的 Agent 每次对话都从零开始。短期记忆让 Agent 记住"刚才说了什么"，工作记忆让 Agent 知道"现在在做什么"，长期记忆让 Agent 记住"用户是谁、喜欢什么"。

## 目录

- [为什么 Agent 需要记忆](#为什么-agent-需要记忆)
- [三层记忆模型](#三层记忆模型)
- [短期记忆：对话历史](#短期记忆对话历史)
- [工作记忆：当前任务的草稿本](#工作记忆当前任务的草稿本)
- [长期记忆：跨会话的持久化知识](#长期记忆跨会话的持久化知识)
- [三层记忆如何协同工作](#三层记忆如何协同工作)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面的旅程你已经掌握了 Agent 的两大认知能力：**[上下文工程](../07-context-engineering/README.md) 教你管理最稀缺的资源——窗口空间**；**[RAG](../08-rag-pipeline/README.md) 教你按需检索外部知识**。但还有一个关键问题没有解决：Agent 自己的经历怎么记住？用户昨天告诉你"我是 Java 开发者"，今天又问同样的问题——Agent 应该记住，而不是每次都从零开始。这篇文章解决核心问题：**Agent 怎么在不同时间尺度上记住信息，让每次交互都比上一次更聪明**。

## 为什么 Agent 需要记忆

LLM 本身没有记忆——它的参数在训练完成后就固定了，不会因为你和它聊了 100 轮就记住你的偏好。所有"记忆"都是你通过**将信息注入上下文**来实现的。

没有记忆的 Agent 面临三个问题：

1. **对话断裂**：用户说"把它改成异步的"，Agent 不知道"它"指的是什么——因为上一轮对话的结果不在上下文中
2. **重复劳动**：用户每次都要重新告诉 Agent"我用 TypeScript""部署在 AWS"——这些信息没有持久化
3. **无法学习**：Agent 犯过的错误、用户纠正过的行为，下次还会重犯——因为没有经验积累

**记忆的本质**：将信息从"上一次的上下文"搬到"这一次的上下文"中。怎么搬、搬什么、搬到哪里——这就是记忆系统要解决的问题。

## 三层记忆模型

借鉴认知科学对人类记忆的分层，Agent 的记忆也分为三层，每层的时间尺度和用途完全不同：

| 层次 | 时间尺度 | 内容 | 存储方式 | 类比 |
|------|---------|------|---------|------|
| **短期记忆** | 当前对话轮次 | 最近几轮的对话历史 | LLM 上下文窗口 | 你正在读的这一页 |
| **工作记忆** | 当前任务周期 | 任务目标、中间步骤、工具调用结果 | 内存中的状态变量 | 你桌上的便签 |
| **长期记忆** | 跨会话持久化 | 用户偏好、学到的事实、历史经验 | 向量数据库 / SQL / 文件 | 你的笔记本 |

**关键区分**：短期记忆和工作记忆是"热数据"——它们直接存在于 LLM 的上下文中，模型可以直接"看到"。长期记忆是"冷数据"——它存储在外部系统中，需要经过检索才能进入上下文。

<p align="center">
  <img src="../../assets/09-memory-management/memory-three-layers.svg" alt="Agent 记忆三层模型架构图" width="90%"/>
  <br/>
  <em>图：三层记忆的时间尺度、存储方式与信息流转</em>
</p>

## 短期记忆：对话历史

短期记忆就是 **LLM 上下文窗口中的对话历史**——`messages` 数组里的所有消息。这是最基础、也是最自然的一层记忆。

```python
# 短期记忆：对话历史直接在 messages 中
messages = [
    {"role": "system", "content": "你是一个技术助手"},
    {"role": "user", "content": "我用 TypeScript 开发"},
    {"role": "assistant", "content": "好的，我记住了。"},
    {"role": "user", "content": "帮我写一个 HTTP 客户端"},
    # Agent 知道要用 TypeScript，因为上一轮对话还在上下文中
]
```

**短期记忆的特点**：

- **零成本实现**：不需要额外代码，对话历史天然在上下文中
- **精确但脆弱**：信息一字不差地保留，但一旦超出上下文窗口就被截断
- **随会话消亡**：对话结束，短期记忆全部丢失

**短期记忆的核心挑战是容量**。上下文窗口有上限（GPT-4.1 是 1M tokens，Claude 3.5 是 200K tokens），一旦对话太长，早期的消息就会被截断。这就是前面 [06 — 上下文工程](../07-context-engineering/README.md) 已经解决的问题。

### 短期记忆的截断策略

当对话超过窗口限制时，你需要决定丢弃哪些消息：

```python
def truncate_messages(messages: list, max_tokens: int) -> list:
    """保留系统提示 + 最近 N 轮对话，截断早期历史"""
    system_msg = messages[0]  # 系统提示永远保留
    conversation = messages[1:]
    
    kept = []
    total_tokens = count_tokens(system_msg)
    
    for msg in reversed(conversation):
        msg_tokens = count_tokens(msg)
        if total_tokens + msg_tokens > max_tokens:
            break
        kept.insert(0, msg)
        total_tokens += msg_tokens
    
    return [system_msg] + kept
```

**关键原则**：系统提示永远保留，最新消息优先保留，最早的消息最先丢弃。这和人类记忆的"近因效应"一致——你更容易记住刚才说的话，而不是 10 分钟前的。

## 工作记忆：当前任务的草稿本

工作记忆是 Agent 在执行复杂任务时的**中间状态存储**——当前目标、已完成的步骤、下一步计划、工具调用的返回结果。

短期记忆记录的是"对话"，工作记忆记录的是"任务"。

```python
class WorkingMemory:
    """Agent 的工作记忆：当前任务的草稿本"""
    
    def __init__(self):
        self.goal: str = ""
        self.plan: list[str] = []
        self.current_step: int = 0
        self.step_results: dict = {}
        self.scratchpad: str = ""  # 自由格式的推理笔记
    
    def update(self, step: int, result: str):
        self.step_results[step] = result
        self.current_step = step + 1
    
    def to_context(self) -> str:
        """将工作记忆转化为 LLM 可理解的文本"""
        lines = [f"当前目标：{self.goal}"]
        lines.append("计划步骤：")
        for i, step in enumerate(self.plan):
            status = "✅" if i < self.current_step else "🔄" if i == self.current_step else "⬜"
            lines.append(f"  {status} 步骤{i+1}：{step}")
        
        if self.step_results:
            lines.append("已完成的结果：")
            for step, result in self.step_results.items():
                lines.append(f"  步骤{step}：{result[:200]}")  # 摘要，不全量复制
        
        return "\n".join(lines)
```

**工作记忆的核心价值**：

1. **任务连贯性**：多步任务中，Agent 知道自己在哪一步、前面做了什么
2. **错误恢复**：某一步失败了，工作记忆保留了之前的进度，可以从失败点重试
3. **推理空间**：scratchpad 让 Agent 有地方"打草稿"——记录中间推理结果，避免重复思考

**工作记忆的生命周期**：随任务开始而创建，随任务完成而清除。如果任务完成后的结果有长期价值（如"用户的偏好"），就提取到长期记忆中。

## 长期记忆：跨会话的持久化知识

长期记忆是 Agent 在**会话之间持久化存储的信息**——用户偏好、学到的事实、历史经验。这是让 Agent"越用越聪明"的关键。

```python
# 长期记忆存储的信息类型
long_term_memory = {
    "user_profile": {
        "name": "张三",
        "role": "后端工程师",
        "languages": ["TypeScript", "Python"],
        "preferences": "偏好函数式风格，不喜欢 class"
    },
    "learned_facts": [
        "用户的项目部署在 AWS us-east-1",
        "用户的数据库是 PostgreSQL 16",
        "上次用户纠正了 AsyncIO 的用法"
    ],
    "task_history": [
        "2026-06-15: 帮用户重构了认证模块",
        "2026-06-17: 帮用户修复了 N+1 查询问题"
    ]
}
```

长期记忆的三个子类型：

| 子类型 | 内容 | 写入时机 | 示例 |
|--------|------|---------|------|
| **语义记忆** | 事实和知识 | 用户明确告知或 Agent 推断 | "用户的项目用 TypeScript" |
| **情景记忆** | 具体事件 | 任务完成时归档 | "6月15日帮用户重构了认证模块" |
| **程序记忆** | 行为模式和偏好 | 从用户反馈中提炼 | "用户偏好函数式风格" |

### 长期记忆的读写流程

```python
class LongTermMemory:
    """长期记忆：跨会话的持久化存储"""
    
    def __init__(self, storage_backend):
        self.storage = storage_backend  # 向量DB / SQL / 文件
    
    def store(self, memory: str, metadata: dict = None):
        """存储一条新记忆"""
        embedding = embed(memory)
        self.storage.upsert(
            id=generate_id(memory),
            text=memory,
            embedding=embedding,
            metadata={
                "created_at": now(),
                "access_count": 0,
                **(metadata or {})
            }
        )
    
    def retrieve(self, query: str, top_k: int = 5) -> list:
        """检索与查询最相关的记忆"""
        query_embedding = embed(query)
        results = self.storage.search(
            embedding=query_embedding,
            top_k=top_k,
            filter={"min_relevance": 0.7}
        )
        for r in results:
            self.storage.update(r.id, access_count=r.metadata["access_count"] + 1)
        return results
```

**长期记忆与短期记忆的关键区别**：

- 短期记忆是**全量注入**——最近 N 轮对话全部放进上下文
- 长期记忆是**按需检索**——只取与当前请求最相关的几条记忆注入上下文

这意味着长期记忆可以无限增长，但每次只使用其中一小部分。检索的质量直接决定了长期记忆的有效性——这是下一篇文章 [记忆存储与检索](./02-memory-storage-retrieval.md) 的核心话题。

## 三层记忆如何协同工作

三层记忆不是孤立的，它们在一个完整的 Agent 交互中紧密配合：

<p align="center">
  <img src="../../assets/09-memory-management/memory-vs-context.svg" alt="Context 上下文 vs Memory 记忆对比" width="90%"/>
  <br/>
  <em>图：上下文（热数据/RAM）vs 记忆（冷数据/硬盘）的核心差异</em>
</p>

```
用户："帮我把上次的认证模块改成 OAuth2"

1. 长期记忆检索：
   → 找到"用户的项目用 TypeScript + Express"
   → 找到"6月15日帮用户重构了认证模块，用的是 JWT"
   → 注入上下文

2. 工作记忆初始化：
   → 目标：将 JWT 认证改为 OAuth2
   → 计划：1) 分析当前实现 2) 设计 OAuth2 流程 3) 实现代码修改
   → 注入上下文

3. 短期记忆（对话进行中）：
   → 用户确认 OAuth2 用 Authorization Code 流程
   → Agent 读取了 auth.ts 文件
   → 这些都在当前对话的 messages 中

4. 任务完成时：
   → 工作记忆清除（任务结束）
   → 有价值的信息写入长期记忆："6月18日帮用户将认证从 JWT 改为 OAuth2"
```

**信息流向总结**：

| 时机 | 信息流动 | 触发条件 |
|------|---------|---------|
| 新会话开始 | 长期记忆 → 上下文 | 用户身份识别后检索相关记忆 |
| 对话进行中 | 对话历史 → 短期记忆 | 每轮对话自动累积 |
| 任务开始时 | 用户请求 → 工作记忆 | Agent 识别到多步任务 |
| 任务进行中 | 工具结果 → 工作记忆 | 每个步骤执行完毕 |
| 任务完成时 | 工作记忆 → 长期记忆 | 提取有价值的信息归档 |
| 对话超限时 | 短期记忆 → 丢弃/摘要 | 超出上下文窗口容量 |

**对开发者的实际影响**：

1. **先实现短期记忆**（几乎免费），再实现工作记忆（中等工作量），最后实现长期记忆（需要存储基础设施）
2. **不要一开始就上向量数据库**——很多场景下，短期记忆 + 工作记忆就够用了
3. **长期记忆的检索质量比存储数量更重要**——存了 1000 条记忆但检索不到正确的那条，等于没有

## 总结

- **Agent 的记忆本质是上下文管理**：LLM 没有记忆，所有记忆都是你将信息注入上下文的结果。
- **三层记忆各有分工**：短期记忆管"刚才说了什么"，工作记忆管"现在在做什么"，长期记忆管"用户是谁、学过什么"。
- **信息在三层之间流动**：短期 → 工作 → 长期（写入），长期 → 上下文（检索），形成完整的记忆循环。
- **按需实现，不要过度设计**：短期记忆免费，工作记忆低成本，长期记忆需要存储基础设施。从简单开始，按需升级。
- **检索质量是长期记忆的生命线**：存得多不如取得准。

> 了解了三层记忆模型，下一步要解决的是：**长期记忆存在哪里？向量数据库、SQL、文件各有什么优劣？怎么实现高质量的记忆检索**？请继续阅读 [记忆存储与检索](./02-memory-storage-retrieval.md)。

## 参考链接

- [LangGraph — Memory Guide](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [Letta (MemGPT) — Memory Management for LLM Agents](https://github.com/letta-ai/letta)
- [Anthropic — Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [Mem0 — Memory Layer for AI Applications](https://github.com/mem0ai/mem0)
- [Cognitive Architecture — Wikipedia](https://en.wikipedia.org/wiki/Cognitive_architecture)
