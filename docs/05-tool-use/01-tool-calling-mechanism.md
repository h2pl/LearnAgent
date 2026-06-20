# 工具调用机制与原理

> 工具调用（Tool Use）让 LLM 从"只会说话"变成"能动手"——输出结构化指令调用外部函数，获取实时数据，执行真实操作。这是 Agent 区别于 Chatbot 的核心能力。

## 目录

- [没有工具调用，Agent 什么都做不了](#没有工具调用agent-什么都做不了)
- [从 Function Calling 到 Tool Use](#从-function-calling-到-tool-use)
- [工具调用的完整流程](#工具调用的完整流程)
- [工具选择的架构基础](#工具选择的架构基础)
- [三大平台的实现差异](#三大平台的实现差异)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [Prompt 工程](../04-prompt-engineering/README.md) 中，你了解了如何精确控制 LLM 的输出。但如果 Agent 只能生成文本，它的能力就被关在笼子里——无法查天气、无法调 API、无法操作数据库。这篇文章解决核心问题：**工具调用如何让 LLM 与外部世界交互，执行真实操作**。

**工具调用（Tool Use）** 是指 LLM 在生成回复的过程中，识别出需要外部能力时，输出一段结构化数据（通常是 JSON），由你的代码解析并执行对应的函数，最后将结果返回给模型继续处理。这是 Agent 从"对话"走向"行动"的关键机制。

## 没有工具调用，Agent 什么都做不了

LLM 本质上是一个文本生成器。它的参数在预训练完成后就固定了——无法查天气、无法读数据库、无法发邮件。工具调用赋予 Agent 三种突破文本边界的能力：

1. **实时信息获取**：查天气、读数据库、检索最新文档。训练数据有截止日期，而工具调用让信息永远新鲜。

2. **精确计算与代码执行**：LLM 不擅长数学计算，但可以通过调用计算器工具精确执行；不擅长代码执行，但可以调用代码沙箱运行并获取结果。

3. **状态变更**：从"查询"到"操作"——发邮件、创建工单、修改配置。这是 Agent 从被动响应转向主动执行的关键。

这也是为什么工具调用是 Agent 区别于 Chatbot 的核心能力：Chatbot 只能对话，Agent 能行动。

## 从 Function Calling 到 Tool Use

OpenAI 在 2023 年 6 月首次推出 **Function Calling** 时，这是一个 API 层面的参数：你在请求中传入函数定义，模型决定是否需要调用。2024 年后，各平台统一改用 **Tool Use** 这个术语，但核心机制不变——模型输出结构化指令，外部系统执行。

**术语演变反映的是认知升级**：早期叫"Function Calling"容易让人误以为只是"让模型调用函数"；而"Tool Use"更准确——LLM 本身并不执行任何代码，它只是在概率分布的约束下，生成一段描述"该用什么工具、传什么参数"的文本。真正的执行发生在你的代码里。

这种设计是刻意的安全边界。LLM 无法直接访问网络或文件系统，所有外部操作必须经过你的代码审核。模型的角色是**决策器**（决定调用什么），你的代码是**执行器**（决定执行什么、怎么执行）。

## 工具调用的完整流程

<img src="../../assets/05-tool-use/tool-calling-flow.svg" alt="工具调用完整流程：定义→选择→执行→回传四阶段" width="95%"/>

一次完整的工具调用包含四个阶段，像接力赛一样环环相扣：

### 1. 定义（Definition）

你向 LLM 提供可用工具的清单，每个工具包含名称、功能描述和参数结构（JSON Schema）。

```python
# 这段代码定义了一个查询天气的工具
weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如\"北京\""
                }
            },
            "required": ["city"]
        }
    }
}
```

**关键事实**：工具定义会消耗 Token。每个工具定义通常占用 100-300 tokens，10 个工具就是 1500-3000 tokens 的额外开销。生产系统必须做工具筛选，只发送当前对话相关的工具。

### 2. 选择（Selection）

模型收到用户请求后，在自回归生成过程中判断是否需要调用工具。这个判断不是"思考"的结果，而是 SFT 训练建立的**条件概率映射**在起作用——用户输入的语义与 Schema 描述文本匹配，概率最高的工具被选中输出。具体的架构机制参见下一节 [工具选择的架构基础](#工具选择的架构基础)。

如果模型判断需要工具，它会停止正常文本生成，输出一段结构化的工具调用请求：

```json
{
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": "{\"city\": \"上海\"}"
            }
        }
    ]
}
```

### 3. 执行（Execution）

你的代码接收到工具调用请求后，解析函数名和参数，执行实际的函数，并将结果返回。这一步完全在你的控制之下——你可以做参数校验、权限检查、超时控制。

```python
# 这段代码执行工具调用并返回结果
def execute_tool_call(tool_call):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    
    if name == "get_weather":
        return get_weather(**args)  # 调用真实 API
    # ... 其他工具
```

### 4. 回传（Observation）

执行结果以消息形式重新注入对话上下文，模型基于这个新信息继续生成最终回复。

```python
# 将工具执行结果回传给模型
messages.append({
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "上海当前天气：多云，26°C，湿度 65%"
})

# 再次调用模型，生成最终回复
response = client.chat.completions.create(
    model="gpt-4.1",
    messages=messages,
    tools=[weather_tool]
)
```

**这四个阶段构成一个循环**：用户请求 → 模型选择工具 → 代码执行 → 结果回传 → 模型生成回复。这个循环可以重复多次，形成**多轮工具调用链**。

<p align="center">
  <img src="../../assets/05-tool-use/tool-calling-sequence.svg" alt="工具调用时序图：用户、Agent、LLM、执行器、外部API之间的交互序列" width="95%"/>
</p>

## 工具选择的架构基础

工具选择是工具调用中最关键、也最容易出问题的一步。理解了"模型为什么能选对工具"，你就知道为什么有些场景下模型选错工具——以及如何规避。

### 训练阶段：SFT 建立条件概率

工具选择不是"模型理解了用户意图然后决定调用什么"，而是 SFT 阶段学习的统计规律在起作用。OpenAI、Anthropic、Google 在 SFT 数据中构造了数十万条"用户请求 + 工具 Schema + 工具调用 JSON"的三元组。模型在优化过程中编码了这样一条规则：**当用户输入的语义与某个工具 Schema 的 description 字段匹配时，在 tool_calls 位置输出对应工具名的条件概率最高**。

这就是为什么 description 字段是工具定义中最重要的部分——它不是给人看的注释，是给模型看的"语义锚点"。description 中多一个关键词或少一个关键词，会显著改变选择概率分布。

### 推理阶段：概率采样而非"决定"

推理时，模型拿到用户输入和 N 个工具的 Schema 后，在自回归生成 `tool_calls` 字段时计算每个工具的条件概率 P(tool_i | user_input, schema_1, ..., schema_N)，然后按平台规则采样（通常是 argmax 或低温度下的 top-1）。

这意味着：

- **Schema 越相似，模型越容易选错**——两个工具的 description 高度重叠时，条件概率接近，采样结果不稳定
- **用户输入越模糊，模型越依赖 description 的具体措辞**——description 中的关键词会显著影响选择
- **模型不"思考"是否需要工具**——是否进入工具调用模式本身也是概率驱动的，受 system prompt 和工具列表的影响

### 能力边界：描述质量决定准确率

理解了这一架构，就能解释常见的选错工具问题：

- description 写"查询天气"，用户问"上海今天多少度"：匹配度高，正确选择
- 两个工具的 description 都包含"天气""气象"等关键词，用户问"上海天气怎么样"：两个 description 都匹配，模型随机选，可能选错
- description 写"获取某城市天气信息"，但用户问"明天会下雨吗"：description 关键词不命中，模型可能不调用工具或选错

OpenAI 2024 年的研究显示，工具数量超过 20 个时，选择准确率会显著下降；description 的措辞差异在 ±10% 内时，模型选错率上升约 3 倍。

**核心结论**：工具选择准确率的上限由 description 质量决定。这就是为什么 [02 — 工具 Schema 设计](./02-tool-schema-design.md) 是整个工具调用章节的核心——它解决的就是怎么写好 description，让模型选对工具。

### 对开发者的影响

理解"工具选择 = 概率采样"后，你的工程实践应该这样调整：

1. **每个工具的 description 必须独特**——避免关键词重叠，宁可写长一点
2. **description 用"做什么"而不是"是什么"**——前者匹配用户意图（"查询实时天气"），后者匹配分类（"天气工具"）
3. **生产环境必须有工具调用日志**——记录模型选了哪个、top-3 概率分布，出问题时能快速定位
4. **不要给模型太多工具**——超过 20 个工具后必须做工具筛选（详见 [03 — 多工具编排](./03-multi-tool-orchestration.md)）

理解了这个概率机制，下一节看不同平台如何基于同一架构实现各自的 API——为什么 OpenAI / Anthropic / Google 工具调用 API 形态各不相同。

## 三大平台的实现差异

2026 年，OpenAI、Anthropic、Google 三家都支持工具调用，但实现细节有差异。理解这些差异对跨平台开发很重要。

| 特性 | OpenAI | Anthropic | Google Gemini |
|------|--------|-----------|---------------|
| 参数结构 | JSON Schema | JSON Schema | JSON Schema |
| 并行调用 | ✅ 原生支持 | ✅ 原生支持 | ✅ 原生支持 |
| 工具选择模式 | `auto` / `required` / `none` | `auto` / `any` / `tool` | `AUTO` / `ANY` / `NONE` |
| 结果回传格式 | `tool` role | `user` role + `tool_result` | `functionResponse` |

**OpenAI 的演进**：2025-2026 年，OpenAI 将新能力的默认载体从 Chat Completions 迁移到 **Responses API**。工具调用在新 API 中更简洁——`tool` 角色直接承载结果，无需额外的格式包装。Chat Completions 仍保留作为兼容层，但新功能优先在 Responses API 上发布。

**Anthropic 的扩展**：Claude 的 Tool Use 支持并行工具调用和结构化的消息流（`tool_use` / `tool_result` 消息块），允许多个工具结果清晰地注入对话上下文。Claude 还引入了 **Extended Thinking**（扩展思考），让推理模型在工具调用前进行更深入的内部推理。

**Google 的整合**：Gemini 将工具调用与**Function Calling**原生集成在模型推理层，支持在生成过程中动态决定工具调用时机，延迟更低。

**跨平台开发建议**：使用 **LiteLLM** 或 **OpenAI Agents SDK** 的 MCP 客户端作为抽象层，屏蔽底层差异。这些工具在 2025-2026 年已成熟，能将不同平台的工具调用格式统一为 OpenAI 风格。

## 总结

- **工具调用不是模型在执行代码**，而是模型生成结构化指令，你的代码负责执行。这是安全边界的设计。
- **完整流程四步走**：定义工具 → 模型选择 → 代码执行 → 结果回传。这个循环可以重复多次。
- **工具定义消耗 Token**，生产系统必须做筛选，避免向模型发送无关工具。
- **2026 年三大平台已收敛**：都支持 JSON Schema、并行调用、工具选择模式。跨平台开发用 LiteLLM 或 MCP 客户端抽象。
- **工具调用是 Agent 的"手"**：它让 LLM 从文本生成器变成能与外部世界交互的行动体。

> 了解了工具调用的机制，下一步要解决的是：**怎么设计工具描述，让模型准确理解每个工具的用途、选对工具、传对参数**？请继续阅读 [工具 Schema 设计](./02-tool-schema-design.md)。

## 参考链接

- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use Overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview)
- [Google Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [MCP Specification](https://modelcontextprotocol.io/)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [LiteLLM Documentation](https://docs.litellm.ai/)
