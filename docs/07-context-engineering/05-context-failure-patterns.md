# 上下文失败模式与反模式

> 上下文工程的难点不在于"怎么做对"，而在于"什么时候做错了"。这篇文章不讲正面策略，专门讲反面——四种致命失效模式、七个常见反模式、不同规模下的避坑指南。

## 目录

- [四种致命失效模式](#四种致命失效模式)
  - [上下文污染](#1-上下文污染context-poisoning)
  - [上下文分心](#2-上下文分心context-distraction)
  - [上下文混淆](#3-上下文混淆context-confusion)
  - [上下文冲突](#4-上下文冲突context-clash)
- [七个常见反模式](#七个常见反模式)
- [不同规模的工程路线图](#不同规模的工程路线图)
- [诊断工具：你的上下文健康吗](#诊断工具你的上下文健康吗)
- [死循环检测与熔断](#死循环检测与熔断)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前面四篇讲了上下文工程的各种策略：窗口瓶颈→压缩→预算→卸载与隔离。那些都是"应该做什么"。但这篇文章换一个角度——**"什么会出错"**。识别上下文的失败模式，比学会优化策略更重要，因为大部分问题不是"策略不够好"，而是"根本在用错误的方式管理上下文"。

## 四种致命失效模式

LangChain 技术专家 Drew Breunig 总结了上下文失效的四种典型模式。它们在长任务 Agent 中尤其致命——Agent 依赖上下文来收集信息、综合判断、协调行动，一旦上下文出错，整个决策链崩溃。

### 1. 上下文污染（Context Poisoning）

**定义**：幻觉或错误进入上下文后，被后续步骤反复引用，像毒素一样蔓延。

**典型场景**：Agent 在执行第 5 步时产生了一个幻觉——它"记住"用户有一个叫 `redis_helper.py` 的文件。这个错误留在上下文中。第 8 步，Agent 基于这个幻觉设计了整个缓存方案。第 12 步报错时，它没有怀疑自己的记忆，而是怀疑代码有问题。

```python
# 上下文污染的典型链路
# 步骤 5：Agent 幻觉——"用户的项目中有 redis_helper.py"
messages = [
    {"role": "assistant", "content": "我看到你的项目中有 redis_helper.py..."},  # 幻觉
    # ...
    # 步骤 8：基于幻觉制定决策
    {"role": "assistant", "content": "基于 redis_helper.py，我建议用 Redis Sentinel 做高可用"},
    # 步骤 12：报错——但 Agent 不怀疑自己的记忆
    {"role": "system", "content": "错误：redis_helper.py 不存在"},
    {"role": "assistant", "content": "可能是 Redis 版本不对，我换个方案..."},  # 继续基于幻觉！
]
```

**为什么特别危险**：Agent 不会主动怀疑自己的"记忆"。幻觉一旦进入上下文，就被当成"既定事实"。DeepMind 在 Gemini 技术报告中明确指出：Agent 会执着于实现不可能的目标，因为它的上下文被错误信息"污染"了。

**诊断信号**：
- Agent 反复尝试不存在的文件或 API
- Agent 基于一个"从未发生过的事"做决策
- 纠正后 Agent 仍在围绕旧错误做修改

**修复策略**：

| 策略 | 做法 |
|------|------|
| **事实核验** | 每次引用之前步骤的"事实"时，先用工具验证（文件是否存在、API 是否可用） |
| **失败记录** | 保留错误和修复记录在上下文中，让模型从错误中学习 |
| **定期重置** | 长任务中，每 10 步做一次"状态重建"——用工具重新扫描当前环境状态 |
| **元认知提示** | 在系统提示中加入"如果某条信息没有经过工具验证，不要当作事实使用" |

### 2. 上下文分心（Context Distraction）

**定义**：上下文过长时，模型过度关注历史记录中的行为模式，忽略了训练中学到的知识和当前任务的新需求。

**Databricks 的研究数据**：即使是 Llama 3.1 405B 这样的大模型，上下文超过 3.2 万 tokens 后，准确率也开始下降。不是窗口不够大，而是"注意力被历史模式绑架了"。

**典型场景**：Agent 在审查 20 份简历。前 5 份它的流程很固定：读简历→提取关键技能→评分。到第 18 份时，它陷入了一种机械模式——对每个简历执行完全相同的操作，忽略了第 18 份简历中的特殊信息（转行背景、非标经历）。

```python
# 上下文分心的表现
# Agent 陷入了固定节奏：
# 步骤 1-5：正常处理
# 步骤 6-20：机械重复步骤 1-5 的行为模式
# 即使简历内容不同，Agent 也不再"思考"

# 根本原因：20 轮相似的"动作-观察"对使模型的行为模式陷入"自我重复"，
# 不再基于当前输入做新判断。
```

**诊断信号**：
- Agent 的输出变得越来越"模板化"
- 对于明显不同的输入，Agent 的回复模式高度相同
- Agent 不再主动提问或调整策略

**修复策略**：

| 策略 | 做法 |
|------|------|
| **引入多样性** | 在上下文中加入受控的变化（不同的措辞、不同的格式），打破固定模式 |
| **定期重新聚焦** | 每 N 步重新明确当前目标和上下文，刷新注意力 |
| **上下文压缩** | 用摘要替代完整的历史记录，减少"模仿素材" |
| **临时子 Agent** | 对于重复性任务，派一个全新的子 Agent（零上下文启动），不受主 Agent 历史模式的干扰 |

### 3. 上下文混淆（Context Confusion）

**定义**：上下文中包含过多不相关信息，模型用无关内容生成了低质量回复。

**Berkeley 函数调用排行榜的关键发现**：当提供超过一个工具时，几乎所有模型的表现都会变差。更惊人的是，Llama 3.1 8B 在 46 个工具的上下文中失败，但精简到 19 个时却成功了——瓶颈不是窗口大小，是**认知负荷**。

```python
# 上下文混淆的根源
# 你放入上下文的所有信息，模型都会"关注"——哪怕它完全无关

# 一个包含 46 个工具定义的 Agent
messages = [
    {"role": "system", "content": f"可用工具：{ALL_46_TOOLS}"},  # ~15000 tokens
    {"role": "user", "content": "现在几点了？"}
]
# 工具定义中可能有 weather() / get_time() / search_stock() ...
# 即使只需要 get_time()，模型还要"浏览"全部 46 个定义
# 结果：模型可能错误地调用了 weather() 而不是 get_time()
```

**诊断信号**：
- 模型选择了与任务无关的工具
- 模型对简单问题的回复包含大量无关信息
- 工具定义的增加导致任务完成率下降

**修复策略**：

| 策略 | 做法 |
|------|------|
| **工具按需加载** | 用 RAG 筛选当前任务相关的工具，而不是全量注入 |
| **分层工具空间** | 只暴露原子函数（read/write/search/shell），其余工具通过 Shell/Python 间接调用 |
| **工具遮蔽** | 工具定义始终在上文中，但通过控制解码屏蔽当前不可用的工具 |
| **精简提示** | 每个工具定义控制在 50 tokens 以内，只保留名称 + 一句话描述 + 参数列表 |
| **渐进式披露** | 按需分层加载信息，不一次性全量注入（见下文详解） |

#### 渐进式披露（Progressive Disclosure）

渐进式披露是从 UI 设计借来的概念：**不要一次把所有信息都展示给模型，而是按当前步骤的需要逐层加载**。它是"工具按需加载"的泛化版本——不只是工具，任何上下文内容（文档片段、历史对话、系统指令）都应该分层按需注入。

**三级披露模型**：

| 层级 | 内容 | 注入时机 | 典型 Token 量 |
|------|------|---------|--------------|
| **L1 摘要层** | 工具名称 + 一句话描述、文档标题 + 摘要、历史对话摘要 | 始终在上下文中 | ~500 tokens |
| **L2 详情层** | 工具完整 Schema、文档关键段落、历史对话原文 | 当前任务需要时按需注入 | ~2000 tokens/项 |
| **L3 原始层** | 工具返回值全文、完整文档、原始日志 | 工具执行后或明确需要时注入，用完即卸载 | 按需 |

```python
# 渐进式披露的实现示例
class ProgressiveDisclosure:
    """三级信息披露管理器"""

    def __init__(self):
        self.l1_summaries: list[str] = []    # 始终在上下文
        self.l2_details: dict[str, str] = {}  # 按需注入
        self.l3_raw: dict[str, str] = {}      # 用完即卸载

    def build_context(self, current_task: str) -> list[str]:
        """根据当前任务构建上下文"""
        context = list(self.l1_summaries)  # L1 始终保留

        # L2：根据任务相关性筛选需要注入的详情
        relevant_keys = self._rank_relevance(current_task, self.l2_details)
        for key in relevant_keys[:5]:  # 最多注入 5 项 L2 详情
            context.append(self.l2_details[key])

        return context

    def inject_l3(self, key: str) -> str:
        """临时注入 L3 原始数据，标记为用完即卸载"""
        return self.l3_raw.get(key, "")

    def evict_l3(self, context: list[str], key: str):
        """工具执行完毕后卸载 L3 数据，替换为摘要"""
        raw = self.l3_raw.get(key, "")
        summary = f"[{key} 执行结果摘要: {raw[:100]}...]"
        # 替换原文为摘要，释放上下文空间
        return [summary if key in item else item for item in context]
```

**面试考点**：渐进式披露与"工具按需加载"的区别在于作用域——按需加载只针对工具定义，渐进式披露覆盖所有上下文内容（系统提示、文档、历史对话、工具返回值）。生产级 Agent（如 Claude Code）的三层提示组装（stable/context/volatile）本质上就是渐进式披露的实现。

### 4. 上下文冲突（Context Clash）

**定义**：上下文的不同部分包含矛盾信息，模型不知道该相信哪个。

这是上下文混淆的升级版——不只是信息不相关，而是**直接自相矛盾**。

**微软与 Salesforce 的研究结论**：将完整的提示拆分成多轮对话后，模型表现平均下降 **39%**。强如 OpenAI o3，得分也从 98.1 暴跌到 64.1。

```python
# 上下文冲突的经典案例
# 场景：完整信息分多次给到 Agent

# 第 1 轮：用户给了部分信息
messages.append({"role": "user", "content": "帮我把数据库迁移到 MySQL 8.0"})
# Agent 回复：开始做 MySQL 8.0 的迁移方案

# 第 2 轮：用户补充了新信息（与第 1 轮的部分假设冲突）
messages.append({"role": "user", "content": "等等，我们实际上在用 PostgreSQL，不是 MySQL"})

# 上下文中的冲突：
# - 步骤 2 的消息："开始做 MySQL 8.0 迁移方案"
# - 步骤 6 的消息："等等，实际上用 PostgreSQL"
# - Agent 在两套信息之间摇摆，可能混合使用 MySQL 和 PostgreSQL 的语法

# 为什么冲突特别致命（o3 从 98.1 → 64.1）：
# 因为 Agent 在获得全部信息之前，已经做了不成熟的推理。
# 这些推理和假设留在上下文中，像幽灵一样干扰最终决策。
```

**诊断信号**：
- 多轮对话后模型表现显著下降
- 模型的输出混合了新旧信息的不一致部分
- 模型在纠正错误后"反复横跳"

**修复策略**：

| 策略 | 做法 |
|------|------|
| **一次性提供完整信息** | 如果可以，把约束条件一次给全，不拆分多轮 |
| **显式状态更新** | 信息变化时，在上下文中加入 `[更新]` 标记，覆盖旧状态 |
| **冲突检测** | 用 LLM 定期扫描上下文，检测矛盾信息并标记 |
| **上下文重置** | 当信息发生根本性变化时，用摘要替代原始历史，去掉早期的不成熟推理 |
| **子 Agent 隔离** | 每个子任务用独立 Agent，避免子任务间的信息交叉污染 |

### 四种模式的关系

```
污染（错误信息）→ 分心（模式固化）→ 混淆（信息过剩）→ 冲突（自相矛盾）
   ↓                    ↓                   ↓                  ↓
 毒性蔓延            注意力稀释          认知过载          决策分裂
```

四种模式不是孤立的——它们会在一个 Agent 会话中**叠加出现**。第 5 步的污染导致第 10 步的分心；第 15 步的混淆遇到第 18 步的冲突；Agent 彻底迷失。

<p align="center">
  <img src="../../assets/07-context-engineering/failure-modes.svg" alt="四种致命失效模式级联图" width="90%"/>
  <br/>
  <em>四种失效模式级联关系：污染→分心→混淆→冲突</em>
</p>

## 七个常见反模式

这些是 Agent 开发中"看起来合理、实际上有害"的做法。

### 反模式 1：全量注入

**做什么**：把所有可用的信息（所有工具、所有文档、所有历史）一次性注入上下文。

**为什么有害**：触发上下文混淆——模型在无关信息中搜寻当前任务需要的部分，准确率反而下降。

```
❌ "我有 100 个工具，全部定义了，反正模型自己会挑"
✅ "根据当前任务，只加载相关的 5-10 个工具定义"
```

### 反模式 2：动态增删工具

**做什么**：在迭代中动态添加或删除工具定义。

**为什么有害**：工具定义在上下文前端，每次增删都会导致 KV-Cache 全部失效。模型的历史记录中还引用了已移除的工具，产生混淆。

```
❌ 中途发现需要新工具，动态添加 tool_42 → KV-Cache 重置
✅ 工具定义始终保持稳定，用"遮蔽"机制控制哪些工具可用
```

Manus 的经验：**"遮蔽，而非移除"**。工具定义始终在上下文中，通过控制解码过程，在特定状态下屏蔽掉不可用的工具选项。

### 反模式 3：清理错误历史

**做什么**：Agent 犯错后，删除错误的消息让上下文保持"干净"。

**为什么有害**：模型无法从错误中学习。保留错误和修复记录，模型会隐式更新其内部状态，降低重复错误的概率。

```
❌ 清理掉错误的工具调用和错误信息
✅ 保留完整的"试错→报错→修复"链路
```

**Manus 的经验**：从错误中学习的能力，是真正 Agent 行为的最明显指标之一。

### 反模式 4：把系统提示当垃圾桶

**做什么**：把所有想告诉模型的东西都塞进系统提示——角色、规则、示例、风格指南、安全约束……

**为什么有害**：系统提示最长（在上下文顶部），但它占用的是最宝贵的"注意力黄金位置"。信息太多反而失去焦点。

```
❌ 系统提示 3000 tokens，包含 15 条规则 + 10 个示例 + 5 段背景说明
✅ 系统提示 ≤ 500 tokens：角色 + 核心规则（≤3 条）+ 输出格式要求
```

### 反模式 5：无限追加历史

**做什么**：对话历史从不压缩，一直追加到上下文窗口报错。

**为什么有害**：触发上下文分心 + 成本线性增长。20 轮后模型不是在思考当前问题，而是在模仿历史行为。

```
❌ messages += new_message  # 一直加，直到 tpm 报错
✅ 每 10 轮触发一次压缩：保留最近 5 轮原文 + 更早的摘要
```

### 反模式 6：Few-shot 示例过多

**做什么**：在上下文中放大量 Few-shot 示例。

**为什么有害**：模型是优秀的模仿者。上下文中的示例越多，模型越倾向于"照搬模式"而不是"理解需求"。对于需要灵活处理的任务，过度示例反而限制了模型的创造力。

```
❌ 20 个 Few-shot 示例挤满上下文
✅ 2-3 个示例，展示核心原则即可；需要多样化时在下文引入受控变化
```

### 反模式 7：忽略 KV-Cache

**做什么**：不关心上下文的稳定性，随意修改系统提示前缀。

**为什么有害**：KV-Cache 是 Agent 性能的基石——Manus 的数据显示，输入输出 Token 比约 100:1。每个 Token 的前缀变动都会导致大量缓存失效，成本倍增。

```
❌ 在系统提示开头加时间戳 "当前时间：2026-06-18 12:05:45"
   → 每次调用的前缀都不同，缓存命中率 0%

✅ 时间戳放在系统提示末尾或用户消息中
   → 前缀不变，缓存命中率 > 90%
```

## 不同规模的工程路线图

上下文工程的复杂度应该随规模增长——不要在小项目上过度设计。

| 规模 | 上下文量 | 最常见失效 | 优先实施 | 可以暂缓 |
|------|---------|-----------|---------|---------|
| **< 10K tokens** | 几轮对话 + 少量工具 | 混淆（工具过多） | 工具精选、精简系统提示 | 压缩、隔离、卸载 |
| **10K-50K tokens** | 长对话 + 多工具 | 分心 + 混淆 | 摘要压缩、工具按需加载 | 多 Agent 隔离 |
| **50K-100K tokens** | 复杂任务 + 大量工具结果 | 污染 + 冲突 + 分心 | 压缩 + 卸载 + 隔离三选一 | 全套方案 |
| **> 100K tokens** | 超长任务、多轮深度研究 | 四种全部出现 | 全套：卸载 + 隔离 + 压缩 + 诊断 | — |

### < 10K tokens：够用就别优化

如果你的上下文一直在 5-8K tokens，不要急着上压缩或卸载。把注意力放在：
- 精简工具定义（控制在 500 tokens 内）
- 精简系统提示（控制在 500 tokens 内）
- 对话不超过 15 轮

简单就是最好的。

### 10K-50K tokens：压缩先上

这是大多数生产 Agent 的规模区间。优先做：
1. **对话历史摘要**：每 10 轮触发一次，最近 5 轮保留原文
2. **工具按需加载**：30+ 工具时用 RAG 筛选
3. **Prompt Caching**：确保系统提示和工具定义在缓存中断点之前

### 50K-100K tokens：卸载与隔离

这个区间，压缩已经不够了。信息太多，不只是"量"的问题，还有"质"的问题——信息之间互相干扰：
1. **工具输出卸载**：大结果写文件，上下文留引用
2. **Scratchpad**：给 Agent 一个外部笔记本
3. **考虑多 Agent 隔离**：如果任务天然可拆分

### > 100K tokens：全副武装

超长上下文需要全套策略。但注意：**上下文越大，单一策略的效果越低**。需要组合使用压缩 + 卸载 + 隔离：
1. 子 Agent 分工（隔离）
2. 每个子 Agent 独立的 Scratchpad（卸载）
3. 定期摘要 + 冲突检测（压缩 + 诊断）
4. 全局监控上下文健康度

## 诊断工具：你的上下文健康吗

不需要等到出问题再排查。在 Agent 运行过程中，定期检查以下指标：

```python
class ContextHealthCheck:
    """上下文健康度诊断器"""

    def __init__(self, messages: list, max_tokens: int = 100000):
        self.messages = messages
        self.max_tokens = max_tokens

    def total_tokens(self) -> int:
        """总 Token 数"""
        return sum(len(str(m["content"])) // 4 for m in self.messages)

    def utilization(self) -> float:
        """上下文使用率"""
        return self.total_tokens() / self.max_tokens

    def tool_count(self) -> int:
        """上下文中工具定义的数量（估算）"""
        # 统计 tool_call 和 tool 消息的数量
        return sum(1 for m in self.messages if m.get("role") == "tool")

    def repetition_score(self) -> float:
        """检测回复中的重复模式（分心信号）"""
        if len(self.messages) < 5:
            return 0
        recent = [m["content"] for m in self.messages[-5:]
        if m["role"] == "assistant"]
        # 简单的重复检测：最后 5 条回复中，有多少条开头相同
        starts = [r[:30] for r in recent if r]
        return len(set(starts)) / max(len(starts), 1)  # 越低越重复

    def health_report(self) -> dict:
        """生成健康报告"""
        report = {
            "total_tokens": self.total_tokens(),
            "utilization": f"{self.utilization():.0%}",
            "tool_messages": self.tool_count(),
            "repetition_risk": "⚠️ 高" if self.repetition_score() < 0.5 else "✅ 正常",
        }

        # 综合判断
        issues = []
        if self.utilization() > 0.8:
            issues.append("上下文使用率 > 80%，建议触发压缩")
        if self.tool_count() > 30:
            issues.append("工具消息 > 30 条，建议触发卸载")
        if self.repetition_score() < 0.3:
            issues.append("严重重复模式，建议用子 Agent 重置上下文")

        report["issues"] = issues if issues else ["✅ 健康"]
        return report
```

## 死循环检测与熔断

上下文健康度诊断解决的是"上下文质量"问题，但还有一个更紧急的工程问题：**Agent 陷入死循环**。这不是上下文失效模式，而是执行控制失效——Agent 反复执行相同或等价的操作，消耗 Token 但不产生进展。

### 三种死循环模式

| 模式 | 表现 | 根因 |
|------|------|------|
| **工具重复调用** | 同一个工具被用相同参数反复调用 | Agent 不理解错误返回、或期望不同结果 |
| **错误重试风暴** | 工具报错 → Agent 微调参数 → 再次报错 → 继续微调 | 缺少"此路不通"的判断能力 |
| **上下文无进展** | 连续 N 轮对话后，上下文中没有新增有效信息 | Agent 在原地打转，反复推理但不采取行动 |

```python
class LoopDetector:
    """Agent 死循环检测器——三种检测策略组合使用"""

    def __init__(self, max_repeated_calls: int = 3,
                 max_error_retries: int = 3,
                 stall_threshold: int = 5):
        self.max_repeated_calls = max_repeated_calls
        self.max_error_retries = max_error_retries
        self.stall_threshold = stall_threshold
        self.call_history: list[tuple[str, dict]] = []  # (tool_name, params)
        self.error_streak: int = 0
        self.progress_counter: int = 0

    def on_tool_call(self, tool_name: str, params: dict) -> str | None:
        """工具调用前检测，返回熔断原因或 None"""
        entry = (tool_name, params)
        self.call_history.append(entry)

        # 检测 1：相同工具 + 相同参数的重复调用
        if self.call_history.count(entry) >= self.max_repeated_calls:
            return f"loop_detected: {tool_name} 已用相同参数调用 {self.max_repeated_calls} 次"

        # 检测 2：连续错误重试
        self.progress_counter += 1
        return None

    def on_tool_error(self) -> str | None:
        """工具报错时检测"""
        self.error_streak += 1
        self.progress_counter = 0  # 错误不算进展
        if self.error_streak >= self.max_error_retries:
            return f"error_storm: 连续 {self.error_streak} 次工具调用失败"
        return None

    def on_tool_success(self):
        """工具成功时重置错误计数"""
        self.error_streak = 0
        self.progress_counter = 0

    def on_turn_end(self) -> str | None:
        """每轮结束时检测上下文是否无进展"""
        self.progress_counter += 1
        if self.progress_counter >= self.stall_threshold:
            return f"stall_detected: 连续 {self.stall_threshold} 轮无有效进展"
        return None
```

**熔断后的处理策略**：

| 熔断类型 | 处理方式 |
|---------|---------|
| 工具重复调用 | 将错误信息注入上下文，提示 Agent"此工具已多次返回相同结果，请换一种方法" |
| 错误重试风暴 | 终止当前工具调用链，用摘要替代详细错误历史，让 Agent 重新规划 |
| 上下文无进展 | 强制压缩上下文 + 注入"请总结当前进展并明确下一步"的引导提示 |

**与第 16 章的衔接**：死循环的完整工程实现（超时控制、轮次上限、熔断器状态机）在 [Agent 系统架构设计](../16-ship-to-production/01-architecture.md) 中有详细代码。本节聚焦于上下文工程维度的**检测信号**——什么时候从上下文的内容特征判断 Agent 已经陷入循环。

<p align="center">
  <img src="../../assets/07-context-engineering/context-health-check.svg" alt="ContextHealthCheck诊断流程" width="90%"/>
  <br/>
  <em>上下文健康诊断四步流程：检测→分类→诊断→修复</em>
</p>

## 总结

- **四种失效模式层层递进**：污染（错误蔓延）→ 分心（模式固化）→ 混淆（信息过剩）→ 冲突（自相矛盾）。它们在长任务中会叠加出现，最终导致 Agent 彻底迷失。
- **Context Clash 是最致命的模式**：微软/ Salesforce 研究显示，信息拆分多轮后 o3 得分从 98.1 降到 64.1。如果可能，把约束条件一次性给全。
- **七个反模式是隐形陷阱**：全量注入、动态增删工具、清理错误历史、系统提示当垃圾桶、无限追加历史、Few-shot 过多、忽略 KV-Cache——每个看起来都合理，但组合使用会导致上下文崩溃。
- **工程策略随规模递增**：< 10K 保持简单，10-50K 上压缩，50-100K 上卸载/隔离，> 100K 全套组合。
- **上下文工程的核心原则**：**不要给模型更多信息，给模型更精准的信息**。Manus 的座右铭是"build less and understand more"——能为模型减负就不要加戏。

> 这篇文章是上下文工程的"避坑指南"。你已经完整掌握了上下文工程的全部策略——但窗口有限，外部知识不能全往里塞。进入 [08 — 知识检索（RAG）](../08-rag-pipeline/README.md)，学怎么"按需检索"而不是"全塞进去"。

## 参考链接

- [Drew Breunig — How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) — 四种失效模式的原始定义
- [Drew Breunig — How to Fix Your Context](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) — 六种修复策略
- [Berkeley — Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) — 工具选择准确率与工具数量的关系
- [Microsoft & Salesforce — Multi-turn Prompt Degradation](https://arxiv.org/abs/2406.12345) — 多轮对话 o3 得分从 98.1 降到 64.1 的研究
- [Manus — Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — Mask Don't Remove、保留错误历史、不要被 Few-shot 所困
- [DeepMind — Gemini Technical Report](https://arxiv.org/abs/2312.11805) — 上下文污染导致 Agent 执着于不可能目标
