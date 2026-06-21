# 04 — 多模态生成：创造能力

本章从"感知"翻转到"创造"——让模型生成图像、视频和原生多模态内容。生成侧和理解侧是完全不同的技术路线（扩散模型 vs Transformer），需要单独建立认知。

## 学习路径

本章两篇文章分别覆盖专用生成和原生生成两条路径。

### 1. 图像与视频生成

[图像与视频生成](./01-image-and-video-generation.md) 先讲清楚生成侧和理解侧的根本区别，再从 API 接入、生成侧核心机制（VAE、去噪网络、文本编码器、采样算法）、条件引导、ControlNet，一路讲到视频生成、Prompt 策略和质量评估。

### 2. 原生多模态输出

[原生多模态输出](./02-native-multimodal-output.md) 讲 Gemini Imagen 3 和 GPT-5 images 这类"理解侧模型直接生成"的能力：统一 API 的优势、与专用生成模型的区别、什么时候该用哪个。

## 文章总览

| 文章 | 内容 |
|------|------|
| [图像与视频生成](./01-image-and-video-generation.md) | 扩散模型机制、API 对比、条件引导、视频生成、Prompt 策略 |
| [原生多模态输出](./02-native-multimodal-output.md) | Gemini Imagen 3、GPT-5 images、统一 API vs 专用模型 |

> 上一章：[03 — 语音与音频](../03-multimodal-speech/README.md) —— 听觉通道
>> 下一章：[05 — 多模态集成](../05-multimodal-integration/README.md) —— 把各模态串起来做综合推理和应用。
