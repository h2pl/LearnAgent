# 检索与重排序策略

> RAG 的检索质量决定答案质量——向量检索找"语义相似"，BM25 找"关键词匹配"，混合检索结合两者优势，Reranker 进一步精排。单一方法不够，组合才能达到最佳效果。

## 目录

- [向量检索：语义相似度](#向量检索语义相似度)
- [BM25：关键词匹配](#bm25关键词匹配)
- [混合检索：语义 + 关键词](#混合检索语义--关键词)
- [Reranker：精排重排序](#reranker精排重排序)
- [检索策略的选择](#检索策略的选择)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [文档切分与向量化](./02-chunking-embedding.md) 中，你完成了 RAG 的索引阶段。这篇文章深入检索阶段——**如何从海量文档中找到最相关的片段**，以及如何用 Reranker 进一步提升质量。

## 向量检索：语义相似度

向量检索是 RAG 的默认检索方式——将问题和文档都转为向量，用余弦相似度找到最相似的文档：

```python
# 向量检索示例
def vector_search(query: str, collection, n_results: int = 5):
    """向量检索"""
    # 1. 将问题转为向量
    embedding = get_embedding(query)
    
    # 2. 在向量数据库中检索
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )
    
    return results
```

**向量检索的优点**：

- **语义理解**：能理解同义词、近义词（如"手机"和"移动电话"）
- **跨语言**：多语言模型能检索不同语言的文档
- **无需关键词**：用户可以用自然语言提问

**向量检索的局限**：

- **精确匹配弱**：无法精确匹配专有名词、产品型号
- **依赖 Embedding 质量**：模型选错，检索效果直接腰斩
- **高维向量计算慢**：大规模文档需要 ANN 索引加速

## BM25：关键词匹配

BM25 是经典的关键词检索算法，基于 TF-IDF 改进，擅长精确匹配：

```python
# BM25 检索示例
from rank_bm25 import BM25Okapi
import jieba

def bm25_search(query: str, documents: list[str], n_results: int = 5):
    """BM25 检索"""
    # 1. 分词
    tokenized_query = list(jieba.cut(query))
    tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
    
    # 2. 构建 BM25 索引
    bm25 = BM25Okapi(tokenized_docs)
    
    # 3. 检索
    scores = bm25.get_scores(tokenized_query)
    
    # 4. 返回 top-n
    top_indices = scores.argsort()[-n_results:][::-1]
    return [(documents[i], scores[i]) for i in top_indices]
```

**BM25 的优点**：

- **精确匹配**：能精确匹配专有名词、产品型号
- **无需训练**：不需要 Embedding 模型
- **解释性强**：匹配原因明确（关键词命中）

**BM25 的局限**：

- **无语义理解**：无法理解同义词（"手机"和"移动电话"不匹配）
- **依赖分词**：分词质量直接影响效果
- **无法处理长文档**：需要预先切分

## 混合检索：语义 + 关键词

混合检索结合向量检索和 BM25 的优势，用 RRF（Reciprocal Rank Fusion）融合两路结果：

<img src="../../assets/08-rag-pipeline/hybrid-retrieval-flow.svg" alt="混合检索流程：向量检索 + BM25 + RRF 融合 + Reranker" width="95%"/>

```python
# 混合检索示例
def hybrid_search(query: str, collection, documents: list[str], 
                  n_results: int = 5, alpha: float = 0.5):
    """混合检索：向量 + BM25"""
    
    # 1. 向量检索
    vector_results = vector_search(query, collection, n_results * 2)
    
    # 2. BM25 检索
    bm25_results = bm25_search(query, documents, n_results * 2)
    
    # 3. RRF 融合
    fused_scores = {}
    
    # 向量检索结果
    for rank, doc_id in enumerate(vector_results["ids"][0]):
        if doc_id not in fused_scores:
            fused_scores[doc_id] = 0
        fused_scores[doc_id] += 1 / (60 + rank)  # RRF 公式
    
    # BM25 结果
    for rank, (doc, score) in enumerate(bm25_results):
        doc_id = documents.index(doc)
        if doc_id not in fused_scores:
            fused_scores[doc_id] = 0
        fused_scores[doc_id] += 1 / (60 + rank)
    
    # 4. 排序并返回 top-n
    sorted_ids = sorted(fused_scores.keys(), 
                       key=lambda x: fused_scores[x], 
                       reverse=True)[:n_results]
    
    return sorted_ids
```

**混合检索的优势**：

| 场景 | 向量检索 | BM25 | 混合检索 |
|------|----------|------|----------|
| 语义查询（"如何优化性能"） | ✅ 强 | ❌ 弱 | ✅ 强 |
| 精确匹配（"error code 500"） | ❌ 弱 | ✅ 强 | ✅ 强 |
| 同义词（"手机" vs "移动电话"） | ✅ 强 | ❌ 弱 | ✅ 强 |

## Reranker：精排重排序

Reranker 是检索后的"精排"阶段——对初步检索结果进行二次排序，提高相关性：

```python
# Reranker 示例
from sentence_transformers import CrossEncoder

def rerank(query: str, documents: list[str], top_k: int = 3):
    """用 Reranker 重排序"""
    
    # 1. 加载 Reranker 模型
    reranker = CrossEncoder("BAAI/bge-reranker-base")
    
    # 2. 构建查询-文档对
    pairs = [(query, doc) for doc in documents]
    
    # 3. 计算相关性分数
    scores = reranker.predict(pairs)
    
    # 4. 排序并返回 top-k
    ranked_indices = scores.argsort()[::-1][:top_k]
    return [(documents[i], scores[i]) for i in ranked_indices]
```

**Reranker 的价值**：

| 阶段 | 模型 | 作用 | 计算量 |
|------|------|------|--------|
| **初筛** | Embedding 模型 | 向量相似度 | 低（向量检索） |
| **精排** | Cross-Encoder | 语义相关性 | 高（逐对计算） |

**Reranker 的工作原理**：

<img src="../../assets/08-rag-pipeline/bi-vs-cross-encoder.svg" alt="Bi-Encoder vs Cross-Encoder 工作原理对比" width="95%"/>

- **Embedding 模型**（Bi-Encoder）：分别编码查询和文档，用余弦相似度匹配
- **Cross-Encoder**：将查询和文档拼接，一起输入模型，输出相关性分数
- Cross-Encoder 效果更好，但计算量大，只能用于精排

**常用 Reranker 模型**：

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| **BAAI/bge-reranker-base** | 中文优化，开源 | 中文场景 |
| **BAAI/bge-reranker-large** | 效果更好，更慢 | 高精度需求 |
| **Cohere Rerank** | 托管服务，API 调用 | 不想自己运维 |

## 检索策略的选择

| 场景 | 推荐策略 | 理由 |
|------|----------|------|
| **快速原型** | 向量检索 | 实现简单，效果够用 |
| **精确匹配重要** | 混合检索 | 兼顾语义和关键词 |
| **高精度需求** | 向量检索 + Reranker | 两阶段检索，效果最佳 |
| **大规模文档** | 混合检索 + Reranker | 平衡效果和性能 |

**完整检索流程**：

```python
# 完整检索流程
def retrieve(query: str, collection, documents: list[str], 
             n_results: int = 5, use_reranker: bool = True):
    """完整检索流程"""
    
    # 1. 混合检索（初筛）
    candidate_ids = hybrid_search(query, collection, documents, n_results * 3)
    candidate_docs = [documents[i] for i in candidate_ids]
    
    # 2. Reranker（精排）
    if use_reranker and len(candidate_docs) > n_results:
        ranked_docs = rerank(query, candidate_docs, top_k=n_results)
        return [doc for doc, score in ranked_docs]
    
    return candidate_docs
```

## 总结

- **向量检索**：语义相似度，擅长理解自然语言，但精确匹配弱
- **BM25**：关键词匹配，擅长精确匹配，但无语义理解
- **混合检索**：结合两者优势，用 RRF 融合两路结果
- **Reranker**：精排阶段，用 Cross-Encoder 进一步提升相关性
- **推荐策略**：初筛用混合检索，精排用 Reranker

> 下一篇，我们将深入 RAG 评测与优化——如何量化 RAG 系统的效果，以及常见的优化技巧。

## 参考链接

- [LangChain — Retrieval](https://python.langchain.com/docs/concepts/retrieval/)
- [Haystack — Retrieval](https://docs.haystack.deepset.ai/docs/retrieval)
- [BGE — Reranker](https://github.com/FlagOpen/FlagEmbedding/tree/master/FlagEmbedding/BAAE)
- [RRF — Reciprocal Rank Fusion](https://plumber.gofynd.io/Understanding-Reciprocal-Rank-Fusion/)
