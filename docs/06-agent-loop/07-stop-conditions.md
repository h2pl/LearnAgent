# Agent 停止条件设计

> Agent 循环必须有明确的停止条件——否则要么无限循环浪费资源，要么过早终止任务失败。好的停止条件是"目标达成"，兜底条件是"最大步数"和"超时"。

## 目录

- [为什么停止条件是安全网](#为什么停止条件是安全网)
- [三种停止条件](#三种停止条件)
- [目标达成判定](#目标达成判定)
- [最大步数与超时](#最大步数与超时)
- [异常退出与降级策略](#异常退出与降级策略)
- [停止条件的组合策略](#停止条件的组合策略)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。在 [ReAct 模式](./03-react-pattern.md) 中，你学会了让 Agent"边想边做"。但如果 Agent 无法正确停止，轻则浪费 Token 和时间，重则陷入无限循环。这篇文章解决核心问题：**如何设计停止条件，让 Agent 在正确的时机停下来**。

## 为什么停止条件是安全网

Agent 循环是动态的——模型根据中间结果决定下一步做什么。如果没有停止条件，Agent 可能：

1. **无限循环**：模型无法判断任务完成，反复调用工具
2. **资源浪费**：每步都消耗 Token 和 API 调用，无限制执行
3. **安全风险**：Agent 可能执行危险操作（如删除数据）

**停止条件的本质**是给 Agent 画一条"红线"：无论模型如何决策，到达红线就必须停止。

## 三种停止条件

Agent 的停止条件分为三类，按优先级从高到低：

| 停止条件 | 触发时机 | 作用 | 优先级 |
|----------|----------|------|--------|
| **目标达成** | Agent 返回最终答案 | 任务完成 | 1（最优） |
| **最大步数** | 循环超过预设次数 | 防止无限循环 | 2（兜底） |
| **超时** | 执行时间超过限制 | 防止资源浪费 | 3（兜底） |

**设计原则**：目标达成是主条件，最大步数和超时是安全网。Agent 应该尽可能通过目标达成停止，只有在异常情况下才触发兜底条件。

<p align="center">
  <img src="../../assets/06-agent-loop/stop-conditions-flowchart.png" alt="停止条件流程" width="95%"/>
  <br/>
  <em>Agent 停止条件：3 种判断 + 组合策略</em>
</p>

## 目标达成判定

目标达成是最理想的停止条件——Agent 自主判断任务完成，返回最终答案。但"任务完成"的判定需要明确的标准。

```python
# 目标达成判定
def is_goal_achieved(decision: dict, user_request: str) -> bool:
    """判断 Agent 是否完成任务"""
    
    # 条件 1：Agent 返回 final_answer
    if decision.get("type") == "final_answer":
        answer = decision.get("answer", "")
        
        # 检查答案是否包含实质性内容
        if len(answer) > 10:  # 最小长度检查
            return True
    
    # 条件 2：任务超时但 Agent 放弃
    if "无法完成" in decision.get("answer", ""):
        return True
    
    return False
```

**目标达成的判定标准**：

| 标准 | 说明 | 示例 |
|------|------|------|
| **答案完整性** | 回答包含实质性内容 | 不是"我不知道"或空答案 |
| **任务覆盖** | 回答了用户的所有问题 | 多问题场景下全部回答 |
| **操作完成** | 所有工具调用都已执行 | 需要查天气和推荐活动，都已完成 |

**潜在风险**：模型可能过早判断"任务完成"——比如只回答了部分问题就返回。需要在 Prompt 中明确要求完整回答。

## 最大步数与超时

最大步数和超时是兜底条件——防止 Agent 无限循环。它们不是"任务完成"，而是"任务失败但必须停止"。

```python
# 最大步数与超时
def check_stop_conditions(state: dict) -> tuple[bool, str]:
    """检查停止条件，返回 (是否停止, 原因)"""
    
    # 条件 1：最大步数
    max_steps = state.get("max_steps", 10)
    if state["step_count"] >= max_steps:
        return True, f"达到最大步数 {max_steps}"
    
    # 条件 2：超时
    timeout = state.get("timeout", 300)  # 默认 5 分钟
    elapsed = time.time() - state["start_time"]
    if elapsed > timeout:
        return True, f"执行超时 ({elapsed:.1f}s > {timeout}s)"
    
    return False, ""
```

**最大步数的设计原则**：

| 原则 | 说明 |
|------|------|
| **经验值** | 简单任务 3-5 步，复杂任务 10-20 步 |
| **任务相关** | 根据任务复杂度调整，不要一刀切 |
| **日志记录** | 记录实际步数，用于后续优化 |

**超时的设计原则**：

| 原则 | 说明 |
|------|------|
| **API 限制** | 考虑 LLM API 的调用频率限制 |
| **用户体验** | 用户等待时间不超过预期（如 5 分钟） |
| **资源预算** | 控制 Token 消耗，避免成本超支 |

## 异常退出与降级策略

当触发兜底条件（最大步数或超时）时，Agent 应该优雅降级，而不是直接崩溃。

```python
# 异常退出与降级策略
def handle_stop_reason(state: dict, stop_reason: str) -> str:
    """处理停止原因，返回降级结果"""
    
    # 记录异常
    print(f"Agent 停止：{stop_reason}")
    
    # 降级策略 1：返回已收集的部分信息
    if state["tool_results"]:
        partial_info = "\n".join([
            f"工具 {r['tool']} 返回：{r['output']}"
            for r in state["tool_results"]
        ])
        return f"任务未能完全完成，但已获取以下信息：\n{partial_info}"
    
    # 降级策略 2：返回通用提示
    return f"任务未能在限定时间内完成。建议：\n1. 简化任务描述\n2. 增加步数限制\n3. 检查工具是否可用"
```

**降级策略的优先级**：

1. **返回部分结果**：如果已收集部分信息，返回给用户
2. **返回错误提示**：告诉用户任务失败，提供可能的解决方案
3. **记录日志**：便于开发者调试和优化

## 停止条件的组合策略

实际应用中，三种停止条件需要组合使用：

```python
# 完整的停止条件检查
class StopConditionChecker:
    def __init__(self, max_steps: int = 10, timeout: int = 300):
        self.max_steps = max_steps
        self.timeout = timeout
        self.start_time = time.time()
    
    def check(self, state: dict, decision: dict) -> tuple[bool, str]:
        """综合检查所有停止条件"""
        
        # 优先级 1：目标达成
        if is_goal_achieved(decision, state["user_input"]):
            return True, "目标达成"
        
        # 优先级 2：最大步数
        if state["step_count"] >= self.max_steps:
            return True, f"达到最大步数 {self.max_steps}"
        
        # 优先级 3：超时
        elapsed = time.time() - self.start_time
        if elapsed > self.timeout:
            return True, f"执行超时 ({elapsed:.1f}s)"
        
        return False, ""
```

**组合策略的配置建议**：

| 任务类型 | 最大步数 | 超时 | 说明 |
|----------|----------|------|------|
| 简单查询 | 3-5 | 30s | 快速响应 |
| 多步推理 | 10-15 | 2min | 平衡质量和速度 |
| 复杂任务 | 20-30 | 5min | 允许深度思考 |
| 探索性任务 | 50+ | 10min | 需要大量工具调用 |

<p align="center">
  <img src="../../assets/06-agent-loop/stop-state-machine.png" alt="Agent 状态机" width="95%"/>
  <br/>
  <em>Agent 状态机：5 个状态 + 转移条件</em>
</p>

## 总结

- **目标达成**是最理想的停止条件，Agent 自主判断任务完成
- **最大步数**和**超时**是兜底条件，防止无限循环和资源浪费
- 异常退出时应优雅降级，返回部分结果或错误提示
- 三种条件需要组合使用，根据任务类型调整参数

> 下一篇，我们将从零实现一个最小 Agent——不使用任何框架，纯代码实现一个能自主决策的 ReAct Agent。

## 参考链接

- [LangChain — How agents work](https://python.langchain.com/docs/concepts/how_agents_work/)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [OpenAI — A practical guide to building agents](https://platform.openai.com/docs/guides/agents)


> 下一页请阅读：[从零实现最小 Agent](./08-minimal-agent.md)
