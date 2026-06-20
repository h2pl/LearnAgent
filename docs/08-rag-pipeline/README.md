# 08 — 知识检索（RAG）

上下文窗口有限，不能什么都往里塞。**RAG（检索增强生成）的答案是：不塞全部，按需检索**——只把和当前问题最相关的信息放入上下文。六篇文章从 [原理概述](./01-rag-overview.md) 出发，深入 [文档切分与向量化](./02-chunking-embedding.md)、[检索与重排序](./03-retrieval-reranking.md)、[评测优化](./04-evaluation-optimization.md)，最后通过 [构建 RAG 系统](./05-build-rag-system.md) 和 [GraphRAG](./06-graphrag.md) 完成从基础到进阶的完整路径。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [RAG 原理概述](./01-rag-overview.md) | LLM 的知识困境与 RAG 的核心思想 |
| 02 | [文档切分与向量化](./02-chunking-embedding.md) | 切分策略、Embedding 模型、向量数据库选型 |
| 03 | [检索与重排序策略](./03-retrieval-reranking.md) | 向量检索、BM25、混合检索、Reranker |
| 04 | [RAG 评测与优化](./04-evaluation-optimization.md) | 检索/生成指标、评测框架、优化技巧 |
| 05 | [构建你的第一个 RAG 系统](./05-build-rag-system.md) | Python + LangChain + ChromaDB 端到端实战 |
| 06 | [GraphRAG：知识图谱增强检索](./06-graphrag.md) | 突破朴素 RAG 天花板，跨文档因果推理 |

> **RAG 解决的是"外部知识怎么进窗口"**——检索外部文档、知识库。但 Agent 还需要记住**自己经历过的事**：上次对话做了什么决策、用户偏好是什么、上次在哪出错了。进入 [09 — 记忆管理](../09-memory-management/README.md)，学怎么让 Agent 拥有跨会话的持久记忆。