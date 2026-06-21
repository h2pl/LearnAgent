# 跨模态表示学习：CLIP 与多模态嵌入

前两篇文章建立了多模态的全景认知和底层机制。本篇深入到表示层面——多模态模型如何让图像和文字在同一个向量空间中"对话"。

## 为什么需要跨模态表示

单模态表示（如 BERT 的文本嵌入、ResNet 的图像特征）各自在自己的空间里。多模态应用需要把不同模态映射到共享语义空间，才能实现：

- **跨模态检索**：用文字搜图片、用图片搜文字
- **Zero-shot 分类**：没见过的类别也能识别
- **多模态 RAG**：同时检索文本和图像知识

## 对比学习：核心训练范式

CLIP（Contrastive Language-Image Pre-training）是跨模态表示学习的里程碑。核心思想：
- 使用 4 亿图文对训练
- Batch 内 N 个图文对构成 N×N 的相似度矩阵
- 对角线是正例，其余是负例
- 用对比损失最大化正例相似度、最小化负例相似度

### InfoNCE 损失

```
L = -log(exp(sim(I,T)/τ) / Σexp(sim(I,T_j)/τ))
```

其中 sim 是余弦相似度，τ 是可学的温度参数。

## 双塔架构

CLIP 采用双塔架构：
- **图像塔**：ViT（Vision Transformer），将图像分为 patches 后做 Transformer 编码
- **文本塔**：标准 Transformer，输出 [EOS] token 作为文本表示
- 两个塔的输出通过投影头映射到相同维度（如 512 维）

训练后，图像和文本的嵌入可以直接比较余弦相似度。

## 多模态嵌入模型演进

| 模型 | 发布时间 | 架构特点 | 亮点 |
|------|----------|----------|------|
| CLIP | 2021 | ViT + Text Transformer | 开创性工作，4 亿数据 |
| SigLIP | 2023 | Sigmoid 损失替代 Softmax | 训练更高效，batch size 不敏感 |
| EVA-CLIP | 2023 | 用 EVA 初始化 ViT | 更强视觉表示 |
| BLIP-2 | 2023 | Q-Former 桥接 | 冻结视觉/语言模型，训练轻量 |
| ImageBind | 2023 | 6 模态联合嵌入 | 不配对也能对齐 |
| SigLIP2 | 2025 | 可变形 patch 编码 | 多分辨率感知 |

## 向量空间的几何特性

经过对比学习训练后，嵌入空间表现出有趣的几何性质：
- **模态对齐**：猫的图片和"猫"的文字在空间中靠近
- **语义方向**：从"狗"到"幼犬"的向量方向，和从"猫"到"小猫"的方向相似
- **组合性**："红色的汽车"的嵌入约等于"红色"+"汽车"的向量组合

## 实际应用

### Zero-shot 分类

CLIP 最惊艳的应用：无需任何训练样本，用"一张{类别}的照片"作为 text prompt，分类未知图片。

### 跨模态检索

构建多模态搜索系统：将知识库图片预编码为嵌入向量，用户输入文字查询后，检索最相似的图片。

### 多模态 RAG 的底层基础

CLIP 嵌入是多模态 RAG 的核心——文档中的图和文分别编码，统一索引，实现图文混合检索。

### Fine-tuning 策略

实际应用中通常需要微调：
- **全微调**：小数据集效果好但开销大
- **LoRA**：轻量适配，保持基础能力
- **Adapter**：仅为特定任务添加小模块

## 局限性

1. **细节感知不足**：CLIP 对颜色、位置等细粒度属性不够敏感
2. **计数能力弱**：难以区分"两个苹果"和"三个苹果"
3. **抽象概念困难**：对隐喻、幽默等高层语义理解有限
4. **数据偏见**：训练数据中不均衡的分布会被编码到嵌入中

## 参考

- [CLIP: Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)
- [SigLIP: Sigmoid Loss for Language Image Pre-Training](https://arxiv.org/abs/2303.15343)
- [BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders](https://arxiv.org/abs/2301.12597)
- [ImageBind: One Embedding Space To Bind Them All](https://arxiv.org/abs/2305.05665)
- [OpenAI CLIP GitHub](https://github.com/openai/CLIP)
