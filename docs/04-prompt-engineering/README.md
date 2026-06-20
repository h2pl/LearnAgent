# 04 — Prompt 工程

通过文字精确控制模型行为。本章六篇文章从基础到进阶层层递进：先通过 [Prompt 工程入门](./01-introduction.md) 理解 LLM 如何处理 Prompt 和三种消息角色，然后掌握 [四种核心设计模式](./02-prompt-design-patterns.md)、[结构化输出](./03-structured-output.md) 和 [System Prompt 设计](./04-system-prompt.md)，最后用数据驱动的方法学习 [Prompt 鲁棒性](./05-prompt-robustness.md) 和 [调试评估](./06-prompt-debugging-and-evaluation.md)。

## 文章

| # | 文章 | 内容 |
|---|------|------|
| 01 | [Prompt 工程入门](./01-introduction.md) | 什么是 Prompt、三种消息角色、LLM 处理机制、六条基本原则 |
| 02 | [Prompt 设计模式](./02-prompt-design-patterns.md) | Zero-shot、Few-shot、Chain-of-Thought、角色设定——四种核心模式的选择与组合 |
| 03 | [结构化输出](./03-structured-output.md) | JSON Mode、Schema 约束、输出解析——让 LLM 输出可被代码消费的稳定 JSON |
| 04 | [System Prompt 设计](./04-system-prompt.md) | 四段式结构 + XML 标签——定义 Agent 的角色、边界和输出规范 |
| 05 | [Prompt 鲁棒性](./05-prompt-robustness.md) | 幻觉控制、边界处理、一致性验证——让 Prompt 在意外输入下依然安全可控 |
| 06 | [Prompt 调试与评估](./06-prompt-debugging-and-evaluation.md) | 黄金用例集、LLM-as-Judge、A/B 测试、回归测试——把 Prompt 优化从凭感觉变成数据驱动 |

> 学完本章后，请继续阅读 [05 — 工具调用](../05-tool-use/README.md)，学习如何让 Agent 调用外部函数和 API。
