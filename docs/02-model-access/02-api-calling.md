# LLM 调用方式与 API 实战

> 在动手写代码之前，先搞清楚调用 LLM 有哪些方式。本文从调用方式的宏观视角出发，再深入到 OpenAI API 格式的实战细节——流式输出、多模型统一调用和生产级错误处理。

## 目录

- [调用 LLM 的四种主要方式](#调用-llm-的四种主要方式)
- [为什么 API 是 Agent 开发的首选](#为什么-api-是-agent-开发的首选)
- [事实标准：OpenAI API 格式](#事实标准openai-api-格式)
- [基础调用示例](#基础调用示例)
- [流式输出（Streaming）](#流式输出streaming)
- [多模型统一调用（LiteLLM）](#多模型统一调用litellm)
- [错误处理与重试](#错误处理与重试)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。模型选好了，接下来就是写代码把它调通。

但在打开 IDE 之前，先退一步看看全景图：**调用 LLM 到底有哪些方式？** 每种方式适合什么场景？搞清楚这个，你才能为自己的项目做出正确的技术选择。

## 调用 LLM 的四种主要方式

```
┌─────────────────────────────────────────────────────┐
│                   调用 LLM 的四种方式                  │
│                                                     │
│  1. 云端 API（HTTP/REST）                            │
│     └─ OpenAI / Anthropic / DeepSeek / Gemini       │
│     ├─ 优点：零运维、自动更新、按量付费               │
│     └─ 缺点：数据出域、延迟依赖网络、有配额限制        │
│                                                     │
│  2. SDK / 语言客户端                                 │
│     └─ openai-python / anthropic-sdk / genai         │
│     ├─ 优点：类型提示、自动重试、流式封装              │
│     └─ 缺点：绑定特定语言、版本兼容问题               │
│                                                     │
│  3. 本地推理引擎                                     │
│     └─ Ollama / vLLM / llama.cpp                    │
│     ├─ 优点：数据不出内网、无 API 费用、低延迟        │
│     └─ 缺点：需要 GPU 硬件、自己维护模型更新           │
│                                                     │
│  4. CLI / 命令行工具                                 │
│     └─ ollama run / curl 直接请求 / AI 编程助手内置   │
│     ├─ 优点：最快上手、调试方便                      │
│     └─ 缺点：不适合生产环境                          │
│                                                     │
│  详细对比 → 见 [本地部署实战](./05-local-deployment.md) │
└─────────────────────────────────────────────────────┘
```

### 方式一：云端 API（REST / HTTP）

这是最主流的方式。通过 HTTP 请求调用厂商提供的模型服务：

```
你的应用 → HTTP POST → api.openai.com/v1/chat/completions → 返回结果
```

**代表厂商**：
| 厂商 | API 端点 | 兼容格式 |
|------|---------|---------|
| OpenAI | `api.openai.com/v1` | 原生格式（行业标准） |
| Anthropic (Claude) | `api.anthropic.com/v1` | 自有格式 |
| Google (Gemini) | `generativelanguage.googleapis.com` | 自有格式 |
| DeepSeek | `api.deepseek.com/v1` | **兼容 OpenAI** |
| 硅基流动 | `api.siliconflow.cn/v1` | **兼容 OpenAI** |
| Groq | `api.groq.com/openai/v1` | **兼容 OpenAI** |

注意到一个重要趋势：**越来越多的厂商选择兼容 OpenAI 的 API 格式**。这意味着你可以用同一套代码切换不同模型。

### 方式二：SDK / 语言客户端

SDK 是对 HTTP API 的封装，提供更友好的编程接口：

```python
# Python SDK 示例（OpenAI）
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(model="gpt-4o", messages=[...])

# vs 原始 HTTP（你需要自己处理认证、序列化、错误码...）
import requests
headers = {"Authorization": f"Bearer {API_KEY}"}
response = requests.post("https://api.openai.com/v1/chat/completions", ...)
```

**主流 SDK**：
- `openai` — OpenAI 官方 Python/Node.js SDK（也被 DeepSeek、硅基流动等兼容方使用）
- `anthropic` — Claude 官方 SDK
- `google-generativeai` — Gemini 官方 SDK
- `litellm` — 统一代理 SDK（下文详细介绍）

### 方式三：本地推理引擎

数据不能出内网？想省 API 费用？本地部署是答案：

| 引擎 | 适用场景 | 上手难度 | 详情见 |
|------|---------|---------|--------|
| **Ollama** | 个人开发、原型验证 | 极低（一条命令） | [本地部署实战](./05-local-deployment.md) |
| **vLLM** | 生产服务、高并发 | 中等 | 同上 |
| **llama.cpp** | 极致轻量、嵌入式 | 较高 | 同上 |

本地引擎通常也提供 **OpenAI 兼容的 REST API**，所以切换成本很低。

### 方式四：CLI / 命令行工具

适合快速测试和调试：

```bash
# Ollama CLI
ollama run qwen2.5:7b "解释装饰器"

# 直接 curl（OpenAI 兼容格式）
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"hi"}]}'
```

## 为什么 API 是 Agent 开发的首选

对于构建 Agent 系统，**云端 API + SDK 是绝大多数情况下的最佳选择**：

| 维度 | API | 本地部署 | CLI |
|------|-----|---------|-----|
| 集成难度 | 低（SDK 封装好） | 中（需装引擎） | 高（需自行解析） |
| 可靠性 | 厂商保障 SLA | 自己负责 | 无保障 |
| 模型更新 | 自动获得最新版 | 手动下载 | 手动 |
| 扩展性 | 天然支持并发 | 受 GPU 数量限制 | 不支持 |
| 数据隐私 | 数据离场 | 数据留内 | 取决于实现 |
| 成本模式 | 按量付费 | 固定硬件投入 | 免费（但受限） |

**简单规则**：
- 原型阶段 / 个人项目 → API 最快
- 生产环境 / 数据敏感 → 本地部署
- 快速测试一个想法 → CLI 够了

接下来的内容聚焦于**最主流的方案：OpenAI 兼容格式的 API 调用**。

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

- **调用 LLM 有四种方式**：云端 API（最主流）、SDK/客户端、本地推理引擎、CLI 命令行——API + SDK 是 Agent 开发的首选
- **OpenAI API 格式是事实标准**——绝大多数厂商兼容，一套代码走天下
- **流式输出是产品必备**——加 `stream=True`，用户体验立刻提升一个档次
- **LiteLLM 解决多模型统一调用**——换个模型名就能切换 Claude/GPT/Gemini
- **生产环境必须加重试**——网络波动和限流是家常便饭，指数退避是标配

> 代码调通了，但你可能注意到了 `temperature`、`max_tokens` 这些参数。它们到底怎么影响模型输出？请前往 [关键参数与调优](./06-key-parameters.md)。

## 参考链接

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat) — 官方 API 文档
- [LiteLLM Documentation](https://docs.litellm.ai/docs/) — 多模型统一调用神器
- [Tenacity Documentation](https://tenacity.readthedocs.io/en/latest/) — Python 重试库
