# VLM 演进：从 CLIP 到 LLaVA

> 2021 年 CLIP 让机器学会了"看图和读文的关联"，2023 年 LLaVA 让开源模型实现了"看图聊天"，2026 年的 Qwen-VL 已经能在图上精确定位物体。这不是一条直线，而是一连串关键突破的接力。

## 目录

- [为什么 VLM 是多模态的主战场](#为什么-vlm-是多模态的主战场)
- [CLIP：一切的起点](#clip一切的起点)
- [BLIP-2：桥接的艺术](#blip-2桥接的艺术)
- [LLaVA：开源多模态对话的破圈时刻](#llava开源多模态对话的破圈时刻)
- [Qwen-VL：中文场景无可撼动的第一梯队](#qwen-vl中文场景无可撼动的第一梯队)
- [其他重要玩家](#其他重要玩家)
- [演进路线总览与实战选型](#演进路线总览与实战选型)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。02 章拆解了多模态 AI 的技术地基——三代架构、三大机制。这一章把镜头聚焦到其中最成熟的分支：视觉语言模型（VLM）。从 CLIP 到今天你能在代码里一行调用 gpt-4o 分析图片，这中间发生了太多事。

## 为什么 VLM 是多模态的主战场

在所有多模态方向里，视觉语言模型是最成熟、竞争最激烈、且对你最有实用价值的领域。三个原因：

1. **数据最丰富**：互联网上天然存在数十亿对图文数据——网页图片配 alt text、社交媒体图文帖子、电商产品图配描述。对比语音或视频，图文数据的获取成本低到忽略不计
2. **应用最广泛**：从文档分析到 UI 自动化到医疗影像，视觉理解是横跨最多行业的多模态能力
3. **开源最活跃**：CLIP、LLaVA、Qwen-VL 全开源——这意味着你不需要 OpenAI 的 API 就能搭建视觉 AI 应用

本文沿时间线走一遍 VLM 的进化——每一步为什么发生、谁是关键推动者、你该怎么选。

## CLIP：一切的起点

2021 年 1 月，OpenAI 发布了 CLIP。当时大多数人没意识到，这篇论文将成为整个多模态 AI 大厦的基石。

### CLIP 之前的世界

在 CLIP 之前，训练一个图片分类模型的方式是：收集图片 → 人工标注类别 → 训练模型识别这些类别。问题是：

- 每个新任务需要重新标注数据。"识别猫"的模型不能用来"识别汽车品牌"
- 标注成本极高——ImageNet 花了数年时间和数百万美元
- 模型只能识别训练时见过的类别，遇到没见过的东西完全抓瞎

CLIP 改变了这一切。它不是在"猫/狗/车的图片"上训练的，而是在 **4 亿对（图片，自然语言描述）** 上训练的——不是标签，而是完整的句子描述。

### CLIP 怎么工作

```python
# CLIP 的核心架构（简化）
# 两个并行的编码器，输出映射到同一个向量空间

image_encoder = ViT(image)           # 图片 → 512维向量
text_encoder = Transformer(text)     # 文字 → 512维向量

# 训练时：让匹配的图文对向量接近，不匹配的远离
loss = contrastive_loss(
    image_encoder(batch_images),     # [N, 512]
    text_encoder(batch_texts)        # [N, 512]
)
```

训练的数学目标很简单：对于第 i 张图片和第 i 段文字（它们是配对好的），让它们的向量尽可能接近；对于第 i 张图片和第 j 段文字（i≠j，不匹配），让它们的向量尽可能远。

**但这个简单目标的效果超乎所有人预期。**

### CLIP 改变了什么

**零样本分类**。训练完成后，CLIP 可以分类它从未见过类别的图片。怎么做？

```python
# 零样本分类：CLIP 区分"猫"和"狗"，从未见过这两个类的标注图片

# 把类别名字变成 Prompt
texts = ["a photo of a cat", "a photo of a dog"]  # 不是标签，是自然语言

# 分别计算图片和两个文字的相似度
image_vector = clip.encode_image(image)           # [512]
text_vectors = clip.encode_text(texts)            # [2, 512]

similarities = image_vector @ text_vectors.T      # [2] — 和"猫"相似度0.82, 和"狗"相似度0.23

prediction = "cat"  # 胜出
```

不需要任何训练数据的零样本分类。给 CLIP 1000 个类别名（自然语言描述），它直接告诉你图片最可能是哪一个。这在之前是不可想象的。

**CLIP 的视觉编码器成为行业标准**。CLIP 训练的 ViT（Vision Transformer）成了"事实标准"的视觉编码器。几乎所有的后续 VLM——LLaVA、BLIP-2、Qwen-VL——都直接用了 CLIP ViT 来提取图像特征。CLIP 不是更先进了，而是**它对齐的图文基础最扎实**。

### CLIP 为什么能成功

三个因素：

1. **数据规模**：4 亿对图文数据——比之前的学术数据集大 1000 倍。数据量本身就是一种能力
2. **自然语言作为监督信号**：不是类别标签（标签会限制你能学的东西），而是完整句子（能学的东西无穷无尽）
3. **简洁的对比学习目标**：不需要语言建模（预测下一个词），只需要判断"图文是否匹配"——训练更高效，效果更好

### CLIP 的边界

CLIP 的局限恰恰定义了 VLM 后续演进的方向：

- **能做匹配，不能做推理**：问 CLIP"根据这张胸部X光片，病人可能有哪种疾病？"——它只能告诉你"这是胸部X光片"，不能分析影像中的病理特征
- **只能"看图"，不能"看图说话"**：CLIP 只能输出一个相似度分数，不能生成一段描述文字。你需要另一个模型（LLM）来做生成
- **粒度粗**：整张图 vs 整段文字的对齐，无法定位"图中第三个人戴的帽子的颜色"这种细粒度问题

这三个局限，正是后续 BLIP-2 和 LLaVA 要去解决的问题。

## BLIP-2：桥接的艺术

2023 年 1 月，Salesforce 发布了 BLIP-2。它要解决的核心问题：**CLIP 只能给相似度打分，不能说话。怎么让一个视觉模型和一个语言模型对话？**

### Q-Former：聪明的提问者

BLIP-2 不做端到端训练。它的策略是：找一个最强的视觉编码器（CLIP ViT 的变体），找一个最强的语言模型（FlanT5），然后在这两者之间架一座桥。

这座桥就是 Q-Former（Querying Transformer）。

Q-Former 的工作原理类似一个聪明的记者：它带着一组"问题"（32 个可学习的查询向量）去看图，从图片中提取和问题最相关的信息，然后把精选的信息转交给 LLM。

```python
# Q-Former 的工作流程
query_tokens = learnable_vectors(shape=[32, 768])   # 32个"问题"

# 第一步：和图像特征交叉注意力
# "图片里这是什么？""有哪些物体？""它们什么关系？"
query_tokens = cross_attention(query_tokens, image_features)

# 第二步：自注意力整合
# "我看到了猫、沙发、窗户——猫在沙发上"
query_tokens = self_attention(query_tokens)

# 输出：32个精选的视觉Token，包含了对问题最有用的视觉信息
```

32 个查询向量 vs LLaVA 的 576 个 Patch 向量——BLIP-2 的输入长度只有后者的 1/18。这意味着 LLM 的处理速度快很多，但代价是丢失了大量视觉细节。

### BLIP-2 的选择和局限

BLIP-2 擅长：快速告诉你"图片里有什么"——物体识别、简单场景描述。

BLIP-2 不擅长：细粒度理解——"图片右下角价格标签上的数字是多少"这类问题，因为 32 个查询向量很难完整保留整张图的细节。

**BLIP-2 的贡献是证明了"桥接"这条路能走通**——不需要从头训练一个图文融合模型，只需要在现成的最强模型之间架一座设计精良的桥。

## LLaVA：开源多模态对话的破圈时刻

2023 年 4 月，微软和威斯康星大学发布了 LLaVA。这是开源 VLM 的"ChatGPT 时刻"——之前的模型只能做图文匹配或简单描述，LLaVA 首次让开源模型实现了流畅的看图聊天。

### LLaVA 为什么特别

LLaVA 做了三件创造性的工作：

**第一件：用 GPT-4 生成训练数据**

这是最天才的一步。当时 GPT-4 的视觉功能还没发布（它只能处理文本），但 LLaVA 团队想到：COCO 数据集有大量图片的文字描述，喂给 GPT-4 让它基于描述生成对话数据。

```python
# LLaVA 的训练数据生成逻辑
for image_description in coco_captions:
    prompt = f"""
    基于以下图片描述，生成一段多轮对话：
    
    描述：{image_description}
    
    对话应该包含不同类型的问题：
    - 物体识别
    - 空间关系
    - 推理和分析
    - 基于视觉信息的判断
    """
    conversation_data = gpt4.generate(prompt)
    # 用 GPT-4 的回答作为 ground truth 训练 LLaVA
```

GPT-4 虽然没有真的看到图片，但它对文字描述的理解能力极其强大。基于一份详细的文字描述，GPT-4 能生成非常自然的问答对——这些问答对反过来训练了 LLaVA，让它学会了"看到图以后怎么用自然语言回答"。

**第二件：极简的投影层**

LLaVA 的投影层就一个矩阵——W × 图像特征向量。没有 Q-Former 的复杂结构，没有多步注意力。

这背后的洞察是：**CLIP 已经做了足够好的对齐**——图像向量和文本向量在同一个语义空间。LLM 本身有足够强的语义理解能力。两者之间只需要最简单的维度转换。额外的复杂性不会带来效果提升，只会拖慢训练。

**第三件：端到端的指令跟随训练**

LLaVA 不只是训练投影层，还训练 LLM 学会"跟随视觉指令"。训练完成后，模型不只是"能看图"，而是"能听懂你关于这张图的复杂要求"——这是从"看图说话"到"看图做事"的关键飞跃。

### LLaVA 1.5/1.6：迭代的力量

**LLaVA 1.5** 在原始 LLaVA 上做的改进：

1. 用学术任务数据（ScienceQA、TextVQA）替换部分 GPT-4 生成数据——更真实的视觉理解训练
2. 提升输入分辨率（224→336 像素）——更精细的视觉细节
3. 换用更强的 CLIP 编码器——更好的视觉基础

效果从 MMBench 的 36.2 分跳到 64.3 分，几乎翻倍。

**LLaVA 1.6** 的核心创新是**动态高分辨率**：

```
传统做法：一张大图 → 缩小到 336×336 → 丢给 ViT → 小字看不清

LLaVA 1.6：一张大图 → 切成多个 336×336 的子图（带重叠）
                → 每个子图独立编码
                → 所有子图的特征拼在一起
                → 大图的小字能看到了
```

OCR 能力（OCRBench）从 210 提升到 317，提升 51%。这就是模型真正"看清"文档类内容的分水岭。

### 动手跑一个 LLaVA

```python
from transformers import LlavaForConditionalGeneration, AutoProcessor
import torch
from PIL import Image

# 加载模型
model = LlavaForConditionalGeneration.from_pretrained(
    "llava-hf/llava-1.5-7b-hf",
    torch_dtype=torch.float16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("llava-hf/llava-1.5-7b-hf")

# 加载图片和问题
image = Image.open("chart.jpg")
conversation = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": "分析这张图表的营收趋势，指出哪个季度增长最快"}
        ]
    }
]

# 处理输入并生成回答
prompt = processor.apply_chat_template(conversation, add_generation_prompt=True)
inputs = processor(images=image, text=prompt, return_tensors="pt").to("cuda")

output = model.generate(**inputs, max_new_tokens=300)
response = processor.decode(output[0], skip_special_tokens=True)
print(response)
```

一张消费级 RTX 3090（24GB VRAM）就能跑 7B 版本的 LLaVA。从下载到出结果，10 分钟。

## Qwen-VL：中文场景无可撼动的第一梯队

阿里巴巴的 Qwen-VL 系列是中文 VLM 的标杆。它在三个维度上超越了开源竞品。

### 优势一：原生中文图文训练

LLaVA 的 CLIP 视觉编码器主要训练数据是英文。这意味着 LLaVA "看"中文图片的能力是间接的——它通过英文的视觉特征去猜中文的内容。

Qwen-VL 用自己的中文图文数据从头训练视觉编码器。结果是：对于中文文档、中文路牌、中文手写文字的识别准确率远高于 LLaVA。

### 优势二：视觉定位（Grounding）

Qwen-VL 不只是看图说话，它能在图上**精确标注位置**：

```python
# Qwen-VL 的视觉定位能力
# 用户："图里价格最高的商品标注出来"

# Qwen-VL 的输出包含坐标
response = {
    "text": "价格最高的商品是右边的 iPhone 16，标价 ¥8999",
    "bounding_boxes": [
        {"label": "iPhone 16", "bbox": [520, 140, 780, 320], "price": "¥8999"}
    ]
}
```

这个能力对 UI 自动化、工业检测、电商商品标注等场景是核心需求。开源模型中目前只有 Qwen-VL 能稳定输出精确的坐标信息。

### 优势三：多图理解和比较

Qwen-VL 支持同时输入多张图片进行对比分析：

- "比较这两张 UI 设计稿在信息架构上的差异"
- "按照时间顺序排列这三张流程图"
- "找出这两份合同的条款差异"

这在 LLaVA 1.6 之前是做不到的（LLaVA 1.6 之后也支持了多图）。

### Qwen-VL 的实际调用

```python
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch

model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-7B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

# 多图对话
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": "design_v1.jpg"},
            {"type": "image", "image": "design_v2.jpg"},
            {"type": "text", "text": "对比这两个版本的首页设计，指出布局和配色的主要变化"}
        ]
    }
]

# 处理多模态输入
text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
image_inputs, video_inputs = process_vision_info(messages)
inputs = processor(text=text, images=image_inputs, return_tensors="pt").to("cuda")

generated_ids = model.generate(**inputs, max_new_tokens=500)
response = processor.batch_decode(
    generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
)[0]
print(response)
```

### Qwen-VL 的版本选择

| 版本 | 参数量 | 适用场景 | 硬件需求 |
|------|:--:|------|:--:|
| Qwen2-VL-2B | 2B | 移动端、实时场景、简单问答 | 4GB VRAM |
| Qwen2-VL-7B | 7B | 通用场景，性价比最佳 | 16GB VRAM |
| Qwen2-VL-72B | 72B | 最高精度，复杂推理 | 4×A100 |

## 其他重要玩家

### InternVL（上海 AI 实验室 / OpenGVLab）

InternVL 在开源社区的口碑很好——它不是某个单项最强，而是**各项均衡，没有明显短板**。

核心设计：InternVL 用了自己训练的 InternViT-6B 作为视觉编码器（不是直接用 CLIP ViT），配合 InternLM 系列 LLM。这种"视觉和语言都自己训练"的策略，让它不像 LLaVA 那样受限于 CLIP 的视觉编码器质量。

在 MMBench、MME、OCRBench 等多个基准上，InternVL 的得分常常排在开源模型的前列。它在 GUI 理解（识别手机和电脑界面的按钮和布局）和 3D 视觉任务上尤其有优势。

### CogVLM（清华大学 / 智谱 AI）

CogVLM 的技术路线和主流不太一样——它在 LLM 的每一层都增加了一个专门的视觉专家模块，而不是在输入端一次性注入视觉信息。思路是让模型在推理的每一层都能"再确认一下图片的内容"，对需要反复参照图片的复杂推理有帮助。

### MiniCPM-V / MiniCPM-o（OpenBMB）

轻量级 VLM 中的黑马。MiniCPM-o 2.6 只有 8B 参数，但支持实时音视频交互——不是"上传一段视频等结果"，而是打开摄像头实时对话。这是移动端和 IoT 设备上最有想象力的方向。

## 演进路线总览与实战选型

### 能力演进

```
2021  CLIP         → 能判断"图和文是否匹配"
2023  BLIP-2       → 能用自然语言描述图片内容
2023  LLaVA        → 能看图聊天，跟随复杂指令
2023  LLaVA 1.5    → 文档和图表理解大幅提升
2023  Qwen-VL      → 能在图上精确标注位置（Grounding）
2024  LLaVA 1.6    → 高分辨率策略，小字能看清楚了
2026  InternVL 3   → 综合能力开源最强，3D视觉
2026  MiniCPM-o    → 实时音视频交互，落地移动端
```

### 选型速查

| 你的场景 | 推荐模型 | 为什么 |
|---------|---------|--------|
| 本地原型验证 | LLaVA 1.5-7B | 社区最大、资料最多、一张 RTX 3090 能跑 |
| 中文文档 / OCR | Qwen2-VL-7B | 中文训练最优，定位框选独有 |
| 最高精度（不差钱） | GPT-4o API | 综合最强，不用管部署 |
| 多图对比分析 | Qwen2-VL / LLaVA 1.6 | 都支持多图输入 |
| 移动端 / 低延迟 | MiniCPM-V / Qwen2-VL-2B | 参数量小，可在手机上推理 |
| 3D 视觉 / GUI 理解 | InternVL | 这两个场景的特殊优化 |
| 微调到自己的业务 | Qwen2-VL（开源，文档好） | 社区活跃，微调教程多 |

## 总结

- CLIP 是 VLM 大厦的地基——**4 亿对自然语言图文数据的对比学习**，让机器第一次学会了"看懂图和读懂文是同一件事"的不同表达
- BLIP-2 的 Q-Former 证明了"桥接"方案可行——不需要重新训练视觉或语言模型，只需要一个聪明的翻译层
- LLaVA 做了两件改变行业的事：**用 GPT-4 生成训练数据降低了标注成本，用极简投影层证明了"不需要复杂架构"**
- Qwen-VL 在中文 VLM 领域建立了四个壁垒：原生中文训练、视觉定位（Grounding）、多图理解、从 2B 到 72B 的全系列覆盖
- 开源 VLMs 已经能覆盖 80% 的日常视觉需求，只有在复杂推理和最高精度场景下才需要 GPT-4o/Claude
- 下一篇跳出开源阵营，看看 GPT-4o、Gemini、Claude 这三大闭源旗舰在视觉能力上的真正差异

## 参考链接

- [CLIP: Learning Transferable Visual Models (2021)](https://arxiv.org/abs/2103.00020)
- [BLIP-2: Bootstrapping Language-Image Pre-training (2023)](https://arxiv.org/abs/2301.12597)
- [LLaVA: Visual Instruction Tuning (2023)](https://arxiv.org/abs/2304.08485)
- [LLaVA 1.5: Improved Baselines (2023)](https://arxiv.org/abs/2310.03744)
- [Qwen-VL: A Versatile Vision-Language Model (2023)](https://arxiv.org/abs/2308.12966)
- [InternVL: Scaling up Vision Foundation Models (2023+)](https://arxiv.org/abs/2312.14238)
- [CogVLM: Visual Expert for Pretrained Language Models (2023)](https://arxiv.org/abs/2311.03079)

> CLIP 到 LLaVA 到 Qwen-VL——开源的 VLM 演进线看完了。但商业模型的玩法完全不同。下一篇 [闭源旗舰：GPT-4o / Gemini / Claude](./02-commercial-vlms.md) 带你看看三大闭源巨头在视觉能力上的差异化竞争。
