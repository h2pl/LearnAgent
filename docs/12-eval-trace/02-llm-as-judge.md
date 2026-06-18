# LLM-as-Judge：用 LLM 做自动评测

> 人评太慢，规则评分太僵。LLM-as-Judge 用语言模型的自然语言理解能力做自动评分器——兼顾灵活性与可扩展性。

## 目录

- [为什么需要 LLM-as-Judge](#为什么需要-llm-as-judge)
- [Judge 的设计模式](#judge-的设计模式)
- [评分体系设计](#评分体系设计)
- [Judge Prompt 工程](#judge-prompt-工程)
- [校准与偏差控制](#校准与偏差控制)
- [实践案例：Agent 任务评分](#实践案例agent-任务评分)
- [工具集成](#工具集成)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇文章我们谈了评测体系的三个层次。无论是组件级还是任务级，都面临一个共同的问题：**谁来做评分？**

人评最准，但成本太高。规则评分又快又稳，但写规则的速度永远赶不上场景变化的速度。LLM-as-Judge 提供了一个折中——**用模型来评模型**。

## 为什么需要 LLM-as-Judge

传统评测方案各有局限：

| 方案 | 优势 | 劣势 |
|------|------|------|
| 人工标注 | 最准确，能理解细微差别 | 成本高、速度慢、一致性差 |
| 规则评分 | 速度快、完全一致 | 表达力有限，复杂场景写不出规则 |
| 精确匹配 | 客观可复现 | 对非确定性输出完全无效 |
| BLEU/ROUGE | 自动、标准 | 不适合开放式任务，忽略语义 |

LLM-as-Judge 的优势在于：**它"理解"输出内容**，而不是做模式匹配。适合的场景：

- 评估 Agent 的回答质量（有用性、礼貌性、完整性）
- 判断工具调用是否正确（参数值是否等价）
- 评估任务完成度（部分成功 vs 完全成功）
- 检测有害内容或 prompt injection

## Judge 的设计模式

LLM-as-Judge 有几种常见的使用模式，**按复杂度递增排列**。

### 点式评分 (Pointwise)

给定 (输入, 输出) → 输出一个分数。这是最基础的模式。

```
输入：用户问题 + Agent 回答
输出：1-5 分 + 评分理由
```

### 成对比较 (Pairwise)

给定两个输出 + 评分标准 → 输出谁更好。适合 A/B 测试。

```
输入：用户问题 + Agent A 回答 + Agent B 回答
输出：A 更好 / B 更好 / 平局 + 理由
```

### 多维评分 (Multi-Dimension)

同一输出从多个维度独立评分。这是最有实操价值的模式。

```
输入：用户问题 + Agent 回答
输出：
  - 正确性 (1-5) + 理由
  - 完整性 (1-5) + 理由
  - 安全性 (Pass/Fail)
  - 效率 (步骤是否最优)
```

**推荐默认使用多维评分**。一个维度高分但另一个维度低分的输出，比一个"平均分"输出更有信息量。

## 评分体系设计

评分体系需要平衡**表达能力**和**一致性**。以下是推荐的实践。

### 评分维度

针对 Agent 评测，建议包含以下维度：

| 维度 | 定义 | 评测对象 |
|------|------|----------|
| 任务达成 | 用户的核心目标是否完成 | 最终输出 |
| 轨迹效率 | 步骤数是否合理，是否最优路径 | 执行日志 |
| 工具使用 | 工具选择、参数、调用顺序是否正确 | 中间步骤 |
| 安全合规 | 是否触犯安全规则、输出是否合规 | 所有内容 |
| 用户体验 | 回答是否友好、清晰、易于理解 | 最终输出 |

### 评分量表

建议使用 **5 分量表 + 锚点定义**：

| 分 | 标记 | Agent 任务示例 |
|----|------|---------------|
| 5 | 完美 | 任务完成，路径最优，无任何问题 |
| 4 | 良好 | 任务完成，但有小的改进空间 |
| 3 | 合格 | 主要目标达成，有次要问题但不严重 |
| 2 | 不足 | 主要目标未达成但有部分进展 |
| 1 | 失败 | 完全偏离目标 |

5 分制比 3 分制更有区分度，又比 10 分制更容易保持标注一致性。

## Judge Prompt 工程

**Judge prompt 本身需要打磨**，就像你打磨 Agent 的 system prompt 一样。

### 标准 Judge Prompt 模板

```
你是一个专业的 AI Agent 评测员。请根据以下标准对 Agent 的表现评分。

## 任务描述
{task_description}

## 用户输入
{user_input}

## Agent 执行轨迹
{trajectory}

## Agent 最终回答
{agent_response}

## 评分标准
1. 任务达成 (1-5)：用户的目标是否完成？
   - 5：完美达成，无任何遗漏
   - 3：主要达成，有细节遗漏
   - 1：未达成
2. 轨迹效率 (1-5)：
   - 5：最少步骤实现最优路径
   - 3：有冗余步骤但不影响结果
   - 1：存在死循环或严重绕路

## 输出格式
```json
{{
  "scores": {{
    "task_completion": <int>,
    "trajectory_efficiency": <int>
  }},
  "reasoning": "对各维度的详细评分理由",
  "issues": ["列出的具体问题（如果有）"]
}}
```

请先思考再评分，确保理由充分。
```

### 关键技巧

**给 Judge 看轨迹而不是只看结果**。一个"回答正确但路径绕了 10 步"的 Agent 和一个"3 步搞定"的 Agent，评分应该不同。

**要求 Judge 输出理由**。这是最重要的质量控制手段。理由能帮你发现 Judge 是否理解错了任务、看漏了细节。

**使用 Few-shot 示例**。每个分数等级给一个参考示例，能显著提升评分一致性。

**让 Judge 慢思考**。在 prompt 中加入"请逐步分析后再打分"，类似 Chain-of-Thought，能提升评分准确率。

## 校准与偏差控制

LLM-as-Judge 不是完美的。它有系统性的偏好需要校准。

### 常见偏差

| 偏差 | 表现 | 缓解方法 |
|------|------|----------|
| 自肥偏差 | 对自己喜欢的模型输出评分偏高 | 盲评（隐藏模型来源） |
| 位置偏差 | 成对比较中偏好第一个或最后一个输出 | 多次比较交换顺序 |
| 长度偏差 | 偏好更长的输出 | 在评分标准中加入简洁度维度 |
| 严厉/宽松偏差 | 同一 Judge 对类似输出评分不一致 | 使用更细粒度的评分锚点 |
| 身份偏差 | 对不同角色的回答有系统性偏好 | 确保 Judge 的角色中立 |

### 校准方法

**定期做人类校验**。随机抽样 10% 的 LLM-as-Judge 评分，让人类重新标注，计算人-模型一致性：一致性 > 80% 说明 Judge 可靠，低于 70% 需要调整 prompt。

**使用多 Judge 投票**。多个不同的 LLM（如 GPT-4o + Claude + Gemini）同时对同一输出评分，取多数投票或平均分，能显著提升可靠性。

**反向验证**。对于"满分"或"零分"的输出，定期抽查确认并非 Judge 误判。

## 实践案例：Agent 任务评分

以下是一个实际的 Agent 评测用例：

**任务**：用户想取消"明天下午3点"的会议，同时把"后天上午10点"的会议改到下午2点。

**Agent 响应**（简化）：

```
1. cancel_event(event_id="evt_001")
   → 成功取消
2. query_events(time_range="后天")
   → 找到 event_id="evt_002"（后天 10:00）
3. reschedule_event(event_id="evt_002", new_time="后天14:00")
   → 成功改期
```

**LLM-as-Judge 评分**：

- 任务达成：5/5（两件事都做了，而且对的）
- 轨迹效率：5/5（先查询再改期，合理顺序）
- 工具使用：5/5（先查 event_id 再操作，正确做法）

如果 Agent 在第一步需要用户先提供 event_id 而不主动查询——这就是一个"能做但不够好"的案例，任务达成可能 4/5，效率 3/5。

## 工具集成

已有成熟的工具支持 LLM-as-Judge 工作流：

- **LangSmith**: 内置 annotation queue，支持手动标注 + LLM-as-Judge 自动评分
- **Langfuse**: 支持 manual scoring 和 model-based scoring
- **OpenAI Evals**: 开源框架，提供多种预设评测器和模板
- **DeepEval**: 专为 LLM 评测设计的开源库，支持 14+ 评测指标

<details>
<summary>LangSmith 自动评测配置示例</summary>

```python
from langsmith.evaluation import evaluate
from langsmith.schemas import Example, Run

# 定义 LLM-as-Judge 评测器
def agent_quality(run: Run, example: Example) -> dict:
    client = OpenAI()
    messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": f"输入：{example.inputs['input']}"},
        {"role": "assistant", "content": f"Agent 输出：{run.outputs['output']}"}
    ]
    response = client.chat.completions.create(
        model="gpt-4o", messages=messages
    )
    return json.loads(response.choices[0].message.content)

# 执行评测
results = evaluate(
    agent_func,
    data="my_dataset",
    evaluators=[agent_quality]
)
```
</details>

## 总结

LLM-as-Judge 是目前最实用的自动评测方案。它不完美，但在**性价比上远超人工标注和规则评分**。

核心要点：多维评分优于单维、点式优于成对（但成对适合 A/B）、5 分量表优于 3 分或 10 分、Judge prompt 需要持续迭代。

**下一篇**：可观测性与全链路追踪——当评测发现问题时，怎么定位到具体环节。

## 参考链接

- [LM Evaluation Harness](https://github.com/EleutherAI/lm-evaluation-harness)
- [Anthropic — LLM-as-Judge Best Practices](https://docs.anthropic.com/en/docs/test-and-evaluate/evaluate)
- [LangSmith — LLM-as-Judge](https://docs.smith.langchain.com/evaluation/llm-as-judge)
- [DeepEval Documentation](https://docs.confident-ai.com/)
- [OpenAI — Using GPT-4 as Evaluator](https://openai.com/index/using-gpt-4-as-an-evaluator/)
- [Position Bias in LLM-as-Judge](https://arxiv.org/abs/2310.07629)
