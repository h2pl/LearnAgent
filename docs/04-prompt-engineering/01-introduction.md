# Prompt 工程入门

> Prompt 是你发给 LLM 的全部输入，它的质量直接决定模型输出质量。本文从消息角色、LLM 处理机制到六条基本原则，建立 Prompt 工程的基础认知。

## 目录

- [什么是 Prompt](#什么是-prompt)
- [三种消息角色](#三种消息角色)
- [LLM 怎么处理 Prompt](#llm-怎么处理-prompt)
- [Prompt 工程 vs 传统编程](#prompt-工程-vs-传统编程)
- [写好 Prompt 的六条原则](#写好-prompt-的六条原则)
- [Prompt 工程不是什么](#prompt-工程不是什么)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面两章你搞懂了 LLM 能做什么、怎么选模型、怎么调 API。现在进入一个更关键的问题：**怎么写指令，才能让模型稳定地按你的要求工作？**

这门技术叫 Prompt 工程（Prompt Engineering）。听起来像玄学，其实是一套系统化的方法论。后面四篇文章会逐一展开具体技术，但这篇先解决更基本的问题：Prompt 到底是什么、LLM 是怎么理解它的、写好 Prompt 有哪些通用原则。

## 什么是 Prompt

**Prompt 就是你发给 LLM 的全部输入。** 在 API 调用中，它是 `messages` 列表里的每一条消息；在 ChatGPT 对话框里，它是你输入的文字加上平台预设的系统指令。

LLM 收到 Prompt 后做的事情很简单：根据这段文字，**预测最可能的下一个 Token（词元），然后一个接一个地生成回答。** 它不是"理解你的意图再回答"，而是做统计意义上的概率续写。所以同样一个模型，换一段 Prompt，输出可能天差地别。

```
用户看到的：  "帮我写一封拒绝邮件"        →   模型输出完整邮件
实际发生的：  [system + user messages]     →   逐 Token 概率续写
```

**Prompt 工程的本质：通过精心设计输入，引导 LLM 的概率分布朝你想要的方向偏移。** 不是"求"模型做好，而是给它足够的信号，让它"不得不"做好。你在 API 调用中设置的 `temperature`、`max_tokens` 等参数（详见[关键参数与调优](../03-model-access/02-key-parameters-and-tuning.md)）控制的是生成过程的随机性和长度，而 Prompt 控制的是**内容方向**——两者配合使用，才能精确控制输出。

## 三种消息角色

调用 Chat Completions API 时，每条消息都有一个 `role` 字段。理解这三种角色的区别和权重，是写好 Prompt 的前提：

| 角色 | 谁写的 | 作用 | 模型对它的权重 |
|------|-------|------|-------------|
| **system** | 开发者 | 定义 Agent 的身份、规则、边界、输出格式 | **最高** — 模型会优先遵循 |
| **user** | 终端用户 | 提问、下指令、提供上下文信息 | **中等** — 模型据此生成回答 |
| **assistant** | 模型自己 | 历史回复，维持对话连贯性 | **参考** — 模型会保持风格一致 |

<p align="center">
  <img src="../../assets/04-prompt-engineering/message-roles.svg" alt="三种消息角色与LLM交互流程" width="90%"/>
  <br/>
  <em>三种消息角色的交互流程与权重关系</em>
</p>

### 一个实际的 API 调用

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        # system: 开发者设定规则，权重最高
        {"role": "system", "content": "你是电商客服助手，只回答与订单和退货相关的问题。拒绝回答无关话题。"},
        # user: 用户提问
        {"role": "user", "content": "你们的退货政策是什么？"},
        # assistant: 模型之前的回复，用于维持上下文
        {"role": "assistant", "content": "我们支持 7 天无理由退货，退货时商品需保持原包装。"},
        # user: 用户继续追问
        {"role": "user", "content": "那帮我退一下昨天买的耳机"}
    ],
    temperature=0  # Agent 场景通常用 0
)
```

### 三个关键认知

**System Prompt 是你对模型施加的最强控制。** 它像是 Agent 的"宪法"——User Prompt 中的指令在大多数情况下不能覆盖 System 里的规则。这意味着：你希望 Agent 始终遵守的行为（如"不讨论政治""不泄露内部数据"），必须写在 System Prompt 里。

**Assistant 消息不只是历史记录。** 它同时是 Few-shot 示例的载体——你可以在 Assistant 消息中预设"理想回复"，教模型用特定格式回答。后面讲 Few-shot 时会详细展开。

**角色的顺序很重要。** 标准顺序是 System → User → Assistant → User → Assistant → ...。System 永远在最前面，User 和 Assistant 交替出现。模型对**最近的消息关注度最高**（见下文注意力分布），所以最新一轮 User 消息的权重实际上很高。

## LLM 怎么处理 Prompt

理解 LLM 内部处理 Prompt 的机制，能帮你写出更有效的指令。不需要深入数学，只需要掌握三个关键事实：

### 1. 逐 Token 阅读，不是"理解整段再回答"

模型不是一次性"读完"你的 Prompt 再给出回答。它把文本切分成 Token（通常一个中文字 ≈ 1-2 个 Token，一个英文单词 ≈ 1-1.5 个 Token），然后逐层处理。这意味着：

- **精确用词比模糊描述更有效** — "输出 200 字以内"比"简短一点"给模型更明确的概率信号
- **结构化的输入比散文更有效** — 列表、标签、代码块这类结构让模型更容易精确提取信息
- **重复关键指令可以提高遵循率** — 如果某条规则非常重要，可以在 System 和 User 中各提一次

### 2. 注意力分布不均匀："Lost in the Middle"

模型对 Prompt 中每个 Token 的关注程度不同。研究表明，LLM 对**开头和结尾**的内容关注度最高，中间的长文本容易被"稀释"——这就是所谓的 "Lost in the Middle" 效应：

<p align="center">
  <img src="../../assets/04-prompt-engineering/attention-distribution.svg" alt="LLM注意力分布" width="90%"/>
  <br/>
  <em>LLM 对 Prompt 各位置的注意力权重分布</em>
</p>

**这对你的实际影响**：

- **关键规则放开头**（System Prompt）— 不会被"遗忘"
- **最新指令放结尾**（最近的 User 消息）— 注意力最高
- **无关长文本不要塞中间** — 会被稀释，甚至干扰模型对核心指令的理解
- **长文档摘要后再使用** — 不要直接把 5000 字的文档塞进 Prompt，先提取关键段落

### 3. 上下文窗口是有限的

所有消息的 Token 总和不能超过模型的上下文窗口（Context Window）。超出部分会被截断，通常是丢掉最早的消息。这意味着：

- **对话越长，模型越容易"忘记"早期内容** — 20 轮对话后，第 1 轮的内容可能已被截断
- **System Prompt 不会被截断** — 各主流平台都对 System 消息做了保护，它始终保留
- **长上下文不等于长记忆** — 即使模型标称支持 128K Token，实际测试中超过 32K 后中间信息的召回率显著下降

## Prompt 工程 vs 传统编程

很多开发者刚接触 Prompt 工程时会不习惯，因为它的思维方式跟传统编程有本质区别：

| 维度 | 传统编程 | Prompt 工程 |
|------|---------|------------|
| **指令方式** | 精确指令：`if x > 0 return "positive"` | 概率引导：给示例、给上下文、给约束 |
| **执行结果** | 确定性的：同一输入永远同一输出 | 概率性的：同一 Prompt 可能产生不同输出 |
| **调试方式** | 断点 + 单步执行 | 反复测试 + 调整 Prompt |
| **错误处理** | `try/catch` 精确捕获 | 输出解析 + 重试 + fallback |
| **维护方式** | 改代码逻辑 | 改 Prompt 文本，回归测试 |

**核心差异**：传统编程是"告诉机器每一步怎么做"，Prompt 工程是"告诉模型你要什么结果，让它自己决定怎么做"。你控制的是**目标和约束**，不是执行路径。

这就是为什么 Prompt 工程需要一套完全不同的方法论——后面四篇文章会系统展开。

## 写好 Prompt 的六条原则

在学具体技巧之前，先掌握这六条原则。后面四篇文章的所有技术——Few-shot、Schema 约束、System Prompt 设计、鲁棒性防御——都是这些原则的具体实现。

### 原则一：明确具体

模型无法猜测你没说清楚的需求。字数、格式、语气、受众——越具体，输出越可控。

```
❌ "帮我写点东西"
✅ "帮我写一封 200 字以内的邮件，拒绝供应商的涨价请求，语气礼貌但立场坚定，署名：采购部 张经理"
```

**判断标准**：如果你的 Prompt 发给三个不同的模型，得到的输出格式和风格应该基本一致。如果差异很大，说明不够具体。

### 原则二：给上下文

同样的问题，有无上下文，回答质量差 10 倍。

```
❌ "这个 bug 怎么修？"
✅ "Python 3.11 + FastAPI 0.109，报错 TypeError: cannot unpack non-iterable NoneType。
    出错的函数是 parse_user_profile()，输入数据是：{'name': 'Alice', 'age': null}。
    完整 traceback 如下：..."
```

**上下文包括**：运行环境、输入数据、期望输出、已尝试的方案。提供的上下文越精确，模型的"猜测空间"越小，输出越准确。

### 原则三：定义输出格式

不定义格式 = 接受模型的自由发挥。定义格式 = 得到可预测的结构化输出。

```
❌ "分析一下这两个技术方案的优缺点"
✅ "对比这两个方案，用 Markdown 表格，包含以下列：方案名、优势（3 点）、劣势（3 点）、推荐场景、预估成本"
```

在 Agent 开发中，输出格式尤其重要——Agent 需要用代码解析模型的输出（JSON、XML 等）。后面的[结构化输出](./03-structured-output.md)会详细讲如何用 JSON Mode 和 Schema 约束来保证格式稳定。

### 原则四：区分指令和数据

用 XML 标签、分隔符把"指令"和"要处理的内容"分开，模型才能准确识别哪些是你要它做的事，哪些是素材。

```
❌ "总结这篇文章：[粘贴 3000 字文章]"
✅ "请总结以下文章，提取 3 个核心观点，每个观点用一句话概括。
    文章用 <article> 标签包裹：
    <article>
    [粘贴 3000 字文章]
    </article>"
```

**为什么要这样做**：如果不用标签分隔，模型可能把你的"总结"指令当成文章的一部分来"续写"，而不是当成要执行的命令。标签越清晰，模型的遵循率越高。

### 原则五：给示例

当文字描述不够精确时，给 2-3 个示例比写 500 字说明更有效。

```
❌ "把用户的问题分类为'技术问题'、'账单问题'或'其他'"
✅ "把用户的问题分类。示例：
    问：'我的密码忘了怎么办' → 分类：技术问题
    问：'上个月多扣了一笔钱' → 分类：账单问题
    问：'你们公司地址在哪' → 分类：其他

    现在请分类：'App 打不开了'"
```

这就是 Few-shot 模式——通过示例教模型你想要什么。它是 Prompt 工程中最实用的技巧之一，后面会专门讲。

### 原则六：迭代优化

**好的 Prompt 不是一次写出来的。** 每次输出不理想时，不要盲目大改，而是问自己：是哪条原则没做好？

| 输出问题 | 可能原因 | 改进方向 |
|---------|---------|---------|
| 格式不对 | 原则三没做好 | 明确定义输出格式 |
| 内容跑题 | 原则二没做好 | 补充上下文信息 |
| 过于笼统 | 原则一没做好 | 增加具体约束（字数、维度） |
| 混淆指令和数据 | 原则四没做好 | 加标签分隔 |
| 风格不一致 | 原则五没做好 | 给 2-3 个示例 |

**迭代流程**：写 Prompt → 测试 → 分析失败原因 → 针对性修改 → 再测试。这个循环通常需要 3-5 轮才能得到稳定的 Prompt。

## Prompt 工程不是什么

在正式开始学习具体技术之前，澄清几个常见误解：

**不是"念咒语"。** 网上流传的"加上这段话效果提升 10 倍"大多是噪音。Prompt 工程的效果来自对 LLM 工作机制的理解，不是靠背诵几个"魔法短语"。

**不是"一次到位"。** 即使是最有经验的 Prompt 工程师，也需要反复测试和调整。生产环境的 Prompt 通常经过了数十轮迭代。

**不是"越多越好"。** Prompt 过长反而会降低效果（注意力稀释）。精准的 200 字 Prompt 通常优于冗长的 2000 字 Prompt。

**不是"只靠 System Prompt"。** System Prompt 定义了 Agent 的基线行为，但 User Prompt 的质量同样重要。两者配合使用才能达到最佳效果。

## 总结

- **Prompt 是你发给 LLM 的全部输入** — 模型根据它逐 Token 续写，Prompt 质量直接决定输出质量
- **三种消息角色** — System（开发者设规则，权重最高）、User（用户输入）、Assistant（模型历史回复），System 是你的最强控制手段
- **LLM 对开头和结尾最敏感** — 中间长文本容易被稀释（Lost in the Middle）；上下文窗口有限，对话越长越容易"失忆"
- **Prompt 工程 ≠ 传统编程** — 你控制的是目标和约束，不是执行路径；结果是概率性的，不是确定性的
- **六条基本原则** — 明确具体、给上下文、定义输出格式、区分指令和数据、给示例、迭代优化
- **Prompt 工程是系统化方法论** — 不是念咒语，不是一次到位，需要理解机制 + 反复测试

这篇文章建立了 Prompt 工程的基础认知。接下来四篇文章逐一展开具体技术：

- [Prompt 设计模式](./02-prompt-design-patterns.md)：四种组织 Prompt 的核心方法
- [结构化输出](./03-structured-output.md)：让输出能被代码消费
- [System Prompt 设计](./04-system-prompt.md)：定义 Agent 的身份和边界
- [Prompt 鲁棒性](./05-prompt-robustness.md)：应对意外输入的防御体系

> 基础概念搞清楚了，接下来学习四种核心的 Prompt 组织方式。请前往 [Prompt 设计模式](./02-prompt-design-patterns.md)。

## 参考链接

- [OpenAI — Chat Completions API](https://platform.openai.com/docs/guides/chat-completions) — messages 结构和角色定义
- [Anthropic — System Prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts) — System Prompt 最佳实践
- [Liu et al. — Lost in the Middle (2023)](https://arxiv.org/abs/2307.03172) — 注意力分布不均匀的实证研究
- [Prompt Engineering Guide](https://www.promptingguide.ai/) — 社区维护的系统化教程
- [Anthropic — Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) — Anthropic 官方 Prompt 工程文档
