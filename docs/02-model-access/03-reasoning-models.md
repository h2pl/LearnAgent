# 推理模型专题

> o1、o3、DeepSeek R1、Claude Extended Thinking——这些"会思考"的模型和普通 LLM 有什么本质区别？本文从机制、调用方式、成本到适用场景，帮你建立推理模型的完整认知。

## 目录

- [什么是推理模型](#什么是推理模型)
- [推理模型 vs 普通 LLM：本质区别](#推理模型-vs-普通-llm本质区别)
- [主流推理模型一览](#主流推理模型一览)
- [如何调用推理模型](#如何调用推理模型)
- [什么时候该用推理模型](#什么时候该用推理模型)
- [什么时候不该用](#什么时候不该用)
- [成本与延迟的权衡](#成本与延迟的权衡)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。[模型尺寸与变体](./02-model-variants.md)讲了同一家族不同大小的模型。但有一类模型，它们不是靠"更大"来变强，而是靠**"想得更久"**来变强。

这就是**推理模型（Reasoning Model）**——2024 年底到 2025 年最重要的技术方向之一。OpenAI 的 o 系列、DeepSeek R1、Claude Extended Thinking 都属于这一类。它们在回答之前会先"思考"一段相当长的时间，然后才给出最终答案。

## 什么是推理模型

**推理模型**是一类在生成最终答案之前，会先执行内部多步推理链（Chain of Thought）的 LLM。

普通 LLM 的工作流程：

```
用户问题 → [一次前向传播] → 直接给出答案
```

推理模型的工作流程：

```
用户问题 → [思考阶段：多步推理] → [回答阶段：基于推理结果输出]
```

这个"思考阶段"可能是几百个 Token 到几万个 Token 不等，取决于问题的复杂度。关键是：**这些思考 Token 是模型在内部生成的，用于辅助最终答案的生成，而不是直接展示给用户的**（虽然也可以选择展示）。

## 推理模型 vs 普通 LLM：本质区别

### 架构层面的差异

普通 LLM 和推理模型使用的基础架构相同（都是 Transformer），但**训练目标和推理行为**有根本差异：

| 维度 | 普通 LLM | 推理模型 |
|------|---------|---------|
| 训练目标 | 预测下一个词 | 先推理再回答，奖励正确答案 |
| 推理过程 | 单次前向传播 | 多次自回归生成（思维链） |
| 计算分配 | 固定（每次调用一样多） | 动态（简单问题少想，复杂问题多想） |
| 典型场景 | 聊天、翻译、写作 | 数学证明、代码调试、逻辑分析 |

### 为什么"想得更久"能变强

在 [LLM 能做什么](../01-llm-basics/04-capabilities.md) 中讲过：普通 LLM 每次预测下一个 Token 时只有**一次前向传播的计算量**。对于需要多步推理的问题（如数学计算 `34598 × 23489`），单次计算的中间状态必须全部编码进隐层向量中——信息容易丢失或混淆。

推理模型通过**把计算拆成多步**来解决这个问题：
- 第 1 步："先算 34598 × 20000 = 691,960,000"
- 第 2 步："再算 34598 × 3000 = 103,794,000"
- 第 3 步："...最后加起来"

每一步都是一次完整的前向传播，上一步的结果作为新的上下文进入下一步。这就像考试时允许打草稿vs只准写答案的区别。

<p align="center">
  <img src="../../assets/02-model-access/reasoning-vs-standard.png" alt="推理模型与普通模型的工作流对比" width="90%"/>
  <br/>
  <em>推理模型 vs 普通模型：单次生成 vs 多步思维链</em>
</p>

## 主流推理模型一览

### OpenAI o 系列（o1 / o3 / o4-mini）

OpenAI 是推理模型的先驱。o1 于 2024 年发布，是第一个大规模商用的推理模型系列。

**核心机制**：在训练阶段使用强化学习（RL），让模型学会"在回答之前先生成推理链"。推理过程中模型会产生内部的"思考 Token"（thinking tokens），这些 Token 不对用户可见（除非特别请求）。

**关键 API 参数**：`reasoning_effort`，控制模型"想多久"：

```python
from openai import OpenAI

client = OpenAI()

# 低推理努力模式：快速但深度有限
response_low = client.chat.completions.create(
    model="o4-mini",
    messages=[{"role": "user", "content": "15 * 27 + 13 * 8 = ?"}],
    reasoning_effort="low"   # low / medium / high
)

# 高推理努力模式：更慢但更准确
response_high = client.chat.completions.create(
    model="o4-mini",
    messages=[{"role": "user", "content": "证明根号2是无理数"}],
    reasoning_effort="high"
)
```

`reasoning_effort` 是推理模型独有的参数——它让你在**速度和准确率之间做细粒度调节**，这是普通模型做不到的。

### DeepSeek R1 系列

DeepSeek R1 是开源推理模型的代表，其训练方法尤为值得关注。

**R1-Zero：纯 RL 的奇迹**。DeepSeek 先用纯强化学习（GRPO 算法）在一个 Base 模型上训练，**不使用任何 SFT 数据**。令人惊讶的是，模型自发地学会了生成长思维链——它自己"发现"了"先想再做"能提高正确率。AIME 2024 数学竞赛成绩从 15.6% 飙升到 71.0%。

**R1：生产版本**。R1-Zero 虽然推理能力强，但输出可读性差（语言混杂、格式混乱）。R1 在此基础上加入了：
- **冷启动 SFT**：少量高质量 (思维链, 答案) 对，规范输出格式
- **通用领域 SFT**：写作、事实问答等非推理任务的对齐数据
- **最终 RL 微调**：兼顾推理能力和通用表现

**API 调用特点**：DeepSeek R1 的推理过程用 ` thinker` 标签包裹：

```
<thinkuser>让我仔细算一下这个问题...</thinkuser>

答案是 610。
```

`<thinkuser>` 内的内容就是模型的思维链，你可以选择是否向用户展示。

### Claude Extended Thinking

Anthropic 的方案叫 **Extended Thinking（扩展思考）**，通过 API 参数启用：

```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000   # 分配给思考的 Token 预算
    },
    messages=[{"role": "user", "content": "分析这段代码的时间复杂度"}]
)

# 思维块和正文分开返回
for block in message.content:
    if block.type == "thinking":
        print(f"[思考]: {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"[回答]: {block.text}")
```

Claude 的设计特点是**显式预算控制**：你告诉模型"最多想多少个 Token"，模型在这个预算内自主决定怎么分配思考深度。

## 如何调用推理模型

### 统一调用模式

虽然各家实现不同，但调用推理模型的核心模式是一致的：

```python
def call_reasoning_model(provider, question, effort="medium"):
    """
    统一调用推理模型的封装
    provider: "openai" | "deepseek" | "anthropic"
    effort: "low" | "medium" | "high"
    """
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model="o4-mini",
            messages=[{"role": "user", "content": question}],
            reasoning_effort=effort
        )
        return resp.choices[0].message.content

    elif provider == "deepseek":
        from openai import OpenAI  # DeepSeek 兼容 OpenAI 格式
        client = OpenAI(base_url="https://api.deepseek.com/v1")
        resp = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "user", "content": question}]
        )
        # DeepSeek R1 返回中包含 thinkuser 标签
        return resp.choices[0].message.content

    elif provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        budget = {"low": 3000, "medium": 8000, "high": 15000}[effort]
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": budget},
            messages=[{"role": "user", "content": question}]
        )
        return next(b.text for b in resp.content if b.type == "text")
```

### 注意事项

- **推理 Token 也计费**：DeepSeek R1 的推理 Token 价格是普通 Token 的约 3 倍。OpenAI 的 o 系列推理 Token 单独计费。不要忽略这部分成本。
- **延迟显著更高**：一个复杂问题可能需要 10-30 秒才能得到回答（普通模型通常 1-3 秒）。实时交互场景需谨慎使用。
- **Temperature 建议**：推理模型建议设为 0 或接近 0。高 Temperature 会干扰推理链的一致性。

## 什么时候该用推理模型

### 明确适合的场景

| 场景 | 示例 | 为什么需要推理模型 |
|------|------|------------------|
| 数学计算 | 复杂算术、方程求解、概率统计 | 多步精确运算，不能靠概率猜测 |
| 代码调试 | 定位 bug 原因、分析报错堆栈 | 需要追踪执行路径和多文件关联 |
| 逻辑分析 | 法律条款对比、合同审查 | 长链条条件判断 |
| 科学推理 | 实验设计、假设验证 | 需要系统性排除错误假设 |
| Agent 规划器 | 决定工具调用顺序、处理分支条件 | 多步决策，每步依赖上一步 |

### Agent 开发中的最佳位置

推理模型最适合放在 **Agent 的规划层（Planner）**：

```python
# Agent 核心循环中的分层策略

def agent_loop(user_input):
    # 1. 意图识别 → 小模型（快）
    intent = classify_intent(user_input)  # Haiku / Flash

    # 2. 规划 → 推理模型（准）
    plan = reasoner_plan(              # o4-mini / R1 / Claude Thinking
        user_input=user_input,
        available_tools=get_tools(),
        reasoning_effort="medium"
    )

    # 3. 工具执行 → 代码直接执行
    results = execute_tools(plan.actions)

    # 4. 结果汇总 → 中模型（平衡）
    final_answer = synthesize(results)  # Sonnet / GPT-5.4

    return final_answer
```

**规划层是整个 Agent 最不能出错的地方**——如果规划错了，后面所有工具调用都白费。所以这里值得花更多的时间和 Token 用推理模型。

## 什么时候不该用

推理模型不是万能的。以下场景用它纯属浪费钱和时间：

- **简单问答**："Python 的列表怎么去重？"→ 普通模型 1 秒搞定，推理模型要 5-8 秒
- **文本生成**：写邮件、翻译、摘要 → 推理模型不会写得更好，只会更慢
- **高并发低延迟场景**：客服聊天、实时推荐 → 延迟要求 < 2s，推理模型做不到
- **创意任务**：写诗、头脑风暴 → 推理模型的"严谨"反而限制创造力
- **格式化任务**：JSON 提取、数据清洗 → 小模型就够用

**简单判断标准**：如果一个问题你能在 30 秒内心算出答案，那大概率不需要推理模型。

## 成本与延迟的权衡

用一个具体例子说明成本差异：

假设你的 Agent 每天处理 1000 个查询，其中 20% 需要深度推理：

| 方案 | 推理查询成本 | 普通查询成本 | 日总成本 | 平均延迟 |
|------|------------|------------|---------|---------|
| 全用 GPT-5.4（普通） | $0.75 | $3.00 | $3.75 | ~2s |
| 全用 o4-mini（推理） | $2.50 | $2.50 | $5.00 | ~8s |
| **混合策略**（推理+普通） | $2.50（200个） | $2.40（800个） | **$4.90** | ~4s |

混合策略的成本介于两者之间，但**关键任务的质量显著提升**。这就是为什么生产环境的 Agent 系统几乎都采用多模型路由。

## 总结

- **推理模型的核心创新**是在回答之前先执行多步思维链，用更多计算换取更高准确率
- **三家主流方案**：OpenAI o 系列（reasoning_effort 控制）、DeepSeek R1（纯 RL 训练 + thinker 标签）、Claude Extended Thinking（budget_tokens 显式预算）
- **Agent 最佳实践**：推理模型放在规划层，工具提取用小模型，汇总用中模型
- **不该用的场景**：简单问答、文本生成、高并发低延迟、创意任务——用了就是浪费
- **成本意识**：推理 Token 单独计费且更贵，延迟比普通模型高 3-10 倍

> 掌握了模型选型和推理模型的使用，接下来看看怎么通过 API 把它们调通。请前往 [LLM API 调用实战](./04-api-calling.md)。

## 参考链接

- [OpenAI — Reasoning Models Guide](https://platform.openai.com/docs/guides/reasoning) — o 系列官方指南
- [DeepSeek-R1 Technical Report](https://arxiv.org/abs/2501.12948) — R1 的完整技术论文
- [Anthropic — Extended Thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) — Claude 扩展思考官方文档
- [Reasoning Models Guide (myengineeringpath.dev)](https://myengineeringpath.dev/genai-engineer/reasoning-models/) — 推理模型综合对比教程
