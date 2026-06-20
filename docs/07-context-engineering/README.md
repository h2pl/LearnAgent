# 07 — 上下文工程

每一轮 Agent 循环都要往上下文窗口里塞东西——系统提示、工具定义、对话历史、工具返回结果……但窗口有限，信息无限。**上下文工程就是学会管理这个最稀缺的资源**。五篇文章从 [瓶颈分析](./01-context-window-bottleneck.md) 开始，依次讲解 [压缩策略](./02-context-compression.md)、[Token 预算](./03-token-budget-cost.md)、[卸载与隔离](./04-context-offloading-isolation.md)，最后总结 [失败模式与反模式](./05-context-failure-patterns.md)。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [上下文窗口：Agent 的瓶颈资源](./01-context-window-bottleneck.md) | 上下文窗口的本质限制、"迷失在中间"现象、信息优先级设计 |
| 02 | [上下文压缩策略](./02-context-compression.md) | 摘要压缩、Token 裁剪、滑动窗口、选择性注入 |
| 03 | [Token 预算与成本控制](./03-token-budget-cost.md) | Prompt Caching、KV Cache、上下文预算分配、成本优化实战 |
| 04 | [上下文卸载与隔离](./04-context-offloading-isolation.md) | 文件系统当无限记忆、可逆压缩、分层工具空间、主子 Agent 隔离 |
| 05 | [上下文失败模式与反模式](./05-context-failure-patterns.md) | 四种失效模式深度分析、七个常见反模式、不同规模工程路线图 |

> **上下文工程管的是"窗口"**——怎么把有限的空间用好。学完你会明白一个道理：不能什么都往窗口里塞。那外部知识怎么办？进入 [08 — 知识检索（RAG）](../08-rag-pipeline/README.md)，学怎么"按需取"而不是"全塞进去"。