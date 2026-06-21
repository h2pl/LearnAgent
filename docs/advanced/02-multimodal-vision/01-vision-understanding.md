# 视觉理解：让模型看懂图像与屏幕

> 视觉是 2026 年最成熟的多模态能力。本文从 API 调用到 Computer Use 架构，从成本优化到常见坑点，帮你系统掌握"让模型看懂图片和屏幕"这件事。

## 目录

- [视觉理解 API 怎么调用](#视觉理解-api-怎么调用)
- [典型任务：模型最擅长看什么](#典型任务模型最擅长看什么)
- [Computer Use：让 Agent 操控屏幕](#computer-use让-agent-操控屏幕)
- [视觉 RAG：图像作为检索的一部分](#视觉-rag图像作为检索的一部分)
- [图像 token 成本：算清楚这笔账](#图像-token-成本算清楚这笔账)
- [常见坑与应对策略](#常见坑与应对策略)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前两篇讲了多模态的全景和内部机制，从这篇开始进入具体的能力模块。视觉理解是目前所有多模态能力里最成熟的——几乎所有主流模型都支持图片输入，生产案例也最丰富。

不管你是想让 Agent 分析用户上传的截图、解读文档里的图表、还是直接操控屏幕完成任务，这篇都会覆盖到。

## 视觉理解 API 怎么调用

视觉理解的核心很简单：把图片当作消息的一部分传给模型。

### 单图理解（以 Claude API 为例）

```python
import anthropic
import base64

client = anthropic.Anthropic()

# 读取图片并编码为 base64
with open("screenshot.png", "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data,
                },
            },
            {
                "type": "text",
                "text": "这张截图里有什么？描述你看到的内容。"
            },
        ],
    }],
)
print(response.content[0].text)
```

### 多图对比

同一个请求里可以传多张图片，模型会同时理解所有图片并做对比分析：

```python
messages=[{
    "role": "user",
    "content": [
        {"type": "image", "source": {"type": "base64", ...}},  # 图 1
        {"type": "image", "source": {"type": "base64", ...}},  # 图 2
        {"type": "text", "text": "对比这两张设计稿，指出差异。"}
    ],
}],
```

### 视频帧提取

大多数模型不直接接受视频文件，需要你先抽帧再传：

```python
import cv2

def extract_frames(video_path, interval_sec=2):
    """每隔 N 秒提取一帧"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % int(fps * interval_sec) == 0:
            frames.append(frame)
        frame_count += 1

    cap.release()
    return frames
```

抽取关键帧后，把它们作为多张图片一起传给模型。注意帧数不要太多——每帧都会消耗图像 token。

### URL 方式传图

除了 base64，大多数 API 也支持直接传图片 URL：

```python
# OpenAI 格式
{
    "type": "image_url",
    "image_url": {"url": "https://example.com/image.png"}
}

# Gemini 格式：支持直接传 file_uri
```

## 典型任务：模型最擅长看什么

不同任务上模型的视觉理解能力差异很大。以下是 2026 年模型表现最好的几类任务：

### 截图分析与 UI 理解

模型能准确识别 UI 元素：按钮、输入框、导航栏、对话框。这让"Agent 操控屏幕"成为可能。

Claude Opus 4.8 在这个任务上最强——它能精确定位 UI 元素的位置坐标，输出结构化 JSON 描述界面布局。

### 文档与图表解读

合同扫描件、财务报表、流程图——模型能同时理解其中的文字、数字和空间布局。

注意：复杂表格的识别准确率还达不到 100%，尤其是合并单元格和嵌套表格。关键数据建议人工复核。

### 场景理解与视觉问答

"这张图片里有什么？" "这个人在做什么？" "图中的建筑风格是什么？"——这类开放式视觉问答是模型的基本能力，准确率很高。

### OCR 与文字提取

现代多模态模型的文字提取能力已经超越传统 OCR 工具，尤其是手写体和艺术字体。但如果你只需要纯文字提取（不需要理解图片含义），传统 OCR 工具成本更低。

### 模型不太擅长的

- 精确计数（"图里有多少个螺丝钉"——数到 10 以上就不太靠谱）
- 微小物体识别（分辨率受限 patch 粒度）
- 高度专业化的医学/科学影像（需要领域微调）

## Computer Use：让 Agent 操控屏幕

Computer Use 是视觉理解在 Agent 场景下最激动人心的应用：**让模型看到屏幕截图，决定下一步点哪里或输入什么，然后执行操作。**

### 核心循环

```
截图 → 模型分析界面 → 输出动作（点击坐标 / 输入文本 / 滚动）→ 执行 → 截图 → ...
```

每一步都是一个标准的 Agent Loop（参见[第 6 章 Agent 循环](../../06-agent-loop/README.md)），只不过感知输入从文本变成了截图。

### 架构要素

一个完整的 Computer Use 系统包含：

1. **截屏模块**：定时或按需获取屏幕截图
2. **视觉模型**：分析截图内容，理解当前界面状态
3. **决策模块**：根据用户目标和当前状态决定下一步动作
4. **执行模块**：模拟鼠标点击、键盘输入、滚动等操作
5. **安全护栏**：URL 白名单、操作确认、敏感操作拦截

### 两种主流实现

**Project Mariner（Gemini）**：Google 基于 Gemini 2.5 Pro 的浏览器操控方案。模型直接输出浏览器操作指令（点击、输入、导航），通过 Chrome Extension 执行。

**Claude Computer Use**：Anthropic 的方案，模型输出标准化的动作 JSON（如 `{"action": "click", "coordinate": [234, 567]}`），由外部框架（如 [computer-use-demo](https://github.com/anthropics/anthropic-quickstarts)）执行。

### 生产注意事项

- **每步都要确认**：至少在前几个版本，关键操作应该让用户确认
- **设置超时**：Agent 可能陷入死循环（反复点同一个地方），需要有最大步数限制
- **截图标注**：给截图加上网格坐标和元素编号，能显著提高模型的定位准确率

## 视觉 RAG：图像作为检索的一部分

传统的 RAG（检索增强生成）只检索文本。视觉 RAG 把图像也纳入检索范围——当你问一个问题时，系统不仅找到相关文档段落，还能找到相关的图片。

### 架构思路

```
用户提问 → 检索文本片段 + 检索相关图片 → 一起传给多模态模型 → 综合回答
```

关键点在于"检索图片"这一步。常见做法：

- **CLIP 嵌入**：用 CLIP 把图片编码成向量，存入向量数据库。查询时用文本生成向量，做相似度检索
- **多模态 RAG 框架**：LlamaIndex 的 `MultiModalVectorStoreIndex` 已经封装了这个流程
- **预生成描述**：先把每张图片用视觉模型生成文字描述，然后对描述做文本检索（简单但信息损失大）

这和[第 8 章 RAG](../../08-rag-pipeline/README.md)的思路完全一致，只是检索对象从纯文本扩展到了"文本 + 图像"。

## 图像 token 成本：算清楚这笔账

视觉理解最大的实际限制就是成本——图片比文字贵得多。

### 怎么算的

以 Claude 为例：
- 一张 1080×1080 的图片，大约消耗 ~1500-2000 个 token
- 一张 4K 图片可能消耗 10000+ 个 token
- 相比之下，一段 1000 字的中文文本只有约 1500 个 token

**一张高清图片的成本 ≈ 1000 字的文本。** 如果你一次传 5 张图，就等于额外增加了 5000 字的输入成本。

### 优化策略

- **缩小分辨率**：如果任务不需要细节（比如只问"这是什么场景"），把图片缩到 512×512 就够了
- **裁剪感兴趣区域**：不要把整个屏幕截图传过去，只裁切需要分析的部分
- **降低帧率**：视频分析不需要每秒一帧，2-5 秒一帧通常足够
- **缓存结果**：同一张图片多次分析时，缓存第一次的理解结果

### OpenAI 的 detail 参数

GPT-5 支持 `detail` 参数控制图像处理的精细程度：
- `low`：快速低成本，适合简单分类任务
- `high`：全分辨率处理，适合详细分析
- `auto`：模型自动判断

## 常见坑与应对策略

### 幻觉（Hallucination）

模型有时候会"看到"图片里不存在的东西。比如把图片里的模糊物体说成猫，或者编造图片中不存在的文字。

应对：用 temperature=0 降低随机性；在 prompt 中明确说"只描述你确定看到的内容"。

### 隐私泄露

用户可能上传包含敏感信息的图片（身份证、银行卡、密码输入界面）。模型会"看到"并可能在回答中泄露这些信息。

应对：上传前做敏感区域检测/模糊处理；不要将包含 PII 的图片传给外部 API。

### 图像对抗攻击

精心修改过的图片可能让模型产生完全错误的理解。虽然在 2026 年这类攻击已经减少，但在安全敏感场景下仍需注意。

应对：对高风险场景做输入校验；使用多个模型交叉验证。

### 分辨率与细节的权衡

分辨率太高成本爆炸，太低又看不清关键信息。经验法则：

- 文字提取：至少 72dpi，推荐 150dpi
- 场景理解：256×256 就够
- UI 元素定位：至少 1024×768
- 图表数据读取：至少 1080p

## 总结

视觉理解是 2026 年最成熟的多模态能力。核心要点：

- API 调用简单直接——图片当消息内容传即可，支持单图、多图、视频帧
- 典型强项是截图分析、文档解读、场景理解，精确计数和微小物体是弱项
- Computer Use 是 Agent + 视觉的最热方向，核心是"截图→推理→动作"的循环
- 视觉 RAG 把图像纳入检索范围，扩展了传统 RAG 的能力边界
- 成本是最大限制——一张图 ≈ 1000 字的文本成本，优化策略包括缩小分辨率和裁剪区域

下一篇你进入听觉维度：语音与音频。

> 下一篇：[语音与音频：让模型能听能说](../03-multimodal-speech/01-speech-and-audio.md)

## 参考链接

- [Anthropic Vision Documentation](https://platform.claude.com/docs/en/build-with-claude/vision)
- [OpenAI Vision Guide](https://platform.openai.com/docs/guides/vision)
- [Google Gemini Vision Capabilities](https://ai.google.dev/gemini-api/docs/vision)
- [Claude Computer Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)
- [LlamaIndex Multi-Modal RAG](https://docs.llamaindex.ai/en/stable/examples/multi_modal/)
- [Project Mariner (Google)](https://deepmind.google/technologies/gemini/project-mariner/)
