# 多模态 RAG：图文混合检索

主线第 8 章讲的是纯文本 RAG——基于文本嵌入检索文档片段。多模态 RAG 增加了一个维度：图像、表格、图表这些视觉元素也需要被索引和检索。一个包含图片的文档，光检索文字会丢失大量信息。

## 为什么需要多模态 RAG

传统 RAG 的局限：

- PDF 中的图片被忽略，丢失视觉信息
- 图表中的数据无法被检索到
- 用户的问题可能需要同时引用文字和图片来回答

多模态 RAG 的核心能力：让检索系统能同时理解和处理文本与视觉信息。

## 架构方案

### 方案一：图文分离检索

```
文档 → 文本提取 → 文本嵌入(Text Embedding)
     → 图片提取 → 图片嵌入(CLIP/SigLIP)
     
检索时：文字查询 → 同时检索文本库和图片库 → 合并排序
```

优点：灵活，各模态独立优化
缺点：跨模态语义对齐依赖嵌入质量

### 方案二：统一多模态嵌入

```
文档 → 图文对 → 统一嵌入(多模态模型)
检索时：文字/图片查询 → 统一检索
```

优点：跨模态语义一致
缺点：嵌入模型选择少、费用高

### 方案三：MLLM Re-ranking

```
第一阶段：粗检索（文本+CLIP 图片）
第二阶段：用多模态 LLM 对结果重排序
```

优点：准确率高，结合语义和视觉
缺点：延迟较高，成本增加

## 视觉索引构建

### CLIP 索引流程

1. 文档切分：识别文档中的图片区域
2. 图片提取：从 PDF 中提取图片，保持原始分辨率
3. 嵌入生成：用 CLIP/SigLIP 生成图片嵌入向量
4. 元数据记录：图片的上下文（所在段落、页面位置、图注文字）
5. 向量存储：存入向量数据库（Milvus/Pinecone/Chroma）

### 图文关联策略

图片脱离上下文就没有意义。关键是要保持图文关联：
- 按页面关联：同一页的文本和图片关联
- 按段落关联：引用该图片的文字段落为上下文
- 按图注关联：用图注作为图片的"标题"

## 检索与融合

### 多路召回

```
用户查询
  ├─→ 文本检索（Dense + Sparse） → Top-K 文本
  └─→ 图片检索（CLIP embedding） → Top-K 图片

合并 → 按相关性重排序 → 输出结果
```

### 融合排序策略

| 策略 | 方法 | 适用场景 |
|------|------|----------|
| 加权融合 | 文本分 * α + 图片分 * (1-α) | 图文分明确 |
| RRF | 倒数排序融合 | 不依赖分数校准 |
| MLLM Re-rank | 多模态模型统一打分 | 追求最高准确率 |

## 框架支持

| 框架 | 多模态 RAG 能力 | 特点 |
|------|----------------|------|
| LlamaIndex | 原生支持多模态检索 | 丰富的多模态 reader |
| LangChain | 需自行组合多路检索 | 灵活但配置复杂 |
| Haystack | Pipeline 多模态支持 | 企业级特性 |
| Canopy（Pinecone） | 端到端多模态 RAG | 托管方案 |

### LlamaIndex 示例思路

```python
# 多模态文档索引
from llama_index.core import VectorStoreIndex
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from llama_index.vector_stores.qdrant import QdrantVectorStore

# 图文分离索引
text_index = VectorStoreIndex.from_documents(text_docs)
image_index = VectorStoreIndex.from_documents(image_docs)

# 多路检索 + MLLM 融合
retriever = MultiModalRetriever(
    text_retriever=text_index.as_retriever(),
    image_retriever=image_index.as_retriever(),
    fusion_strategy="rrf"
)
```

## 实践建议

1. **先确认是否需要**：如果文档中图片很少，纯文本 RAG 就够了
2. **图片质量很重要**：低分辨率或模糊的图片，嵌入质量会显著下降
3. **上下文是关键**：检索出的图片要带上下文信息，否则无法使用
4. **评估指标**：除了检索召回率，还要关注图片的相关性和可用性
5. **成本控制**：图片嵌入的存储和计算成本远高于文本

## 参考

- [LlamaIndex Multi-Modal RAG](https://docs.llamaindex.ai/en/stable/examples/multi_modal/)
- [CLIP for Multi-Modal Retrieval](https://github.com/openai/CLIP)
- [ColPali: Efficient Document Retrieval with Vision Language Models](https://arxiv.org/abs/2407.01449)
- [Qdrant Multi-Modal Search](https://qdrant.tech/documentation/tutorials/multimodal-search/)
