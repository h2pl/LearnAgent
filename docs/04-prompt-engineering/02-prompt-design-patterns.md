# Prompt 设计模式：从推测到精准控制

> 掌握 Zero-shot、Few-shot、Chain-of-Thought 和角色设定四种核心 Prompt 模式，你就掌握了控制 LLM 行为的"元语言"——从凭感觉写进化为系统化精准控制。

## 目录

- [什么是 Prompt 设计模式](#什么是-prompt-设计模式)
- [模式一：Zero-shot](#模式一zero-shot)
- [模式二：Few-shot](#模式二few-shot)
- [模式三：Chain-of-Thought](#模式三chain-of-thought)
- [模式四：角色设定](#模式四角色设定)
- [模式组合与选型](#模式组合与选型)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前两章搞懂了 LLM 是什么、怎么接入，现在到了最关键的一步——怎么组织你的指令，让模型产出你真正想要的结果。这四种模式，就是 Prompt 工程的"语法"。

这篇文章回答一个核心问题：**面对不同的场景和需求，你应该用什么方式组织 Prompt？** 四种模式——Zero-shot（零样本）、Few-shot（少样本）、Chain-of-Thought（思维链）和角色设定——不是零散的技巧，而是一套递进的系统。从"直接问"到"给示例"，再到"让它多想一步"，最后到"定义一个完整的角色"，它们的复杂度逐渐升高，控制精度也逐渐提升。理解这四种模式，才算真正入门了 Prompt 工程。

## 什么是 Prompt 设计模式

**Prompt 设计模式是组织 LLM 输入的标准化方法。** 就像软件工程中的 GoF 设计模式一样，Prompt 工程中也有经过验证的、可复用的组织方式。它们不是死板的模板，而是面向不同场景的"策略"——告诉你什么时候该给示例，什么时候该让模型"多想一想"，什么时候该给它一个完整的角色定义。

这些模式的核心目标只有一个：**降低模型输出的不确定性。** LLM 的本质是一个概率模型——参数通过大规模预训练编码了语言的统计规律，给定同一个 Prompt，它不一定生成完全相同的输出。Prompt 设计模式通过增加约束和引导，减少这种随机性，让输出更可控、更符合预期。

四种模式的递进关系：

<p align="center">
  <img src="../../assets/04-prompt-engineering/pattern-progression.svg" alt="四种模式递进关系" width="90%"/>
  <br/>
  <em>四种 Prompt 模式：控制精度与复杂度的递进</em>
</p>

| 模式 | 控制精度 | Token 消耗 | 适用复杂度 |
|------|---------|-----------|-----------|
| Zero-shot | 低 | 最少 | 简单任务 |
| Few-shot | 中 | 中等 | 中等任务 |
| Chain-of-Thought | 中高 | 较多 | 推理任务 |
| 角色设定 | 高 | 中等 | 任意复杂度 |

## 模式一：Zero-shot

**Zero-shot 是最基础的 Prompt 模式——只给指令，不给示例。** 你直接告诉模型你要什么，模型根据预训练中编码的知识直接生成响应。

**工作原理**：LLM 在万亿级 token 的海量数据上预训练后，参数中已经编码了大量任务的统计模式。对于常见任务（翻译、摘要、分类），你不需要提供示例，直接描述需求即可——模型能零样本地泛化到这些任务上。

```python
# Zero-shot：直接下指令，不给任何示例
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "用一句话解释什么是 Transformer。"}]
)
```

**适用场景**：任务描述清晰、目标明确、输出格式自由。比如"翻译以下文本为英文"、"给这段代码写注释"、"总结这篇文章的主要内容"。

**局限**：当任务要求特定的输出格式、风格、或领域知识时，单纯的一句指令往往不够。模型可能"自由发挥"，给出格式不符或风格不对的结果。比如你想让模型以"JSON 数组"的形式输出分类结果，Zero-shot 可能给你返回一个纯文本段落。这时候，你需要升级到 Few-shot。

## 模式二：Few-shot

**Few-shot 在 Zero-shot 的基础上，给模型提供 2-5 个示例，让模型通过示例"学会"你想要的输出格式和风格。**

**工作原理**：LLM 具有强大的**上下文学习（In-Context Learning）**能力——不需要更新模型参数，只需要在上下文窗口中提供示例，自注意力机制就能在推理时临时捕捉示例中的模式，使模型生成的输出分布向示例靠拢。

```python
# Few-shot：用示例定义输出格式和分类标准
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": """将用户反馈分类为"Bug"、"需求"或"咨询"。

示例1：
输入：登录按钮点不了
输出：Bug

示例2：
输入：能不能支持导出 PDF
输出：需求

示例3：
输入：这个功能怎么收费
输出：咨询

现在请分类：
输入：密码重置邮件收不到
输出："""}]
)
```

**示例设计原则**：

| 原则 | 说明 | 反例 |
|------|------|------|
| **典型性** | 示例应代表最常见的输入情况 | 用极端边缘 case 做示例会带偏模型 |
| **多样性** | 2-5 个示例覆盖不同变体（正面/负面、简短/详细） | 5 个示例全是同一类型 |
| **格式严格一致** | 示例的输入和输出格式必须与最终期望完全一致 | 示例用 JSON、却期望模型输出 YAML |
| **顺序的影响** | 最近的示例对模型影响最大，关键示例放最后 | 随意排列，不考虑近因效应 |

**动态 Few-shot**：在 Agent 开发中，示例不应该写死在 Prompt 里。更好的做法是维护一个示例库，根据用户输入动态检索最相关的示例拼接到 Prompt 中。这是 RAG 和 Prompt 工程的一个重要结合点，我们会在 RAG 管线章节详细展开。

```python
# 动态 Few-shot 示意（伪代码）
def build_prompt(user_input):
    examples = vector_search(user_input, example_db, top_k=3)
    return f"{format_examples(examples)}\n\n{user_input}"
```

Few-shot 能解决格式和风格问题，但当任务需要多步推理时，光是给示例还不够。模型需要被显式引导着"想一想"——这就是 Chain-of-Thought 要做的事。

## 模式三：Chain-of-Thought

**Chain-of-Thought（CoT，思维链）让模型在给出最终答案之前，先展示中间推理步骤。** 这个看似简单的改变，将模型从"直接跳到答案"转变为"先推理再回答"，大幅提升了数学、逻辑、规划等复杂任务上的准确率。

<p align="center">
  <img src="../../assets/04-prompt-engineering/cot-comparison.svg" alt="标准回答 vs CoT 对比" width="90%"/>
  <br/>
  <em>标准回答 vs Chain-of-Thought：同样的输入，不同的思考方式</em>
</p>

CoT 有两种变体：

**标准 CoT（Few-shot CoT）**：在 Few-shot 的示例中加入推理过程。每个示例不仅展示"输入→输出"，还展示"推理步骤→最终答案"。

```python
# 标准 CoT：示例中包含完整的推理步骤
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": """逐步推理，给出最终答案。

示例：
问题：小明有 5 个苹果，吃了 2 个，买了 3 个，给了朋友 1 个。还剩几个？
推理：初始 5 个 → 吃 2 个后剩 3 个 → 买 3 个后共 6 个 → 给朋友 1 个后剩 5 个
答案：5 个

现在请回答：
问题：一个水池，进水管 3 小时注满，排水管 5 小时排空。两管同时开，多久注满？
推理："""}]
)
```

**零样本 CoT（Zero-shot CoT）**：不需要准备带推理的示例，只需要在 Prompt 末尾加一句"Let's think step by step"（让我们一步一步思考），就能显著提升推理准确率。这一发现在 2022 年由 Kojima 等人证明，成为 Prompt 工程最著名的技巧之一。

```python
# 零样本 CoT：不需要示例，一句"step by step"就够了
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": """一个水池，进水管 3 小时注满，排水管 5 小时排空。
两管同时开，多久注满？请一步一步推理。"""}]
)
```

**CoT 对 Agent 开发的意义**：CoT 是 Agent **任务规划**的技术基础。在 ReAct 模式中（Agent 循环章节会详细展开），Agent 在每一步行动前都会"想一想"当前状态和下一步行动——这个"想"本质上就是 CoT 的应用。有了 CoT，Agent 才能将复杂目标拆解为可执行的子任务序列。

**CoT 的适用范围**：

- ✅ 数学推理、逻辑推理、多步决策
- ✅ Agent 任务规划与分解
- ✅ 需要拆解复杂问题的场景
- ❌ 简单的翻译、摘要任务（额外 token 是浪费）
- ❌ 高度不确定的创意任务（过度推理可能限制发散性）

## 模式四：角色设定

**角色设定（Role Prompting）通过定义模型的身份、领域、行为边界和输出格式，让模型在特定场景下输出更一致、更专业的结果。**

这不是简单的"你是一个 XX 专家"——那是无效的角色设定。有效的角色设定是一个包含四个要素的系统方法：

| 要素 | 作用 | 示例 |
|------|------|------|
| **角色（Role）** | 回答者是谁 | "资深 Python 后端工程师" |
| **上下文（Context）** | 在什么场景下 | "正在帮助 3 年 Java 经验者转 Python" |
| **约束（Constraint）** | 不能做什么 | "不使用 datetime 之外的时间库" |
| **格式（Format）** | 输出长什么样 | "Markdown 表格对比，代码用 f-string" |

一个完整的角色设定示例：

```python
system_prompt = """你是一个资深 Python 后端工程师，正在 code review 同事的代码。
同事有 3 年 Java 开发经验，正在学习 Python。

规则：
1. 优先指出逻辑问题，其次才是风格问题
2. 每个问题给出"为什么这样改"的理由
3. 用 Java 中类似的写法做类比，帮助对方理解
4. 不推荐未经验证的第三方库

输出格式：
- 问题：[代码行] — [严重程度：高/中/低]
- 原因：[一句话解释]
- 建议：[代码示例]"""
```

**角色设定的关键原则**：

- **越具体越有效**："资深 Python 后端工程师，专注 FastAPI + SQLAlchemy"比"编程助手"效果好得多
- **约束比角色更重要**：告诉模型不能做什么，比告诉它是什么，对输出的约束力更强
- **能力与模型要匹配**：给 Claude Opus 设定"顶级架构师"没问题，给轻量模型同等的角色期望可能力不从心
- **放在 System Prompt 中**：不要把角色定义放在 User 对话里，应该放在 System Prompt 中（后面有专门的文章讲 System Prompt 的设计）

**角色设定 vs System Prompt**：角色设定是一种 Prompt 模式，System Prompt 是实现它的最佳载体。你可以把角色设定看作是"设计"，把 System Prompt 看作是"实现"。后面的文章会展开 System Prompt 的结构化设计方法。

## 模式组合与选型

四种模式不是互斥的，实际开发中几乎总是组合使用：

<p align="center">
  <img src="../../assets/04-prompt-engineering/pattern-combo.svg" alt="模式组合示例" width="90%"/>
  <br/>
  <em>四种模式的典型组合方式</em>
</p>

| 组合方式 | 典型场景 | 为什么这样组合 |
|---------|---------|-------------|
| 角色 + Few-shot | 客服 Agent | 角色定义语调和边界，Few-shot 示范具体回复格式 |
| 角色 + CoT | 代码审查 Agent | 角色定义审查标准，CoT 确保逐步分析而非跳到结论 |
| Few-shot + CoT | 数据标注 Agent | Few-shot 定义标注规范，CoT 示范如何判断边界 case |
| 全组合 | 教学 Agent | 教师角色 + 解题示例 + 逐步讲解——全覆盖 |

**选型决策流程**：

1. 任务简单、输出要求不高 → **Zero-shot** 起步
2. 需要特定格式或风格 → **增加 Few-shot**
3. 涉及推理或多步决策 → **增加 CoT**
4. 需要长期保持行为一致性 → **增加角色设定**

这四个模式是你 Prompt 工具箱的基础。从下一篇文章开始，我们进入更细粒度的领域——如何让模型输出稳定的结构化数据、如何设计 System Prompt、如何提升 Prompt 的鲁棒性。

## 总结

这篇文章建立了 Prompt 设计的系统框架：

- **Zero-shot**：最轻量的起点，适合任务明确、格式自由的场景。效果不够好，就升级到 Few-shot
- **Few-shot**：通过 2-5 个示例教模型你想要什么。关键在于示例的典型性、多样性和格式一致性。Agent 开发中优先用动态 Few-shot，而不是硬编码示例
- **Chain-of-Thought**：让模型"先想再说"，显著提升推理准确率。标准 CoT 用示例示范推理，零样本 CoT 只加一句"step by step"。这是 Agent 任务规划的核心技术
- **角色设定**：从身份、上下文、约束、格式四个维度定义 Agent 行为。角色越具体、约束越明确，输出越可靠

四种模式从简单到复杂、从低控制到高控制，构成了 Prompt 工程的完整工具箱。

> 掌握了"让模型说什么"，下一步是"让模型怎么说"——结构化输出是 Agent 与工具交互的桥梁。接下来请阅读 [结构化输出：让 LLM 输出稳定的 JSON](./03-structured-output.md)。

## 参考链接

- [Anthropic — Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [OpenAI — Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (2022)](https://arxiv.org/abs/2201.11903) — CoT 原始论文
- [Large Language Models are Zero-Shot Reasoners (2022)](https://arxiv.org/abs/2205.11916) — 零样本 CoT 论文
- [Language Models are Few-Shot Learners (GPT-3, 2020)](https://arxiv.org/abs/2005.14165) — Few-shot 能力奠基论文
- [Prompt Engineering Guide (DAIR.AI)](https://www.promptingguide.ai/) — 最全面的社区 Prompt 工程指南
