# LangChain 详解

> LangChain 是目前最流行的 LLM 应用开发框架——理解它的核心概念、LCEL 组合语言、工具集成，以及什么时候该用、什么时候不该用。

## 目录

- [LangChain 是什么](#langchain-是什么)
- [核心概念](#核心概念)
- [LCEL：组合语言](#lcel组合语言)
- [构建一条完整的 Chain](#构建一条完整的-chain)
- [工具集成](#工具集成)
- [错误处理与重试](#错误处理与重试)
- [LangChain 的优缺点](#langchain-的优缺点)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在上一篇中我们比较了主流框架的选型。这一篇，我们深入 LangChain——目前生态最完善、社区最活跃的 LLM 应用框架。

读完本文，你将理解 LangChain 的核心概念、学会用 LCEL 组合各种组件、能够构建一个完整的 LLM 应用链路。

## LangChain 是什么

LangChain 是一个用于构建 LLM 应用的开源框架。它提供了一套标准化的组件和组合方式，让你可以快速搭建基于大模型的应用，而不需要从零处理 API 调用、Prompt 管理、输出解析等重复性工作。

### 生态组成

LangChain 不是一个单独的库，而是一个生态：

| 组件 | 作用 |
|------|------|
| **langchain-core** | 核心抽象和组合语言（LCEL） |
| **langchain-community** | 第三方集成（向量数据库、LLM 提供商等） |
| **langchain-openai** | OpenAI 模型的专用集成 |
| **LangSmith** | 追踪、调试、评估平台（商业服务） |
| **LangGraph** | 基于图的 Agent 编排框架（下一篇详解） |

安装：

```bash
pip install langchain langchain-openai langchain-community
```

## 核心概念

LangChain 围绕几个核心概念构建。理解这些概念，就理解了 LangChain 的设计哲学。

### 模型（Model）

LangChain 封装了各种 LLM 提供商的接口，提供统一的调用方式：

```python
from langchain_openai import ChatOpenAI

# 基础用法
llm = ChatOpenAI(model="gpt-4o")

# 配置参数
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,        # 创造性（0-1）
    max_tokens=2000,      # 最大输出长度
    timeout=30,           # 超时时间
    max_retries=2,        # 自动重试次数
)

# 调用
response = llm.invoke("你好，请自我介绍")
print(response.content)
```

所有 LangChain 的模型接口都遵循同一个模式：`llm.invoke(输入)` 返回 `AIMessage` 对象。

### 消息（Message）

LangChain 用消息对象来表示对话中的不同角色：

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

messages = [
    SystemMessage(content="你是一个专业的技术顾问"),
    HumanMessage(content="什么是 RAG？"),
    AIMessage(content="RAG 是检索增强生成..."),
    HumanMessage(content="它和微调有什么区别？"),
]

response = llm.invoke(messages)
```

消息类型：

| 类型 | 角色 | 用途 |
|------|------|------|
| `SystemMessage` | system | 设置 AI 的行为和角色 |
| `HumanMessage` | user | 用户输入 |
| `AIMessage` | assistant | AI 的回复 |
| `ToolMessage` | tool | 工具调用的结果 |

### Prompt 模板（Prompt Template）

Prompt 模板让你可以动态生成 Prompt，避免硬编码：

```python
from langchain_core.prompts import ChatPromptTemplate

# 简单模板
prompt = ChatPromptTemplate.from_template("请用中文解释：{topic}")

# 多消息模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}，用{style}的风格回答问题"),
    ("human", "{question}"),
])

# 生成 Prompt
messages = prompt.invoke({
    "role": "技术专家",
    "style": "简洁专业",
    "question": "什么是 RAG？"
})
```

模板的核心价值：将 Prompt 逻辑与业务逻辑分离，便于管理和复用。

### 输出解析器（Output Parser）

LLM 返回的是文本，但你通常需要结构化的数据。输出解析器负责将文本转为 Python 对象：

```python
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

# 字符串解析（最简单）
parser = StrOutputParser()

# JSON 解析
class TechAnswer(BaseModel):
    summary: str = Field(description="一句话总结")
    details: str = Field(description="详细解释")
    pros: list[str] = Field(description="优点")
    cons: list[str] = Field(description="缺点")

parser = JsonOutputParser(pydantic_object=TechAnswer)

# 在 Prompt 中注入格式说明
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个技术顾问。{format_instructions}"),
    ("human", "{question}"),
])

chain = prompt | llm | parser
result = chain.invoke({
    "question": "比较 RAG 和微调",
    "format_instructions": parser.get_format_instructions(),
})
```

### Runnable 接口

LangChain 中几乎所有组件都实现了 `Runnable` 接口，这意味着它们都可以用统一的方式调用：

```python
# invoke：单次调用
result = llm.invoke("你好")

# batch：批量调用
results = llm.batch(["问题1", "问题2", "问题3"])

# stream：流式输出
for chunk in llm.stream("讲一个故事"):
    print(chunk.content, end="", flush=True)

# ainvoke：异步调用
result = await llm.ainvoke("你好")
```

这个统一接口是 LCEL 的基础。

## LCEL：组合语言

LCEL（LangChain Expression Language）是 LangChain 的核心创新——用 `|` 管道运算符将组件串联起来，就像 Unix 管道一样。

### 基本用法

```python
chain = prompt | llm | parser
result = chain.invoke({"topic": "RAG"})
```

`|` 管道运算符的意思是：左边的输出作为右边的输入。就像一条流水线：

```
输入数据 → prompt（格式化） → llm（生成） → parser（解析） → 结构化输出
```

### 为什么用 LCEL

传统的写法：

```python
# 传统写法
def answer(topic):
    messages = prompt.invoke({"topic": topic})
    response = llm.invoke(messages)
    result = parser.parse(response)
    return result
```

LCEL 写法：

```python
# LCEL 写法
chain = prompt | llm | parser
result = chain.invoke({"topic": "RAG"})
```

LCEL 的优势：

- **代码更简洁**：一行定义完整链路
- **自动支持流式**：`chain.stream()` 直接可用
- **自动支持批量**：`chain.batch([...])` 直接可用
- **自动支持异步**：`await chain.ainvoke()` 直接可用
- **易于组合**：链可以嵌套到更大的链中

### RunnableParallel：并行执行

当你需要同时执行多个独立步骤时：

```python
from langchain_core.runnables import RunnableParallel

# 并行执行两个独立的 Chain
review_chain = review_prompt | llm | StrOutputParser()
summary_chain = summary_prompt | llm | StrOutputParser()

# 两个 Chain 并行执行，结果合并为一个字典
parallel_chain = RunnableParallel(
    review=review_chain,
    summary=summary_chain,
)

result = parallel_chain.invoke({"text": "一篇长文章"})
# result = {"review": "...", "summary": "..."}
```

### RunnablePassthrough：透传

当你需要保留原始输入时：

```python
from langchain_core.runnables import RunnablePassthrough

# 检索+生成的典型模式
chain = (
    {
        "context": retriever,           # 检索结果
        "question": RunnablePassthrough(),  # 透传原始问题
    }
    | prompt
    | llm
    | StrOutputParser()
)
```

### RunnableLambda：自定义函数

当你需要嵌入自定义逻辑时：

```python
from langchain_core.runnables import RunnableLambda

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

chain = (
    {
        "context": retriever | RunnableLambda(format_docs),
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)
```

## 构建一条完整的 Chain

将以上概念组合，构建一个完整的问答 Chain：

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 1. 组件
llm = ChatOpenAI(model="gpt-4o", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# 2. Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "基于以下参考资料回答问题。如果找不到答案，说"找不到"。\n\n{context}"),
    ("human", "{question}"),
])

# 3. 格式化函数
def format_docs(docs):
    return "\n\n".join(f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs))

# 4. 组装 Chain
rag_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
    | StrOutputParser()
)

# 5. 调用
answer = rag_chain.invoke("什么是 RAG？")
print(answer)
```

这是一个完整的 RAG Chain，总共不到 30 行核心代码。LCEL 让你一眼就能看清数据流向。

## 工具集成

LangChain 提供了标准化的工具定义和调用机制：

### 定义工具

```python
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """搜索互联网获取最新信息"""
    # 这里接入实际的搜索 API
    return f"搜索结果：关于 '{query}' 的最新信息..."

@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"
```

`@tool` 装饰器会自动从函数签名和 docstring 生成工具的名称、描述和参数 schema，LLM 可以据此判断何时调用哪个工具。

### 在 Chain 中使用工具

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([search_web, calculate])

# LLM 会决定是否调用工具
response = llm_with_tools.invoke("今天北京天气怎么样？")
print(response.tool_calls)
# [{'name': 'search_web', 'args': {'query': '今天北京天气'}, 'id': '...'}]
```

### 工具执行器

手动执行工具调用：

```python
tools_by_name = {"search_web": search_web, "calculate": calculate}

def execute_tools(tool_calls):
    results = []
    for call in tool_calls:
        tool = tools_by_name[call["name"]]
        result = tool.invoke(call["args"])
        results.append({"tool_call_id": call["id"], "content": result})
    return results
```

## 错误处理与重试

LangChain 内置了重试和超时机制：

```python
from langchain_openai import ChatOpenAI

# 配置重试和超时
llm = ChatOpenAI(
    model="gpt-4o",
    max_retries=3,       # 自动重试 3 次
    timeout=30,          # 超时 30 秒
    request_timeout=30,  # 请求超时
)
```

### 自定义错误处理

```python
from langchain_core.runnables import RunnableLambda

def safe_llm_call(input_text):
    try:
        return llm.invoke(input_text)
    except Exception as e:
        return f"抱歉，服务暂时不可用：{e}"

chain = prompt | RunnableLambda(safe_llm_call) | parser
```

### 使用 Retryer

```python
from langchain_core.runnables import RunnableWithFallbacks

# 主链 + 降级链
primary_chain = prompt | primary_llm | parser
fallback_chain = prompt | fallback_llm | parser

chain_with_fallback = primary_chain.with_fallbacks([fallback_chain])
```

当主链失败时，自动尝试降级链。这在生产环境中非常有用——比如主模型不可用时切换到备用模型。

## LangChain 的优缺点

### 优点

| 优点 | 说明 |
|------|------|
| **生态完善** | 几乎集成了所有 LLM 提供商和向量数据库 |
| **LCEL** | 组合方式简洁直观，支持流式/批量/异步 |
| **社区活跃** | 遇到问题容易找到解决方案 |
| **文档丰富** | 官方教程和 API 文档完善 |
| **LangSmith** | 配套的追踪和调试平台 |

### 缺点

| 缺点 | 说明 |
|------|------|
| **抽象层多** | 调试时需要穿越多层抽象，定位问题较难 |
| **版本迭代快** | API 频繁变化，升级可能遇到 breaking change |
| **过度封装** | 简单场景可能引入不必要的复杂性 |
| **性能开销** | 抽象层带来一定的性能损耗 |

### 什么时候用 LangChain

- **快速原型**：需要快速验证一个 LLM 应用的想法
- **集成多种工具**：需要连接多种外部服务和数据源
- **团队协作**：团队成员水平不一，需要统一的开发模式
- **生产系统**：需要重试、超时、可观测性等生产级能力

### 什么时候不用

- **极简场景**：只需要简单调用 LLM API，直接用 OpenAI SDK 更简单
- **极致性能**：对延迟和吞吐量有极致要求，框架开销不可接受
- **深度定制**：需要完全控制执行流程，框架的抽象反而是束缚

## 总结

- **LangChain** 是 LLM 应用开发的"瑞士军刀"——组件丰富、生态完善、上手快
- **核心概念**：Model、Message、Prompt Template、Output Parser、Runnable
- **LCEL**：用 `|` 管道运算符组合组件，自动支持流式/批量/异步
- **工具集成**：`@tool` 装饰器定义工具，LLM 自动决定何时调用
- **错误处理**：内置重试、超时、降级链
- **适用场景**：快速原型、多工具集成、团队协作、生产系统

> 下一篇，我们将深入 LangGraph——当 LangChain 的线性链路不够用时，用状态图定义更复杂的 Agent 流程。

## 参考链接

- [LangChain Documentation](https://python.langchain.com/) — LangChain 官方文档
- [LCEL 指南](https://python.langchain.com/docs/how_to/lcel/) — LCEL 详解
- [LangChain Tutorials](https://python.langchain.com/docs/tutorials/) — 官方教程集
- [LangChain GitHub](https://github.com/langchain-ai/langchain) — 源码和 Issue
- [LangSmith](https://smith.langchain.com/) — 追踪和调试平台
