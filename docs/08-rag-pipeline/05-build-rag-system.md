# 构建你的第一个 RAG 系统

> 用 Python + LangChain + ChromaDB，从零搭建一个完整的 RAG 系统——加载文档、切分、向量化、检索、生成，端到端跑通。

## 目录

- [准备工作](#准备工作)
- [项目结构](#项目结构)
- [Step 1：安装依赖](#step-1安装依赖)
- [Step 2：加载文档](#step-2加载文档)
- [Step 3：切分文档](#step-3切分文档)
- [Step 4：向量化并存入 ChromaDB](#step-4向量化并存入-chromadb)
- [Step 5：检索相关文档](#step-5检索相关文档)
- [Step 6：生成答案](#step-6生成答案)
- [完整代码](#完整代码)
- [调试与优化](#调试与优化)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前四篇我们讲了 RAG 的原理、切分策略、检索方法和评估指标。这一篇，我们**动手写代码**，从零搭建一个能用的 RAG 系统。

<img src="../../assets/08-rag-pipeline/build-rag-system.svg" alt="实战 RAG 系统架构：LangChain + ChromaDB + OpenAI" width="95%"/>

读完本文，你将拥有一个可以回答"基于你的私有文档"问题的 AI 助手，并且理解每一步在做什么。

## 准备工作

开始之前，你需要准备：

| 准备项 | 说明 |
|--------|------|
| **Python 3.9+** | 推荐 3.11 或更新版本 |
| **OpenAI API Key** | 用于 Embedding 和 LLM 调用。如果不想付费，可以用本地模型替代（后文会提到） |
| **一个 PDF 文档** | 用于测试。可以是公司手册、产品文档、或任何你感兴趣的 PDF |

### API Key 获取

如果你还没有 OpenAI API Key：

1. 访问 https://platform.openai.com/api-keys
2. 注册/登录账号
3. 创建一个 API Key
4. 设置环境变量：

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-你的密钥"

# Linux/Mac
export OPENAI_API_KEY="sk-你的密钥"
```

## 项目结构

最终的项目结构如下：

```
my-rag/
├── data/
│   └── your_document.pdf    # 你的测试文档
├── rag.py                   # 主程序
└── requirements.txt         # 依赖
```

## Step 1：安装依赖

创建 `requirements.txt`：

```txt
langchain>=0.2
langchain-openai>=0.1
langchain-community>=0.2
chromadb>=0.5
pypdf>=4.0
```

安装：

```bash
pip install -r requirements.txt
```

各库的作用：

| 库 | 作用 |
|----|------|
| langchain | RAG 流程编排框架 |
| langchain-openai | OpenAI Embedding 和 Chat 模型的封装 |
| langchain-community | 向量数据库（ChromaDB）和文档加载器（PyPDF）的集成 |
| chromadb | 向量数据库，负责存储和检索向量 |
| pypdf | PDF 文档解析 |

## Step 2：加载文档

将 PDF 文档加载为 LangChain 的 Document 对象：

```python
from langchain_community.document_loaders import PyPDFLoader

# 加载 PDF
loader = PyPDFLoader("data/your_document.pdf")
documents = loader.load()

print(f"加载了 {len(documents)} 页")
print(f"第一页内容预览：{documents[0].page_content[:200]}")
```

每个 Document 对象包含两个字段：

- `page_content`：页面的文本内容
- `metadata`：元数据（如页码、文件名）

```python
# 查看元数据
print(documents[0].metadata)
# {'source': 'data/your_document.pdf', 'page': 0}
```

### 加载多个文件

如果要加载整个文件夹：

```python
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader

loader = DirectoryLoader(
    "data/",
    glob="**/*.pdf",
    loader_cls=PyPDFLoader,
)
documents = loader.load()
print(f"共加载 {len(documents)} 页")
```

### 其他格式

除了 PDF，LangChain 还支持多种文档格式：

| 格式 | 加载器 |
|------|--------|
| PDF | `PyPDFLoader` |
| Word (.docx) | `Docx2txtLoader` |
| HTML | `BSHTMLLoader` |
| Markdown | `UnstructuredMarkdownLoader` |
| 纯文本 | `TextLoader` |

## Step 3：切分文档

文档需要切成小块（chunk），否则向量化和检索的效果会很差。

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,      # 每个片段约 300 字符
    chunk_overlap=50,    # 相邻片段重叠 50 字符
    separators=["\n\n", "\n", "。", "！", "？", "，", " "],  # 中文分隔符
)

chunks = text_splitter.split_documents(documents)
print(f"切分后共 {len(chunks)} 个片段")
print(f"片段示例：{chunks[0].page_content[:100]}")
```

**关键参数说明**：

- `chunk_size`：控制片段大小。太小会丢失上下文，太大会引入噪音。建议从 300 开始调优
- `chunk_overlap`：相邻片段的重叠部分。避免把一句话切断，通常设为 chunk_size 的 10%-20%
- `separators`：按优先级尝试的分隔符列表。中文文档建议加上中文标点

### 切分效果检查

```python
# 打印前 3 个片段，检查切分效果
for i, chunk in enumerate(chunks[:3]):
    print(f"\n--- 片段 {i+1} ---")
    print(chunk.page_content)
```

如果发现切分效果不好（比如一句话被切断），可以增大 `chunk_size` 或调整 `separators`。

## Step 4：向量化并存入 ChromaDB

用 OpenAI 的 Embedding 模型将文本片段转为向量，存入 ChromaDB：

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# 初始化 Embedding 模型
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

# 将文档片段向量化并存入 ChromaDB
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory="./chroma_db",  # 持久化目录
)

print(f"已存入 {vectorstore._collection.count()} 个向量")
```

`persist_directory` 让 ChromaDB 将向量保存到磁盘，下次运行时可以直接加载，不需要重新向量化。

### 加载已有的 ChromaDB

```python
# 下次运行时，直接加载
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embedding_model,
)
```

## Step 5：检索相关文档

基于用户问题，在向量数据库中检索最相关的文档片段：

```python
# 创建检索器
retriever = vectorstore.as_retriever(
    search_type="similarity",  # 相似度检索
    search_kwargs={"k": 4},    # 返回 Top-4
)

# 测试检索
query = "这个文档的主要内容是什么？"
docs = retriever.invoke(query)

print(f"检索到 {len(docs)} 个相关片段：")
for i, doc in enumerate(docs):
    print(f"\n--- 片段 {i+1} (页码: {doc.metadata.get('page', 'N/A')}) ---")
    print(doc.page_content[:200])
```

**检索参数调优**：

- `k`：返回的片段数量。太少可能漏掉信息，太多会引入噪音。通常 3-6 效果最好
- `search_type`：`similarity`（默认）、`mmr`（最大边际相关性，多样性更好）

### 使用 MMR 增加多样性

```python
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 4, "fetch_k": 20},  # 先取 20 个，再选 4 个最多样化的
)
```

## Step 6：生成答案

将检索结果和用户问题组合成 Prompt，交给 LLM 生成答案：

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# 初始化 LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 定义 Prompt 模板
prompt_template = ChatPromptTemplate.from_template("""
你是一个知识问答助手。请基于以下参考资料回答用户的问题。

要求：
1. 只基于参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，明确告知"找不到相关信息"
3. 在回答中标注引用来源（如 [1]、[2]）

---
参考资料：
{context}
---

用户问题：{question}
""")

# 格式化检索结果
def format_docs(docs):
    formatted = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "未知来源")
        page = doc.metadata.get("page", "N/A")
        formatted.append(f"[{i+1}] (来源: {source}, 第{page}页)\n{doc.page_content}")
    return "\n\n".join(formatted)

# 组装 RAG Chain（使用 LCEL 语法）
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

rag_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt_template
    | llm
    | StrOutputParser()
)

# 提问
answer = rag_chain.invoke("这个文档的主要内容是什么？")
print(answer)
```

### 不用 LCEL 的写法

如果你觉得 LCEL 语法不直观，可以用传统写法：

```python
def ask(question):
    # 1. 检索
    docs = retriever.invoke(question)

    # 2. 构造 Prompt
    context = format_docs(docs)
    prompt = prompt_template.format(context=context, question=question)

    # 3. 生成
    answer = llm.invoke(prompt)
    return answer.content

# 测试
print(ask("这个文档的主要内容是什么？"))
```

两种写法效果完全一样，选你觉得清晰的就行。

## 完整代码

将以上步骤整合为一个完整的 `rag.py`：

```python
"""RAG 系统 - 基于 PDF 文档的知识问答"""

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# --- 配置 ---
DATA_PATH = "data/your_document.pdf"
DB_PATH = "./chroma_db"
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
TOP_K = 4


def load_documents(path):
    """加载 PDF 文档"""
    loader = PyPDFLoader(path)
    docs = loader.load()
    print(f"✓ 加载了 {len(docs)} 页")
    return docs


def split_documents(docs):
    """切分文档"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "，", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"✓ 切分为 {len(chunks)} 个片段")
    return chunks


def build_vectorstore(chunks):
    """向量化并存入 ChromaDB"""
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH,
    )
    print(f"✓ 已存入 {vectorstore._collection.count()} 个向量")
    return vectorstore


def create_rag_chain(vectorstore):
    """创建 RAG Chain"""
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K},
    )

    prompt = ChatPromptTemplate.from_template("""
你是一个知识问答助手。请基于以下参考资料回答用户的问题。

要求：
1. 只基于参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，明确告知"找不到相关信息"
3. 在回答中标注引用来源（如 [1]、[2]）

---
参考资料：
{context}
---

用户问题：{question}
""")

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

    def format_docs(docs):
        formatted = []
        for i, doc in enumerate(docs):
            page = doc.metadata.get("page", "N/A")
            formatted.append(f"[{i+1}] (第{page}页)\n{doc.page_content}")
        return "\n\n".join(formatted)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def main():
    # 1. 加载文档
    docs = load_documents(DATA_PATH)

    # 2. 切分文档
    chunks = split_documents(docs)

    # 3. 向量化并存储
    vectorstore = build_vectorstore(chunks)

    # 4. 创建 RAG Chain
    chain = create_rag_chain(vectorstore)

    # 5. 交互式问答
    print("\n" + "=" * 50)
    print("RAG 系统已就绪！输入问题开始对话，输入 q 退出。")
    print("=" * 50)

    while True:
        question = input("\n你：")
        if question.lower() in ("q", "quit", "exit"):
            break
        if not question.strip():
            continue

        answer = chain.invoke(question)
        print(f"\nAI：{answer}")


if __name__ == "__main__":
    main()
```

<p align="center">
  <img src="../../assets/08-rag-pipeline/rag-component-interaction.svg" alt="RAG组件交互图：文档→加载→切分→向量化→存储→检索→Prompt→LLM→答案" width="95%"/>
</p>

## 调试与优化

### 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 答案不相关 | 检索结果不相关 | 增大 `k`；调整 `chunk_size`；尝试 MMR 检索 |
| 答案胡说八道 | 模型没有基于文档回答 | 检查 Prompt 是否明确要求"基于文档"；降低 `temperature` |
| 答案太短/不完整 | 检索到的片段太少或太碎 | 增大 `k`；增大 `chunk_size` |
| 运行太慢 | 向量化或检索耗时 | 首次运行需向量化，后续加载 `chroma_db` 即可加速；考虑换更快的 Embedding 模型 |
| OpenAI 报错 | API Key 问题或网络问题 | 确认 Key 正确；国内需配置代理或使用兼容 API |

### 效果优化技巧

**1. 查询改写**

用户的问题有时表述模糊，可以用 LLM 改写后再检索：

```python
rewriter_prompt = ChatPromptTemplate.from_template("""
请将以下用户问题改写为更适合搜索的形式，保持原意但表述更清晰。

用户问题：{question}
改写后的搜索查询：
""")

rewriter = rewriter_prompt | llm | StrOutputParser()

# 使用改写后的查询检索
def retrieve_with_rewrite(question):
    rewritten = rewriter.invoke(question)
    print(f"原始问题：{question}")
    print(f"改写后：{rewritten}")
    return retriever.invoke(rewritten)
```

**2. 流式输出**

对于长答案，可以使用流式输出让用户实时看到生成过程：

```python
for chunk in rag_chain.stream("这个文档的主要内容是什么？"):
    print(chunk, end="", flush=True)
print()  # 换行
```

**3. 返回来源**

用户通常想知道答案来自文档的哪个位置：

```python
def ask_with_sources(question):
    docs = retriever.invoke(question)
    context = format_docs(docs)
    prompt = prompt_template.format(context=context, question=question)
    answer = llm.invoke(prompt)

    print(f"答案：{answer.content}")
    print(f"\n参考来源：")
    for i, doc in enumerate(docs):
        print(f"  [{i+1}] 第 {doc.metadata.get('page', 'N/A')} 页")
```

**4. 使用免费/本地模型替代 OpenAI**

如果不想付费，可以使用本地模型：

```python
# 方案 1：使用 Ollama（需安装 Ollama）
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama

embedding_model = OllamaEmbeddings(model="nomic-embed-text")
llm = Ollama(model="qwen2.5:7b")

# 方案 2：使用 Hugging Face 本地模型
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
```

## 总结

这一篇我们从零搭建了一个完整的 RAG 系统，走过了六个步骤：

1. **加载文档**：用 PyPDFLoader 解析 PDF
2. **切分文档**：用 RecursiveCharacterTextSplitter 切分为小块
3. **向量化存储**：用 OpenAI Embedding + ChromaDB 存储向量
4. **检索**：基于用户问题检索最相关的文档片段
5. **生成**：将检索结果和问题交给 LLM 生成答案
6. **调试优化**：查询改写、流式输出、返回来源

这是一个最小可用的 RAG 系统。实际项目中，你可能还需要处理更多细节（如多格式文档、权限控制、并发处理等），但核心流程是一样的。

> 这是一个最小可用的 RAG 系统。实际项目中，你可能还需要处理更多细节（如多格式文档、权限控制、并发处理等），但核心流程是一样的。朴素 RAG 有一个天花板——跨文档的因果关系它推理不了。下一篇 [GraphRAG：知识图谱增强检索](./06-graphrag.md) 会突破这个天花板。

## 参考链接

- [LangChain — Quickstart](https://python.langchain.com/docs/tutorials/rag/) — LangChain RAG 官方教程
- [ChromaDB — Getting Started](https://docs.trychroma.com/docs/overview/getting-started) — ChromaDB 快速开始
- [LangChain — Text Splitters](https://python.langchain.com/docs/how_to/recursive_text_splitter/) — 文档切分详解
- [OpenAI — Embeddings Guide](https://platform.openai.com/docs/guides/embeddings) — Embedding 模型使用指南
- [LangChain — Retrievers](https://python.langchain.com/docs/concepts/retrievers/) — 检索器概念详解
