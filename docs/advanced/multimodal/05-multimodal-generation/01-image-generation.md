# 图像生成：扩散模型与主流工具

> 前面三章都在讲 AI 怎么"理解"世界——看图、听话。从这一章开始，我们讲 AI 怎么"创造"世界。首当其冲的是图像生成——2026 年最成熟、竞争最激烈、对普通人影响最大的生成式 AI 赛道。

## 目录

- [扩散模型：从噪声中"浮现"图像](#扩散模型从噪声中浮现图像)
- [DALL-E：Prompt 理解最强的商业方案](#dall-eprompt-理解最强的商业方案)
- [Midjourney：审美天花板但你需要知道怎么用](#midjourney审美天花板但你需要知道怎么用)
- [Stable Diffusion 与 Flux：开源路线的双极](#stable-diffusion-与-flux开源路线的双极)
- [国产生图方案](#国产生图方案)
- [图像生成的局限与坑](#图像生成的局限与坑)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面几章你学会了怎么让 AI 看图、看视频、听声音。现在，反过来——怎么让 AI 创造不存在的东西。

## 扩散模型：从噪声中"浮现"图像

扩散模型是 2022 年后图像生成革命的数学引擎。理解它的原理，比记住每个工具的用法更重要——因为所有工具（DALL-E、Midjourney、Stable Diffusion）底层都是同一套机制的不同实现。

### 核心思想：逆向工程"噪声化"

扩散模型有两个阶段：

**前向过程（加噪）**：拿一张清晰的图片，逐步加入随机噪声——经过足够多步后，图片变成完全的随机噪声。这个过程是不可逆的——就像你把墨水滴进清水里，墨迹扩散后不可能复原。

**逆向过程（去噪）**：训练一个神经网络，学会从加了不同程度噪声的图片中"预测并移除噪声"。经过足够多的训练后，这个网络能从完全的随机噪声开始，一步步"恢复"出一张清晰图片。

```python
# 扩散模型的核心训练逻辑（极大简化）
def train_step(clean_image, noise_scheduler, denoiser):
    # 随机选一个噪声强度
    noise_level = random.randint(1, 1000)

    # 给图片加噪
    noise = torch.randn_like(clean_image)
    noisy_image = noise_scheduler.add_noise(clean_image, noise, noise_level)

    # 让模型预测噪声（核心学习任务）
    predicted_noise = denoiser(noisy_image, noise_level)

    # 损失：预测的噪声和实际噪声的差距
    loss = (predicted_noise - noise).pow(2).mean()

    return loss
```

### 文生图：把文字注入去噪过程

前面讲的扩散模型只能"从噪声恢复图片"，不能按你的要求生成特定内容。文生图的关键技术是**条件引导**：

```python
# 条件扩散模型的推理流程（简化）
def text_to_image(prompt, denoiser, text_encoder, noise_scheduler):
    # 将Prompt编码为语义向量
    text_embedding = text_encoder(prompt)  # CLIP文本编码器

    # 从纯噪声开始
    image = torch.randn(1, 3, 512, 512)

    # 逐步去噪（通常20-50步）
    for step in range(noise_scheduler.num_steps):
        # 关键：去噪时同时传入图像和文字嵌入
        # 模型学会"在有文字引导的情况下应该保留什么、去掉什么"
        predicted_noise = denoiser(image, step, text_embedding)
        image = noise_scheduler.step(predicted_noise, step, image)

    return image
```

**理解了这个，你就理解了所有文生图工具的本质**：一个学会了"从噪声中恢复图片"的神经网络 + 一个告诉你"恢复成什么样"的文字引导信号。文字越精确，引导越有效，生成的图越符合预期。

## DALL-E：Prompt 理解最强的商业方案

OpenAI 的 DALL-E 在 ChatGPT 中深度集成，它的核心优势不是画质，而是**对 Prompt 的精确理解**。

### DALL-E 的独有强项

**文字渲染**。2026 年的 DALL-E 已经能稳定地在图片中生成可读的中英文文字——海报标题、UI 文案、商店招牌。Midjourney 在这件事上仍然不可靠（尤其是中文）。

**对话式迭代**。"把背景改成蓝色""把猫换成狗""把文字加大两号"——像聊天一样修改图片，而不是每次都从头输入完整的 Prompt。

**长 Prompt 精确跟随**。"一张 1920 年代风格的咖啡店海报，左上角用衬线字体写'Grand Opening'，右下角用小字写地址和电话，整体偏暖棕色调，有轻微的做旧纹理"——DALL-E 能同时处理所有这些细节指令而不遗漏。

```python
from openai import OpenAI

client = OpenAI()

# 生成图片
response = client.images.generate(
    model="dall-e-3",
    prompt="一只穿着西装的橘猫坐在办公桌前，桌上有一台MacBook和一杯咖啡，窗外是城市天际线，电影感光照，暖色调",
    size="1024x1024",
    quality="hd",
    n=1
)
image_url = response.data[0].url

# 基于已有图片编辑（对话式迭代）
response = client.images.edit(
    model="dall-e-3",
    image=open("original.png", "rb"),
    prompt="把西装的颜色从黑色改成深蓝色，背景的窗户换成落地窗"
)
```

### DALL-E 的局限

- **审美天花板明显**：画质不如 Midjourney，这几乎成了产品定位——DALL-E 追求"理解你的需求"，不是"画出最好看的图"
- **风格控制不如 Midjourney**：对大艺术风格（油画、水彩、浮世绘）的执行力有明显差距
- **必须联网**：没有开源版本，API 不可本地部署

## Midjourney：审美天花板但你需要知道怎么用

Midjourney 在 01 章已经作为产品介绍过，这里聚焦技术使用层面。

### Prompt 的五个维度

Midjourney 的 Prompt 质量直接决定出图质量。好的 Prompt = 主体 + 环境 + 风格 + 光影 + 技术参数：

```
差的 Prompt: "一只猫"
好的 Prompt: "a orange tabby cat sitting on a windowsill,
              afternoon sunlight streaming through venetian blinds,
              warm golden hour lighting, shallow depth of field,
              cinematic composition, hyperrealistic, 8K --ar 16:9 --v 6"

拆解：
主体:    orange tabby cat（橘色虎斑猫）
环境:    windowsill, venetian blinds（窗台，百叶窗）
风格:    cinematic, hyperrealistic（电影感，超写实）
光影:    afternoon sunlight, golden hour, shallow depth of field
技术:    --ar 16:9 --v 6（宽高比16:9，v6模型）
```

### Midjourney 的主要参数

| 参数 | 作用 | 常用值 |
|------|------|--------|
| `--ar` | 宽高比 | 16:9 / 1:1 / 9:16 / 3:2 |
| `--v` | 模型版本 | 6 (最新) / 5.2 |
| `--s` | 风格化程度 | 0-1000，越高越"艺术"越偏离写实 |
| `--c` | 创意随机性 | 0-100，越高越随机 |
| `--no` | 排除元素 | 如 `--no text` 禁止文字 |
| `--iw` | 参考图权重 | 0.5-2.0，图生图时参考图的影响程度 |

### 图生图与进阶玩法

```python
# Midjourney 的图生图（Image Prompt）
/imagine prompt: [reference_image_url] a cat in similar style --iw 1.5

# 混合两张图
/blend image1.jpg image2.jpg

# 局部重绘（Vary Region）——选中区域，只改这部分
# Web 端操作，不支持命令行
```

## Stable Diffusion 与 Flux：开源路线的双极

### Stable Diffusion 3.5

Stable Diffusion 是开源图像生成的代名词。它的最大价值是**完全可定制**：

```python
from diffusers import StableDiffusion3Pipeline
import torch

pipe = StableDiffusion3Pipeline.from_pretrained(
    "stabilityai/stable-diffusion-3.5-large",
    torch_dtype=torch.float16
)
pipe = pipe.to("cuda")

# 基础文生图
image = pipe(
    prompt="a cat wearing a wizard hat, digital art, trending on ArtStation",
    negative_prompt="blurry, low quality, distorted",
    num_inference_steps=28,      # 去噪步数
    guidance_scale=7.5,          # Prompt引导强度
    width=1024, height=1024
).images[0]
image.save("wizard_cat.png")

# 图生图（Img2Img）
from PIL import Image
init_image = Image.open("sketch.png")
image = pipe(
    prompt="a detailed digital painting of a cat wizard",
    image=init_image,
    strength=0.7                 # 0=保留原图，1=完全重画
).images[0]
```

### SD 的生态优势

- **ControlNet**：用人体骨骼图、深度图、边缘图精确控制生成结果。这是 Midjourney 和 DALL-E 做不到的——你可以上传一张建筑线稿，ControlNet 只填充材质和光照，不改变结构
- **LoRA**：用几十张特定风格的图片微调模型，学会"我喜欢的画风"。一个人花 30 分钟就能训练一个专属的 LoRA 模型
- **ComfyUI / Automatic1111**：图形化的节点式工作流——拖拽节点、连线、批量生成

### Flux：开源新贵

Flux 由 Stability AI 的前核心团队创立（Black Forest Labs），被广泛认为是 2024-2026 年开源生图的质量跃进：

- **文字渲染能力**：在图片中生成可读的长段文字——这是 SD 的长期弱项
- **手指处理**：对手部和复杂手势的理解比 SD 进步明显
- **Prompt 跟随度**：对长 Prompt 的精确执行接近 DALL-E 水平

Flux 和 SD 的定位差异：SD 胜在生态（ControlNet、LoRA、ComfyUI 等海量生态工具），Flux 胜在基础模型质量。

## 国产生图方案

### 豆包 Seedream 4.0

字节跳动的 Seedream 4.0 在 2026 年有几个实质性突破：
- **4K 高清输出**：直接出 4K 分辨率图片，不需要后期超分辨率处理
- **中文文字渲染**：在图片中生成中文文字的能力国产最强
- **豆包生态集成**：在豆包聊天中直接说"帮我生成一张海报"，不需要切换工具

### 通义万相

阿里的通义万相在电商场景有独特优势——商品图生成、模特换装、场景图批量制作。对电商卖家来说，这是降本增效的刚需工具。

## 图像生成的局限与坑

**手指和复杂肢体**。2026 年的模型已经大幅改善，但仍不稳定。画 10 张有手的图，3-4 张可能需要重画。

**文字的可用性**。DALL-E 和 Flux 可以稳定生成英文和中文文字，Midjourney 和 SD 在这件事上仍然不可靠。

**一致性和连续生成**。同一只猫在同一场景的不同角度——目前的模型做不到连续视角的一致性。每次生成都是独立的。这是视频生成模型的优势领域。

**版权水印**。你的 Prompt 描述得太像某个特定的 IP（如"一只像皮卡丘的黄色电气鼠"）——DALL-E 会拒绝生成。

**你花的钱**。DALL-E 3 每张 $0.04-$0.12，Midjourney $10-60/月，SD 本地部署几乎免费（只有电费和 GPU 折旧）。高频场景下，本地部署能省出巨大差距。

## 总结

- 扩散模型是图像生成的数学引擎：**前向加噪 + 逆向去噪**——所有文生图工具本质都是"学会从噪声中恢复图片 + 用文字引导恢复方向"
- **DALL-E** 强在 Prompt 理解，适合对话式迭代和需要精确文字渲染的场景
- **Midjourney** 强在审美和画质，但需要学习 Prompt 工程五个维度
- **Stable Diffusion / Flux** 是开源双极——SD 胜在生态（ControlNet/LoRA/ComfyUI），Flux 胜在基础模型质量
- **国产生图**已具备实用价值：Seedream 4.0 中文文字+4K，通义万相电商场景
- 图像生成的最大局限：手指/文字/一致性/copyright——知道这些坑才能有效避坑
- 下一篇从静态到动态：[视频生成](./02-video-generation.md)

## 参考链接

- [DALL-E API 文档](https://platform.openai.com/docs/guides/images)
- [Midjourney Prompt 指南](https://docs.midjourney.com/docs/prompts)
- [Stable Diffusion 3 论文](https://arxiv.org/abs/2403.03206)
- [Flux 模型页面](https://huggingface.co/black-forest-labs)
- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)

> 静态图片会画了。下一篇进入最烧钱的生成式 AI 赛道——[视频生成](./02-video-generation.md)，有 Sora 退出的故事、Runway 的出路、和国产方案的崛起。
