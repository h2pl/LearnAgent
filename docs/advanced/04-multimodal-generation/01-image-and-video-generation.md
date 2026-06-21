# 图像与视频生成：让模型创造视觉内容

> 前几篇讲的是模型怎么"看懂"世界。这篇反过来——模型怎么"创造"视觉内容。从 DALL-E 到视频生成，本文帮你理解图像生成的原理、API 接入和工程决策。

## 目录

- [生成侧：一条完全不同的技术路线](#生成侧一条完全不同的技术路线)
- [图像生成 API 接入](#图像生成-api-接入)
- [视频生成：2026 年的现状](#视频生成2026-年的现状)
- [生成侧核心机制：从噪声到图像](#生成侧核心机制从噪声到图像)
- [条件引导：怎么控制生成内容](#条件引导怎么控制生成内容)
- [ControlNet：精确控制生成](#controlnet精确控制生成)
- [何时生成 vs 何时检索](#何时生成-vs-何时检索)
- [Prompt 工程：怎么让 Agent 写出好的生成指令](#prompt-工程怎么让-agent-写出好的生成指令)
- [质量评估与审核](#质量评估与审核)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面讲了视觉理解（看）和语音交互（听说），这篇进入"创造"维度——让模型生成图片和视频。

在[两条技术路线](../01-multimodal-fundamentals/04-two-tech-routes.md)已经讲过，多模态 AI 有两条完全不同的技术路线。理解侧用的是 Transformer 架构，生成侧用的是扩散模型架构。两者从训练方式到推理过程都截然不同。这篇会系统讲清楚生成侧的完整机制，而不只是"够用就好"。

## 生成侧：一条完全不同的技术路线

在讲 API 之前，先把生成侧和理解侧的关系讲清楚。

[编码](../01-multimodal-fundamentals/06-encoding.md)、[融合](../01-multimodal-fundamentals/07-fusion.md)和[对齐](../01-multimodal-fundamentals/08-alignment-and-representation.md)讲了理解侧的三个核心机制。这些机制服务于 Transformer 架构，目标是"把多模态输入变成文字输出"。

生成侧（图像/视频生成）用的是完全不同的技术栈：

| 维度 | 理解侧（Transformer） | 生成侧（扩散模型） |
|------|---------------------------|----------------------------|
| 核心任务 | 看懂图片/音频 → 输出文字 | 输入文字 → 创造图片/视频 |
| 核心架构 | Transformer + 感知编码器 | VAE + 去噪网络 + 文本编码器 |
| 推理过程 | 一次前向传播（快） | 20-50 步迭代去噪（慢） |
| 计算瓶颈 | 注意力计算（与序列长度平方成正比） | 去噪步数（步数越多质量越高但越慢） |
| 训练数据 | 图文配对 + 指令微调 | 大规模图像/视频 + 文字描述 |
| 典型延迟 | 0.5-3 秒 | 3-30 秒（图片）/ 1-5 分钟（视频） |

关键点：**即使你用的是同一个厂商的产品（比如 GPT-5 既能理解图片也能生成图片），底层也是两套独立的引擎在跑。** 理解用的是 GPT-5 的 Transformer，生成用的是 DALL-E 3 的扩散模型。它们之间不共享模型权重，只是通过 API 层统一调度。

理解了这个区别，你就会明白为什么：
- 理解和生成的延迟差这么多
- 两个能力的 API 是分开的
- 计费方式不同（token vs 张数/时长）
- 优化策略不同（理解优化 token 成本，生成优化采样步数）

接下来先讲 API 接入（实际使用），再深入生成侧的内部机制。

## 图像生成 API 接入

2026 年主流的图像生成服务都提供了简单易用的 API。

### DALL-E 3（OpenAI）

```python
from openai import OpenAI

client = OpenAI()

response = client.images.generate(
    model="dall-e-3",
    prompt="一只橘猫坐在堆满书的桌子上，旁边放着一杯咖啡，温暖的光线，摄影风格",
    size="1024x1024",
    quality="hd",
    n=1,
)

image_url = response.data[0].url
print(image_url)
```

特点：质量稳定、理解能力强、支持文字渲染（图片里可以写字）。

### Stable Diffusion（开源 / API）

Stable Diffusion 是开源方案中最成熟的。你可以自己部署，也可以用 Stability AI 的 API：

```python
import requests

response = requests.post(
    "https://api.stability.ai/v2beta/stable-image/generate/core",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"none": ""},
    data={
        "prompt": "A tabby cat sitting on a desk full of books",
        "output_format": "png",
        "aspect_ratio": "1:1",
    },
)

with open("output.png", "wb") as f:
    f.write(response.content)
```

特点：可本地部署、可控性强、生态丰富（ControlNet、LoRA 等扩展）。

### Flux（Black Forest Labs）

Flux 是 2024-2025 年涌现的高质量开源模型，在图像质量和 prompt 跟随度上接近 DALL-E 3：

```python
# 通过 Replicate API 调用 Flux
import replicate

output = replicate.run(
    "black-forest-labs/flux-1.1-pro",
    input={
        "prompt": "A professional product photo of a coffee cup...",
        "width": 1024,
        "height": 1024,
    }
)
```

### Midjourney API

Midjourney 在 2025 年开放了 API（之前只能通过 Discord 使用）。在艺术风格和美学质量上仍然是最强的：

```python
# Midjourney API（示例）
response = requests.post(
    "https://api.midjourney.com/v1/imagine",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "prompt": "An architectural visualization of a modern library...",
        "aspect_ratio": "16:9",
    }
)
# 异步返回，需要轮询结果
```

### 怎么选

| 场景 | 推荐方案 |
|------|----------|
| 快速原型 / 通用生成 | DALL-E 3 |
| 需要本地部署 / 精细控制 | Stable Diffusion + ControlNet |
| 高质量 / prompt 准确 | Flux Pro |
| 艺术风格 / 美学优先 | Midjourney |
| 图片中包含文字 | DALL-E 3（文字渲染能力最强） |

## 视频生成：2026 年的现状

视频生成在 2025-2026 年经历了爆发式发展，但和图像生成相比，质量和可控性仍有明显差距。

### 主流方案

**Sora（OpenAI）**：文本/图片→视频，最长 1 分钟，物理模拟能力强，画面流畅。2025 年底开放 API。

**可灵 Kling（快手）**：国产方案中质量最高，支持图生视频、运镜控制，对中文 prompt 理解好。

**Runway Gen-3 Alpha**：商业方案中最早成熟的，适合广告和短片素材。

**Veo（Google DeepMind）**：质量最高之一，但 API 可用性有限。

### 视频生成的局限

- **一致性差**：同一物体在不同帧之间可能"变形"
- **物理规则不完美**：虽然比 2024 年好很多，但复杂物理交互（液体、碰撞）仍然会出错
- **可控性有限**：精确控制每一帧的内容仍然很难
- **延迟高**：生成 10 秒视频通常需要 1-5 分钟
- **成本高**：比图像生成贵 10-50 倍

### 适用场景

目前视频生成最适合：
- 概念预览和创意探索
- 短视频和广告素材
- 产品演示动画
- 不适合：需要精确控制的场景、实时生成

## 生成侧核心机制：从噪声到图像

前面讲了怎么用 API，现在进入生成侧的内部。和理解侧的"编码→融合→对齐"对应，生成侧也有自己的核心机制链条。本文用系统的方式讲清楚。

### 整体架构：三个组件

一个完整的图像生成系统由三个核心组件组成：

```
文字描述 → [1. 文本编码器] → 条件向量
                                  ↓
纯噪声 → [2. 去噪网络] ← 条件引导（迭代 20-50 步）
                                  ↓
                         [3. VAE 解码器] → 清晰图像
```

这三个组件分别负责不同的事情，理解它们的关系能帮你在实际使用中更好地调参和排错。

### 组件 1：VAE（变分自编码器）——压缩与解码

VAE（Variational Autoencoder）解决的是一个基础问题：原始图像的像素空间太高维了，直接在这个空间里做生成计算量太大。

VAE 的做法是把图像压缩到一个低维的"潜在空间（Latent Space）"：

- **编码器**：把一张 512×512 的图像压缩成 64×64 的潜在表示（缩小 8 倍）
- **解码器**：把潜在表示还原回原始图像

Stable Diffusion 的全称其实是"Latent Diffusion Model"——它不是在像素空间做扩散，而是在潜在空间做扩散，这就是它能比早期 DALL-E 高效得多的原因。计算量缩小了约 48 倍（512² / 64² = 64，再考虑通道数）。

**对开发者的意义**：当你调整生成图片的分辨率时，实际影响的是潜在空间的大小。分辨率翻倍不是计算量翻 4 倍那么简单——内存和时间的增长都是非线性的。

### 组件 2：去噪网络——生成的核心引擎

这是扩散模型的“大脑”，负责在每一步去噪中决定"下一步该把噪声变成什么样子"。

#### 扩散过程的正向与反向

扩散模型的核心思想分两步：

**正向过程（训练时）**：给一张清晰图片，逐步加噪声，直到变成纯噪声。模型观察这个"破坏"过程。

```
清晰图像 → 加一点噪声 → 加更多噪声 → ... → 纯噪声
```

**反向过程（推理时）**：从纯噪声开始，模型学习逐步去噪，还原出清晰图像。

```
纯噪声 → 去噪 step 1 → 去噪 step 2 → ... → 去噪 step N → 清晰图像
```

训练的目标就是让模型能完成"反向过程"——给定一个带噪声的图像，预测出应该去掉多少噪声。

#### 主流去噪网络架构

**UNet**：Stable Diffusion 1.x / 2.x / SDXL 使用的架构。原本是医学图像分割的经典架构，由下采样路径（编码器）和上采样路径（解码器）组成，中间有跳跃连接。在扩散模型中，UNet 在每个时间步预测噪声。

**DiT（Diffusion Transformer）**：Flux、Sora、Stable Diffusion 3 使用的新架构。把 UNet 替换成 Transformer，用注意力机制代替卷积。DiT 的优势是更容易 scale——更大的模型能带来更稳定的质量提升。这也是 2025-2026 年生成质量飞涨的底层原因之一。

**对开发者的意义**：如果你在选择模型时看到"DiT 架构"，基本可以认为它的 scaling 特性更好、质量上限更高，但推理可能比 UNet 更重。Flux 和 SD3 用 DiT，SDXL 用 UNet。

### 组件 3：文本编码器——条件引导的桥梁

扩散模型需要知道"应该生成什么"。这个信息来自你的文字 prompt，但不是直接把文字喂给去噪网络——需要先通过文本编码器转换成向量。

主流的文本编码器有两种：

**CLIP Text Encoder**：Stable Diffusion 1.x / SDXL 使用。把文字编码成 77 个 token 的向量序列。限制是最多只能处理 77 个 token，所以超长 prompt 会被截断。

**T5（Text-to-Text Transfer Transformer）**：Flux、Stable Diffusion 3 使用。能处理更长的文本，语义理解更深入。这是 Flux 在 prompt 跟随度上超越 SDXL 的关键原因之一。

一些模型会同时用两个文本编码器（比如 SDXL 同时用 CLIP ViT-L 和 OpenCLIP ViT-bigG），让条件信息更丰富。

**对开发者的意义**：如果你发现生成的图片和 prompt 描述不太一致，先检查是不是文本编码器截断了你的 prompt。用 SDXL 时 prompt 不要超过 77 个 token（大约 50-60 个英文单词）。

### 采样算法：速度与质量的权衡

去噪过程需要迭代多步。采样算法决定了"每一步怎么去噪"，直接影响生成速度和质量。

**主流采样器**：
- **DDPM**：最基础的采样器，需要 1000 步，质量好但极慢，生产中不用
- **DDIM**：DDPM 的加速版，20-50 步就能出不错的结果
- **Euler / Euler a**：简单高效，20-30 步质量好，是最常用的采样器
- **DPM++ 2M Karras**：质量最好的一批，20 步接近收敛，SDXL 推荐
- **Flow Matching**：Flux 使用的新一代采样方法，4-8 步就能出高质量图，是当前最快的方案

**步数 vs 质量的规律**：
- 5-10 步：基本轮廓出现，细节模糊
- 15-25 步：大部分场景已经足够好
- 30-50 步：精细质量提升，边际收益递减
- 50 步以上：几乎看不出差异，纯粹浪费时间

**对开发者的意义**：生产环境中，20 步 + Euler 采样器通常是最佳性价比。如果需要更快（比如实时预览），可以用 4-8 步 + Flow Matching（如果模型支持）。不建议超过 30 步。

## 条件引导：怎么控制生成内容

扩散模型从噪声生成图像，但怎么确保生成的是你想要的东西？这就是条件引导（Conditioning）的作用。

### 三种条件引导方式

**文字 prompt 引导**：最基本的方式。你的文字描述通过文本编码器变成条件向量，在每一步去噪时“指引”模型往正确方向走。prompt 写得越准确，生成结果越贴合。

**参考图像引导（Image-to-Image）**：给一张参考图，模型在这个基础上加噪再去噪，生成和参考图风格/构图相似的新图像。典型用法：
- 把草图变成真实图像
- 把照片变成特定艺术风格
- 调整图片的某些细节（inpainting）

**CFG（Classifier-Free Guidance）强度**：这是一个关键参数，控制模型多大程度上“听从”你的 prompt。CFG 值越高，生成结果越贴合 prompt 但可能过度饱和；CFG 值越低，模型越“自由发挥”。

```
最终噪声预测 = 无条件预测 + CFG × (有条件预测 - 无条件预测)
```

典型值：
- CFG = 1-3：模型自由发挥，适合创意探索
- CFG = 5-7：平衡质量和跟随度，大多数场景的最佳值
- CFG = 8-15：严格跟随 prompt，但可能出现过饱和/锐化
- CFG > 15：通常会产生伪影，不推荐

### ControlNet：精确控制生成

ControlNet 是 Stable Diffusion 生态中最重要的扩展。它让你可以用额外的"控制图"来精确指导生成过程：

- **边缘图**：指定物体的轮廓线
- **深度图**：指定场景的深度关系
- **姿态图**：指定人物的姿势
- **涂鸦图**：用简单的涂鸦指定构图

对 Agent 来说，ControlNet 的价值在于：**Agent 可以先用代码生成一张控制图（比如布局草图），然后用 ControlNet 指导图像生成，实现更精确的视觉输出。**

## 何时生成 vs 何时检索

Agent 在需要视觉内容时，有两个选择：生成（从零创建）或检索（从已有资源中找）。

### 生成的适用场景

- 内容不存在（"一个赛博朋克风格的图书馆"——没有现成图片）
- 需要高度定制化（特定布局、特定风格、特定组合）
- 一次性使用（不需要维护图片库）

### 检索的适用场景

- 内容已经存在（产品图、团队照片、已有素材）
- 需要真实性和准确性（不能用 AI 生成的假图代表真实产品）
- 对质量要求极高（生成的图可能不够完美）
- 成本敏感（检索成本远低于生成）

### 混合策略

最佳实践是混合策略：

```
需要视觉内容 → 先检索已有素材库 → 没找到合适的 → 再调用生成
```

这比每次都生成更高效，也避免了不必要的幻觉风险（AI 生成的图可能"看起来对但实际错误"）。

## Prompt 工程：怎么让 Agent 写出好的生成指令

图像生成的质量 80% 取决于 prompt。当 Agent 需要调用图像生成工具时，它生成的 prompt 质量至关重要。

### 好的图像生成 prompt 结构

```
[主体描述] + [环境/背景] + [风格/光线] + [构图/视角] + [质量修饰]
```

例子：
- 差：`一只猫`
- 好：`一只橘猫蜷缩在窗台上，午后阳光透过百叶窗洒下来，摄影风格，浅景深，温暖色调`

### Agent 的 prompt 策略

让 Agent 生成高质量图像 prompt 的方法：

1. **在 system prompt 中教 Agent prompt 格式**：告诉它生成图像时要包含哪些要素
2. **提供 few-shot 示例**：给几个"用户描述→好的图像 prompt"的示例
3. **分步生成**：先让用户确认描述，再细化为图像 prompt
4. **负面 prompt**：告诉模型不要包含什么（"不要模糊、不要变形、不要多余的手指"）

### 示例：Agent 工具调用

```python
# Agent 的图像生成工具定义
{
    "name": "generate_image",
    "description": "生成一张图片。prompt 应该包含：主体、环境、风格、构图、质量修饰词",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "详细的图像描述，至少 50 字，包含主体、环境、风格"
            },
            "negative_prompt": {
                "type": "string",
                "description": "不希望出现的内容"
            },
            "style": {
                "type": "string",
                "enum": ["photo", "illustration", "3d_render", "anime"]
            }
        }
    }
}
```

## 质量评估与审核

图像生成的质量评估比文本生成更主观，但也有一些工程化方法。

### 自动化评估

- **CLIP Score**：用 CLIP 计算生成图片和 prompt 之间的相似度（越高越匹配）
- **FID（Fréchet Inception Distance）**：评估生成图片和真实图片分布的差异（越低越好）
- **美学评分模型**：LAION Aesthetic Predictor 等模型可以给图片的美学质量打分

### 人工审核

对于生产场景，人工审核仍然是最后一道关：

- **真实性检查**：图片中的物体是否合理（手指数量、文字内容）
- **品牌一致性**：是否符合品牌调性和视觉规范
- **安全合规**：是否包含不当内容

### Agent 的审核流程

```
Agent 生成图片 → CLIP Score 自动评估（< 阈值则重新生成）→ 关键场景人工审核 → 交付
```

对于低风险场景（内部文档配图、原型设计），可以省略人工审核。对于面向用户的场景（营销素材、产品页面），建议保留人工审核环节。

## 总结

图像与视频生成是多模态的"创造"侧能力，和理解侧（Transformer 体系）是完全不同的技术路线：

**生成侧的核心架构**：
- **VAE**：把图像压缩到潜在空间，降低计算成本
- **去噪网络（UNet/DiT）**：从噪声逐步还原图像，是生成的核心引擎
- **文本编码器（CLIP/T5）**：把文字 prompt 变成条件向量，引导生成方向
- **采样算法**：控制去噪的步数和策略，是速度与质量的关键平衡点

**工程决策要点**：
- 图像生成 API 已经非常成熟——DALL-E 3 / Flux / Stable Diffusion / Midjourney 各有优劣
- 视频生成快速发展但仍有局限，适合概念预览而非精确控制
- ControlNet 提供像素级的生成控制能力
- Agent 应该优先考虑检索已有素材，找不到再生成
- Prompt 质量决定生成质量——教 Agent 写出结构化的图像描述是关键
- 质量评估靠 CLIP Score 自动筛选 + 高风险场景人工审核

下一篇把所有模态串起来，讲多模态推理——当模型需要同时处理图像、文字、语音做综合判断时，事情变得更有意思了。

> 下一章：[多模态推理：跨模态综合理解](../05-multimodal-integration/01-cross-modal-reasoning.md)

## 参考链接

- [Denoising Diffusion Probabilistic Models (DDPM)](https://arxiv.org/abs/2006.11239)
- [High-Resolution Image Synthesis with Latent Diffusion Models (Stable Diffusion)](https://arxiv.org/abs/2112.10752)
- [Scalable Diffusion Models with Transformers (DiT)](https://arxiv.org/abs/2212.09748)
- [ControlNet: Adding Conditional Control to Text-to-Image](https://arxiv.org/abs/2302.05543)
- [OpenAI DALL-E 3 Documentation](https://platform.openai.com/docs/guides/images)
- [Stable Diffusion Documentation](https://stability-ai.github.io/stablediffusion-docs/)
- [Flux Model (Black Forest Labs)](https://blackforestlabs.ai/flux-1.1-pro)
- [OpenAI Sora](https://openai.com/sora)
- [CLIP Score for Image Captioning Evaluation](https://arxiv.org/abs/2104.08718)
