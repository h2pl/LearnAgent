# RAG 评测与优化

> RAG 系统上线前必须评测——检索质量决定答案质量，检索指标（Recall@K、MRR）量化检索效果，生成指标（Faithfulness、Relevancy）量化答案质量，两阶段都需要优化。

## 目录

- [为什么需要评测 RAG](#为什么需要评测-rag)
- [检索阶段的评测指标](#检索阶段的评测指标)
- [生成阶段的评测指标](#生成阶段的评测指标)
- [RAG 评测框架](#rag-评测框架)
- [常见优化技巧](#常见优化技巧)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [检索与重排序策略](./03-retrieval-reranking.md) 中，你学会了多种检索策略。但"用了混合检索和 Reranker"不代表效果好——**你必须量化评测**。这篇文章解决核心问题：**如何衡量 RAG 系统的效果，以及如何系统性地优化**。

## 为什么需要评测 RAG

RAG 系统有两个阶段需要评测：

| 阶段 | 问题 | 后果 |
|------|------|------|
| **检索阶段** | 找到的文档不相关 | 答案错误或幻觉 |
| **生成阶段** | 答案没有基于文档 | 答案不可靠 |

**评测的价值**：

1. **量化效果**：用数字说话，而不是"感觉还行"
2. **定位瓶颈**：知道是检索问题还是生成问题
3. **对比方案**：不同策略的效果差异
4. **持续优化**：建立基线，跟踪改进效果

## 检索阶段的评测指标

检索阶段评测“找对了没有”：

<img src="../../assets/08-rag-pipeline/rag-evaluation-metrics.svg" alt="RAG 评测指标体系：检索评测 + 生成评测" width="95%"/>

| 指标 | 定义 | 适用场景 |
|------|------|----------|
| **Recall@K** | top-K 结果中包含多少相关文档 | 召回率优先 |
| **Precision@K** | top-K 结果中有多少是相关的 | 精确率优先 |
| **MRR** | 相关文档的排名倒数 | 排名优先 |
| **NDCG** | 考虑排名位置的评分 | 综合评估 |

```python
# 检索评测示例
def evaluate_retrieval(queries: list[str], 
                       relevant_docs: list[list[str]], 
                       retrieved_docs: list[list[str]],
                       k: int = 5):
    """评测检索质量"""
    
    metrics = {
        "recall@k": [],
        "precision@k": [],
        "mrr": []
    }
    
    for query, relevant, retrieved in zip(queries, relevant_docs, retrieved_docs):
        # Recall@K：top-K 中包含多少相关文档
        retrieved_set = set(retrieved[:k])
        relevant_set = set(relevant)
        recall = len(retrieved_set & relevant_set) / len(relevant_set)
        metrics["recall@k"].append(recall)
        
        # Precision@K：top-K 中有多少是相关的
        precision = len(retrieved_set & relevant_set) / k
        metrics["precision@k"].append(precision)
        
        # MRR：相关文档的排名倒数
        mrr = 0
        for i, doc in enumerate(retrieved):
            if doc in relevant_set:
                mrr = 1 / (i + 1)
                break
        metrics["mrr"].append(mrr)
    
    # 计算平均值
    return {metric: sum(values) / len(values) 
            for metric, values in metrics.items()}
```

**指标解读**：

| 指标 | 理想值 | 说明 |
|------|--------|------|
| Recall@5 | > 0.8 | top-5 能找到 80% 相关文档 |
| Precision@5 | > 0.6 | top-5 中 60% 是相关的 |
| MRR | > 0.7 | 相关文档平均在前 1-2 位 |

## 生成阶段的评测指标

生成阶段评测"答案质量"：

| 指标 | 定义 | 适用场景 |
|------|------|----------|
| **Faithfulness** | 答案是否基于检索文档 | 防幻觉 |
| **Relevancy** | 答案是否回答了问题 | 相关性 |
| **Answer Correctness** | 答案是否正确 | 准确性 |

```python
# 生成评测示例（使用 LLM-as-Judge）
def evaluate_generation(query: str, 
                        context: str, 
                        answer: str) -> dict:
    """用 LLM 评测生成质量"""
    
    prompt = f"""请评测以下 RAG 系统的回答质量。

问题：{query}
检索文档：{context}
系统回答：{answer}

请从以下维度评分（1-5 分）：
1. Faithfulness（答案是否基于检索文档，没有编造）
2. Relevancy（答案是否回答了问题）
3. Answer Correctness（答案是否正确）

输出 JSON 格式：{{"faithfulness": 分数, "relevancy": 分数, "correctness": 分数}}
"""
    
    response = llm.generate(prompt)
    return parse_scores(response)
```

**指标解读**：

| 指标 | 理想值 | 说明 |
|------|--------|------|
| Faithfulness | > 4 | 答案基于文档，无幻觉 |
| Relevancy | > 4 | 答案回答了问题 |
| Correctness | > 4 | 答案正确 |

## RAG 评测框架

使用成熟的评测框架简化评测流程：

| 框架 | 特点 | 适用场景 |
|------|------|----------|
| **RAGAS** | 专注 RAG 评测，指标丰富 | RAG 系统评测 |
| **DeepEval** | 通用 LLM 评测，支持多种指标 | LLM 应用评测 |
| **LangSmith** | LangChain 官方，集成度高 | LangChain 项目 |

```python
# RAGAS 评测示例
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

# 准备评测数据
eval_dataset = {
    "question": ["北京天气怎么样？"],
    "answer": ["北京今天晴，25°C"],
    "contexts": [["北京今天晴，25°C，湿度 45%"]],
    "ground_truth": ["北京今天晴，25°C"]
}

# 运行评测
result = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy]
)

print(result)
```

## 常见优化技巧

根据评测结果，针对性优化：

| 问题 | 优化技巧 | 适用场景 |
|------|----------|----------|
| **检索不准** | 混合检索 + Reranker | 关键词匹配重要 |
| **文档太长** | 优化切分策略 | 语义被切断 |
| **答案幻觉** | 改进 Prompt，强调"只基于文档" | 模型编造信息 |
| **答案不完整** | 增加上下文窗口 | 信息被截断 |
| **响应太慢** | 缓存热门查询，异步检索 | 用户体验要求高 |

**优化优先级**：

1. **先优化检索**：检索质量是基础，检索不准，生成再好也没用
2. **再优化生成**：检索质量达标后，优化答案质量和格式
3. **最后优化体验**：响应速度、错误处理、用户界面

```python
# 优化示例：改进 Prompt 减少幻觉
optimized_prompt = f"""基于以下文档回答问题。

文档：
{context}

要求：
1. 只使用文档中的信息回答
2. 如果文档中没有相关信息，明确说"文档中没有相关信息"
3. 不要编造任何信息

问题：{query}
"""
```

<p align="center">
  <img src="../../assets/08-rag-pipeline/rag-evaluation-radar.svg" alt="RAG评测雷达图：六大指标优化前后对比，检索+生成全面评测" width="95%"/>
</p>

## 总结

- **检索评测**：Recall@K、Precision@K、MRR 量化检索质量
- **生成评测**：Faithfulness、Relevancy、Correctness 量化答案质量
- **评测框架**：RAGAS、DeepEval、LangSmith 简化评测流程
- **优化策略**：先优化检索，再优化生成，最后优化体验

> 评测帮你知道了 RAG 系统的"体检报告"。下一步是动手实战——从零搭建一个完整的 RAG 系统。请继续阅读 [构建你的第一个 RAG 系统](./05-build-rag-system.md)。

## 参考链接

- [RAGAS — RAG Evaluation](https://docs.ragas.io/)
- [DeepEval — LLM Evaluation](https://docs.confident-ai.com/)
- [LangChain — Evaluation](https://python.langchain.com/docs/how_to/evaluation/)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
