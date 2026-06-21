# 多模态 Agent：计算机使用与视觉交互

多模态 Agent 是 Agent 架构的进阶形态——Agent 不再只能处理文字，而是能"看见"屏幕、理解界面、操作软件。这种能力被称为"Computer Use"或"GUI Agent"。

## 什么是多模态 Agent

从单模态到多模态 Agent 的能力跃迁：

```
单模态 Agent: 文字输入 → 推理 → 文字输出
多模态 Agent: 截图/视频/语音输入 → 视觉理解 → GUI 操作/文字/图像输出
```

核心区别：Agent 通过视觉感知环境，通过 GUI 操作反作用于环境。

## Computer Use：让 Agent 操作电脑

### 工作流程

```
1. 截取屏幕 → 2. 视觉理解当前界面 → 3. 决定下一步操作
    ↑                                            |
    └──────────────── 执行操作 ←──────────────────┘
```

### 操作原语

| 操作 | 说明 | 示例 |
|------|------|------|
| click(x,y) | 点击坐标位置 | 点击搜索框 |
| type(text) | 输入文本 | 输入搜索关键词 |
| scroll(dx,dy) | 滚动页面 | 向下翻页 |
| keypress(key) | 按键操作 | 按 Enter |
| select(region) | 选择区域 | 框选截图区域 |
| wait(ms) | 等待 | 等待页面加载 |

### 坐标获取方式

- 绝对坐标：直接指定 (x,y) 位置
- 元素定位：通过视觉识别找到按钮位置
- DOM 映射：浏览器场景下关联 DOM 元素

## 视觉 Grounding

视觉 grounding 是将文字描述映射到图像中具体位置的能力。对 GUI Agent 来说就是："找到搜索框"→ 返回坐标。

### 方案对比

| 方案 | 准确率 | 速度 | 适用场景 |
|------|--------|------|----------|
| 纯 MLLM 定位 | 中等 | 慢 | 通用场景 |
| 目标检测（YOLO/Detr） | 高 | 快 | 固定 UI 元素 |
| OCR + 坐标映射 | 高 | 中 | 文字密集界面 |
| 混合方案 | 高 | 中 | 推荐方案 |

## Agent 规划

多模态 Agent 的规划比文本 Agent 更复杂，因为：
- 界面状态是连续的（每次操作后界面变化）
- 操作结果是视觉反馈（需要再次截图）
- 中间状态不可预知（弹窗、加载、错误）

### 规划策略

### ReAct 增强

```
思考：我需要搜索 "多模态 RAG" 
动作：找到搜索框位置 → click(x,y)
观察：搜索框获得焦点
思考：输入关键词
动作：type("多模态 RAG")
观察：输入框显示文字
思考：按搜索按钮
动作：找到搜索按钮 → click(x2,y2)
...
```

### 分层规划

高层次规划（任务级）→ 低层次执行（操作级）：
```
高层次: 在网站上搜索"多模态 RAG"并截图第一个结果
低层次: 打开浏览器 → 输入URL → 等待加载 → 找到搜索框 → 输入 → 点击 → 截图
```

### 错误恢复

Agent 需要能处理：
- 弹窗干扰（Cookie 确认、升级提醒）
- 页面加载超时
- 操作无响应
- 预期界面未出现

## 主流方案对比

| 方案 | 提供方 | 定位 | 特点 |
|------|--------|------|------|
| Computer Use | Anthropic | API 级 | Claude 直接操作电脑，最成熟的方案 |
| Project Mariner | Google | 实验性 | Gemini 驱动的浏览器 Agent |
| Operator | OpenAI | 产品级 | CUA（Computer Use Agent）模型 |
| CogAgent | 开源 | 研究级 | 专注 GUI grounding 的开源模型 |
| Screen Agent | 社区 | 框架级 | 基于 MLLM 的通用框架 |

## 工程实践

### 稳定性设计

1. **状态校验**：每次操作后验证界面是否达到预期
2. **超时处理**：设置合理的操作超时（一般 5-15 秒）
3. **重试机制**：失败操作自动重试 2-3 次
4. **安全边界**：限制可操作的区域（不触碰系统设置）

### 成本控制

- 截图分辨率：降低到 1440p 足够
- 操作频率：两次操作间至少间隔 1 秒
- 缓存设计：相同界面截图可缓存分析结果

### 安全与权限

- 沙箱执行：Agent 操作应在隔离环境中运行
- 操作审计：记录所有操作日志
- 人工确认：敏感操作（付款、删除）需要人工确认
- 限速控制：防止 Agent 操作太快引发问题

## 参考

- [Anthropic Computer Use Documentation](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)
- [OpenAI CUA (Computer Use Agent)](https://platform.openai.com/docs/guides/tools-computer-use)
- [Project Mariner (Google)](https://deepmind.google/technologies/gemini/project-mariner/)
- [CogAgent: A Visual Language Model for GUI Agents](https://arxiv.org/abs/2312.08914)
- [Screen Agent: SeeUI Framework](https://github.com/bytedance/screen-agent)
