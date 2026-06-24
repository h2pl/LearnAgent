# 文档、图表与 UI 理解

> 你可能不需要视频理解，但你一定需要 AI 读 PDF、看图表、分析界面截图。这是三个最高频的视觉 AI 落地场景——拆解为什么有的方案"能看"但不能"看懂"，以及怎么选对工具。

## 目录

- [三个场景，三个挑战](#三个场景三个挑战)
- [文档理解：PDF 里的文字和表格](#文档理解pdf-里的文字和表格)
- [图表理解：从像素到数据](#图表理解从像素到数据)
- [UI 理解：截图里的界面逻辑](#ui-理解截图里的界面逻辑)
- [方案选型：VLM 够用吗](#方案选型vlm-够用吗)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前几篇讲的都是模型演进和底层原理。这篇回到你最常遇到的真实场景——一份 PDF 合同、一张财报图表、一个 App 界面截图。这三件事的 AI 处理比你想象的更复杂，也比你以为的更好用。

## 三个场景，三个挑战

| 场景 | 核心挑战 | 为什么普通 VLM 不够 |
|------|---------|-------------------|
| **文档理解** | 版面复杂、表格嵌套、手写体 | VLM 看 PDF 像看一张图，丢掉了文本的结构化信息 |
| **图表理解** | 需要精确数值，不是"大概" | VLM 对柱状图能说出趋势，但说不出精确数值 |
| **UI 理解** | 元素层级、交互逻辑、状态变化 | VLM 看不到按钮的"可点击性"和输入框的"当前值" |

## 文档理解：PDF 里的文字和表格

### VLM 直接看 PDF：能看，但不够

最简单的做法：PDF 转图片 → VLM 看图理解。这在简单文档上效果不错：

```python
from pdf2image import convert_from_path
from openai import OpenAI

client = OpenAI()
images = convert_from_path("contract.pdf", dpi=200)  # PDF→图片

content = [{"type": "text", "text": "提取这份合同中的关键条款：违约责任、付款条件、保密条款"}]
for img in images[:10]:  # 限制页数
    img_base64 = pil_to_base64(img)
    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})

response = client.chat.completions.create(
    model="gpt-4o", messages=[{"role": "user", "content": content}]
)
```

但这个方案有三类问题：

**问题一：表格提取不准**。VLM 看到的是表格的"图片"——它知道"这是一个 4 列 6 行的表格"，但对于"每个单元格里精确的内容是什么"经常出错。特别是数字密集的财务报表——把 1,234,567 看成 1,234,568 是常见错误。

**问题二：版面复杂度**。学术论文的双栏排版、图文混排、页眉页脚——VLM 经常把左栏第一段的末尾和右栏第一段的开头当成连贯的文字。

**问题三：跨页表格**。一个跨两页的大表格，VLM 处理每一页时不知道"这个表格上一页已经开始了"。

### 专业方案：OCR + 版面分析 + VLM 理解

对于需要高精度的文档处理，推荐三层流水线：

```python
# 三层文档处理流水线
def process_document(pdf_path):
    # 第一层：OCR + 版面分析（高精度文字提取）
    import layoutparser as lp
    import pytesseract

    pages = convert_from_path(pdf_path, dpi=300)
    model = lp.Detectron2LayoutModel('lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config')

    extracted_data = []
    for page in pages:
        # 自动检测版块：标题、正文、表格、图片、列表
        layout = model.detect(page)
        page_data = {"text_blocks": [], "tables": [], "figures": []}

        for block in layout:
            if block.type == "Table":
                # 表格区域 → OCR → 结构化提取
                table_image = page.crop(block.coordinates)
                table_data = extract_table_from_image(table_image)
                page_data["tables"].append(table_data)
            elif block.type == "Text":
                text = pytesseract.image_to_string(page.crop(block.coordinates), lang='chi_sim+eng')
                page_data["text_blocks"].append(text)

        extracted_data.append(page_data)

    # 第二层：跨页合并（VLM 做全局理解）
    # 检测跨页表格、跨页段落，合并为完整结构

    # 第三层：语义理解（VLM 分析提取的结构化数据）
    # "分析这份合同：我方作为乙方有什么风险条款？"
    return extracted_data
```

**为什么需要三层**：

| 层 | 做什么 | 为什么不能跳过 |
|----|--------|--------------|
| OCR+版面分析 | 精确提取文字和表格的结构化数据 | VLM 直接看图的文字提取准确率约 85-95%，专业 OCR 达 99.5%+ |
| 跨页合并 | 识别跨页的表格和段落 | VLM 每页独立处理，不知道跨页内容的连续性 |
| VLM 语义理解 | 基于结构化数据分析逻辑、判断风险 | OCR 只能"看到字"，不能"理解字的意思" |

### PDF 文档处理的工具选型

| 工具 | 方案 | 适用场景 | 精度 | 成本 |
|------|------|---------|:--:|:--:|
| VLM 直接看 | GPT-4o/Claude 看图 | 简单文档、快速预览 | 85-95% | 中 |
| LayoutParser + OCR | 检测版块+Tesseract/PaddleOCR | 学术论文、杂志排版 | 95-99% | 低（开源免费） |
| Unstructured.io | 一站式开源文档处理 | 通用文档、多种格式 | 90-98% | 低 |
| Azure Document Intelligence | 云服务，预训练模型 | 发票、合同等固定格式 | 99%+ | 中（按页计费） |
| LlamaParse | LlamaIndex 的文档解析 | RAG 管道的文档预处理 | 92-98% | 低 |

## 图表理解：从像素到数据

图表是 VLM 最棘手的视觉任务之一。因为图表里的**信息精确性**很重要——你问"Q3 营收是多少"，VLM 回答"大概 1200 万到 1300 万之间"是不够的。

### VLM 看图表的表现

**擅长**：
- 趋势判断："整体呈上升趋势，Q2 到 Q3 增长最快"
- 类型识别：柱状图、折线图、饼图、散点图
- 异常点检测："有一个明显的下降点"
- 图例和标注理解

**不擅长**：
- 精确数值提取：柱状图里第三根柱子的精确高度
- 刻度读取：Y 轴是"百万"还是"亿"
- 比例计算：饼图中某块的精确百分比
- 密集图表：10 条以上的折线、堆叠柱状图

### 最佳实践：分步提取

```python
def extract_chart_data(chart_image):
    """分步提取图表数据"""
    client = OpenAI()

    # 第一步：让模型描述图表的整体结构和坐标轴
    step1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": """
                描述这张图表的完整信息：
                1. 图表类型
                2. X轴和Y轴的标签和单位
                3. 所有图例项
                4. 坐标轴刻度范围
                不要提取具体数值，只描述结构。
                """},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{chart_base64}"}}
            ]
        }]
    )

    # 第二步：基于第一步的坐标理解，精确提取数值
    step2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"""
                基于以下图表结构信息：
                {step1.choices[0].message.content}

                现在提取所有数据点的精确数值。
                对于每个数据系列，列出每项的标签和对应数值。
                如果数值无法精确读取，标注为'近似值'并给出范围。
                """},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{chart_base64}"}}
            ]
        }]
    )

    return {
        "structure": step1.choices[0].message.content,
        "data": step2.choices[0].message.content
    }
```

**为什么分两步而不是一步**：VLM 在一次推理中既要理解坐标结构又要读精确数值——这两类信息在模型的注意力分布中竞争。先让它"看清楚坐标"，再让它"读数值"，准确率明显提升。

### 什么时候该用编程而不是 VLM

如果图表是常见的标准格式（而不是手绘的、不规则的、或拍照的模糊图），用编程提取比 VLM 更精确：

```python
# 如果图表是标准格式且有原始数据，直接解析
import matplotlib.pyplot as plt

# 从数据源生成图表 → 直接读数据，不需要 "看图"
data = pd.read_csv("revenue_data.csv")
print(data.groupby("quarter")["revenue"].sum())
# 精确到小数点，没有任何识别误差
```

**规则**：有原始数据用编程，没有原始数据用 VLM 分步提取。

## UI 理解：截图里的界面逻辑

UI 截图分析是视觉 AI 增长最快的落地场景之一——产品评审、自动化测试、竞品分析、无障碍适配，都需要 AI 理解界面。

### VLM 看 UI 的三个层次

**层次一：描述（Screenshot Description）**
"这是一个电商 App 的商品详情页，顶部有搜索栏和购物车图标，中间是商品图片轮播，下方是价格和'加入购物车'按钮。"

GPT-4o 和 Claude 在这一层都做得不错。但这只是"看图说话"。

**层次二：分析（Layout & UX Analysis）**
"搜索栏和购物车图标间距过大，商品图片占据了屏幕 60% 的面积导致关键信息被挤到折叠线以下，'加入购物车'按钮的对比度不足在阳光下可能看不清。"

Claude 在这一层有明显优势——它对 UI 设计规范的理解更深入，能给出符合 WCAG 无障碍标准的具体建议。

**层次三：操作（Computer Use）**
"I see a list of 15 items. I will now scroll down to load more, then count the total."

只有 Claude Computer Use 能真正做到——不是"分析截图"，而是真的操作界面。这已经超越了视觉理解的范畴。

### 实用代码：UI 对比分析

```python
def compare_ui_versions(version_a_path, version_b_path):
    """对比两个版本的UI设计截图"""
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": """
                对比这两个UI版本的差异，请从以下维度逐一分析：
                1. 布局变化：哪些元素移动了位置？哪些新增/删除？
                2. 视觉层级：信息层级和视觉引导是否有变化？
                3. 交互可发现性：按钮、输入框等交互元素是否更易察觉？
                4. 信息密度：是否为关键信息留出了足够的空间？
                5. 给出优先级排序的改进建议
                """},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{version_a_base64}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{version_b_base64}"}}
            ]
        }]
    )
    return response.choices[0].message.content
```

### UI 理解的精度问题

VLM 在 UI 截图上的精度瓶颈非常明确：

| 任务 | 准确度 | 问题 |
|------|:--:|------|
| 识别界面元素类型（按钮/输入框/列表）| ★★★★★ | 很准确 |
| 读出可见文字 | ★★★★☆ | 小字会出错 |
| 判断布局问题和改进建议 | ★★★★☆ | Claude 最强 |
| 识别可点击区域的精确像素坐标 | ★★☆☆☆ | VLM 普遍困难 |
| 判断一个元素的"状态"（选中/禁用/加载中）| ★★★★☆ | — |
| 理解多步骤流程的完整性 | ★★★☆☆ | 每步是静态截图，缺少流程上下文 |

对于需要精确像素坐标的场景（如 UI 自动化测试），`playwright` 这样的框架比 VLM 更适合——它直接读取 DOM 树，不需要"看"截图。

## 方案选型：VLM 够用吗

| 任务 | VLM 直接看 | 需要辅助工具 | 推荐工具链 |
|------|:--:|:--:|------|
| 简单文档（通知/信件）| ✅ 够用 | — | GPT-4o / Claude |
| 复杂PDF（合同/论文）| ❌ 不够 | OCR+版面分析 | LayoutParser + OCR + VLM |
| 表格数据提取 | ❌ 不够 | OCR+结构化提取 | PaddleOCR / Unstructured |
| 图表趋势分析 | ✅ 够用 | — | GPT-4o 分步提取 |
| 图表精确数值 | ❌ 不够 | 编程解析原始数据 | pandas / matplotlib |
| UI 设计评审 | ✅ 够用 | — | Claude（UI分析最强） |
| UI 自动化测试 | ❌ 不够 | DOM解析 | Playwright / Selenium |

**核心原则**：VLM 像是一个"实习生"——它能快速看懂大部分内容并给出合理的分析，但在需要精确数值、复杂结构解析时，你需要给这个实习生配备专业工具。

## 总结

- 文档理解不能只靠 VLM 看图——**三层流水线（OCR + 版面分析 + VLM 语义理解）** 才能达到企业级的精度
- 图表理解的最佳策略是**分步提取**——先让模型"看清楚坐标"，再让它"读数值"。如果有原始数据，直接用编程解析
- UI 理解是 Claude 的专属强项——在布局分析和 UX 建议上，它比 GPT-4o 深一个层次
- **VLM 像实习生，能看懂大部分内容，但需要精确结果时必须配备专业工具**
- 下一篇进入 03 章的收尾——[视觉 AI 实战与成本优化](./05-vision-practice.md)，把所有理论变成可以上线的生产方案

## 参考链接

- [LayoutParser: A Toolkit for Document Layout Analysis](https://layout-parser.github.io/)
- [PaddleOCR: 飞桨OCR工具包](https://github.com/PaddlePaddle/PaddleOCR)
- [Unstructured.io 开源文档处理](https://github.com/Unstructured-IO/unstructured)
- [Claude Computer Use 文档](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)
- [Playwright 浏览器自动化](https://playwright.dev/)

> 文档、图表、UI——三个最高频场景的实践看完了。最后一篇把所有内容串起来：[视觉 AI 实战与成本优化](./05-vision-practice.md) —— 从 API 调用到生产部署的全链路。
