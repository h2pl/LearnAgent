# 文档切分与向量化

> RAG 的基础是"切分"和"向量化"——切分决定检索粒度，向量化决定检索质量。切分太粗会漏掉关键信息，切分太细会产生碎片；向量化模型选错，检索效果直接腰斩。

## 目录

- [文档解析：从原始格式到纯文本](#文档解析从原始格式到纯文本)
- [切分策略：固定长度 vs 语义边界](#切分策略固定长度-vs-语义边界)
- [Embedding 模型选型](#embedding-模型选型)
- [向量数据库选型](#向量数据库选型)
- [代码实现](#代码实现)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [RAG 原理概述](./01-rag-overview.md) 中，你理解了 RAG 的核心思想。这篇文章深入 RAG 的基础——**文档切分与向量化**，解决三个核心问题：怎么切文档、用什么模型向量化、存到哪里。

## 文档解析：从原始格式到纯文本

在切分之前，需要将各种格式的文档转为纯文本：

| 格式 | 解析工具 | 注意事项 |
|------|----------|----------|
| **PDF** | PyMuPDF、pdfplumber、Unstructured | 扫描版 PDF 需要 OCR |
| **Word** | python-docx、mammoth | 保留标题层级 |
| **HTML** | BeautifulSoup、Trafilatura | 去除导航、广告等噪音 |
| **Markdown** | 直接读取 | 保留标题结构 |
| **代码** | 直接读取 | 保留函数/类边界 |

**关键原则**：解析时保留文档结构（标题、段落、列表），后续切分可以利用这些结构。

```python
# PDF 解析示例
import fitz  # PyMuPDF

def parse_pdf(file_path: str) -> list[dict]:
    """解析 PDF，返回页面列表"""
    doc = fitz.open(file_path)
    pages = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages.append({
            "page": page_num + 1,
            "content": text,
            "metadata": {"source": file_path, "page": page_num + 1}
        })
    
    return pages
```

## 切分策略：固定长度 vs 语义边界

切分策略决定文档被分割成多大的片段，直接影响检索效果：

<img src="../../assets/08-rag-pipeline/chunking-strategies.svg" alt="文档切分策略对比：固定长度 vs 语义边界 vs 递归切分" width="95%"/>

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **固定长度** | 实现简单，可预测 | 可能切断语义 | 快速原型 |
| **语义边界** | 保持语义完整 | 实现复杂 | 生产系统 |
| **递归切分** | 平衡粒度和完整性 | 需要调参 | 通用场景 |

### 固定长度切分

按字符数或 Token 数切分，简单但可能切断句子：

```python
# 固定长度切分
def fixed_length_split(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """按固定长度切分，带重叠"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap  # 重叠部分
    
    return chunks
```

**重叠（Overlap）的作用**：让相邻片段有重叠，避免切断上下文。通常设置为 chunk_size 的 10%-20%。

### 语义边界切分

按自然段落、标题、代码块等语义边界切分：

```python
# 语义边界切分
def semantic_split(text: str, max_chunk_size: int = 1000) -> list[str]:
    """按语义边界切分（段落、标题）"""
    import re
    
    # 先按标题切分
    sections = re.split(r'\n(?=#{1,3} )', text)
    
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # 如果 section 太大，继续按段落切分
        if len(section) > max_chunk_size:
            paragraphs = section.split('\n\n')
            for para in paragraphs:
                if len(para) > max_chunk_size:
                    # 仍然太大，用固定长度切分
                    chunks.extend(fixed_length_split(para, max_chunk_size))
                else:
                    chunks.append(para)
        else:
            chunks.append(section)
    
    return chunks
```

### 递归切分

LangChain 推荐的策略——先按大边界切分，如果仍然太大则递归切分：

```python
# 递归切分（LangChain 风格）
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", "。", "！", "？", "，", " "]
)

chunks = splitter.split_text(document)
```

**切分策略选择建议**：

| 场景 | 推荐策略 | 理由 |
|------|----------|------|
| 快速原型 | 固定长度 | 实现简单，效果够用 |
| 文档问答 | 语义边界 | 保持段落完整性 |
| 代码检索 | 语义边界 | 按函数/类切分 |
| 长文档 | 递归切分 | 平衡粒度和完整性 |

## Embedding 模型选型

Embedding 模型将文本转为向量，是 RAG 检索质量的关键：

| 模型 | 维度 | 特点 | 适用场景 |
|------|------|------|----------|
| **OpenAI text-embedding-3-small** | 1536 | 性价比高，效果好 | 通用场景 |
| **OpenAI text-embedding-3-large** | 3072 | 效果最好，价格贵 | 高精度需求 |
| **BGE-large-zh** | 1024 | 中文优化，开源 | 中文场景 |
| **Jina Embeddings v3** | 1024 | 多语言，支持长文本 | 多语言场景 |
| **Cohere Embed v3** | 1024 | 多语言，支持检索优化 | 检索场景 |

**选型原则**：

1. **语言匹配**：中文场景优先选 BGE 或 Jina
2. **成本控制**：OpenAI 模型按 Token 计费，开源模型免费
3. **效果优先**：如果预算充足，用 text-embedding-3-large

```python
# OpenAI Embedding 示例
from openai import OpenAI

client = OpenAI()

def get_embedding(text: str) -> list[float]:
    """获取文本的 Embedding 向量"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
```

## 向量数据库选型

向量数据库存储 Embedding 向量，支持高效的相似度检索：

| 数据库 | 类型 | 特点 | 适用场景 |
|--------|------|------|----------|
| **Chroma** | 嵌入式 | 轻量，易上手 | 原型开发 |
| **Qdrant** | 独立服务 | 高性能，功能丰富 | 生产系统 |
| **Milvus** | 分布式 | 高可用，可扩展 | 大规模场景 |
| **pgvector** | PostgreSQL 扩展 | 与现有数据库集成 | 已有 PG 的团队 |
| **Pinecone** | 托管服务 | 免运维，开箱即用 | 不想自己运维 |

**选型建议**：

| 场景 | 推荐 | 理由 |
|------|------|------|
| 本地开发 | Chroma | 轻量，无需额外服务 |
| 小型生产 | Qdrant | 性能好，易部署 |
| 大型生产 | Milvus | 高可用，可扩展 |
| 已有 PostgreSQL | pgvector | 无需引入新组件 |

```python
# Chroma 示例
import chromadb

# 创建客户端
client = chromadb.Client()

# 创建集合
collection = client.create_collection("documents")

# 添加文档
collection.add(
    documents=["文档1内容", "文档2内容"],
    ids=["doc1", "doc2"],
    metadatas=[{"source": "file1.pdf"}, {"source": "file2.pdf"}]
)

# 检索
results = collection.query(
    query_texts=["查询问题"],
    n_results=3
)
```

<p align="center">
  <img src="../../assets/08-rag-pipeline/embedding-vector-selection.svg" alt="Embedding模型与向量数据库选型：特性对比与场景决策" width="95%"/>
</p>

## 代码实现

完整的索引流程：

```python
# RAG 索引流程
from openai import OpenAI
import chromadb

def build_rag_index(documents: list[dict], collection_name: str = "documents"):
    """构建 RAG 索引"""
    
    # 初始化
    openai_client = OpenAI()
    chroma_client = chromadb.Client()
    collection = chroma_client.create_collection(collection_name)
    
    # 处理每个文档
    for doc in documents:
        # 1. 解析文档（假设已经是纯文本）
        text = doc["content"]
        metadata = doc.get("metadata", {})
        
        # 2. 切分
        chunks = semantic_split(text, max_chunk_size=1000)
        
        # 3. 向量化并存储
        for i, chunk in enumerate(chunks):
            # 获取 Embedding
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            )
            embedding = response.data[0].embedding
            
            # 存入 Chroma
            collection.add(
                documents=[chunk],
                embeddings=[embedding],
                ids=[f"{metadata.get('source', 'unknown')}_{i}"],
                metadatas=[{**metadata, "chunk_index": i}]
            )
    
    return collection
```

## 总结

- **文档解析**：将 PDF/Word/HTML 转为纯文本，保留结构信息
- **切分策略**：固定长度简单，语义边界保持完整，递归切分平衡两者
- **Embedding 模型**：中文优先 BGE/Jina，通用用 OpenAI，高精度用 text-embedding-3-large
- **向量数据库**：本地用 Chroma，生产用 Qdrant/Milvus，已有 PG 用 pgvector

> 下一篇，我们将深入检索与重排序——如何从向量数据库中找到最相关的文档，以及如何用 Reranker 进一步提升检索质量。

## 参考链接

- [LangChain — Text Splitters](https://python.langchain.com/docs/how_to/recursive_text_splitter/)
- [OpenAI — Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [Chroma — Getting Started](https://docs.trychroma.com/docs/overview/getting-started)
- [Qdrant — Quick Start](https://qdrant.tech/documentation/quickstart/)
