# Prompt 调试与评估

> Prompt 写完不是结束——没有评估就没有优化，调试和评估是把 Prompt 从"凭感觉"变成"可量化、可回滚"的关键工程能力。这一篇讲方法论、指标、LLM-as-Judge 实战和迭代闭环。

## 目录

- [为什么需要调试与评估](#为什么需要调试与评估)
- [黄金用例集：测试集如何构建](#黄金用例集测试集如何构建)
  - [用例来源与覆盖度](#用例来源与覆盖度)
  - [用例的标注规范](#用例的标注规范)
- [评估方法：人评 vs LLM-as-Judge](#评估方法人评-vs-llm-as-judge)
  - [三种评估方式对比](#三种评估方式对比)
  - [什么时候用哪种](#什么时候用哪种)
- [LLM-as-Judge 实战](#llm-as-judge-实战)
  - [评分 Prompt 设计](#评分-prompt-设计)
  - [代码实现](#代码实现)
  - [LLM-as-Judge 的陷阱](#llm-as-judge-的陷阱)
- [A/B 测试：对比两个 Prompt](#ab-测试对比两个-prompt)
  - [配对对比法](#配对对比法)
  - [用 LLM 做偏好判断](#用-llm-做偏好判断)
- [回归测试：保证改动不破坏现状](#回归测试保证改动不破坏现状)
- [Prompt 迭代闭环](#prompt-迭代闭环)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面五篇讲了 Prompt 的设计模式、结构化输出、System Prompt、鲁棒性——这些解决了"**怎么写好一个 Prompt**"。但真正在生产环境跑起来，你会遇到新的问题：改了一个 Prompt，老用户的问题突然答错了；新加的 few-shot 示例让某类问题的准确率上去了，另一类却下降了；同一段 Prompt 不同时间效果有波动……

这篇文章回答一个工程问题：**如何系统化地评估、调试、迭代你的 Prompt？** 四个核心模块：黄金用例集是你的测试基准，人评 vs LLM-as-Judge 是评估手段，A/B 测试和回归测试保证改动可控，迭代闭环把整个流程串起来。这一篇补上 Prompt 工程化能力的最后一块——从"凭感觉写"进化到"用数据驱动迭代"。

## 为什么需要调试与评估

**Prompt 优化是连续动作，不是写完就结束。** 同一个 Prompt 在不同模型上效果不同，同一个模型在不同时间也可能因版本更新而行为漂移。生产环境里，Prompt 是会被反复修改的代码——而修改必须有评估支撑，否则就是在赌运气。

三类典型场景说明为什么必须做评估：

| 场景 | 没评估的后果 |
|------|------------|
| **新版本上线** | 改了一个词，发现某类请求的准确率从 90% 掉到 60%，等到用户投诉才发现 |
| **多模型切换** | 同一个 Prompt 在 Claude 和 GPT 上效果差异巨大，没有指标无法判断"哪个更适合这个场景" |
| **团队协作** | A 同事改了 Prompt，B 同事在另一个任务上做改动，两人互不知情，叠加起来导致整体回退 |

**评估是 Prompt 工程从"手艺"走向"工程"的转折点。** 没有评估的 Prompt 优化是玄学；有了评估，每一步改动都有数据支撑，团队协作也有共同语言。

<p align="center">
  <img src="../../assets/04-prompt-engineering/prompt-iteration-loop.png" alt="Prompt 迭代闭环" width="90%"/>
  <br/>
  <em>Prompt 迭代闭环：假设 → 改动 → 评估 → 对比 → 决策</em>
</p>

## 黄金用例集：测试集如何构建

**黄金用例集（Golden Set）是一组带有期望输出的代表性输入，是 Prompt 评估的基准。** 没有黄金用例集，所有"Prompt 变好了"的主观判断都不可信。

### 用例来源与覆盖度

用例集不是越大越好，关键是**覆盖度**——能代表你真实业务中遇到的所有典型场景。一个 50 条但分布合理的用例集，比 500 条全是一类问题的用例集更有效。

| 来源 | 比例建议 | 价值 |
|------|---------|------|
| **真实生产日志** | 50% | 代表真实用户意图，最有价值 |
| **人工构造的边界 case** | 30% | 异常输入、恶意注入、模糊问题 |
| **从失败案例反推** | 20% | 历史上让 Prompt 答错的同类变体 |

**覆盖度的三个维度**：

- **意图覆盖**：核心场景（订单查询、问题诊断、闲聊）每类都有用例
- **难度覆盖**：简单 case、中等 case、困难 case（长上下文、多轮、反问）各占一定比例
- **语言/格式覆盖**：中英文、Markdown/JSON/纯文本、含图片/不含图片

### 用例的标注规范

每条用例至少包含三个字段：

```python
# 单条用例的最小结构
golden_case = {
    "id": "case_001",                              # 唯一标识，便于追踪
    "input": "我想退掉昨天买的耳机",                # 用户输入（与生产一致）
    "expected_intent": "refund_request",           # 期望的意图/分类
    "expected_fields": ["order_id"],               # 期望输出中必须包含的字段
    "tags": ["refund", "user_with_history"],       # 多维度标签，便于分组分析
}
```

**标注的"严松"选择**：

| 严格度 | 适用场景 | 标注成本 |
|-------|---------|---------|
| **严格匹配**（输出必须完全一致） | 分类、路由、提取固定字段 | 高，需要枚举所有合法输出 |
| **字段匹配**（关键字段存在即可） | 信息抽取、结构化输出 | 中，定义必含字段即可 |
| **语义匹配**（含义正确即可） | 开放式回答、文本生成 | 低，可由 LLM 辅助标注 |

**推荐**：能用严格匹配就别用语义匹配——前者是确定的、可重复的；后者有评估噪声。语义匹配留给真正开放的任务。

## 评估方法：人评 vs LLM-as-Judge

### 三种评估方式对比

| 方式 | 速度 | 成本 | 准确性 | 适用阶段 |
|------|------|------|-------|---------|
| **规则评估** | 极快 | 极低 | 中（只能检查规则覆盖的） | 格式、关键词、长度 |
| **LLM-as-Judge** | 中 | 中（需调用 LLM） | 中高（取决于 Prompt 设计） | 日常迭代、回归测试 |
| **人评** | 慢 | 高 | 高 | 关键决策、新 Prompt 首次评估 |

### 什么时候用哪种

- **开发阶段**：规则评估 + LLM-as-Judge。快速迭代，每次改 Prompt 几小时内就能得到反馈
- **上线前**：人评 + LLM-as-Judge 双重验证。关键场景必须有真人抽样检查
- **上线后**：规则评估（监控告警）+ 定期抽样人评。日常自动监控，每周抽样人评保证评估质量不漂移

## LLM-as-Judge 实战

**LLM-as-Judge 是用一个大模型（如 Claude Opus）评估另一个模型（如 GPT-5.5）的输出。** 核心假设是：评估比生成更容易，所以评估模型可以比被评估模型弱一档，但仍能可靠地判断质量。

### 评分 Prompt 设计

**关键原则：给评估模型明确的、原子化的评分维度。** 不要写"请评估这个回答好不好"——模型会根据自己的偏好给分，结果不稳定。

```python
# LLM-as-Judge 评分 Prompt（推荐结构）
JUDGE_PROMPT = """你是一个严格的输出质量评估员。请按以下维度对【待评估输出】评分（1-5 分）：

## 1. 准确性（accuracy）
- 5 = 所有事实完全正确，无任何编造
- 3 = 大部分正确，有 1-2 处小错
- 1 = 存在明显的事实错误或幻觉

## 2. 格式合规（format_compliance）
- 5 = 完全符合期望的 JSON Schema/输出结构
- 3 = 主要结构正确，有 1-2 处字段缺失或多余
- 1 = 完全不符合期望格式

## 3. 指令遵循（instruction_following）
- 5 = 完全遵循 system prompt 中的所有约束
- 3 = 遵循主要约束，忽略 1-2 个次要约束
- 1 = 明显违反 system prompt 的核心约束

## 4. 简洁性（conciseness）
- 5 = 表达精炼，无冗余
- 3 = 略有冗余但不影响理解
- 1 = 大量冗余或答非所问

【用户输入】: {user_input}
【期望输出】: {expected_output}
【待评估输出】: {actual_output}

请先逐项打分（每项 1-5），然后给一个综合分（加权平均，准确性权重最高）。
最后用一行说明打分理由。

输出格式（严格 JSON）：
{
  "accuracy": <int>,
  "format_compliance": <int>,
  "instruction_following": <int>,
  "conciseness": <int>,
  "overall": <float>,
  "reason": "<one line>"
}
"""
```

### 代码实现

```python
import json
from openai import OpenAI

client = OpenAI()

def llm_judge(user_input: str, expected: str, actual: str) -> dict:
    """用 LLM 评估另一个 LLM 的输出"""
    prompt = JUDGE_PROMPT.format(
        user_input=user_input,
        expected_output=expected,
        actual_output=actual
    )

    resp = client.chat.completions.create(
        model="gpt-5.5",  # 用更强的模型做评估
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},  # 强制 JSON 输出
    )

    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 评估模型偶尔会返回非 JSON，记录下来便于排查
        return {"error": "invalid_json", "raw": raw}


def evaluate_prompt(prompt_func, golden_set: list) -> dict:
    """对一组黄金用例跑评估，返回汇总指标"""
    scores = []
    for case in golden_set:
        actual = prompt_func(case["input"])
        judgment = llm_judge(case["input"], case["expected_intent"], actual)
        scores.append(judgment)

    # 汇总：各维度平均分 + 整体通过率（overall >= 4 算通过）
    summary = {
        "total": len(scores),
        "avg_accuracy": sum(s.get("accuracy", 0) for s in scores) / len(scores),
        "avg_format": sum(s.get("format_compliance", 0) for s in scores) / len(scores),
        "avg_overall": sum(s.get("overall", 0) for s in scores) / len(scores),
        "pass_rate": sum(1 for s in scores if s.get("overall", 0) >= 4) / len(scores),
    }
    return summary
```

### LLM-as-Judge 的陷阱

LLM-as-Judge 不是万能的。**已知偏差**：

| 偏差 | 表现 | 缓解方法 |
|------|------|---------|
| **位置偏差** | 倾向于给第一个出现的回答打高分 | 随机交换两个回答的位置，跑两次取平均 |
| **长度偏差** | 倾向于给更长的回答打高分 | 在 Prompt 中明确"拒绝冗长回答，给 5 分" |
| **自我偏好** | 评估模型倾向于给同系列模型的输出打高分 | 评估模型用与被评估模型不同厂商的（如 Claude 评 GPT） |
| **Prompt 敏感性** | 评分 Prompt 改动一个字，结果就漂移 | 评分 Prompt 锁定版本，每次评估用同一份 |

**核心原则：LLM-as-Judge 是相对指标，不是绝对指标。** 用来判断"Prompt A 比 Prompt B 好"是可靠的；用来判断"这个 Prompt 得了 4.2 分，绝对好不好"是不可靠的。

<p align="center">
  <img src="../../assets/04-prompt-engineering/llm-as-judge-pipeline.png" alt="LLM-as-Judge 评估流水线" width="90%"/>
  <br/>
  <em>LLM-as-Judge 评估流水线：黄金用例集 → 实际输出 → 评分 Prompt → 评估模型 → 指标</em>
</p>

## A/B 测试：对比两个 Prompt

**A/B 测试是把两个 Prompt 放在同一组用例上跑，比较哪个更好。** 这是 Prompt 优化最高频的操作——每次想到一个改进点，先 A/B 测试看是不是真的更好。

### 配对对比法

```python
def ab_test(prompt_a, prompt_b, golden_set: list) -> dict:
    """配对 A/B 测试：同一用例两个 Prompt 都跑，看胜率"""
    wins = {"a": 0, "b": 0, "tie": 0}

    for case in golden_set:
        out_a = prompt_a(case["input"])
        out_b = prompt_b(case["input"])

        # 让评估模型判断哪个更好（包含位置交换以消除位置偏差）
        winner_first = compare_pair(case["input"], out_a, out_b, "A", "B")
        winner_second = compare_pair(case["input"], out_b, out_a, "B", "A")

        # 只有两次判断一致才计入
        if winner_first == "A" and winner_second == "B":
            wins["a"] += 1
        elif winner_first == "B" and winner_second == "A":
            wins["b"] += 1
        else:
            wins["tie"] += 1

    total = len(golden_set)
    return {
        "a_win_rate": wins["a"] / total,
        "b_win_rate": wins["b"] / total,
        "tie_rate": wins["tie"] / total,
        "sample_size": total,
    }
```

### 用 LLM 做偏好判断

```python
COMPARE_PROMPT = """你是一个严格的 A/B 评估员。给定同一个用户问题的两个回答，请判断哪个更好。

【用户问题】: {question}
【回答 A】: {output_a}
【回答 B】: {output_b}

判断标准（按优先级）：
1. 准确性：A 和 B 谁的事实更正确、更少幻觉
2. 格式合规：谁更符合期望的输出结构
3. 指令遵循：谁更好地遵循了 system prompt 约束
4. 简洁性：在前三个维度相当时，谁更精炼

请只输出一个字母：A 或 B，不要解释。
"""
```

**样本量要求**：A/B 测试要有统计意义，黄金用例集至少 30 条以上，否则一次结果不可信。建议跑多次取平均。

## 回归测试：保证改动不破坏现状

**回归测试的核心：保存一组"已知能答对"的用例，每次改 Prompt 都要保证这组用例继续通过。** 这是防止"修一个 bug 引入三个 bug"的关键。

```python
# 回归测试集：这些是历史证明能答对的 case
REGRESSION_CASES = [
    # 从生产日志中抽取的"标准 case"
    {"input": "我要退货", "expected_intent": "refund_request"},
    {"input": "订单还没收到", "expected_intent": "logistics_inquiry"},
    # ... 50 条经过验证的用例
]

def regression_test(prompt_func, regression_set=REGRESSION_CASES) -> bool:
    """回归测试：所有历史 case 必须仍然通过"""
    failures = []
    for case in regression_set:
        actual = prompt_func(case["input"])
        judgment = llm_judge(case["input"], case["expected_intent"], actual)
        if judgment.get("overall", 0) < 4:
            failures.append({"case": case, "judgment": judgment})

    if failures:
        print(f"回归测试失败 {len(failures)}/{len(regression_set)} 条")
        for f in failures:
            print(f"  - {f['case']['input']}: {f['judgment'].get('reason')}")
        return False
    return True
```

**回归测试的工程实践**：

- **每次 Prompt 改动前必跑**——这是最低门槛
- **回归集要持续扩充**——线上出现新 case，加进来
- **回归集和黄金集是不同概念**：回归集是"历史不能退步"，黄金集是"当前能力评估"。两者通常黄金集更大、更复杂

## Prompt 迭代闭环

**把上面的所有环节串起来，就形成了 Prompt 迭代闭环。** 这是一个数据驱动的工程化流程：

```
[1. 假设]  基于失败案例，提出改进假设（"加 few-shot 会更好"）
    ↓
[2. 改动]  在 Prompt 中实施改动
    ↓
[3. 评估]  跑黄金用例集，看整体指标变化
    ↓
[4. 对比]  跑回归测试集，确保历史能力不退步
    ↓
[5. 决策]  通过 → 上线；未通过 → 回滚，回到 [1] 重新假设
```

**关键工程纪律**：

| 纪律 | 说明 |
|------|------|
| **一次只改一个变量** | 不要同时改 Prompt 和模型——你无法判断是哪个变了 |
| **改动必须有数据支撑** | "我觉得好"不算数，必须有指标变化 |
| **失败案例要归档** | 每次 LLM-as-Judge 评出的低分 case，存进失败案例库，作为下一轮假设的输入 |
| **Prompt 版本化管理** | 每次通过评估的 Prompt 存一个版本（Git 提交或专用工具），便于回滚和对比 |

> **没有评估的 Prompt 优化是赌博**。黄金用例集 + LLM-as-Judge + A/B 测试 + 回归测试 = 把赌博变成有数据支撑的工程决策。这是 Prompt 能力从"初级"走向"高级"的分水岭。

## 总结

Prompt 调试与评估是 Prompt 工程化的最后一块拼图：

- **黄金用例集**：覆盖真实场景的代表性测试集，是评估的基准。严格匹配 > 字段匹配 > 语义匹配，能用前者就别用后者
- **三种评估方式**：规则评估（快、覆盖窄）、LLM-as-Judge（中等、覆盖广）、人评（慢、最准）。日常迭代靠 LLM-as-Judge，关键决策靠人评
- **LLM-as-Judge 实战**：原子化评分维度、用 JSON 强制输出、明确评估 Prompt 锁定版本。记住它有位置偏差、长度偏差、自我偏好——是相对指标不是绝对指标
- **A/B 测试**：配对对比 + 位置交换消除偏差，至少 30 条样本。Prompt 优化最高频的操作
- **回归测试**：保存历史能答对的 case，每次改动必跑。防止"修一个 bug 引入三个 bug"
- **迭代闭环**：假设 → 改动 → 评估 → 对比 → 决策。一次只改一个变量，改动必须有数据支撑

到这里，Prompt 工程的所有核心能力你都学完了——基础认知、设计模式、结构化输出、System Prompt、鲁棒性、调试与评估，构成了一套完整的工程化方法论。

> Prompt 工程的"内功"已成，下一步是"招式"——让 LLM 不只生成文本，而是能执行真实操作。下一章进入 [05 — 工具调用](../05-tool-use/README.md)，学习 Agent 的"动手能力"。

## 参考链接

- [Anthropic — Claude as a Judge](https://docs.anthropic.com/en/docs/build-with-claude/test-and-evaluate/strengthen-guardrails/use-claude-as-a-judge) — LLM-as-Judge 的官方实现
- [OpenAI — Evals Framework](https://github.com/openai/evals) — OpenAI 开源的评估框架
- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (2023)](https://arxiv.org/abs/2306.05685) — LLM-as-Judge 偏差的系统研究
- [Anthropic — Prompt Evaluation Guide](https://docs.anthropic.com/en/docs/build-with-claude/test-and-evaluate/strengthen-guardrails/eval-driven-development) — 评估驱动的开发方法论
- [LangSmith — Prompt Evaluation](https://docs.smith.langchain.com/) — LangChain 生态的 Prompt 评估平台
- [Promptfoo — LLM Evaluation Toolkit](https://github.com/promptfoo/promptfoo) — 开源的 Prompt A/B 测试工具
