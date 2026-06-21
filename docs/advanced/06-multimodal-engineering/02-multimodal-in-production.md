# 多模态工程实践：评估、成本与上线

> 前六篇讲了多模态的原理和能力。这篇收尾：把所有工程侧的问题集中解决——怎么评估质量、怎么控制成本、怎么监控、怎么安全上线。从 demo 到生产，需要补的就是这些。

## 目录

- [多模态评估：不能只看文本指标](#多模态评估不能只看文本指标)
- [成本控制：算清楚每种模态的账](#成本控制算清楚每种模态的账)
- [可观测性：多模态 trace 怎么抓](#可观测性多模态-trace-怎么抓)
- [延迟优化：从模型路由到流式处理](#延迟优化从模型路由到流式处理)
- [安全与治理](#安全与治理)
- [上线 checklist](#上线-checklist)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。这是多模态栏目的最后一篇。前面我们从全景到机制、从能力到推理，把多模态"是什么"和"怎么用"都讲清楚了。但一个系统能不能上线、上了之后能不能持续运转，取决于工程层面的事情——评估、成本、监控、安全。

这篇对应主线 13-16 章（评测、可观测、安全、交付）的角色，只不过聚焦在多模态场景下。

## 多模态评估：不能只看文本指标

纯文本系统的评估相对简单：准确率、F1、BLEU、或者 LLM Judge 打分。多模态系统需要更多维度的评估。

### 多模态特有的评估维度

| 维度 | 含义 | 怎么测 |
|------|------|--------|
| 视觉准确率 | 图片/视频理解是否正确 | 标注数据集 + 人工抽查 |
| 跨模态一致性 | 是否同时利用了所有输入模态 | LLM Judge 评估融合度 |
| 音频延迟 | 语音交互的端到端延迟 | 自动测量首音频 token 延迟 |
| 生成质量 | 生成图像的美学/真实性 | CLIP Score + 人工评估 |
| 鲁棒性 | 输入质量下降时的表现 | 噪声/模糊/截断测试 |

### 构建多模态回归测试集

```python
# 回归测试集的结构
multimodal_regression_set = [
    # 视觉理解类
    {
        "type": "vision",
        "input": {"image": "test_images/chart_001.png", "text": "Q3 收入是多少？"},
        "expected": "4.2 亿美元",
        "tolerance": "exact_match",
    },
    # 跨模态推理类
    {
        "type": "cross_modal",
        "input": {"image": "test_images/contract.png", "text": "和邮件条款一致吗？"},
        "expected_keywords": ["一致", "net 30"],
        "evaluation": "llm_judge",
    },
    # 语音类
    {
        "type": "audio",
        "input": {"audio": "test_audio/query_001.mp3"},
        "expected": "明天下午三点的会议",
        "tolerance": "semantic_match",
    },
]
```

### 持续评估

不能只在上线前评一次。生产环境的数据分布会漂移，需要持续评估：

- 每周对线上请求做 5% 抽样评估
- 用 LLM Judge 自动打分 + 人工复核异常样本
- 设立告警阈值：准确率下降超过 2% 时触发

## 成本控制：算清楚每种模态的账

多模态系统的成本比纯文本复杂得多。每种模态的计费方式不同。

### 各模态成本模型

**文本**（按 token 计费）：
- 最便宜，约 $3-15 / 1M input tokens
- 1000 中文字 ≈ 1500 tokens

**图像理解**（按 image token 计费）：
- 一张标准图片 ≈ 1000-2000 text tokens 的成本
- 高分辨率图片（4K）可能消耗 10000+ tokens
- **一张图 ≈ 1000 字文本的成本**

**语音**（按秒/分钟计费）：
- Whisper STT：$0.006 / 分钟
- TTS：$15-30 / 1M 字符
- Realtime API：$0.06-0.24 / 分钟（输入+输出）

**图像生成**（按张计费）：
- DALL-E 3：$0.04-0.08 / 张
- Stable Diffusion API：$0.01-0.05 / 张
- 本地部署：只算 GPU 时间，约 $0.001-0.005 / 张

**视频生成**（按秒计费）：
- Runway / Kling：$0.05-0.50 / 秒
- 生成 10 秒视频：$0.5-5

### 成本优化策略

**图像侧**：
- 压缩分辨率（256×256 做场景理解够了）
- 裁剪感兴趣区域（不传整屏截图）
- 视频降低采样帧率（2-5 秒一帧）
- 缓存重复图片的理解结果

**语音侧**：
- 本地 Whisper 做 STT（免费）
- 控制语音输出长度（模型回答控制在 3 句以内）
- 非实时场景用异步 TTS（更便宜）

**生成侧**：
- 优先检索已有素材，找不到再生成
- 用低分辨率 draft 确认构图，再高分辨率精修
- 批量生成比逐张生成便宜

### 成本预估公式

```
单次多模态交互成本 ≈ 
  文本 token 成本 + 
  图片数量 × 单图 token 成本 + 
  语音时长 × 语音单价 + 
  图片生成数量 × 单张成本
```

举例：一次"用户发了一张截图 + 语音提问 + 文字回答"的交互：
- 图片理解：~2000 tokens ≈ $0.006
- 语音转录：~10 秒 ≈ $0.001
- 文字回答：~500 tokens ≈ $0.002
- 总计：约 $0.01 / 次

## 可观测性：多模态 trace 怎么抓

纯文本系统的 trace 很简单：输入文本→模型推理→输出文本。多模态系统的 trace 需要捕获更多维度的信息。

### 多模态 trace 需要记录什么

```python
# 一次多模态交互的 trace 结构
{
    "trace_id": "abc123",
    "timestamp": "2026-06-21T10:30:00Z",
    "spans": [
        {
            "name": "image_processing",
            "input_modality": "image",
            "image_tokens": 1847,
            "image_resolution": "1024x768",
            "duration_ms": 230,
        },
        {
            "name": "audio_processing",
            "input_modality": "audio",
            "audio_duration_sec": 8.5,
            "transcript": "帮我看看这个报错怎么解决",
            "duration_ms": 150,
        },
        {
            "name": "llm_reasoning",
            "input_tokens": 2347,  # text + image tokens
            "output_tokens": 456,
            "model": "claude-opus-4-7",
            "duration_ms": 1200,
        },
        {
            "name": "tts_output",
            "output_modality": "audio",
            "output_duration_sec": 5.2,
            "duration_ms": 300,
        },
    ],
    "total_latency_ms": 1880,
    "total_cost_usd": 0.012,
}
```

### 关键指标

- **首 token 延迟**（TTFT）：用户发完消息到收到第一个回复 token 的时间
- **首音频延迟**（TTFA）：语音场景下收到第一个音频片段的时间
- **模态使用率**：模型是否真的用了所有输入模态（还是只看了文字）
- **Token 消耗分布**：多少 token 来自文本、多少来自图像
- **端到端延迟**：从用户操作完成到收到完整回复的总时间

### 工具选择

- **OpenTelemetry + 自定义 span**：最灵活，可以记录任意多模态元数据
- **LangSmith / Langfuse**：支持多模态 trace 的可视化
- **自建仪表盘**：Grafana + Prometheus，重点监控延迟和成本指标

## 延迟优化：从模型路由到流式处理

多模态系统的延迟是用户体感最敏感的指标。文本对话 3 秒延迟可接受，语音对话超过 1 秒就会让人觉得卡。

### 延迟来源分析

```
总延迟 = 网络传输 + 模态编码 + 模型推理 + 输出生成
```

各部分的典型耗时：
- 网络传输：50-200ms
- 图像编码：100-300ms
- 音频编码（Whisper）：200-500ms
- 模型推理（LLM）：500-2000ms
- TTS 生成：200-500ms（流式）/ 1000-3000ms（非流式）

### 优化策略

**模型路由（小模型本地 + 大模型云端）**：

```python
async def route_request(user_input):
    # 简单请求 → 本地小模型（快、免费）
    if is_simple_query(user_input):
        return await local_model.generate(user_input)

    # 需要多模态推理 → 云端大模型
    if has_image(user_input) or needs_deep_reasoning(user_input):
        return await cloud_model.generate(user_input)

    # 默认 → 云端中等模型
    return await cloud_model_medium.generate(user_input)
```

**流式处理**：
- 音频：流式 TTS，边生成边播放
- 图像理解：先返回低分辨率快速结果，再返回高精度结果
- 文本：streaming 输出（这个大家都在用了）

**并行处理**：
- 图片编码和文本编码可以并行
- 多个子任务（如"看图"和"查数据库"）可以并行执行

**缓存**：
- 相同图片的理解结果缓存（用图片 hash 做 key）
- 相似查询的推理结果缓存（用 embedding 相似度做 key）

## 安全与治理

多模态系统面临的安全挑战比纯文本更多。

### 多模态特有的安全风险

**对抗图像/音频**：精心修改的图片或音频可能让模型产生错误输出。虽然 2026 年这类攻击已经减少，但在高风险场景仍需注意。

**隐私泄露**：
- 用户可能上传包含敏感信息的图片（身份证、银行卡、密码）
- 模型会"看到"并在回答中泄露这些信息
- 音频可能包含背景对话（旁边人在说私密内容）

**深度伪造**：
- 图像生成能力可能被用于生成虚假证据
- 语音克隆可能用于冒充他人
- 需要在使用条款中明确禁止恶意使用

### 防御措施

```python
# 图像安全检查流程
async def safe_image_processing(image):
    # 1. PII 检测：模糊化敏感信息
    image = detect_and_blur_pii(image)

    # 2. 内容安全：检查是否包含违禁内容
    safety_check = await content_safety_model.analyze(image)
    if safety_check.flagged:
        return "图片包含不适当内容，无法处理"

    # 3. 正常处理
    return await multimodal_model.analyze(image)
```

**治理框架**：
- 记录所有多模态交互的审计日志
- 对生成内容打水印（标识 AI 生成）
- 限制敏感场景下的图像生成能力
- 定期审查模型输出中的偏见和有害内容

## 上线 checklist

从 demo 到生产，确认以下每一项都就绪：

### 功能验证

- [ ] 所有目标模态的输入输出都经过测试
- [ ] 跨模态推理场景覆盖（不只是单模态任务）
- [ ] 边界情况测试（空图片、无声音频、超长视频）
- [ ] 多模态混合输入测试（图片+文字+音频同时输入）

### 质量保障

- [ ] 回归测试集 ≥ 100 条，覆盖主要场景
- [ ] 自动评估 pipeline 就绪（CI/CD 集成）
- [ ] LLM Judge 评估配置完毕，和人工评估对齐率 > 85%
- [ ] 人工评估 baseline 已建立

### 性能与成本

- [ ] 延迟指标达标（文本 < 2s、语音首音频 < 1s）
- [ ] 成本预估完成，有 budget 上限告警
- [ ] 图片分辨率/音频采样率优化到性价比最优点
- [ ] 缓存策略已实现并验证命中率

### 可观测性

- [ ] 多模态 trace 接入完毕，能看到每个 span
- [ ] 关键指标仪表盘上线（延迟、成本、准确率）
- [ ] 告警规则配置（延迟突增、成本超支、准确率下降）
- [ ] 日志收集完整（包含模态元数据）

### 安全与合规

- [ ] PII 检测/模糊化就位
- [ ] 内容安全检查覆盖所有输入模态
- [ ] 生成内容水印策略确定
- [ ] 审计日志记录完整
- [ ] 数据保留和删除策略明确

### 运维

- [ ] 模型降级方案（云端不可用时切换到本地模型）
- [ ] A/B 测试框架就位（方便切换模型版本）
- [ ] 回滚流程验证通过
- [ ] on-call 手册包含多模态特有的故障排查步骤

## 总结

多模态系统的工程化比纯文本系统复杂一个量级。核心要点：

- **评估**：需要多维指标——视觉准确率、跨模态一致性、延迟、成本都要度量
- **成本**：图像 token 和语音时长是主要成本来源，优化策略包括压缩、裁剪、缓存、路由
- **可观测性**：trace 需要记录每种模态的元数据，不能只记文本
- **延迟**：模型路由 + 流式处理 + 并行 + 缓存是四大优化手段
- **安全**：对抗攻击、隐私泄露、深度伪造是多模态特有的风险
- **上线**：用 checklist 确保每个环节都覆盖到

---

这就是多模态栏目的全部内容。我们从全景认知出发，经过核心机制、逐项能力、跨模态推理，最终到达工程落地。这七篇文章构成了一个完整的知识闭环——和主线 16 章的"认知→原理→技能→架构→交付"是同样的叙事节奏。

多模态 AI 还在快速演进。这个栏目会持续更新，覆盖新的模型能力、新的工程模式和新的最佳实践。

> 返回栏目总览：[进阶扩展 — 多模态 AI 系统化讲解](../README.md)

## 参考链接

- [OpenAI Pricing](https://openai.com/pricing)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Google Gemini Pricing](https://ai.google.dev/pricing)
- [OpenTelemetry for AI/ML](https://opentelemetry.io/blog/2024/genai-otel/)
- [Langfuse Multi-Modal Tracing](https://langfuse.com/docs/tracing)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
