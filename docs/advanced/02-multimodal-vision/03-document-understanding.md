# 文档与图表理解

企业环境中超过 80% 的知识以文档形式存在：PDF、扫描件、表格、图表。让 Agent 能准确理解这些结构化的视觉信息，是多模态最重要的落地场景之一。

## 文档理解的层次

| 层次 | 能力 | 技术方案 |
|------|------|----------|
| 文字提取 | OCR、文字检测与识别 | Tesseract、DocTR、PaddleOCR |
| 版面分析 | 段落、表格、图片、页眉页脚的边界识别 | LayoutLM、YOLO-based 检测 |
| 结构还原 | 阅读顺序、层级关系、列表编号 | Seq2Seq 版面重建、MLLM 推理 |
| 语义理解 | 文档意图、关键信息抽取、关系提取 | GPT-5/Gemini 多模态理解 |
| 深层推理 | 多文档对比、数据交叉验证、图表洞见 | Agentic RAG + 多模态 LLM |

## PDF 解析技术栈

### 传统管线

```
PDF → OCR（必要时）→ 版面检测 → 结构还原 → 文本提取 → 语义理解
```

优点：成熟稳定、成本可控
缺点：误差累积、复杂版面（多栏、嵌套表格）容易出错

### 端到端 MLLM 方案

直接让多模态模型"看"文档页面，输出结构化结果。

优点：对复杂版面鲁棒、能理解上下文
缺点：成本高、延迟大、不适合大批量

### 混合方案（推荐）

- 用传统方案做第一遍粗提取
- 用 MLLM 做关键字段的精细提取
- 用 Agent 做跨文档的推理验证

## 表格提取

表格是文档理解最大的难点之一：

- **无边框表格**：视觉上无表格线，纯靠对齐判断
- **合并单元格**：行列跨越，结构化重建困难
- **嵌套表格**：表格套表格
- **多页表格**：跨页断裂，需要拼接
- **旋转文字**：特殊方向的文字

### 推荐方案

1. Camelot/Tabula：对有边框表格效果好
2. MLLM（GPT-5/Gemini）：对复杂表格效果好
3. 结合 pipeline：先检测表格区域 → 分类表格类型 → 选择解析方案

## 图表解读

图表从图像中提取数据需要几个关键步骤：

### 图表类型识别

饼图、折线图、柱状图、散点图、雷达图——不同类型的解读策略不同。

### 数据提取

- 坐标轴定位和刻度识别
- 数据点/柱/扇区的值提取
- 图例与数据系列的映射

### 趋势与洞见

- 上升/下降/周期性趋势
- 异常值检测
- 数据对比（同比/环比）

### 图表 Agent 实践

```
用户提问 → 识别图表类型 → 提取数据 → 分析趋势 → 生成回答
                                                        ↓
                                             可视化验证（生成标注图）
```

## 方案选型决策

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 大批量 PDF 文本提取 | PyMuPDF/pdfplumber | 快速、成本低，纯文本场景 |
| 扫描件/图片 PDF | PaddleOCR / Azure Document Intelligence | OCR 能力强，支持多语言 |
| 复杂版面（表格混排） | GPT-5 / Gemini 视觉理解 | MLLM 对复杂版面最优 |
| 实时文档问答 | 混合：粗提取 + MLLM 精提取 | 平衡速度与准确率 |
| 企业级文档处理 | Unstructured.io / LlamaParse | 全流程管线，支持 20+ 文件类型 |

## 参考

- [LayoutLMv3: Pre-training for Document AI](https://arxiv.org/abs/2204.08387)
- [Unstructured.io Document Parsing](https://unstructured.io/)
- [LlamaParse: GenAI-native Document Parsing](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [Azure Document Intelligence](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence)
