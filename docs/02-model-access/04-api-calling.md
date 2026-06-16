# LLM API 调用实战

> OpenAI 的 API 格式已成为行业标准，本文以 Python 为例，展示基础调用、流式输出、多模型统一调用和生产级错误处理。

## 目录

- [事实标准：OpenAI API 格式](#事实标准openai-api-格式)
- [基础调用示例](#基础调用示例)
- [流式输出（Streaming）](#流式输出streaming)
- [多模型统一调用（LiteLLM）](#多模型统一调用litellm)
- [错误处理与重试](#错误处理与重试)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。模型选好了，接下来就是写代码把它调通。

好消息是，你不需要为每个模型学习一套新的 API。在 LLM 领域，**OpenAI 的 API 格式已经成为了事实上的行业标准**。绝大多数开源模型（如 DeepSeek、Qwen）和云服务商（如硅基流动、Groq）都完全兼容 OpenAI 的 SDK。

本篇将以 Python 为例，展示如何优雅、健壮地调用 LLM API。

## 事实标准：OpenAI API 格式

一个标准的对话请求（Chat Completions）包含两个核心部分：`model` 和 `messages`。

`messages` 是一个数组，里面包含不同角色的消息：
- `system`：系统提示词，用于设定 Agent 的角色和行为规范。
- `user`：用户的输入。
- `assistant`：模型的回复（在多轮对话中，你需要把模型之前的回复也放进数组里传回去）。

## 基础调用示例

首先安装官方 SDK：
```bash
pip install openai
```

最基础的调用代码：

```python
import os
from openai import OpenAI

# 初始化客户端
# 如果调用其他兼容厂商（如 DeepSeek），只需修改 base_url 和 api_key
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    # base_url="https://api.deepseek.com/v1"  # 切换到 DeepSeek
)

response = client.chat.completions.create(
    model="gpt-4o", # 或者 "deepseek-chat"
    messages=[
        {"role": "system", "content": "你是一个资深的 Python 工程师，回答要简明扼要。"},
        {"role": "user", "content": "解释一下什么是 Python 的装饰器？"}
    ],
    temperature=0.7,
    max_tokens=500
)

# 提取并打印回复内容
print(response.choices[0].message.content)
```

## 流式输出（Streaming）

在实际产品中，LLM 生成长文本可能需要几秒甚至十几秒。为了不让用户干等，我们必须使用**流式输出（Streaming）**——模型生成一个字，前端就显示一个字。

在 API 中，只需要加上 `stream=True`：

<p align="center">
  <img src="../../assets/02-model-access/api-streaming-flow.png" alt="流式输出时序图" width="90%"/>
  <br/>
  <em>流式输出（Streaming）完整时序</em>
</p>

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "写一首关于春天的长诗。"}],
    stream=True  # 开启流式输出
)

# response 现在是一个生成器（generator）
for chunk in response:
    # 每次提取增量的文本片段
    content = chunk.choices[0].delta.content
    if content is not None:
        print(content, end="", flush=True)
```

## 多模型统一调用（LiteLLM）

虽然大多数厂商兼容 OpenAI 格式，但 Anthropic (Claude) 和 Google (Gemini) 有自己独立的 SDK。如果你想在代码里无缝切换所有模型，推荐使用 **LiteLLM**。

LiteLLM 是一个轻量级的代理库，它把所有厂商的 API 都包装成了 OpenAI 的格式。

```bash
pip install litellm
```

```python
from litellm import completion
import os

# 设置各家 API Key
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

# 调用 GPT-4o
response1 = completion(
    model="gpt-4o",
    messages=[{"role": "user", "content": "你好"}]
)

# 代码完全不用改，只需换个模型名字，就能调用 Claude
response2 = completion(
    model="claude-3-5-sonnet-20240620",
    messages=[{"role": "user", "content": "你好"}]
)
```

在构建复杂的 Agent 系统时，LiteLLM 能帮你极大地简化模型路由（Model Routing）的代码。

<p align="center">
  <img src="../../assets/02-model-access/api-call-flow.png" alt="API 调用流程" width="90%"/>
  <br/>
  <em>API 调用流程：从客户端请求到模型响应</em>
</p>

## 错误处理与重试

在生产环境中调用 API，网络波动和限流（Rate Limit）是家常便饭。你必须加上重试机制。

OpenAI SDK 默认自带了重试机制（默认重试 2 次），但如果你想更精细地控制，可以使用 `tenacity` 库：

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import openai

@retry(
    stop=stop_after_attempt(3), # 最多重试 3 次
    wait=wait_exponential(multiplier=1, min=2, max=10), # 指数退避：等 2s, 4s, 8s
    reraise=True
)
def call_llm_with_retry(messages):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            timeout=30 # 设置超时时间
        )
        return response.choices[0].message.content
    except openai.RateLimitError:
        print("触发限流 (429)，准备重试...")
        raise
    except openai.APIConnectionError:
        print("网络连接失败，准备重试...")
        raise
    except openai.APIError as e:
        print(f"API 内部错误: {e}")
        raise

# 调用
result = call_llm_with_retry([{"role": "user", "content": "你好"}])
```

## 总结

- **OpenAI API 格式是事实标准**——绝大多数厂商兼容，一套代码走天下
- **流式输出是产品必备**——加 `stream=True`，用户体验立刻提升一个档次
- **LiteLLM 解决多模型统一调用**——换个模型名就能切换 Claude/GPT/Gemini
- **生产环境必须加重试**——网络波动和限流是家常便饭，指数退避是标配

> 代码调通了，但你可能注意到了 `temperature`、`max_tokens` 这些参数。它们到底怎么影响模型输出？请前往 [关键参数与调优](./06-key-parameters.md)。

## 参考链接

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat) — 官方 API 文档
- [LiteLLM Documentation](https://docs.litellm.ai/docs/) — 多模型统一调用神器
- [Tenacity Documentation](https://tenacity.readthedocs.io/en/latest/) — Python 重试库
