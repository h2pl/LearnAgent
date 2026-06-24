# 生成实战与选型

> 图像、视频、原生输出——三篇文章拆开了讲。这一篇把它们串成你可以直接使用的选型指南和实战工作流。回答一个所有人都要面对的问题：这么多生成工具，我该用哪个、怎么用、花多少钱。

## 目录

- [统一选型框架](#统一选型框架)
- [图像生成选型指南](#图像生成选型指南)
- [视频生成选型指南](#视频生成选型指南)
- [Prompt 工程：生成质量的瓶颈不是模型](#prompt-工程生成质量的瓶颈不是模型)
- [成本全景](#成本全景)
- [完整实战：搭建一个品牌物料自动生成系统](#完整实战搭建一个品牌物料自动生成系统)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面的三篇文章分别拆了图像、视频和原生输出。这一篇把选型逻辑和实战经验整合起来，让你不只是知道"有什么"，而是知道"怎么做"。

## 统一选型框架

选择生成工具的决策维度有五个：

```
你的生成需求
    ├── 精度要求：追求最高画质 or 够用就行？
    ├── 迭代模式：一次性出图 or 需要来回修改？
    ├── 预算约束：免费 or 几美元 or 专业订阅？
    ├── 生态需求：独立工具 or 需要和其他系统联动？
    └── 部署要求：云 or 本地？
```

## 图像生成选型指南

### 按场景选

| 你的场景 | 推荐工具 | 月成本 | 核心优势 |
|---------|---------|:--:|------|
| 随便玩玩、快速试效果 | ChatGPT 内 DALL-E | $20 | 最方便，聊天中直接生成 |
| 追求最高画质的个人创作 | Midjourney | $10-60 | 画质公认第一 |
| 需要反复修改、精确控制 | GPT-4o 原生生图 | $20 | 多轮迭代编辑，一致性最佳 |
| 大批量、自动化、定制 | SD 3.5/Flux + ComfyUI | 免费+GPU | 完全可控、可脚本化 |
| 电商商品图 | 通义万相 / Seedream | 按量付费 | 中文优化，电商场景 |
| 中文海报/封面 | Seedream / ChatGPT DALL-E | 免费-$20 | 中文文字渲染要好 |

### 按成本选

```python
# 假设每天生成 20 张图片，比较月成本
midjourney_basic = 10         # $10/月
chatgpt_plus_dalle = 20        # $20/月（无限次DALL-E）
sd_local = 0 + 0.30 * 30      # ~$9/月电费（RTX 3090）
api_dalle = 0.08 * 20 * 30    # ~$48/月 DALL-E API
api_sd = 0.02 * 20 * 30       # ~$12/月（Replicate托管SD/Flux）
```

## 视频生成选型指南

| 你的场景 | 推荐工具 | 成本参考 | 核心优势 |
|---------|---------|:--:|------|
| 专业视频创作（海外） | Runway Gen-4 | $35/月起 | 完整工具链+最高画质 |
| 中文短视频 | 可灵 / 即梦 AI | 免费+付费 | 中文理解好+免费额度 |
| 人物一致性场景 | Seedance | 免费+付费 | 同一人物多次生成保持外貌 |
| 创意玩法和特效 | Pika | 免费+付费 | 趣味玩法多 |
| 3D 视角视频 | Luma | 按量付费 | 3D一致性 |

## Prompt 工程：生成质量的瓶颈不是模型

生成式 AI 领域有一个反直觉的规律：**出图质量 60% 靠 Prompt 质量，25% 靠选对模型，15% 靠模型本身的能力。** 大多数人抱怨"AI 画不好"时，问题在 Prompt，不在模型。

### 图像生成 Prompt 的五个维度

```
维度1 主体：你要什么？（一只猫/一座城市/一张海报）
维度2 环境：在什么地方？（窗台上/雨天的街道/咖啡店）
维度3 风格：什么画风？（写实/插画/油画/赛博朋克/浮世绘）
维度4 光影：什么光照？（午后阳光/柔和的摄影棚光/霓虹灯/月光）
维度5 参数：技术细节（分辨率/宽高比/模型版本/随机种子）

好的 Prompt = 主体清晰 × 环境具体 × 风格明确 × 光照有细节 × 参数合理
```

### 视频生成 Prompt 的额外维度

视频 Prompt 比图像多了两个维度：**动作（Movement）** 和 **镜头（Camera）**。

```
动作：一只猫从窗台跳下来，落地后甩了甩尾巴
镜头：镜头从低角度缓缓上摇，跟随猫的跳跃动作
      浅景深，背景虚化，慢动作 60fps
```

### 迭代策略：从粗到精

```
第1轮：用非常简单的 Prompt 出图，看模型的理解方向
       "a cat sitting on a windowsill"

第2轮：加入风格和光影，让画面"好看"
       "a cat sitting on a windowsill, golden hour
        lighting, film photography, cozy atmosphere"

第3轮：微调细节，精修不满意的地方
       "--no ugly, distorted, low quality --ar 16:9"
```

不要期望第一轮就出完美结果。Prompt 工程的核心是**快速迭代**——用简单 Prompt 锁定方向，再用细节 Prompt 提升质量。

## 成本全景

### 图像生成的月度成本估算

```
轻量级（每天 10 张图）：
  ChatGPT Plus (DALL-E) ：$20/月 ← 推荐
  Midjourney Basic ：$10/月
  SD 本地：~$5/月电费

中等量（每天 50 张图）：
  Midjourney Standard ：$30/月
  API调用（DALL-E）：~$120/月
  API调用（SD托管）：~$30/月 ← 性价比最高

大量（每天 500 张图）：
  必须本地部署 SD/Flux
  硬件投入：$1500 RTX 4090（一次性）
  月电费：~$30
```

### 视频生成的月度成本估算

```
轻量级（每天 2-3 段 5秒视频）：
  可灵免费额度：$0 ← 推荐
  Runway Basic ：$15/月

中等量（每天 10 段）：
  可灵付费 ：约￥30-50/月
  Runway Standard ：$35/月

大量（每天 50+ 段）：
  Runway + 可灵 混合使用
  约 ¥200-500/月
```

## 完整实战：搭建一个品牌物料自动生成系统

把本章所有知识串起来——一个自动生成社交媒体物料的系统：

```python
class BrandContentGenerator:
    """品牌物料自动生成器"""

    def __init__(self, openai_client, brand_style):
        self.client = openai_client
        self.brand = brand_style  # {"colors": [...], "fonts": [...], "tone": "..."}

    def generate_social_post(self, topic, platform="wechat"):
        """为指定话题生成完整的社交媒体内容"""

        # 1. 用GPT-4o生成文案（理解+创作）
        copy_response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": f"你是{self.brand['name']}的文案，风格：{self.brand['tone']}。"
            }, {
                "role": "user",
                "content": f"写一段关于'{topic}'的{platform}文案，150字以内。"
            }]
        )
        copy_text = copy_response.choices[0].message.content

        # 2. 用GPT-4o原生生成配图（理解+生成合一）
        image_response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"""生成一张{platform}风格的配图：
                    主题：{topic}
                    文案：{copy_text}
                    品牌色：{', '.join(self.brand['colors'])}
                    风格：简洁现代，留白充足，适合社交媒体浏览"""}
                ]
            }]
        )

        # 3. 整合输出
        return {
            "platform": platform,
            "copy": copy_text,
            "image": image_response,  # 模型原生生成的图片
            "hashtags": self._generate_hashtags(topic)
        }

    def generate_batch(self, topics, platforms=["wechat", "xiaohongshu"]):
        """批量生成多平台多话题内容"""
        results = []
        for topic in topics:
            for platform in platforms:
                content = self.generate_social_post(topic, platform)
                results.append(content)
        return results
```

这个系统的关键在于：文案和图片是由同一个模型完成的——它们共享上下文，理解一致。文案中提到的颜色会自动反映在配图中；配图的风格和文案的调性自然匹配。传统模式（ChatGPT 写文案 + 其他工具配图）做不到这种程度的一致性。

## 总结

- 生成工具选型没有"最好"，只有"最合适"——**五个决策维度：精度、迭代、预算、生态、部署**
- **Prompt 质量决定了 60% 的出图质量**——花 10 分钟打磨 Prompt 比花 10 美元升级模型更有效
- 图像生成成本区间：$0-120/月，视频生成：$0-500/月——**高频场景必须本地部署开源方案**
- 原生多模态输出正在改变"文案+配图"的工作流——理解+生成在同一个模型中完成，上下文一致
- 05 章全部结束。最后一章把所有知识落地到生产环境：[06 工程落地](../06-engineering-production/README.md)

## 参考链接

- [DALL-E Prompt 工程指南](https://platform.openai.com/docs/guides/images/prompting)
- [Midjourney Prompt 指南](https://docs.midjourney.com/docs/prompts)
- [Stable Diffusion 社区 Wiki](https://stable-diffusion-art.com/)
- [可灵 AI Prompt 指南](https://klingai.kuaishou.com/)

> 生成领域的工具和实战全部讲完。但 AI 生成的图片和视频怎么评估好坏？部署到线上要怎么做安全合规？最后一章 [06 工程落地](../06-engineering-production/README.md) 补齐这些工程必修课。
