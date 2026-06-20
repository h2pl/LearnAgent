# 深度思考与推理能力

> 2024 年的 o1、DeepSeek R1 是独立的"推理模型" SKU。但到 2026 年，**独立推理模型已不存在**——GPT-5.5、Claude Opus 4.7、Gemini 3.x 等所有旗舰模型都内置了深度思考能力，通过 `reasoning_effort` 参数控制。本文从调用方式、成本权衡到 Agent 规划层最佳实践，帮你用好这个"想得更久"的能力。

## 目录

- [从独立 SKU 到统一参数：2026 现状](#从独立-sku-到统一参数2026-现状)
- [深度思考是怎么工作的](#深度思考是怎么工作的)
- [推理模型 vs 普通 LLM：本质区别](#推理模型-vs-普通-llm本质区别)
- [主流模型深度思考能力一览（2026 现状）](#主流模型深度思考能力一览2026-现状)
- [如何调用深度思考](#如何调用深度思考)
- [什么时候该用深度思考](#什么时候该用深度思考)
- [什么时候不该用](#什么时候不该用)
- [成本与延迟的权衡](#成本与延迟的权衡)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。[主流模型对比与选型](./01-model-comparison.md)讲了如何选对模型。但旗舰模型之间还有一个关键差异：**它们“想”多久**——不是模型大小不同，而是同一型号的模型，愿意花多少 Token 在内部推理上。

2024-2025 年，这曾是一类独立产品：o1、o3、R1、QwQ 是专门的"推理模型" SKU。但到 2026 年 6 月，**所有主流旗舰都已统一**——没有独立的"推理模型"了，深度思考能力是内置功能，通过 `reasoning_effort` 参数控制。本文不讨论"什么是推理模型"（那已是历史概念），而是讨论**怎么在 Agent 开发中用好这个能力**。

## 从独立 SKU 到统一参数：2026 现状

**先讲最重要的趋势**：到 2026 年 6 月，主流闭源模型已经**没有"独立推理模型" SKU**——所有旗舰都是"统一模型 + 思考参数"。

| 时间 | 模式 | 代表 |
|------|------|------|
| 2024-2025 早期 | 两个独立 SKU：推理 vs 不推理 | GPT-4o vs o1、DeepSeek V3 vs R1 |
| **2025 末-2026** | **统一 SKU + 思考参数** | GPT-5.5 / Claude Opus 4.7 / Gemini 3.x / DeepSeek V4-Pro |

**2026 年 6 月统一状态**：

| 厂商 | 模型 | 思考控制 | 默认值 | 备注 |
|------|------|---------|-------|------|
| **OpenAI** | GPT-5.5 / GPT-5.5 Pro | `reasoning_effort`: none/low/medium/high/xhigh | medium | 5 档 |
| **Anthropic** | Claude Opus 4.6/4.7/4.8 / Sonnet 4.6 / Claude 5 | `effort`: low/medium/high/max，**adaptive thinking** | 4.6/4.7/Sonnet 4.6 auto；4.8/5 默认 high | **Claude 5 思考始终开启，不能关** |
| **Google** | Gemini 3 Flash / 3 Pro / 3.1 Pro | `reasoning_effort`: low/medium/high | low | 3 档 |
| **DeepSeek** | V4-Pro / V4-Flash | `reasoning_effort`: high/xhigh | high | 2 档，xhigh=最大思考 |
| **阿里** | Qwen3.5 / 3.6 / 3.7-Max | 内置 thinking mode，**思考上下文跨会话保留** | 开 | Apache 2.0 |
| **xAI** | Grok 4.20 Multi-Agent Beta | `reasoning_effort` | 跟随模型 | 256K 上下文 |
| **Meta** | Llama 4 Scout / Maverick | 内置思考，可配置 budget | 开 | 10M 上下文 |

**三巨头设计哲学**：

- **OpenAI**：5 档最精细，提供 `none`（彻底不思考）和 `xhigh`（极致思考）
- **Anthropic**：`max` 档独家，**adaptive thinking** 让模型自己决定怎么用预算；Claude 5 强制开启
- **Google**：3 档最简，依赖模型本身的原始速度优势

**对 Agent 框架的影响**：

```python
# 过去的 Agent：路由选模型
if is_hard_problem(q):
    model = "o1"           # 强制深度思考
else:
    model = "gpt-4o"       # 不思考

# 2026 年的 Agent：调一个参数
response = client.chat.completions.create(
    model="gpt-5.5",
    reasoning_effort="high" if is_hard_problem else "low",
    messages=[{"role": "user", "content": q}]
)
```

> 详细对比表见 [主流模型深度思考能力一览](#主流模型深度思考能力一览2026-现状)

## 深度思考是怎么工作的

**深度思考**（Deep Thinking / Reasoning）是 LLM 在生成最终答案之前，先执行内部多步推理链（Chain of Thought）的能力。

普通 LLM 的工作流程：

```
用户问题 → [一次前向传播] → 直接给出答案
```

开启深度思考后的工作流程：

```
用户问题 → [思考阶段：多步推理] → [回答阶段：基于推理结果输出]
```

这个"思考阶段"可能是几百个 Token 到几万个 Token 不等，取决于问题的复杂度和 `reasoning_effort` 档位。**思考 Token 通常计为输出 token 单价**——这是成本的主要来源。

## 推理模型 vs 普通 LLM：本质区别

### 架构层面的差异

普通 LLM 和推理模型使用的基础架构相同（都是 Transformer），但**训练目标和推理行为**有根本差异：

| 维度 | 普通 LLM | 开启深度思考 |
|------|---------|-------------|
| 训练目标 | 预测下一个词 | 先推理再回答，奖励正确答案 |
| 推理过程 | 单次前向传播 | 多次自回归生成（思维链） |
| 计算分配 | 固定（每次调用一样多） | 动态（简单问题少想，复杂问题多想） |
| 典型场景 | 聊天、翻译、写作 | 数学证明、代码调试、逻辑分析 |

### 为什么"想得更久"能变强

在 [LLM 核心能力](../02-llm-basics/04-capabilities.md) 中讲过：普通 LLM 每次预测下一个 Token 时只有**一次前向传播的计算量**。对于需要多步推理的问题（如数学计算 `34598 × 23489`），单次计算的中间状态必须全部编码进隐层向量中——信息容易丢失或混淆。

开启深度思考通过**把计算拆成多步**来解决这个问题：
- 第 1 步："先算 34598 × 20000 = 691,960,000"
- 第 2 步："再算 34598 × 3000 = 103,794,000"
- 第 3 步："...最后加起来"

每一步都是一次完整的前向传播，上一步的结果作为新的上下文进入下一步。这就像考试时允许打草稿vs只准写答案的区别。

<p align="center">
  <img src="../../assets/03-model-access/reasoning-vs-standard.png" alt="推理模型与普通模型的工作流对比" width="90%"/>
  <br/>
  <em>推理模型 vs 普通模型：单次生成 vs 多步思维链</em>
</p>

## 主流模型深度思考能力一览（2026 现状）

### OpenAI：GPT-5.5 / GPT-5.5 Pro

OpenAI 是推理模型的先驱，o1 是第一个大规模商用的推理模型（2024-09）。到 2026 年 6 月，**整个 o 产品线已并入 GPT-5.5 主线**——不再有独立的"o 系列"。

**当前状态（GPT-5.5，2026-04 发布）**：

- **5 档 `reasoning_effort`**：none / low / medium / high / xhigh
- **默认 medium**——大多数请求自动启用"思考"
- **GPT-5.5 Pro**：高阶版本，提供更激进的思考深度

**调用示例**：

```python
from openai import OpenAI
client = OpenAI()

# 低档思考：快速分类、提取
resp = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "判断这段文本情感极性"}],
    reasoning_effort="low"
)

# 高档思考：复杂推理
resp = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "证明根号 2 是无理数"}],
    reasoning_effort="high"
)

# 极致思考：异步任务、关键决策
resp = client.chat.completions.create(
    model="gpt-5.5-pro",
    messages=[{"role": "user", "content": "为一个 7x7 棋盘设计最优开局策略"}}],
    reasoning_effort="xhigh"
)
```

**注意**：默认 medium 意味着**每个普通请求都会思考**——计算成本比 2024 年的 GPT-4o 高。预算敏感场景需要显式设 `reasoning_effort="low"`。

### Anthropic：Claude Opus 4.6/4.7/4.8 + Sonnet 4.6 + Claude 5

Anthropic 的方案叫 **Extended Thinking（扩展思考）**。到 2026 年，**整个 Claude 4.6+ 系列都使用 adaptive thinking**——你设预算，模型自己决定怎么花。

**当前状态**：

| 模型 | `effort` 档位 | 默认 | 关键特性 |
|------|-------------|------|---------|
| **Claude Opus 4.6** | low/medium/high/max | auto | adaptive thinking 首发 |
| **Claude Opus 4.7** | low/medium/high/max/xhigh | auto | 加 xhigh 档 |
| **Claude Opus 4.8** | low/medium/high/max/xhigh | high | 默认 high |
| **Claude Sonnet 4.6** | low/medium/high | auto | 中端平衡 |
| **Claude 5** | low/medium/high/max | high | **思考始终开启，无法关闭** |

**调用示例（Opus 4.7）**：

```python
import anthropic
client = anthropic.Anthropic()

# 简单任务：low effort，几乎不思考
message = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=4096,
    thinking={"type": "enabled", "budget_tokens": 1024},  # ~1K token 思考预算
    messages=[{"role": "user", "content": "提取这段文本的所有 URL"}]
)

# 复杂任务：high effort，让模型用满预算
message = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 16000},
    messages=[{"role": "user", "content": "分析这段代码的并发安全 bug"}]
)

# 思维块和正文分开返回
for block in message.content:
    if block.type == "thinking":
        print(f"[思考]: {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"[回答]: {block.text}")
```

**adaptive thinking 的特别说明**：你给的是**预算（budget_tokens）**，不是"思考 X 步"。模型自己决定用多少。给 16K 不代表一定用 16K——可能简单问题只用了 2K，难题用满。

**特别说明 Claude 5**：思考**始终开启**，无法关闭。`effort=none` 不会关闭思考，模型继续以服务端默认思考。

### Google：Gemini 3 Flash / 3 Pro / 3.1 Pro

Google 的方案最简洁——3 档 `reasoning_effort`：

| 变体 | 上下文 | 档位 | 适用 |
|------|--------|------|------|
| **Gemini 3 Flash** | 1M | minimal/low/medium/high | 速度之王，284 token/s |
| **Gemini 3 Pro** | 1M | low/medium/high | 长上下文 + 推理 |
| **Gemini 3.1 Pro** | 1M+ | low/medium/high | 2026 年中最新 |

**调用示例**：

```python
from google import genai

client = genai.Client(api_key="...")

# 低档思考
resp = client.models.generate_content(
    model="gemini-3-flash",
    contents="总结这篇文章",
    config={"reasoning_effort": "low"}
)

# 高档 + 超长上下文
resp = client.models.generate_content(
    model="gemini-3-pro",
    contents="分析这份 500 页 PDF 的所有法律风险",
    config={"reasoning_effort": "high"}
)
```

**Gemini 3.5 Flash 优势**：速度是 GPT-5.5 的 4 倍（284 vs 75 token/s）+ 极低成本（输入 $1.5/M）。高并发低延迟场景首选。

### DeepSeek V4-Pro / V4-Flash（2026-04）

开源端仍然保留"普快 vs 高推理"双 SKU 模式，但**也用 `reasoning_effort` 切档**：

| 模型 | 激活参数 | 上下文 | 价格（输出 \$/M）| reasoning_effort |
|------|---------|--------|----------------|-----------------|
| **V4-Pro** | 1.6T 总 / 49B 激活 | 1M | $2.60 | high / xhigh（xhigh=max）|
| **V4-Flash** | 284B 总 / 13B 激活 | 1M | $0.20 | high / xhigh |

**调用示例**：

```python
from openai import OpenAI  # 兼容 OpenAI API
client = OpenAI(base_url="https://api.deepseek.com/v1")

resp = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[{"role": "user", "content": "..."}],
    reasoning_effort="xhigh"  # max reasoning
)
# 响应中 reasoning_content 字段包含思维链
print(resp.choices[0].message.reasoning_content)  # 思考过程
print(resp.choices[0].message.content)           # 最终答案
```

**R1 的历史价值**：R1（2025-01）首创纯 RL（GRPO）训练，证明了"无需 SFT 也能涌现长思维链"——这个发现影响了整个行业。R1 已并入 V4-Pro。

### 阿里 Qwen3.5 / 3.6 / 3.7-Max

阿里保留独立推理模型系列（**Qwen3.7-Max** 为 2026 国产新王者），同时在普通版本里内置 thinking mode：

| 模型 | 特点 | 推理能力 | 开源 |
|------|------|---------|------|
| **Qwen3.5-397B** | 17B 激活 MoE + GDN | 内置思考 | Apache 2.0 |
| **Qwen3.6 27B** | 密集 27B + 多模态 | **思考上下文跨会话保留** | Apache 2.0 |
| **Qwen3.6-Max-Preview** | 闭源旗舰 | 顶级 | 闭源 |
| **Qwen3.7-Max** | 2026-05 阿里云峰会发布，国产 Arena 第一 | 顶级 | 闭源 |

**Qwen3.6 27B 独特卖点**：思考上下文**跨会话保留**——你下午开始的思考，明天打开继续。这是其他模型没有的。

### 其他重要模型

#### Kimi K2.6（月之暗面）

Kimi K2.6 是开源长文本标杆：

- **1T 总 / 32B 激活 MoE**，1M 上下文
- **AA Intelligence Index 开源第一**
- **200 万 token 上下文**（Kimi 自家闭源版本）
- 价格 ~$2.50/M 输出

#### Grok 4.20 Multi-Agent Beta（xAI）

- **多智能体协作**：内置 4 个 Grok 实例互相辩论，输出更鲁棒
- **256K 上下文**
- **幻觉率最低**之一（"hallucination-resistant research agents"）

#### GLM-5.1（智谱）

- **最大 MIT 协议开源旗舰**
- 企业级推理 + 中文技术场景强

#### Llama 4 Scout / Maverick（Meta）

- **10M token 上下文**（Scout）——史上最长
- 内置思考 + 1000 万 token 让"整库单次推理"成为可能

### 深度思考能力全景对比（2026-06）

| 模型 | 厂商 | 思考参数 | 档位 | 上下文 | 价格（输出 \$/M）| 核心特色 |
|------|------|---------|------|--------|----------------|---------|
| **GPT-5.5** | OpenAI | `reasoning_effort` | 5 档 | 1M | $30 | 三巨头最精细档位 |
| **GPT-5.5 Pro** | OpenAI | `reasoning_effort` | 5 档 + xhigh | 1M | $180 | 极致思考 |
| **Claude Opus 4.7** | Anthropic | `effort` | 4 档 + xhigh | 1M | $25 | adaptive thinking + max 档 |
| **Claude 5** | Anthropic | `effort` | 4 档 | — | — | 思考始终开启 |
| **Gemini 3 Pro** | Google | `reasoning_effort` | 3 档 | 1M | — | 长文档推理 |
| **Gemini 3.5 Flash** | Google | `reasoning_effort` | 4 档（含 minimal）| 1M | $1.5 | **速度之王** 284 t/s |
| **DeepSeek V4-Pro** | DeepSeek | `reasoning_effort` | 2 档 | 1M | $2.60 | **最强开源** |
| **DeepSeek V4-Flash** | DeepSeek | `reasoning_effort` | 2 档 | 1M | $0.20 | **极致性价比** |
| **Qwen3.7-Max** | 阿里 | 内置 | — | 1M | — | 国产 Arena 第一 |
| **Qwen3.6 27B** | 阿里 | 内置 | — | 262K | $3.20 | 思考跨会话保留 |
| **Kimi K2.6** | 月之暗面 | 内置 | — | 1M | $2.50 | AA Index 开源第一 |
| **Grok 4.20** | xAI | `reasoning_effort` | — | 256K | — | 多智能体辩论 |
| **Llama 4 Scout** | Meta | 内置 | budget 控制 | **10M** | 自部署 | 史上最长上下文 |
| **GLM-5.1** | 智谱 | 内置 | — | 200K | — | MIT 协议 |

<p align="center">
  <img src="../../assets/03-model-access/reasoning-models-landscape.png" alt="推理模型全景图" width="90%"/>
  <br/>
  <em>2026 推理模型全景图</em>
</p>

## 如何调用深度思考

### 统一调用模式（2026 版）

**核心原则**：到 2026 年 6 月，调用深度思考的统一模式是——**选一个支持 `reasoning_effort` 的旗舰模型 + 设置档位**。

```python
def call_with_reasoning(model, question, effort="medium"):
    """
    2026 年统一调用模式：模型 + reasoning_effort
    model: "gpt-5.5" | "claude-opus-4-7" | "gemini-3-pro" | "deepseek-v4-pro"
    effort: "none" / "low" / "medium" / "high" / "xhigh"
    """
    from openai import OpenAI
    client = OpenAI()

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
        reasoning_effort=effort
    )

    # OpenAI 兼容格式：reasoning_content（思考）+ content（答案）
    if hasattr(resp.choices[0].message, 'reasoning_content'):
        print(f"[思考]: {resp.choices[0].message.reasoning_content[:200]}...")

    return resp.choices[0].message.content


# 调用示例
print(call_with_reasoning("gpt-5.5", "证明根号 2 是无理数", effort="high"))
print(call_with_reasoning("gemini-3-flash", "总结这段文本", effort="low"))
```

### Anthropic 特殊处理（adaptive thinking）

Anthropic 用 `budget_tokens` 而非档位：

```python
import anthropic

client = anthropic.Anthropic()

# 简单任务：1K token 预算
message = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=4096,
    thinking={"type": "enabled", "budget_tokens": 1024},
    messages=[{"role": "user", "content": "提取 URL"}]
)

# 复杂任务：16K token 预算
message = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 16000},
    messages=[{"role": "user", "content": "分析并发 bug"}]
)

# 思维块单独返回
for block in message.content:
    if block.type == "thinking":
        print(f"[思考]: {block.thinking[:200]}...")
    elif block.type == "text":
        print(f"[回答]: {block.text}")
```

### 注意事项

- **思考 Token 按输出 token 计费**：所有主流厂商都把思考 token 计入输出 token 价格。`reasoning_effort=high` 的成本可能是 `=low` 的 5-10 倍。
- **延迟差异显著**：`=low` 几秒，`=xhigh` 可能 30-60 秒。异步任务用高档，同步任务用低档。
- **Temperature 必须低**：深度思考建议 `temperature=0` 或接近 0——高 temperature 干扰推理链一致性。
- **不要手动写 CoT**：2026 年的模型已经会自己思考，prompt 里写"step by step"反而**干扰内部推理**——浪费 thinking budget。

## 什么时候该用深度思考

### 明确适合的场景

| 场景 | 示例 | 为什么需要深度思考 |
|------|------|------------------|
| 数学计算 | 复杂算术、方程求解、概率统计 | 多步精确运算，不能靠概率猜测 |
| 代码调试 | 定位 bug 原因、分析报错堆栈 | 需要追踪执行路径和多文件关联 |
| 逻辑分析 | 法律条款对比、合同审查 | 长链条条件判断 |
| 科学推理 | 实验设计、假设验证 | 需要系统性排除错误假设 |
| Agent 规划器 | 决定工具调用顺序、处理分支条件 | 多步决策，每步依赖上一步 |

### Agent 开发中的最佳位置

深度思考最适合放在 **Agent 的规划层（Planner）**：

```python
# Agent 核心循环中的分层策略

def agent_loop(user_input):
    # 1. 意图识别 → 小模型（快）
    intent = classify_intent(user_input)  # Haiku / Flash

    # 2. 规划 → 深度思考（准）
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

**规划层是整个 Agent 最不能出错的地方**——如果规划错了，后面所有工具调用都白费。所以这里值得花更多的时间和 Token 用深度思考。

## 什么时候不该用

深度思考不是万能的。以下场景用它纯属浪费钱和时间：

- **简单问答**："Python 的列表怎么去重？"→ 普通模型 1 秒搞定，深度思考要 5-8 秒
- **文本生成**：写邮件、翻译、摘要 → 深度思考不会写得更好，只会更慢
- **高并发低延迟场景**：客服聊天、实时推荐 → 延迟要求 < 2s，深度思考做不到
- **创意任务**：写诗、头脑风暴 → 深度思考的"严谨"反而限制创造力
- **格式化任务**：JSON 提取、数据清洗 → 小模型就够用

**简单判断标准**：如果一个问题你能在 30 秒内心算出答案，那大概率不需要深度思考。

## 成本与延迟的权衡

用一个具体例子说明成本差异（基于 2026-06 数据）：

假设你的 Agent 每天处理 1000 个查询，其中 20% 需要深度推理：

| 方案 | 推理查询成本 | 普通查询成本 | 日总成本 | 平均延迟 |
|------|------------|------------|---------|---------|
| **全用 GPT-5.5 @ low** | $0.75 | $3.00 | $3.75 | ~2s |
| **全用 GPT-5.5 @ high** | $7.50 | $7.50 | $15.00 | ~25s |
| **全用 DeepSeek V4-Flash** | $0.20 | $0.20 | $0.20 | ~3s |
| **混合策略**（GPT-5.5 high + Flash） | $7.50（200个）| $0.20（800个）| **$7.70** | ~8s |
| **全用 Claude Opus 4.7** | $6.25 | $6.25 | $6.25 | ~15s |

**关键洞察**：

- **DeepSeek V4-Flash** 是极致性价比——同能力下比 GPT-5.5 便宜 30-150 倍
- **混合策略** 比"全用旗舰"更经济——用 Flash 处理 80% 普通任务，用 GPT-5.5 high 处理 20% 关键任务
- **思考 budget 是最大成本杠杆**——同一模型，`high` 比 `low` 贵 10 倍

**生产环境 Agent 系统几乎都采用多模型路由**——按问题难度动态分配模型和 effort 档位。

## 总结

- **核心趋势（2026 现状）**：主流闭源模型已**没有"独立推理模型" SKU**——所有旗舰都是"统一模型 + `reasoning_effort` 参数"
- **三巨头档位设计**：OpenAI 5 档（none/xhigh）、Anthropic 4 档 + adaptive thinking（max 档独家，Claude 5 思考始终开启）、Google 3 档最简
- **三档映射**：
  - **GPT-5.5 / 5.5 Pro**（OpenAI）— 5 档最精细，Pro 提供 $180/M 极致档
  - **Claude Opus 4.6/4.7/4.8 + Sonnet 4.6 + Claude 5**（Anthropic）— adaptive thinking 首发
  - **Gemini 3 Flash / 3 Pro / 3.1 Pro**（Google）— 3 档最简，Flash 速度之王（284 t/s）
- **开源三强**：
  - **DeepSeek V4-Pro**（最强开源，$2.60/M）+ **V4-Flash**（极致性价比，$0.20/M）
  - **Qwen3.7-Max**（国产 Arena 第一）+ **Qwen3.6 27B**（Apache 2.0，思考跨会话保留）
  - **Kimi K2.6**（AA Index 开源第一，1M 上下文）
  - **Llama 4 Scout**（史上最长 10M 上下文）
- **其他重要模型**：Grok 4.20（多智能体辩论）、GLM-5.1（最大 MIT 开源旗舰）
- **Agent 最佳实践**：用旗舰模型 + `reasoning_effort` 动态调节，不路由不同模型
- **不该用的场景**：简单问答、文本生成、高并发低延迟、创意任务——用了就是浪费
- **成本意识**：思考 Token 按输出计费，`high` 比 `low` 贵 5-10 倍；DeepSeek V4-Flash 比 GPT-5.5 便宜 30-150 倍
- **Prompt 警告**：不要在 prompt 里写"step by step"——会干扰 2026 模型的内部推理，浪费 thinking budget

> 掌握了模型选型和深度思考的使用，云端 API 也已经会调了。但如果你的数据不能出内网呢？请前往 [模型本地部署实战](./06-local-deployment.md)。

## 参考链接

- [OpenAI — Reasoning Models Guide](https://platform.openai.com/docs/guides/reasoning) — GPT-5.5 reasoning_effort 官方指南
- [Anthropic — Adaptive Thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking) — Claude 4.6+ adaptive thinking 文档
- [Anthropic — Extended Thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) — Claude 旧版扩展思考文档
- [Google — Gemini Thinking](https://ai.google.dev/gemini-api/docs/thinking) — Gemini 3.x 思考模式文档
- [DeepSeek-R1 Technical Report](https://arxiv.org/abs/2501.12948) — R1 纯 RL 训练的原始论文
- [Inspect AI — Reasoning](https://inspect.aisi.org.uk/reasoning.html) — 跨厂商 reasoning_effort 映射参考
- [Best LLMs May 2026](https://futureagi.com/blog/best-llms-may-2026) — 2026 年 5 月模型对比快照
