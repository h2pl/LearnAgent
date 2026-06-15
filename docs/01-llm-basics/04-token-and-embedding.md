# Token 与 Embedding

> LLM 处理文本的最小单位不是"字"也不是"词"，而是 Token。本文从分词原理讲到 Embedding 向量化，帮你建立对 LLM 成本、上下文窗口和语义理解的完整认知。

## 目录

- [什么是 Token](#什么是-token)
- [Tokenization 过程](#tokenization-过程)
- [Token 与成本、性能的关系](#token-与成本性能的关系)
- [Embedding：从文本到向量](#embedding从文本到向量)
- [总结](#总结)
- [参考链接](#参考链接)

在 [LLM 发展简史](./03-llm-evolution.md) 之后，这一篇从最微观的视角切入——LLM 处理文字时，看到的不是"字"或"词"，而是 **Token（词元）**。

理解 Token 和 **Embedding（嵌入）** 是理解 LLM 所有后续概念的基础：
- **Token** 决定了 LLM 的输入输出粒度、成本、上下文窗口长度
- **Embedding** 是把文本变成数学向量的技术，是 RAG、语义搜索、记忆等一切高级功能的前提

## 什么是 Token

### 不是字，不是词，是 subword

当你把一句话输入给 LLM 时，它并不是按"字"或"词"来理解的。它会把输入切分成一个个 **Token**——这是一个介于"字"和"词"之间的单位。

举个例子，英文句子：

```
"The quick brown fox jumps over the lazy dog"
```

用 GPT 的分词器（BPE 算法）切分后，会变成：

```
["The", " quick", " brown", " fox", " jumps", " over", " the", " lazy", " dog"]
```

而中文的切分方式完全不同：

```
"中国的首都是北京"
→  ["中国的", "首都", "是", "北京"]     （GPT-4o 的分词结果）
```

### 中英文 Token 的关键差异

这对你作为开发者来说很重要：

| 维度 | 英文 | 中文 |
|------|------|------|
| 1 个 Token ≈ | 0.75 个词（约 4 个字符） | 0.5-1 个汉字 |
| 100 个 Token ≈ | 75 个英文词 | 约 50-80 个汉字 |
| 原因 | 英文有空格天然分隔，常见词/子词各占一个 Token | 中文字符密集，每个字的信息量大，但分词没有天然分隔符 |

**实际影响**：同样一段 1000 字的文章，中文版消耗的 Token 比英文版少得多。反过来，如果你的 API 按 Token 计费，问中文问题的成本实际上比英文低。

### 常用 Token 估算

作为参考：

| 内容类型 | Token 数量（约） |
|---------|----------------|
| 1 个英文字 | 0.25 token |
| 1 个中文字 | 1-2 tokens |
| 1 页英文书（500 词） | ~380 tokens |
| 1 页中文书（500 字） | ~700 tokens |
| ChatGPT 一次回复（平均） | 500-1000 tokens |
| 一篇公众号长文（3000 字） | ~4000 tokens |

> 注意：不同的模型使用不同的分词器，同样的文字在不同模型下 Token 数量可能有差异。精确估算请使用各模型提供的 Tokenizer 工具。

## Tokenization 过程

### BPE（Byte Pair Encoding）算法直觉

Tokenization 就是"把文本切成 Token"的过程。目前主流 LLM 使用的核心算法是 **BPE（Byte Pair Encoding）**。

它的思想很直观：

1. **初始状态**：把每个字符当做一个 Token（包括空格和标点）
2. **合并**：统计相邻 Token 对出现的频率，把最高频的组合合并成一个新 Token
3. **重复**：重复第 2 步，直到达到预设的 Token 数量上限

用中文来类比一下这个过程：

```
第 1 轮：把 "中"+"国" 合并成 "中国"（因为"中国"频繁出现）
第 2 轮：把"中国"+"的" 合并成"中国的"（也是高频组合）
第 3 轮：把"北京"合并成一个 Token
...
最终：高频词和常见组合会变成单独的 Token，低频词可能保持切分状态
```

所以"我喜欢吃北京烤鸭"可能会被切分成：`["我喜欢", "吃", "北京", "烤鸭"]`

- **常见词**（北京、中国、我）→ 单独 Token
- **罕见组合**（特定人名、专业术语）→ 可能被拆成更小的单位

### 为什么用 BPE？

BPE 的优点是它不需要"理解"语言，纯靠统计就能工作。它天然处理了：
- **未知词（OOV）问题**：即使遇到没见过的词，也能拆成子词或字符级 Token
- **词汇量控制**：通过控制合并轮数来决定最终的 Token 表大小
- **跨语言统一**：无论中文、英文还是代码，都用同一套算法处理

<p align="center">
  <img src="../../assets/01-llm-basics/bpe-tokenization.png" alt="BPE 分词学习过程" width="90%"/>
  <br/>
  <em>BPE 第一阶段：从语料中统计字符对频率，按频率排序后逐步合并为 Token</em>
</p>

### 实操：tiktoken

OpenAI 的 [tiktoken](https://github.com/openai/tiktoken) 是一个快速 Tokenizer 库。你可以用它对任何文本做精确的 Token 计数：

```python
import tiktoken

# GPT-4 / GPT-4o 使用的编码
enc = tiktoken.get_encoding("cl100k_base")
tokens = enc.encode("中国的首都是北京")
print(f"Token 数量: {len(tokens)}")
print(f"Token IDs: {tokens}")
print(f"解码还原: {enc.decode(tokens)}")
```

输出类似：
```
Token 数量: 4
Token IDs: [15575, 7370, 8370, 17775]
解码还原: 中国的首都是北京
```

其他模型也提供了各自的 Tokenizer：
- **Claude**：[Anthropic Console](https://console.anthropic.com/) 内置 Tokenizer
- **Gemini**：Google AI Studio 内置 Token 计数器
- **Llama**：使用 sentencepiece 库

> 作为 Agent 开发者，不需要深入分词算法的细节，但需要知道：**Token 计数不是按字数算的**。这意味着估算成本、设计 Prompt 长度、计算上下文窗口时，不能凭"字数"来估算，要用 Tokenizer 精确计算。

## Token 与成本、性能的关系

### API 按 Token 计费

几乎所有 LLM API 都按 Token 计费：

| 模型（2026 年 6 月） | 输入价格（每百万 Token） | 输出价格（每百万 Token） |
|---------------------|----------------------|----------------------|
| Claude Haiku 4.5 | $0.80 | $4.00 |
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| GPT-5.5 | $10.00 | $40.00 |
| DeepSeek V4 Pro | $0.50 | $2.00 |

输出 Token 通常比输入 Token 贵 3-5 倍，因为生成比处理更消耗计算资源。

### Context Window 是 Token 数量限制

每个模型都有最大上下文窗口，这个窗口也是按 Token 算的：

- Claude Sonnet 4.6：200K tokens
- GPT-5.5：128K tokens
- Gemini 3.1 Pro：2M tokens
- Grok 4.3：2M tokens

**重要推论**：在 Agent 应用中，每次对话的输入（系统 Prompt + 历史消息 + 用户输入）加起来不能超过这个限制。一旦超出，要么截断，要么报错。这直接影响了 Agent 的记忆策略——你需要决定哪些历史信息值得保留在上下文中。

### System Prompt 也占 Token

你可能觉得把整套指令放在 System Prompt 里"反正不花钱"——实际上它完全占用 Token 额度。做个简单计算：

- 你的 System Prompt：500 tokens
- 当前对话历史：3000 tokens
- 用户输入：200 tokens
- 可用给模型输出的部分：200K - 500 - 3000 - 200 = 196.3K tokens（看起来还很多）

但在 Agent 场景下，每次工具调用的结果都会回到上下文里，Token 消耗很快。一个复杂的 Agent 任务可能一次执行就消耗 50K+ tokens。所以 **Token 管理是 Agent 工程的基础问题**。

## Embedding：从文本到向量

### 文本 → 高维向量

如果说 Token 是 LLM 的"输入格式"，那 Embedding 就是 LLM 的"理解方式"。

**Embedding 的本质**：把一段文本映射到一个高维空间中的向量（一组浮点数）。

比如"北京"这个词，embedding 之后可能是：
```
[0.0234, -0.1567, 0.0891, ..., 0.4567]  # 通常 768 到 3072 维
```

这个向量本身没有意义，但把大量文本都映射到同一个向量空间后，就出现了有意义的规律：

```
vec("国王") - vec("男人") + vec("女人") ≈ vec("女王")
vec("北京") - vec("中国") + vec("法国") ≈ vec("巴黎")
```

这就是为什么 Embedding 被称为"语言的空间化"——语言中的语义关系被转换成了向量空间中的几何关系。

<p align="center">
  <img src="../../assets/01-llm-basics/word-embedding.png" alt="词嵌入向量映射" width="90%"/>
  <br/>
  <em>Embedding 将词汇映射为固定长度的数值向量，语义相近的词在向量空间中距离更近</em>
</p>

### 语义相似度

有了向量之后，"语义相似度"变成了一个数学问题：

```
相似度(A, B) = cos(vec(A), vec(B))
                = A·B / (|A| * |B|)
```

这个值越接近 1，表示两段文本语义越相似。

### Embedding 模型

常用的 Embedding 模型（不是对话模型，是专门的嵌入模型）：

| 模型 | 向量维度 | 特点 |
|------|---------|------|
| text-embedding-3-small | 1536 | OpenAI，性价比高 |
| text-embedding-3-large | 3072 | OpenAI，精度更高 |
| bge-m3 | 1024 | BAAI，开源，多语言 |

### Embedding 在 Agent 中的核心应用：RAG

Embedding 最常见的用途是 **RAG（检索增强生成）**，它的工作流是：

```
用户提问："Claude 的上下文窗口有多大？"
     ↓
1. 把问题转成 Embedding 向量
     ↓
2. 在知识库的向量数据库中搜索最相似的 Top-K 段落
     ↓
3. 把找到的段落 + 原始问题一起发给 LLM
     ↓
LLM 基于提供的资料生成回答
```

<p align="center">
  <img src="../../assets/01-llm-basics/rag-workflow.png" alt="RAG 检索增强生成工作流程" width="90%"/>
  <br/>
  <em>RAG 三阶段：离线索引（文档→向量数据库）→ 在线检索（问题编码为向量，搜索最相关的 Top-K 文档块）→ 生成（检索结果 + 原始问题一起输入 LLM）</em>
</p>

Embedding 还有更多应用场景：

| 场景 | 原理 | 示例 |
|------|------|------|
| 语义搜索 | 把搜索词转为向量，与文档库比对 | 比关键词搜索准确得多 |
| 聚类分析 | 把相似的文本聚集到一起 | 自动分类用户反馈 |
| 去重检测 | 计算向量距离判断相似度 | 发现重复提交的工单 |
| 推荐系统 | 用户向量 × 内容向量 | 推荐相关文章 |
| **记忆系统** | Agent 把历史对话向量化存储 | 检索相关记忆注入上下文 |

### 你的第一步实践

作为一个 Java 后端开发者，你可以在本地用 Python 快速体验 Embedding：

```python
from openai import OpenAI
import numpy as np

client = OpenAI()

texts = [
    "中国的首都是北京",
    "北京是中国的政治文化中心",
    "巴黎是法国的首都",
    "我今天吃了火锅"
]

# 获取 Embedding
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=texts
)

embeddings = [r.embedding for r in response.data]

# 计算相似度矩阵
for i in range(len(texts)):
    for j in range(i+1, len(texts)):
        sim = np.dot(embeddings[i], embeddings[j])  # 余弦相似度简化版
        print(f"相似度({texts[i][:12]}..., {texts[j][:12]}...) = {sim:.3f}")
```

预期结果：
```
相似度(中国的首都是北京..., 北京是中国的政治文化中心...) = 0.92
相似度(中国的首都是北京..., 巴黎是法国的首都...) = 0.68
相似度(中国的首都是北京..., 我今天吃了火锅...) = 0.12
```

和北京相关的句子相似度很高，和"巴黎是首都"有一定关联（都是"首都"话题），和"吃火锅"基本不相关——这就是 Embedding 的直觉理解。

## 总结

这一篇覆盖了两个基础概念：

- **Token**：LLM 处理文本的最小单位，影响成本、上下文窗口和性能。中文 1 字 ≈ 1-2 tokens，英文 ≈ 0.75 个词 / token。
- **Embedding**：把文本转化为数学向量，让机器理解语义关系，是 RAG、记忆、搜索等应用的基础。

理解这两者，你就知道：**写 Agent 时，Token 是你的预算，Embedding 是你的武器。** 前者决定了你能不能跑得起来，后者决定了你跑得好不好。

> 接下来请阅读 [Transformer 架构直觉](./05-transformer-intuition.md)，深入 LLM 最核心的架构原理，理解"自注意力"到底是怎么回事。

## 参考链接

- [OpenAI Tokenizer](https://platform.openai.com/tokenizer) — 在线体验 Token 切分
- [Andrej Karpathy — Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE) — 深入 BPE 实现
- [BPE 原始论文 (Neural Machine Translation of Rare Words with Subword Units, 2016)](https://arxiv.org/abs/1508.07909)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [text-embedding-3-small 发布说明](https://openai.com/index/new-embedding-models-and-api-updates/)
- [bge-m3 embedding model (BAAI)](https://github.com/FlagOpen/FlagEmbedding)
- [tiktoken GitHub](https://github.com/openai/tiktoken)
