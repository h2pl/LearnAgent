# 视频理解

> 视频是多模态 AI 最难的感知任务——一张图是二维的，一段视频是三维的（空间+时间）。本文拆解视频理解的底层挑战、工程策略和三种主流方案的实际效果。

## 目录

- [视频理解为什么比图片难一个数量级](#视频理解为什么比图片难一个数量级)
- [方案一：抽帧分析（最通用）](#方案一抽帧分析最通用)
- [方案二：原生连续处理（Gemini独有）](#方案二原生连续处理gemini独有)
- [方案三：专项视频模型](#方案三专项视频模型)
- [三种方案实测对比](#三种方案实测对比)
- [实战：搭建视频分析流水线](#实战搭建视频分析流水线)
- [成本模型：一段视频花多少钱](#成本模型一段视频花多少钱)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前两篇讲了 VLM 的演进和三大旗舰的定位差异。这一篇聚焦最硬核的视觉任务——视频理解。它不是"看很多张图"的简单累加，而是一个有自己独特难点的独立问题域。

## 视频理解为什么比图片难一个数量级

### 数据量爆炸

一段 10 秒的 1080p 30fps 视频：

```
10 秒 × 30 帧/秒 = 300 帧
每帧 1920×1080×3 颜色通道 = 6,220,800 个像素值
总计 = 300 × 6,220,800 ≈ 18.7 亿个像素值
```

把 18.7 亿个像素值全喂给模型不现实——GPT-4o 的输入上限约 128K Token。所以视频理解的第一个工程问题是：**怎么从 300 帧里选出最有信息量的几个瞬间？**

### 时序因果性

图片是静态的——一张猫的照片，你可以从头看到脚，从脚看到头，没有"顺序"约束。但视频有：

- "球员射门"——必须先有跑动、再有摆腿、最后才有球飞出去。帧的顺序不可颠倒
- "在煮面"——锅里的水从冷到热到沸腾，状态连续变化

模型不仅要知道"每一帧里有什么"，还要理解**帧和帧之间的因果关系和时间顺序**。

### 运动与遮挡

- 快速运动：足球比赛射门瞬间，足球在相邻两帧之间的位置差可以超过球的直径。相邻帧之间的物体几乎没有重叠——传统的目标追踪算法会失效
- 遮挡：一个人走过一面镜子，镜中倒影和真人"打架"——哪一个是真实物体？
- 运动模糊：低光环境下的视频，快速移动的物体在每一帧上都是模糊拖影

### 语义的时间跨度

不同视频内容的信息密度差异巨大：

- 10 秒的体育动作回放：每一帧都关键，含极密集的运动信息
- 1 小时的监控录像：90% 的时间是静态画面，真正的"事件"只有几十秒
- 30 分钟的产品演示视频：说话人在讲，但视觉信息变化不大，关键信息在语音而非画面

**同一个"视频理解"任务，对体育视频和监控视频需要完全不同的处理策略。**

## 方案一：抽帧分析（最通用）

这是目前最主流的方案——GPT-4o、Claude、Qwen-VL 都用这个思路。

### 核心策略

```
视频文件 (10分钟, 18000帧)
    ↓
按策略抽取 N 帧 (通常 10-64帧)
    ↓
每帧 = 一张图片 → VLM分析
    ↓
汇总所有帧的分析结果 → 形成对整段视频的理解
```

抽帧策略的选择是关键——抽少了丢信息，抽多了浪费 Token。

### 四种抽帧策略

| 策略 | 怎么做 | 适合场景 | 不适合场景 |
|------|--------|---------|-----------|
| **均匀采样** | 固定间隔抽帧（每N秒一帧） | 变化均匀的视频（讲座、演示） | 有快速动作段+静态段的混合视频 |
| **关键帧检测** | 用画面变化量算法找"变化大"的帧 | 体育、动作片 | 对话类（视觉变化小的场景） |
| **场景分割+每场景抽关键帧** | 先用算法切场景，每个场景抽 1-2 帧 | 多场景切换的视频（会议、课程） | 单场景长镜头 |
| **自适应密度** | 信息密度高处多抽，低处少抽 | 混合内容视频 | 需要额外预处理步骤 |

### 代码实现：均匀采样 + GPT-4o

```python
import cv2
import base64
from openai import OpenAI

def extract_frames_uniform(video_path, num_frames=16):
    """均匀采样N帧"""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    interval = max(1, total_frames // num_frames)

    frames = []
    timestamps = []
    for i in range(0, total_frames, interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret and len(frames) < num_frames:
            # 压缩到合理分辨率
            frame = cv2.resize(frame, (512, 512))
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append(base64.b64encode(buffer).decode())
            timestamps.append(i / cap.get(cv2.CAP_PROP_FPS))
    cap.release()
    return frames, timestamps

# 使用
frames, timestamps = extract_frames_uniform("demo.mp4", num_frames=16)
content = [{"type": "text", "text": "分析这段视频中发生的所有操作步骤，标注每步大致发生的时间"}]
for i, frame in enumerate(frames):
    content.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
    })

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": content}],
    max_tokens=1000
)
print(response.choices[0].message.content)
```

### 抽帧方案的局限

抽帧方案的根本问题：**帧之间的信息链路断了。**

"他从桌上拿起水杯，喝了一口，然后放下"——这三个动作是连续的，但在抽帧方案中变成了三个孤立的画面。模型可能第一帧看到"手在杯子上"，第三帧看到"杯子在桌上"，但中间发生了什么？它只能猜。

对需要**精确时序判断**的场景——体育裁判、医学影像、工业自动化——抽帧方案的准确度上限很低。

## 方案二：原生连续处理（Gemini 独有）

Gemini 是目前唯一支持原生视频连续处理的商业模型。它的视频理解不是"抽帧→逐帧分析→汇总"，而是把视频当作**连续的 Token 数据流**来处理。

### 技术原理

原生连续处理的核心机制是**时间注意力**：

```
传统抽帧方案：
帧1 → [VLM处理] → 结果1
帧2 → [VLM处理] → 结果2    （帧1和帧2没有直接交互）
帧3 → [VLM处理] → 结果3
      ↓
汇总结果1+2+3 → 回答

Gemini原生处理：
帧1 → ┐
帧2 → [统一的Transformer，自注意力机制跨所有帧]  → 综合理解
帧3 → ┘
```

因为所有帧在同一个 Transformer 里通过自注意力交互，模型可以建立帧与帧之间的直接关联。第 5 帧里发生了什么，可以通过直接关注第 4 帧和第 6 帧来理解——不需要先"逐帧描述"再"跨帧对比"。

### Gemini 视频分析的代码

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-2.5-flash")  # Flash版本对视频有优化

# 上传视频——直接传文件，不需要抽帧
video = genai.upload_file("product_demo.mp4")

# 等待处理完成
import time
while video.state.name == "PROCESSING":
    time.sleep(2)
    video = genai.get_file(video.name)

# 分析
response = model.generate_content([
    video,
    """请按时间线分析这段产品演示视频：
    1. 每个操作步骤的开始和结束时间点
    2. 用户在每个步骤的操作路径（点击了什么、输入了什么）
    3. 是否有异常或不符合预期的操作"""
])
print(response.text)
```

### 什么场景下原生处理不可替代

- **体育动作分析**：需要精确判断动作的起始帧和结束帧，抽帧方案容易错过
- **安全监控**："从进入画面到离开画面，这个人停留了多久？做了什么？"
- **工业检测**：传送带上物体的连续运动轨迹分析
- **医学视频**：内窥镜或超声视频中病变的动态变化

在这些场景里，抽帧方案和原生连续处理的差距不是"90分 vs 95分"，而是"不可用 vs 可用"。

## 方案三：专项视频模型

除了通用 VLM（GPT-4o、Gemini）的视频理解，还有专门为视频设计的模型：

### 视频理解专项模型

| 模型 | 公司 | 专长 |
|------|------|------|
| **Twelve Labs** | Twelve Labs | 语义视频搜索——用自然语言搜视频中的片段 |
| **Video-LLaVA** | 开源社区 | 开源视频对话模型 |
| **TimeSformer** | Meta | 基于时空注意力的视频分类 |
| **VideoMAE** | Meta | 自监督视频预训练，动作识别 |

### Twelve Labs：语义视频搜索

这是最实用的专项工具之一——你不需要抽帧，不需要写分析逻辑，直接用自然语言在视频库中搜索：

```python
# Twelve Labs 的语义搜索
query = "顾客在收银台用手机支付的片段"
results = twelve_labs_client.search(
    index_id="store_surveillance",
    query=query
)
# 返回所有匹配的视频片段和精确时间戳
for segment in results:
    print(f"视频: {segment.video_id}, 时间: {segment.start}-{segment.end}, 置信度: {segment.score}")
```

这对视频资产管理、监控视频检索、体育赛事回放等场景是革命性的。

## 三种方案实测对比

基于相同的测试任务（分析一段 5 分钟的咖啡机制作教程视频，提取操作步骤），三种方案的表现：

| 维度 | 抽帧+GPT-4o (16帧) | Gemini原生处理 | Video-LLaVA (开源) |
|------|:--:|:--:|:--:|
| 步骤提取完整度 | ★★★☆☆ | ★★★★★ | ★★☆☆☆ |
| 时间戳准确度 | ★★☆☆☆ | ★★★★★ | ★☆☆☆☆ |
| 细节识别（按钮/手势）| ★★★★☆ | ★★★☆☆ | ★★★☆☆ |
| 响应速度 | ★★★★☆ | ★★★☆☆ | ★★★★★ |
| 成本 | 中（16张图片Token） | 高（按视频时长计） | 免费 |
| 中文 Prompt 理解 | ★★★★★ | ★★★★☆ | ★★★☆☆ |

**抽帧方案在细节识别上反而更好**——因为每帧作为独立图片交给 VLM 分析，GPT-4o 的静态图片理解能力极强。但时序一致性明显不如原生处理。

## 实战：搭建视频分析流水线

一个生产级的视频分析流水线需要结合多种策略：

```python
import cv2
from openai import OpenAI
from typing import List, Dict

class VideoAnalyzer:
    def __init__(self, openai_client, gemini_client=None):
        self.openai = openai_client
        self.gemini = gemini_client

    def analyze(self, video_path: str, task: str) -> Dict:
        """统一入口——根据任务类型选择方案"""
        cap = cv2.VideoCapture(video_path)
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        # 短视频 (< 2分钟) + 精确时序需求 → Gemini
        if duration < 120 and self._needs_temporal_precision(task):
            return self._gemini_continuous(video_path, task)

        # 长视频 → 场景分割 + 关键场景抽帧 + GPT-4o
        elif duration >= 120:
            return self._scene_based_sampling(video_path, task)

        # 默认 → 均匀采样 + GPT-4o
        else:
            return self._uniform_sampling(video_path, task)

    def _needs_temporal_precision(self, task: str) -> bool:
        keywords = ["步骤", "时间线", "顺序", "动作", "运动", "变化过程"]
        return any(kw in task for kw in keywords)

    def _uniform_sampling(self, video_path, task):
        # 使用前面定义的 extract_frames_uniform
        frames, _ = extract_frames_uniform(video_path, num_frames=16)
        return self._call_gpt4o_vision(frames, task)

    def _scene_based_sampling(self, video_path, task):
        """场景分割后每场景抽关键帧"""
        scenes = detect_scene_changes(video_path)
        keyframes = []
        for scene_start, scene_end in scenes:
            mid_frame = extract_keyframe(video_path, (scene_start + scene_end) / 2)
            keyframes.append(mid_frame)
        return self._call_gpt4o_vision(keyframes, task)

    def _gemini_continuous(self, video_path, task):
        video = genai.upload_file(video_path)
        response = self.gemini.generate_content([video, task])
        return {"method": "gemini_continuous", "result": response.text}

    def _call_gpt4o_vision(self, frames, task):
        content = [{"type": "text", "text": task}]
        for frame in frames:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame}"}})
        response = self.openai.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": content}]
        )
        return {"method": "gpt4o_sampling", "result": response.choices[0].message.content}
```

这个流水线根据视频长度和任务类型自动选择处理方案——不需要你手动判断用抽帧还是原生连续。

## 成本模型：一段视频花多少钱

| 方案 | 10秒视频 | 1分钟视频 | 10分钟视频 |
|------|:--:|:--:|:--:|
| 均匀采样+GPT-4o (16帧) | ~$0.03 | ~$0.03 | ~$0.03 |
| 均匀采样+GPT-4o (64帧) | ~$0.12 | ~$0.12 | ~$0.12 |
| Gemini原生连续处理 | ~$0.05 | ~$0.30 | ~$3.00 |
| 场景分割+GPT-4o | ~$0.05 | ~$0.15 | ~$0.50 |
| 开源方案 (Video-LLaVA) | 免费 | 免费 | 免费 |

**成本洞察**：抽帧方案的成本和视频长度几乎无关——因为只处理固定数量的帧。原生连续方案的成本随视频长度线性增长。所以长视频用抽帧、短视频用原生处理是经济上最优的策略。

## 总结

- 视频理解的难度来自四个维度：**数据量爆炸**（18亿像素值/10秒）、**时序因果性**、**运动与遮挡**、**不同内容的信息密度差异巨大**
- **抽帧分析是通用方案**，适合大多数场景——关键在于抽帧策略的选择（均匀/关键帧/场景分割/自适应密度）
- **Gemini 的原生连续处理**在需要精确时序判断的场景是唯一可用方案，代价是成本随视频长度线性增长
- 专项视频模型如 Twelve Labs 在视频搜索和检索场景中有独特优势
- 生产级视频分析应该**根据视频长度和任务类型自动选择处理方案**——长短结合、动静分离
- 下一篇从动态回到静态，但聚焦一个更有实用价值的话题——[文档、图表与 UI 理解](./04-document-and-ui.md)

## 参考链接

- [Gemini 视频理解文档](https://ai.google.dev/gemini-api/docs/vision)
- [Twelve Labs 视频搜索 API](https://docs.twelvelabs.io/)
- [Video-LLaVA 论文](https://arxiv.org/abs/2311.10122)
- [TimeSformer: Is Space-Time Attention All You Need?](https://arxiv.org/abs/2102.05095)
- [VideoMAE: Masked Autoencoders for Video](https://arxiv.org/abs/2203.12602)

> 视频理解是最硬核的视觉任务。但日常工作中你更频繁遇到的是另一类问题——怎么让 AI 读 PDF、看懂图表、理解 UI 界面。下一篇 [文档、图表与 UI 理解](./04-document-and-ui.md) 聚焦这三个最高频的视觉 AI 落地场景。
