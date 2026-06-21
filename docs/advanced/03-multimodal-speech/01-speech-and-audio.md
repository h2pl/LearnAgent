# 语音与音频：让模型能听能说

> 语音是最自然的交互通道。2026 年的 Realtime API 已经让"语音进、语音出"变得生产可用。本文从基础概念到架构设计，帮你掌握语音交互的工程实现。

## 目录

- [STT 与 TTS：语音的两端](#stt-与-tts语音的两端)
- [Realtime API：语音交互的范式变革](#realtime-api语音交互的范式变革)
- [语音 Agent 的核心循环](#语音-agent-的核心循环)
- [中断与打断：最难处理的问题](#中断与打断最难处理的问题)
- [语音 + 工具调用](#语音--工具调用)
- [本地 vs 云端：怎么选](#本地-vs-云端怎么选)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇讲了视觉——模型怎么"看"。这篇我们聊"听"和"说"。语音交互听起来只是"把打字换成说话"，但实际实现起来复杂度完全不同：延迟敏感、流式处理、打断处理、情绪感知……每一个都是文本交互中不存在的新问题。

好消息是，2026 年的语音 AI 基础设施已经相当成熟。OpenAI 的 Realtime API 和 Gemini 的 Live API 都实现了亚秒级的语音对话延迟。这篇帮你把这些能力用起来。

## STT 与 TTS：语音的两端

在讲实时语音交互之前，先搞清楚语音最基础的两个能力。

### STT（Speech-to-Text）：让模型听懂

STT 就是把语音转成文字。2026 年最成熟的方案是 OpenAI 的 Whisper 和 Google 的 Gemini 原生音频理解。

```python
# OpenAI Whisper API
from openai import OpenAI

client = OpenAI()
with open("audio.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
    )
print(transcript.text)
```

Whisper 的特点是准确率高、支持多语言、但延迟不适合实时对话。如果你只是需要把一段录音转成文字，Whisper 就是最好的选择。

Gemini 的原生音频理解更进一步——不需要先转文字，模型直接理解音频内容（包括语气、情绪、停顿）。这在需要理解"说话方式"的场景下很有用。

### TTS（Text-to-Speech）：让模型说话

TTS 把文字变成语音。2026 年的 TTS 已经非常自然，支持多种声音风格、情感表达和多语言。

```python
# OpenAI TTS API
response = client.audio.speech.create(
    model="tts-1-hd",
    voice="nova",
    input="你好，这里是语音助手，请问有什么可以帮您？",
)
response.stream_to_file("output.mp3")
```

关键参数：
- `model`：`tts-1`（速度快）vs `tts-1-hd`（质量高）
- `voice`：预设声音（alloy, echo, fable, onyx, nova, shimmer）
- `speed`：语速控制（0.25 到 4.0）

## Realtime API：语音交互的范式变革

传统语音交互是三步串行：STT（语音→文字）→ LLM（文字→文字）→ TTS（文字→语音）。总延迟 = STT延迟 + LLM延迟 + TTS延迟，通常在 3-5 秒。

**Realtime API 打破了这个串行链路。** 模型直接接收音频流、直接输出音频流，不需要中间的文本转换。延迟降低到 500ms-1s，接近人类自然对话的节奏。

### 架构：WebSocket + 流式音频

Realtime API 通过 WebSocket 实现双向流式通信：

```python
import asyncio
import websockets
import json

async def realtime_session():
    uri = "wss://api.openai.com/v1/realtime?model=gpt-5-realtime"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(uri, additional_headers=headers) as ws:
        # 发送会话配置
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": "nova",
                "instructions": "你是一个友好的语音助手。",
            }
        }))

        # 持续发送音频输入，接收音频输出
        async for message in ws:
            event = json.loads(message)
            if event["type"] == "response.audio.delta":
                # 播放收到的音频片段
                play_audio(event["delta"])
```

### VAD（语音活动检测）

VAD 是 Realtime API 的关键能力：**自动检测用户什么时候开始说话、什么时候停止。**

- 用户开始说话 → VAD 检测到 → 开始录音
- 用户停止说话 → VAD 检测到静音 → 结束录音，开始处理
- 用户持续说话 → 继续录音，不打断

VAD 的灵敏度可以调节。太灵敏会在用户思考停顿时误判为"说完了"，太迟钝则会让用户觉得模型反应慢。

```json
{
    "type": "session.update",
    "session": {
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500
        }
    }
}
```

### Gemini Live API 对比

Gemini 的 Live API 架构类似，但有一些差异：

- 支持**原生视频输入**（可以同时传视频流和音频流）
- 音频输出支持**情感风格控制**（更欢快、更严肃等）
- 上下文窗口更长（1M token），适合长对话
- 延迟表现和 GPT-5 Realtime API 在同一水平

## 语音 Agent 的核心循环

语音 Agent 和文本 Agent 的核心循环本质上是同一个 Agent Loop（参见[第 6 章](../../06-agent-loop/README.md)），但输入输出换成了音频：

```
用户说话 → VAD 检测结束 → 模型处理 → 输出语音
   ↑                                        ↓
   └──────── 用户听到回答后继续说话 ←─────────┘
```

### 关键差异

和纯文本 Agent 相比，语音 Agent 有几个额外维度需要处理：

**延迟极其敏感**：文本对话中 3 秒延迟可以接受，语音对话中超过 1 秒用户就会觉得"卡了"。这意味着：
- 优先用 Realtime API 而非 STT+LLM+TTS 拼接
- 如果必须拼接，用流式 TTS（边生成边播放）

**情绪和语调**：模型输出的不只是文字内容，还有说话方式。"很抱歉"这三个字，用平淡语气和用关切语气说出来，体验完全不同。

**多轮上下文**：语音对话天然是多轮的，而且用户说话往往不完整（"那个……就是上次那个……"）。模型需要更强的上下文理解能力。

## 中断与打断：最难处理的问题

语音交互中最棘手的问题：**用户说到一半或模型说到一半时，用户插话了。**

### 场景 1：用户打断模型的输出

模型正在回答问题，用户突然说"等一下"或"不是这个意思"。

处理策略：
- 立即停止当前音频输出
- 丢弃未播放的音频缓冲区
- 把用户的新输入作为新一轮交互的开始
- 把之前已经输出的内容记入上下文

```python
# Realtime API 中的中断处理
if event["type"] == "input_audio_buffer.speech_started":
    # 用户开始说话了 → 立即停止当前输出
    await ws.send(json.dumps({
        "type": "response.cancel"  # 取消当前生成
    }))
    # VAD 会自动处理后续
```

### 场景 2：用户说话中途修改

用户说"帮我订明天……不对，后天的机票"。

这需要模型理解用户的自我纠正。2026 年的 Realtime 模型已经能较好地处理这种情况，因为它们在训练中见过大量自然对话数据。

### 场景 3：多人对话中的定向

如果有多个说话人，需要区分"谁在和 Agent 说话"。这是更高级的问题，目前 Gemini Live API 提供了 speaker diarization（说话人分离）能力。

## 语音 + 工具调用

语音 Agent 也可以调用外部工具——用户说"帮我查一下明天的天气"，Agent 调用天气 API 然后用语音回答。

### 实现方式

在 Realtime API 中，工具调用的流程：

```
用户语音提问 → 模型判断需要调工具 → 输出 function_call 事件
→ 你的代码执行工具 → 把结果返回给模型 → 模型用语音回答
```

```python
# 注册工具
await ws.send(json.dumps({
    "type": "session.update",
    "session": {
        "tools": [{
            "type": "function",
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                }
            }
        }]
    }
}))

# 处理工具调用事件
if event["type"] == "response.function_call_arguments.done":
    result = call_weather_api(event["arguments"])
    await ws.send(json.dumps({
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": event["call_id"],
            "output": json.dumps(result),
        }
    }))
```

这和文本场景下的工具调用（参见[第 5 章](../../05-tool-use/README.md)）逻辑完全一样，只是传输层换成了 WebSocket + 音频流。

## 本地 vs 云端：怎么选

语音模型有本地部署和云端 API 两种选择，各有适用场景。

### 云端（Realtime API / Live API）

**适合**：需要最高质量、最低延迟的场景；对话质量是关键指标的产品。

**优势**：
- 延迟最低（500ms-1s 首音频 token）
- 模型质量最高
- 不需要 GPU 基础设施

**劣势**：
- 成本按音频时长计费
- 隐私敏感数据需要过第三方服务器
- 依赖网络稳定性

### 本地部署

**适合**：隐私敏感场景、高频调用需要控制成本、离线场景。

**可用模型**：
- **Whisper**（本地 STT）：开源、准确率高、延迟可接受
- **Piper / Kokoro**（本地 TTS）：开源、声音自然、延迟低
- **本地小 LLM + STT/TTS 拼接**：延迟较高但成本可控

**劣势**：
- 对话质量不如云端 Realtime API
- 需要 GPU 或较好的 CPU
- 延迟通常比云端高

### 混合方案（推荐）

大多数生产场景的最佳实践是混合方案：

- **STT 用本地 Whisper**：免费、准确、隐私安全
- **推理用云端 LLM**：质量最高
- **TTS 用云端 HD 声音**：质量最好
- 如果延迟要求极高（<1s），切换到 Realtime API 全程云端处理

## 总结

语音交互是 2026 年最成熟的多模态交互方式之一。核心要点：

- STT/TTS 是基础能力，各有成熟方案（Whisper / OpenAI TTS / ElevenLabs）
- Realtime API 是范式变革——直接音频进音频出，延迟降到亚秒级
- 语音 Agent 的循环和文本 Agent 相同，但对延迟、中断、情绪有额外要求
- 打断处理是最大挑战——需要 VAD + 缓冲区管理 + 上下文记忆配合
- 工具调用在语音场景下逻辑不变，只是传输层不同
- 本地 vs 云端取决于延迟要求和隐私需求，混合方案是最佳实践

下一篇我们进入"创造"维度：图像与视频生成。

> 下一章：[图像与视频生成：让模型创造视觉内容](../03-multimodal-generation/01-image-and-video-generation.md)

## 参考链接

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [Google Gemini Live API](https://ai.google.dev/gemini-api/docs/live)
- [OpenAI Whisper Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [OpenAI Text-to-Speech Guide](https://platform.openai.com/docs/guides/text-to-speech)
- [WebRTC vs WebSocket for Realtime AI](https://getstream.io/blog/multimodal-ai-agents/)
- [Kokoro TTS (Open Source)](https://github.com/hexgrad/kokoro)
