# 微调实战指南

> 微调（Fine-tuning）是"改发动机"，调参是"调方向盘"——微调真正改变模型行为，但成本高、门槛高。大多数 Agent 场景不需要微调，先问自己：Prompt 和 RAG 真的不够用吗？

## 目录

- [微调 vs Prompt vs RAG：决策树](#微调-vs-prompt-vs-rag决策树)
- [微调的本质：改模型权重](#微调的本质改模型权重)
- [LoRA：低成本微调的主流方案](#lora低成本微调的主流方案)
- [训练数据怎么准备](#训练数据怎么准备)
- [微调实操流程](#微调实操流程)
- [Agent 开发者的微调边界](#agent-开发者的微调边界)
- [常见坑与避坑指南](#常见坑与避坑指南)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [关键参数](./02-key-parameters.md) 中，你学会了调 temperature、top_p 这些推理时参数。但如果你发现**无论怎么调参、怎么写 Prompt，模型就是不按你想的方式输出**，可能需要微调。这篇文章帮你判断：**什么时候该微调，怎么微调，以及什么时候不该微调**。

## 微调 vs Prompt vs RAG：决策树

先回答最关键的问题：**你的问题真的需要微调吗？**

```
模型输出不符合预期？
├─ 输出格式不对（JSON 格式不稳定）
│  └─ 先试 Few-shot（2-5 个示例）
│     └─ 还不行 → 考虑微调
├─ 模型不懂你的业务知识
│  └─ 用 RAG（检索增强）
│     └─ RAG 效果不够 → 考虑微调补充
├─ 模型风格不符合要求（太正式/太口语）
│  └─ 先试 System Prompt 调整
│     └─ 还不行 → 考虑微调
└─ 模型能力不足（不会用你的工具）
   └─ 用 Function Calling + 工具描述
      └─ 还不行 → 考虑微调
```

**行业共识**：

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 注入新知识 | RAG | 微调注入知识效率低、易遗忘 |
| 控制输出格式 | Prompt Engineering | 几条示例就能稳定，微调成本太高 |
| 特定任务稳定输出 | SFT 微调 | Prompt 无法稳定控制时才考虑 |
| 调整模型风格 | System Prompt 或微调 | 先试 Prompt，不行再微调 |

**一句话原则**：先试 Prompt，再试 RAG，最后才考虑微调。

## 微调的本质：改模型权重

微调是在**已有模型基础上**，用你的数据继续训练，修改模型权重：

```
预训练：海量文本 → Base 模型（学会语言能力）
    ↓
SFT：指令数据 → Instruct 模型（学会听指令）
    ↓
微调：你的数据 → 定制模型（学会你的任务）
```

**微调 vs 预训练**：

| 维度 | 预训练 | 微调 |
|------|--------|------|
| 数据量 | TB 级 | KB~MB 级 |
| 成本 | 数百万美元 | 几十~几百美元 |
| 时间 | 数周~数月 | 几分钟~几小时 |
| 效果 | 从零学会语言 | 在已有能力上适配 |

**微调改的是什么**：通过梯度下降，调整模型参数，让模型在特定任务上的输出概率分布更符合你的期望。比如你希望模型总是输出 JSON 格式，微调后模型输出 JSON 的概率会显著提高。

## LoRA：低成本微调的主流方案

全量微调需要更新所有参数（几十亿），成本极高。LoRA（Low-Rank Adaptation）是目前最主流的低成本微调方案：

```
全量微调：更新所有参数（~8B）
LoRA：冻结原始参数，只训练适配器（~几M）
```

**LoRA 的原理**：

```python
# LoRA 的核心思想
# 原始权重矩阵 W (d × d) 冻结不动
# 新增两个小矩阵 A (d × r) 和 B (r × d)
# r << d（通常 r=8 或 16）

# 前向传播时：
output = W @ x + B @ A @ x
#         ↑        ↑
#      冻结部分   可训练部分
```

**为什么有效**：模型微调时的权重变化是"低秩"的——大部分参数变化集中在少数几个方向上。LoRA 直接建模这个低秩结构，用 0.1% 的参数达到全量微调 90% 的效果。

**QLoRA**：在 LoRA 基础上加入量化，将原始模型参数从 16-bit 压缩到 4-bit，进一步降低显存需求。一张消费级显卡（如 RTX 3090/4090）就能微调 7B~13B 的模型。

## 训练数据怎么准备

微调数据的质量直接决定效果——**垃圾进，垃圾出**。

**数据格式**：标准的指令微调格式（instruction-input-output）：

```json
[
  {
    "instruction": "将以下英文翻译为中文",
    "input": "The weather is nice today.",
    "output": "今天天气很好。"
  },
  {
    "instruction": "从文本中提取人名",
    "input": "张三和李四一起去北京出差。",
    "output": "张三、李四"
  }
]
```

**数据量参考**：

| 任务类型 | 最低数据量 | 推荐数据量 | 说明 |
|----------|-----------|-----------|------|
| 格式对齐 | 50-100 条 | 200-500 条 | 让模型学会输出 JSON 等格式 |
| 风格调整 | 100-300 条 | 500-1000 条 | 让回答更专业/更口语 |
| 领域适配 | 300-1000 条 | 1000-5000 条 | 让模型理解行业术语 |
| 工具调用 | 100-500 条 | 500-2000 条 | 让模型学会调用特定工具 |

**数据质量检查清单**：

- [ ] 每条数据的 output 都是正确的（人工验证）
- [ ] 覆盖了任务的各种边界情况
- [ ] 格式统一，没有不一致的字段
- [ ] 没有重复数据
- [ ] 输入输出长度分布合理（没有特别长或特别短的）

## 微调实操流程

以 Hugging Face + LoRA 为例：

```python
# 完整微调流程
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

# 1. 加载模型
model_name = "meta-llama/Llama-3-8B-Instruct"
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 2. 配置 LoRA
lora_config = LoraConfig(
    r=16,                    # 秩（rank），越大越强但越慢
    lora_alpha=32,           # 缩放系数
    target_modules=["q_proj", "v_proj"],  # 应用到哪些层
    lora_dropout=0.05,
    bias="none",
)

# 3. 应用 LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# 输出：trainable params: 4,194,304 || all params: 8,030,261,248 || 0.05%

# 4. 准备数据（假设已加载为 datasets 格式）
# train_dataset = load_dataset("json", data_files="train.json")

# 5. 配置训练参数
training_config = SFTConfig(
    output_dir="./output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-4,
    logging_steps=10,
    save_strategy="epoch",
)

# 6. 开始训练
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    args=training_config,
)
trainer.train()

# 7. 保存 LoRA 适配器
trainer.save_model("./my-lora-adapter")
```

**关键参数说明**：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| r (rank) | 8-16 | 越大越强但越慢，8 适合大多数场景 |
| lora_alpha | 2 × r | 通常设为 r 的 2 倍 |
| learning_rate | 1e-4 ~ 3e-4 | LoRA 比全量微调高一个数量级 |
| epochs | 1-3 | 数据少时多训几轮，数据多时少训 |

## Agent 开发者的微调边界

Agent 开发中，微调主要用在两个场景：

**场景 1：工具调用格式对齐**

让模型按你的工具定义格式输出 JSON：

```json
// 微调数据示例
{
  "instruction": "根据用户问题，决定调用哪个工具",
  "input": "北京今天天气怎么样？",
  "output": "{\"tool\": \"get_weather\", \"args\": {\"city\": \"北京\"}}"
}
```

**场景 2：领域任务适配**

让模型在特定领域（法律、医疗、金融）的输出更准确：

```json
{
  "instruction": "分析以下合同条款的风险",
  "input": "甲方应在合同签署后30日内支付全款...",
  "output": "风险点：1) 无违约金条款；2) 付款期限过短..."
}
```

**不适合微调的场景**：

| 场景 | 为什么不适合 | 替代方案 |
|------|-------------|----------|
| 注入大量知识 | 微调容量有限，容易遗忘 | RAG |
| 实时信息获取 | 微调无法访问实时数据 | 工具调用 |
| 快速迭代 | 微调周期长（小时~天） | Prompt Engineering |

## 常见坑与避坑指南

| 坑 | 原因 | 避坑方法 |
|----|------|----------|
| **灾难性遗忘** | 微调后模型忘了原来的能力 | 降低学习率、减少 epoch、混入通用数据 |
| **过拟合** | 数据太少，模型"背答案" | 增加数据量、加 dropout、提前停止 |
| **格式不稳定** | 训练数据格式不统一 | 统一数据格式、增加格式示例 |
| **效果不如 Prompt** | 任务太简单，Prompt 就够了 | 先用 Prompt 试，确认不够再微调 |
| **成本超预期** | 数据量大、模型大、epoch 多 | 先用小模型验证，再上大模型 |

## 总结

- **微调 vs Prompt vs RAG**：先试 Prompt，再试 RAG，最后才微调
- **LoRA**：低成本微调主流方案，用 0.1% 参数达到 90% 效果
- **数据质量**：比数据量更重要，人工验证每条数据
- **Agent 场景**：微调主要用于工具调用格式对齐和领域任务适配
- **避坑**：灾难性遗忘、过拟合、格式不稳定是最常见的三个坑

> 本篇完结。回到 [Agent 循环](../05-agent-loop/README.md)，你已经掌握了模型接入的全部知识，现在可以构建能自主决策的 Agent 了。

## 参考链接

- [LoRA 论文 (2021)](https://arxiv.org/abs/2106.09685) — 低成本微调的核心技术
- [QLoRA 论文 (2023)](https://arxiv.org/abs/2305.14314) — 4-bit 量化 + LoRA
- [Hugging Face — PEFT 文档](https://huggingface.co/docs/peft/) — LoRA 实现库
- [Hugging Face — TRL 文档](https://huggingface.co/docs/trl/) — 训练框架
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — Agent 开发者的微调建议
