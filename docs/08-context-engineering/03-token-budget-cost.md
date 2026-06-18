# Token 预算与成本控制

> 一个运行 20 轮的 Agent 可能花掉 $2.00，一个优化过的版本只花 $0.15。Prompt Caching 省 90% 的重复计算成本，KV Cache 省 50% 的推理延迟——上下文工程的最终目标是：用最小的 Token 预算，达到最好的 Agent 效果。

## 目录

- [Token 成本结构](#token-成本结构)
- [Prompt Caching：复用重复计算](#prompt-caching复用重复计算)
- [KV Cache：推理层的加速](#kv-cache推理层的加速)
- [上下文预算分配](#上下文预算分配)
- [成本监控与告警](#成本监控与告警)
- [多模型路由：用便宜模型做简单事](#多模型路由用便宜模型做简单事)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前两篇讲了 [上下文窗口的瓶颈](./01-context-window-bottleneck.md) 和 [压缩策略](./02-context-compression.md)。这篇文章聚焦最后一环：**怎么在有限的 Token 预算内最大化 Agent 效果，同时把成本控制在可接受的范围内**。读完本文，你将掌握从预算设计到成本监控的完整工程方案。

## Token 成本结构

一次 Agent 调用的成本由三部分组成：

```
总成本 = 输入 Token 成本 + 输出 Token 成本 + 工具调用成本
```

以 GPT-4.1 为例（2026 年价格）：

| 项目 | 单价 | 占比（典型 Agent） |
|------|------|------------------|
| 输入 Token | $2.00 / 1M tokens | ~60% |
| 输出 Token | $8.00 / 1M tokens | ~30% |
| 工具调用（API 费用） | 按 API 计费 | ~10% |

**输入 Token 是最大开销**——系统提示、工具定义、对话历史、记忆注入，每次调用都要付费。一个 20 轮的 Agent 会话，输入 Token 成本可能从第一轮的 $0.01 涨到第 20 轮的 $0.15。

### 成本累积曲线

```
第 1 轮：  5K 输入 tokens  → $0.01
第 5 轮：  12K 输入 tokens → $0.024
第 10 轮： 25K 输入 tokens → $0.05
第 15 轮： 40K 输入 tokens → $0.08
第 20 轮： 60K 输入 tokens → $0.12

20 轮总输入成本：$0.58（累积）
```

如果不做任何压缩和优化，一个每天处理 100 个 20 轮会话的 Agent，月成本约 $1740。优化后可以降到 $200 以内。

## Prompt Caching：复用重复计算

**Prompt Caching** 是 2025-2026 年三大平台都支持的关键优化：上下文中**重复的前缀部分**不需要重新计算，直接复用之前的结果。

### 原理

Agent 每次调用时，系统提示 + 工具定义 + 早期对话历史通常是相同的。Prompt Caching 让模型跳过这些重复部分的 KV 计算，只计算新增的内容。

```
第 1 次调用：[系统提示 + 工具定义 + 对话1]  → 全量计算
第 2 次调用：[系统提示 + 工具定义 + 对话1 + 对话2]
             ↑ 缓存命中，跳过计算    ↑ 只计算新增
```

### 各平台的 Caching 支持

| 平台 | 缓存折扣 | 最低缓存长度 | 自动/手动 |
|------|---------|------------|----------|
| **OpenAI** | 输入价格 50-90% 折扣 | 1024 tokens（自动触发） | 自动 |
| **Anthropic** | 输入价格 90% 折扣 | 2048 tokens | 手动标记 `cache_control` |
| **Google** | 阶梯定价 | 模型相关 | 自动 |

### Anthropic 的手动缓存标记

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{
        "role": "user",
        "content": "分析这段代码的问题"
    }],
    system=[{
        "type": "text",
        "text": "你是一个代码审查专家..." * 100,  # 长系统提示
        "cache_control": {"type": "ephemeral"}  # 标记为可缓存
    }],
    tools=[
        # 工具定义也可以标记缓存
    ]
)

# 第一次调用：全量计算
# 第二次调用：系统提示部分命中缓存，节省 90% 输入成本
```

### OpenAI 的自动缓存

OpenAI 不需要手动标记——系统自动检测重复前缀并缓存：

```python
# OpenAI 自动缓存，无需额外代码
# 只要连续调用的前缀相同，就会自动命中

# 第 1 次：全量计费
response1 = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": LONG_SYSTEM_PROMPT},  # 1000 tokens
        {"role": "user", "content": "你好"}
    ]
)

# 第 2 次：系统提示部分自动缓存，输入价格降低 50-90%
response2 = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": LONG_SYSTEM_PROMPT},  # 缓存命中！
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
        {"role": "user", "content": "帮我看看代码"}
    ]
)
```

**Prompt Caching 的成本节省**：

| 场景 | 无缓存 | 有缓存 | 节省 |
|------|--------|--------|------|
| 20 轮对话（固定系统提示 2K tokens） | $0.58 | $0.32 | 45% |
| 100 次调用（相同工具定义 3K tokens） | $6.00 | $0.90 | 85% |
| RAG Agent（固定知识前缀 5K tokens） | $10.00 | $1.50 | 85% |

## KV Cache：推理层的加速

KV Cache 是模型推理层面的优化——**缓存自注意力计算中的 Key-Value 张量**，避免重复计算。

### 与 Prompt Caching 的关系

```
Prompt Caching = API 层面的优化（平台帮你做）
KV Cache = 推理引擎层面的优化（自部署时需要自己配）
```

对于 API 调用者，Prompt Caching 已经在底层利用了 KV Cache——你不需要额外操作。

对于**本地部署**（vLLM、Ollama），KV Cache 的配置直接影响性能：

```python
# vLLM 的 KV Cache 配置
from vllm import LLM

llm = LLM(
    model="Qwen/Qwen2.5-7B-Instruct",
    gpu_memory_utilization=0.9,  # GPU 内存用于 KV Cache 的比例
    max_num_batched_tokens=8192,  # 最大批处理 Token 数
    enable_prefix_caching=True,   # 启用前缀缓存
)
```

**本地部署的 KV Cache 优化效果**：

| 配置 | 首 Token 延迟 | 吞吐量 |
|------|-------------|--------|
| 无 KV Cache | 500ms | 20 tokens/s |
| 启用前缀缓存 | 200ms（-60%） | 45 tokens/s（+125%） |

## 上下文预算分配

生产环境的 Agent 需要为每次调用设定**Token 预算上限**，并动态分配给各个组件：

```python
class TokenBudget:
    """Token 预算管理器"""
    
    def __init__(self, total_budget: int = 15000):
        self.total = total_budget
        # 固定分配（不可压缩）
        self.fixed = {
            "system_prompt": 800,
            "current_input": 500,
        }
        # 弹性分配（可动态调整）
        self.flexible = {
            "tools": 2000,
            "recent_messages": 5000,
            "memory": 500,
            "rag_results": 1500,
            "tool_results": 2000,
        }
        # 缓冲（应对突发）
        self.buffer = total_budget - sum(self.fixed.values()) - sum(self.flexible.values())
    
    def allocate(self, component: str, requested: int) -> int:
        """为某个组件分配 Token，不超过预算"""
        max_allowed = self.fixed.get(component) or self.flexible.get(component, 0)
        return min(requested, max_allowed)
    
    def get_usage_report(self, actual_usage: dict) -> dict:
        """生成使用报告"""
        total_used = sum(actual_usage.values())
        return {
            "total_budget": self.total,
            "total_used": total_used,
            "utilization": total_used / self.total,
            "by_component": actual_usage,
            "over_budget": total_used > self.total
        }
```

### 预算告警

```python
def check_budget(usage_report: dict):
    """预算检查与告警"""
    utilization = usage_report["utilization"]
    
    if utilization > 0.9:
        logger.warning(f"上下文使用率 {utilization:.0%}，接近预算上限")
        # 触发自动压缩
        trigger_context_compression()
    
    if utilization > 0.95:
        logger.error(f"上下文使用率 {utilization:.0%}，超出预算！")
        # 强制截断
        force_truncate()
```

## 成本监控与告警

生产环境的 Agent 必须有成本监控——否则月底账单可能让你大吃一惊。

```python
import time
from dataclasses import dataclass, field

@dataclass
class CostTracker:
    """Agent 成本追踪器"""
    
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    session_costs: dict = field(default_factory=dict)
    
    # 价格配置（按模型）
    prices = {
        "gpt-4.1": {"input": 2.0, "output": 8.0},      # $/1M tokens
        "gpt-4.1-mini": {"input": 0.15, "output": 0.6}, # $/1M tokens
        "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    }
    
    def record(self, model: str, input_tokens: int, output_tokens: int, 
               session_id: str = "default"):
        """记录一次调用的成本"""
        price = self.prices.get(model, {"input": 2.0, "output": 8.0})
        cost = (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        if session_id not in self.session_costs:
            self.session_costs[session_id] = 0.0
        self.session_costs[session_id] += cost
        
        return cost
    
    def get_report(self) -> dict:
        """生成成本报告"""
        return {
            "total_cost": f"${self.total_cost:.2f}",
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "avg_cost_per_call": f"${self.total_cost / max(1, len(self.session_costs)):.4f}",
            "sessions": len(self.session_costs),
        }
    
    def check_alert(self, max_daily_cost: float = 10.0) -> bool:
        """检查是否超过日成本上限"""
        return self.total_cost > max_daily_cost
```

### 成本优化检查清单

| 检查项 | 目标 | 方法 |
|--------|------|------|
| 单次调用不超过 15K tokens | 平均 8-12K | 上下文压缩 + 选择性注入 |
| 固定前缀（系统提示+工具）被缓存 | 缓存命中率 > 80% | Prompt Caching |
| 工具定义不超过 3K tokens | 动态筛选工具 | 关键词匹配 / 轻量模型路由 |
| 日成本不超过预算 | $10/天（100 个会话） | 成本追踪 + 自动告警 |
| 工具结果不超过 500 tokens/条 | 平均 200 tokens | 即时摘要 + 结构化提取 |

## 多模型路由：用便宜模型做简单事

不是每个请求都需要旗舰模型。**用轻量模型处理简单请求，旗舰模型处理复杂请求**，能省 70%+ 的成本。

```python
class ModelRouter:
    """多模型路由器"""
    
    def __init__(self):
        self.flagship = "gpt-4.1"       # 复杂任务
        self.lightweight = "gpt-4.1-mini"  # 简单任务
    
    def route(self, user_input: str, context: dict) -> str:
        """判断使用哪个模型"""
        # 简单规则路由（零额外成本）
        if self._is_simple_request(user_input, context):
            return self.lightweight
        return self.flagship
    
    def _is_simple_request(self, user_input: str, context: dict) -> bool:
        """判断是否为简单请求"""
        # 短输入 + 无工具调用 + 无 RAG = 简单请求
        if len(user_input) < 50 and not context.get("tools") and not context.get("rag"):
            return True
        
        # 闲聊 / 简单问答
        simple_patterns = ["你好", "谢谢", "解释一下", "翻译成"]
        if any(p in user_input for p in simple_patterns):
            return True
        
        return False
```

**路由效果**：

| 场景 | 全用旗舰 | 智能路由 | 节省 |
|------|---------|---------|------|
| 100 个会话（30% 简单） | $10.00 | $4.20 | 58% |
| 100 个会话（50% 简单） | $10.00 | $3.10 | 69% |

更高级的路由可以用一个轻量模型做"意图分类"，再把分类结果传给对应的模型——路由成本约 $0.001/次，远低于用错模型的成本差。

## 总结

- **Token 成本 = 输入 + 输出 + 工具调用**：输入 Token 是最大开销（~60%），因为它每次调用都要付费，且随对话长度累积。
- **Prompt Caching 省 50-90% 重复计算成本**：OpenAI 自动缓存，Anthropic 需要手动标记。系统提示和工具定义是最容易命中缓存的部分。
- **上下文预算管理器**：为每次调用设定 Token 预算上限（推荐 15K），按优先级分配给系统提示、对话历史、工具、记忆、RAG。
- **成本监控是生产环境的必需品**：追踪每次调用的 Token 用量和成本，设置日成本告警，避免月底账单失控。
- **多模型路由省 60-70% 成本**：简单请求用轻量模型（GPT-4.1-mini），复杂请求用旗舰模型。路由判断本身成本极低。

> 掌握了上下文工程，你已经能让 Agent 的记忆精准、上下文精简、成本可控。这些能力加上工具调用和 Agent 循环，你已经具备了构建生产级 Agent 的完整技能。接下来进入 [09 — 框架与编排](../09-framework/README.md)，学习如何用框架管理复杂 Agent。

## 参考链接

- [OpenAI — Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching)
- [Anthropic — Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [vLLM — Prefix Caching](https://docs.vllm.ai/en/latest/features/prefix_caching.html)
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Google — Gemini Caching](https://ai.google.dev/gemini-api/docs/caching)
