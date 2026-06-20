# 结构化输出：让 LLM 输出稳定的 JSON

> LLM 的自由文本回答代码没法直接用。掌握 JSON Mode、Schema 约束和输出解析三项技术，让模型稳定地输出可被代码消费的结构化数据——这是 Agent 与工具协作的基础。

## 目录

- [为什么必须结构化](#为什么必须结构化)
- [JSON Mode：让模型只输出 JSON](#json-mode让模型只输出-json)
  - [不同平台的 JSON Mode](#不同平台的-json-mode)
  - [JSON Mode 的局限](#json-mode-的局限)
- [Schema 约束：精确控制输出结构](#schema-约束精确控制输出结构)
  - [用 Pydantic 定义 Schema](#用-pydantic-定义-schema)
  - [用 JSON Schema 定义结构](#用-json-schema-定义结构)
- [输出解析：当 JSON 不完美时](#输出解析当-json-不完美时)
  - [三层防御策略](#三层防御策略)
  - [正则提取 + 重试 + Fallback](#正则提取--重试--fallback)
- [实战：构造结构化 Agent 输出](#实战构造结构化-agent-输出)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇讲了四种 Prompt 设计模式，掌握了"怎么问"。这一篇解决一个更具体的问题：模型答了，但代码怎么消费它的回答？答案就四个字——结构化输出。

这篇文章回答一个问题：**如何让 LLM 稳定地输出 JSON（或其他结构化格式），让你的代码能可靠地解析它？** 这看起来是个格式问题，但实际上是 Agent 工程的一道分水岭——LLM 的输出如果能被代码消费，它就从"聊天机器人"变成了"可编排的计算单元"。JSON Mode 是基础，Schema 约束是进阶，输出解析是兜底。三者配合，才能把你的 Agent 接入到真实的工具链中。

## 为什么必须结构化

在 Agent 开发中，LLM 的输出不（只）是给人看的，而是给代码消费的。来看两个典型场景：

**场景一：路由 Agent**。用户说"我想退款"，Agent 需要判断意图然后路由到对应模块。它不能返回"好的我帮你退款"，而是要返回：

```json
{"intent": "refund", "confidence": 0.95, "params": {"order_id": null}}
```

**场景二：工具调用 Agent**。Agent 判断需要查天气，不能返回"当前北京气温 25 度"，而要返回一个结构化指令：

```json
{"tool": "get_weather", "arguments": {"city": "北京", "unit": "celsius"}}
```

**如果 LLM 不结构化，Agent 就不可靠。** 自由文本你需要正则、if-else 甚至再调一次 LLM 来解析——每一步都在引入不确定性。结构化输出让你能用 `json.loads()` 一行代码搞定，确定性 100%。

<p align="center">
  <img src="../../assets/04-prompt-engineering/parsing-defense.png" alt="结构化输出三层防御" width="90%"/>
  <br/>
  <em>结构化输出三层防御：JSON Mode → Schema 约束 → 输出解析</em>
</p>

## JSON Mode：让模型只输出 JSON

**JSON Mode 是各 LLM 平台提供的推理参数，强制模型输出合法的 JSON。** 这是结构化输出的第一道防线——从"大概率是 JSON"变成"保证是 JSON"。

### 不同平台的 JSON Mode

```python
# OpenAI — response_format 参数
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "列出 3 种编程语言及其特点"}],
    response_format={"type": "json_object"}  # 强制 JSON 输出
)
data = json.loads(response.choices[0].message.content)
```

```python
# Anthropic (Claude) — 通过 Prompt 引导 + 后处理
# Claude 没有独立的 JSON Mode 参数，通过 Prompt 明确要求
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": """列出 3 种编程语言及其特点。
只输出 JSON，不要包含任何其他文字：
{"languages": [{"name": "...", "feature": "..."}]}"""}]
)
# 注意：Claude 默认用 ```json 代码块包裹，需要手动提取
```

**各平台对比**：

| 平台 | JSON Mode 支持 | 方式 |
|------|--------------|------|
| OpenAI | ✅ `response_format: json_object` | API 参数直接控制 |
| Anthropic | ⚠️ 无独立参数 | Prompt 引导 + 工具调用约束（推荐） |
| Google Gemini | ✅ `response_mime_type: application/json` | API 参数 |
| 开源模型 (vLLM) | ✅ `guided_json` / `guided_regex` | 推理引擎约束 |

### JSON Mode 的局限

**JSON Mode 只能保证"是合法 JSON"，不能保证"是我想要的 JSON"。** 你可能拿到：

```json
// 期望的是字符串数组，结果拿到了对象数组
{"languages": [{"name": "Python"}, {"name": "Java"}]}
// 而不是你期望的
{"languages": ["Python", "Java", "Go"]}
```

所以 JSON Mode 只是第一道防线。要精确控制 JSON 的结构，需要 Schema 约束。

## Schema 约束：精确控制输出结构

**Schema 约束通过定义输出数据的类型、字段、枚举值，让 LLM 严格按照你的结构生成 JSON。** 这是结构化输出的核心——把"大概这格式"变成"就是这个格式"。

### 用 Pydantic 定义 Schema

在 Python 生态中，Pydantic 是定义结构化输出最自然的方式。定义一次，同时用于类型检查、LLM 输出约束和数据验证：

```python
from pydantic import BaseModel, Field
from typing import Literal

# 定义输出结构
class IntentClassification(BaseModel):
    intent: Literal["refund", "inquiry", "complaint", "other"]
    confidence: float = Field(ge=0, le=1, description="置信度 0-1")
    reason: str = Field(max_length=200)
    follow_up_action: str | None = None

# OpenAI Structured Outputs（2024 年推出的功能）
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "我想退掉上周买的商品"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "intent",
            "schema": IntentClassification.model_json_schema()
        }
    }
)
# 输出保证符合 IntentClassification 的结构
result = IntentClassification.model_validate_json(
    response.choices[0].message.content
)
print(result.intent)        # "refund"
print(result.confidence)    # 0.95
```

**Schema 约束的关键原则**：

- **用枚举而非自由文本**：`Literal["refund", "inquiry"]` 比 `str` 可靠得多——模型的选择范围被精确限定
- **加约束条件**：`Field(ge=0, le=1)` 确保 confidence 不可能是 99 或 -1
- **可选字段用 None**：`str | None` 标识这个字段可以留空
- **字段描述就是 Prompt**：`description="置信度 0-1"` 会作为提示发送给模型

### 用 JSON Schema 定义结构

如果你不用 Python 或需要跨语言兼容，直接用 JSON Schema 定义：

```python
# 通用 JSON Schema 方式
schema = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["refund", "inquiry", "complaint", "other"]
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"enum": ["product", "date", "amount", "person"]}
                },
                "required": ["name", "type"]
            }
        }
    },
    "required": ["intent", "entities"]
}

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "上周买的 iPhone 16 屏幕有坏点"}],
    response_format={"type": "json_schema", "json_schema": {
        "name": "extraction", "schema": schema
    }}
)
```

## 输出解析：当 JSON 不完美时

**即使有 JSON Mode 和 Schema 约束，LLM 的输出仍然可能出问题。** 它会偶尔在 JSON 外多写一句话、用错引号、或者漏掉闭合括号。你需要一个健壮的解析层来兜底。

### 三层防御策略

<p align="center">
  <img src="../../assets/04-prompt-engineering/parsing-defense.png" alt="三层解析防御策略" width="90%"/>
  <br/>
  <em>结构化输出的三层防御：JSON Mode → Schema 约束 → 解析兜底</em>
</p>

| 层级 | 策略 | 作用 |
|------|------|------|
| **第一层** | JSON Mode + Schema 约束 | 让模型尽量输出正确 JSON |
| **第二层** | 正则提取 + 修复 | 从混合文本中提取 JSON，修复常见错误 |
| **第三层** | 重试 + Fallback | 解析失败时带着错误信息重试，再失败用默认值 |

### 正则提取 + 重试 + Fallback

```python
import json
import re

def robust_parse(llm_output: str, retries: int = 2) -> dict:
    """健壮的 JSON 解析：提取 → 修复 → 重试 → fallback"""
    # 第一层：直接解析
    try:
        return json.loads(llm_output)
    except json.JSONDecodeError:
        pass

    # 第二层：从代码块或混合文本中提取 JSON
    for attempt in range(retries):
        # 尝试匹配 ```json ... ``` 代码块
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', llm_output, re.DOTALL)
        if match:
            llm_output = match.group(1)

        # 尝试匹配 JSON 对象 { ... }
        match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        break  # 正则修复只试一次

    # 第三层：返回安全的 fallback
    return {"error": "parse_failed", "raw_output": llm_output[:500]}
```

## 实战：构造结构化 Agent 输出

把以上三项技术组合起来，构造一个完整的"意图分类 + 实体提取"Agent 输出：

```python
from pydantic import BaseModel, Field
from typing import Literal
from openai import OpenAI

client = OpenAI()

class Entity(BaseModel):
    name: str
    type: Literal["product", "date", "amount", "person", "location"]

class AgentOutput(BaseModel):
    intent: Literal["refund", "inquiry", "complaint", "order", "other"]
    confidence: float = Field(ge=0, le=1)
    entities: list[Entity] = Field(default_factory=list)
    needs_clarification: bool = False
    summary: str = Field(max_length=100)

def classify_user_message(message: str) -> AgentOutput:
    """将用户消息分类为结构化 Agent 输出"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": "分析用户消息，提取意图和实体。confidence 基于语义确定性，'
                        '明确的退款请求 > 0.9，模糊表达 < 0.7。"
        }, {
            "role": "user",
            "content": message
        }],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "agent_output",
                "schema": AgentOutput.model_json_schema()
            }
        }
    )
    return AgentOutput.model_validate_json(
        response.choices[0].message.content
    )

# 使用
result = classify_user_message("上周在你们平台买的 iPhone 16 屏幕有坏点，我要退")
print(f"意图: {result.intent}, 置信度: {result.confidence}")
# 输出: 意图: refund, 置信度: 0.95
```

**这个 30 行函数就是 Agent 的核心组件**——它把自然语言变成了结构化的机器指令，下一步 Agent 拿到 `intent: "refund"` 就知道该调用退款流程，拿到 `entities: [{name: "iPhone 16", type: "product"}]` 就知道在哪个商品上操作。

## 总结

这篇文章解决了 Agent 开发中"让 LLM 输出可消费数据"的核心问题：

- **JSON Mode**：第一道防线，用 API 参数强制模型输出合法 JSON。但它只管格式，不管内容结构
- **Schema 约束**：核心手段，用 Pydantic 或 JSON Schema 精确定义输出的类型、字段、枚举、约束——让"合法 JSON"变成"你想要的 JSON"
- **输出解析**：兜底策略，正则提取 → 修复 → 重试 → fallback，确保代码不会因为一次 JSON 解析失败就崩溃
- **三者配合**：JSON Mode 做格式保证、Schema 做结构约束、解析器做异常兜底——缺一不可

结构化输出是 Agent 从"生成文本"到"执行操作"的桥梁。下一篇，我们把目光移到 System Prompt——如何从结构层面定义你的 Agent 的核心行为。

> 结构化输出解决了"输出格式"，但 Agent 的角色、边界和行为规范在哪里定义？接下来请阅读 [System Prompt 设计：定义 Agent 的核心行为](./04-system-prompt.md)。

## 参考链接

- [OpenAI — Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Anthropic — Tool Use (Structured Outputs)](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Pydantic — Model JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [Instructor — Structured LLM Outputs](https://python.useinstructor.com/) — 最流行的 LLM 结构化输出库
- [Outlines — Structured Generation](https://dottxt-ai.github.io/outlines/) — 通过约束解码实现结构化生成
