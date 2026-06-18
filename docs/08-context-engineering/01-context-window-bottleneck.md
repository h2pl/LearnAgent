# 上下文窗口：Agent 的瓶颈资源

> 上下文窗口是 Agent 最昂贵的资源——128K 到 1M tokens 看起来很大，但系统提示、工具定义、对话历史、记忆注入、RAG 检索结果一叠加，很容易就撑满了。理解这个瓶颈，是上下文工程的起点。

## 目录

- [上下文窗口的本质](#上下文窗口的本质)
- [上下文里有什么](#上下文里有什么)
- ["迷失在中间"现象](#迷失在中间现象)
- [信息优先级设计](#信息优先级设计)
- [上下文窗口不是越大越好](#上下文窗口不是越大越好)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [跨会话记忆实践](../06-memory-management/03-cross-session-memory.md) 中，你构建了一个带记忆的 Agent。但你可能已经注意到一个问题：系统提示、长期记忆、对话历史、RAG 检索结果——这些信息都要塞进同一个上下文窗口里。**窗口有限，信息无限**。这篇文章解决核心问题：**上下文窗口的瓶颈在哪里、信息应该怎么排优先级、为什么窗口不是越大越好**。

## 上下文窗口的本质

上下文窗口是 LLM 在一次调用中能"看到"的全部文本——以 Token 计量的输入上限。超过这个上限的信息，模型完全看不到。

2026 年主流模型的上下文窗口：

| 模型 | 上下文窗口 | 实际可用（推荐） | 说明 |
|------|-----------|----------------|------|
| GPT-4.1 | 1M tokens | ~200K | 超过 200K 后注意力分散，准确率下降 |
| Claude 3.5 Sonnet | 200K tokens | ~100K | 200K 内表现稳定 |
| Gemini 2.0 Flash | 1M tokens | ~200K | 长文本处理能力强 |
| GPT-4.1-mini | 1M tokens | ~200K | 小模型同样受注意力限制 |

**关键认知**：上下文窗口是**硬上限**（超过就报错），但**有效容量**远小于硬上限——模型在长上下文中的注意力会分散，准确率随长度增加而下降。

## 上下文里有什么

一次典型的 Agent 调用，上下文中包含以下信息：

```
┌─────────────────────────────────────────────┐
│ System Prompt（系统提示）         ~500 tokens  │  固定开销
│ Tool Definitions（工具定义）     ~1500 tokens  │  固定开销
├─────────────────────────────────────────────┤
│ Memory Injection（记忆注入）      ~300 tokens  │  按需注入
│ RAG Results（检索结果）          ~2000 tokens  │  按需注入
├─────────────────────────────────────────────┤
│ Conversation History（对话历史） ~5000+ tokens │  持续增长 ↑
│ Tool Results（工具调用结果）     ~1000+ tokens │  持续增长 ↑
├─────────────────────────────────────────────┤
│ User Message（当前用户输入）       ~100 tokens  │  每次变化
│ [模型生成回复的位置]                            │
└─────────────────────────────────────────────┘
```

**固定开销**（系统提示 + 工具定义）大约 2000 tokens，每次调用都要付。

**可变开销**（记忆、RAG、对话历史）随会话进行不断膨胀。一个 20 轮的对话，对话历史可能从 500 tokens 膨胀到 20000+ tokens。

**这就是瓶颈**：当可变开销不断膨胀，留给模型"思考空间"的余量越来越小，模型的回复质量开始下降。

## "迷失在中间"现象

2023 年斯坦福的研究发现了一个关键现象：**LLM 对上下文中间位置的信息关注度显著低于开头和结尾**。这被称为"Lost in the Middle"（迷失在中间）。

```
上下文位置：
开头（系统提示）   ████████████  ← 高关注度
中间（早期对话）   ████          ← 低关注度 ⚠️
结尾（最近对话）   ████████████  ← 高关注度
```

**对 Agent 的影响**：

- 如果你的长期记忆注入在系统提示之后、对话历史之前，它处于"中间位置"，模型可能不太关注
- 早期对话中用户说的重要信息（"我的数据库密码是 xxx"），在 20 轮对话后可能被"遗忘"
- 工具调用的结果如果夹在大量对话历史中间，模型可能忽略关键细节

**这不是模型的 Bug，是 Transformer 自注意力机制的固有特性**。自注意力对所有 Token 计算关联度，但位置越远的 Token，经过多层计算后注意力权重越分散。

### 应对策略

1. **重要信息放在开头或结尾**：系统提示（开头）和最近几轮对话（结尾）是模型最关注的位置
2. **中间位置只放"参考信息"**：RAG 结果、记忆注入等不需要精确记忆的内容
3. **关键信息重复出现**：如果用户早期说了一个重要偏好，可以在最近的系统消息中再次提醒

## 信息优先级设计

当上下文空间有限时，你需要决定哪些信息优先占位。优先级从高到低：

| 优先级 | 信息类型 | 原因 | Token 预算 |
|--------|---------|------|-----------|
| 1 | 系统提示 | 定义 Agent 行为的基础 | 500-1000 |
| 2 | 当前用户输入 | 模型必须看到的最新请求 | 不限制 |
| 3 | 最近 3-5 轮对话 | 保持对话连贯性 | 2000-5000 |
| 4 | 工具定义 | 模型需要知道能调用什么 | 1000-3000 |
| 5 | 工具调用结果（最近） | 模型基于结果生成回复 | 1000-2000 |
| 6 | 长期记忆注入 | 个性化响应 | 300-500 |
| 7 | RAG 检索结果 | 基于知识回答问题 | 1000-2000 |
| 8 | 早期对话历史 | 历史上下文 | 剩余空间 |

**实际分配代码**：

```python
class ContextBuilder:
    """上下文装配器：按优先级分配 Token 预算"""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.budget = {
            "system": 1000,
            "recent_messages": 4000,
            "tools": 2000,
            "tool_results": 1500,
            "memory": 500,
            "rag": 1500,
            "history": 0,  # 用剩余空间
        }
    
    def build_context(self, system_prompt, messages, tools, 
                      memories, rag_results) -> list:
        """按优先级装配上下文"""
        context = []
        used_tokens = 0
        
        # 1. 系统提示（最高优先级）
        context.append({"role": "system", "content": system_prompt})
        used_tokens += count_tokens(system_prompt)
        
        # 2. 工具定义
        if tools:
            used_tokens += count_tool_tokens(tools)
        
        # 3. 记忆注入（作为系统消息）
        if memories:
            memory_text = self._format_memories(memories, self.budget["memory"])
            context.append({"role": "system", "content": memory_text})
            used_tokens += count_tokens(memory_text)
        
        # 4. RAG 结果
        if rag_results:
            rag_text = self._format_rag(rag_results, self.budget["rag"])
            context.append({"role": "system", "content": rag_text})
            used_tokens += count_tokens(rag_text)
        
        # 5. 对话历史（用剩余空间）
        remaining = self.max_tokens - used_tokens
        history = self._fit_messages(messages, remaining)
        context.extend(history)
        
        return context
    
    def _fit_messages(self, messages: list, token_limit: int) -> list:
        """从最近的消息开始，尽可能多放"""
        fitted = []
        used = 0
        for msg in reversed(messages):
            tokens = count_tokens(msg["content"])
            if used + tokens > token_limit:
                break
            fitted.insert(0, msg)
            used += tokens
        return fitted
```

## 上下文窗口不是越大越好

很多开发者认为"上下文窗口越大越好"——1M tokens 比 200K 强 5 倍。这是错误的。

**大窗口的三个问题**：

1. **注意力稀释**：窗口越大，模型对单个 Token 的关注度越低。200K 窗口中放 100K 内容，准确率可能不如 20K 窗口中放 15K 内容
2. **成本线性增长**：输入 Token 按量计费。1M tokens 的输入成本是 100K 的 10 倍
3. **延迟增加**：更多的 Token 意味着更长的推理时间，用户等待更久

**实测数据**：

| 上下文使用量 | 工具选择准确率 | 成本（GPT-4.1） | 延迟 |
|------------|-------------|----------------|------|
| 5K tokens | ~95% | $0.015 | ~1s |
| 20K tokens | ~90% | $0.06 | ~2s |
| 100K tokens | ~78% | $0.30 | ~5s |
| 500K tokens | ~65% | $1.50 | ~15s |

**最佳实践**：把上下文使用量控制在模型窗口的 **20-30%** 以内。GPT-4.1 的 1M 窗口，实际用到 200K-300K 就够了。超过这个量，不如压缩上下文而不是塞更多。

## 总结

- **上下文窗口是 Agent 最昂贵的瓶颈资源**：硬上限（超过报错）和有效容量（注意力分散导致准确率下降）是两回事。
- **上下文在持续膨胀**：系统提示 + 工具定义是固定开销，对话历史和工具结果会不断增长。20 轮对话后可能从 5K 膨胀到 20K+ tokens。
- **"迷失在中间"是固有特性**：模型对开头和结尾的信息关注度最高，中间位置的信息容易被忽略。重要信息放在开头或结尾。
- **信息优先级决定装配顺序**：系统提示 > 当前输入 > 最近对话 > 工具定义 > 工具结果 > 记忆 > RAG > 早期历史。
- **窗口不是越大越好**：控制在模型窗口的 20-30% 以内，超过就压缩而不是硬塞。

> 了解了上下文窗口的瓶颈，下一步要解决的是：**上下文塞不下了怎么办？摘要压缩、Token 裁剪、滑动窗口——怎么在不丢失关键信息的前提下缩减上下文**？请继续阅读 [上下文压缩策略](./02-context-compression.md)。

## 参考链接

- [Lost in the Middle — Stanford Research (2023)](https://arxiv.org/abs/2307.03172)
- [OpenAI — Context Window Guide](https://platform.openai.com/docs/guides/context-window)
- [Anthropic — Long Context Performance](https://docs.anthropic.com/en/docs/build-with-claude/long-context)
- [Google — Gemini Context Window](https://ai.google.dev/gemini-api/docs/long-context)
