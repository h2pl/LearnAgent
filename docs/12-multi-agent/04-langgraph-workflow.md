# LangGraph 实战：工作流编排

> CrewAI 适合线性流程和角色扮演。但真实业务中涉及条件分支、循环、中断恢复、人机协作时，你需要一个能精细控制每一步执行逻辑的框架——LangGraph。

## 目录

- [前置阅读](#前置阅读)
- [场景设定：代码审查工作流](#场景设定代码审查工作流)
- [LangGraph 核心概念速览](#langgraph-核心概念速览)
- [实现多 Agent 状态图](#实现多-agent-状态图)
- [条件路由与循环](#条件路由与循环)
- [断点恢复与人工审批](#断点恢复与人工审批)
- [运行与验证](#运行与验证)
- [CrewAI vs LangGraph 选型](#crewai-vs-langgraph-选型)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。CrewAI 的 Agent 角色扮演模式好用，但有边界：流程必须是线性的或简单的层级委托。一旦出现"如果这样就走 A 分支，如果那样就走 B 分支，中途可能需要人工介入"的逻辑，CrewAI 就不够用了。

LangGraph 正好解决这个问题——**用状态图（StateGraph）定义多 Agent 的执行流程**。本文用一个**代码审查工作流**实战案例，教你用 LangGraph 实现条件路由、循环重试和人工审批。

## 前置阅读

本文假设你了解 LangGraph 的基本概念（StateGraph、Node、Edge、ConditionalEdge）。如果没读过，建议先看 [LangGraph 详解（一）](../10-framework/03-langgraph-1.md) 前三节。

## 场景设定：代码审查工作流

我们要实现一个**代码审查助手**——当开发者提交 PR 时，系统自动执行以下工作流：

1. **代码审查 Agent** 审查代码，给出修改意见
2. 如果发现严重问题，**安全审查 Agent** 介入检查安全漏洞
3. 如果问题可自动修复，**修复 Agent** 自动修改
4. 所有情况下，都需要**人工审批**才能合并
5. 人工驳回则回到代码审查重新修改

这个流程涉及条件分支（安全问题？）、循环（被打回重改）、中断等待（人工审批），CrewAI 实现不了。

## LangGraph 核心概念速览

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# 1. 定义状态——工作流中所有 Agent 共享的数据容器
class CodeReviewState(TypedDict):
    pr_content: str          # PR 代码内容
    review_result: str       # 审查结果
    has_security_issue: bool  # 是否有安全问题
    auto_fixed: bool         # 是否已自动修复
    approved: bool           # 是否通过审批
    iterations: int          # 修改轮次

# 2. 定义节点——每个 Agent 是一个处理节点
#    def my_agent(state: CodeReviewState) -> dict:
#        # 处理逻辑
#        return {"review_result": "..."}

# 3. 定义边——如何从一个节点走向下一个节点
#    graph.add_edge("node_a", "node_b")
#    graph.add_conditional_edges("node_a", router_function)
```

## 实现多 Agent 状态图

### 定义 Agent 节点

每个 Agent 是一个 Python 函数，接收当前状态，返回状态更新：

```python
import os
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END

llm = ChatAnthropic(model="claude-sonnet-4-6")

# 节点 1：代码审查 Agent
def code_review_agent(state: CodeReviewState) -> dict:
    """审查 PR 代码质量。"""
    review = llm.invoke(
        f"审查以下代码，重点关注：代码质量、潜在 Bug、性能问题：\n"
        f"{state['pr_content']}\n"
        f"输出格式：\n"
        f"## 审查结果\n"
        f"### 严重问题（如安全漏洞、数据丢失）\n"
        f"### 优化建议\n"
        f"### 是否通过"
    )
    has_security = "安全" in review.content or "注入" in review.content
    return {
        "review_result": review.content,
        "has_security_issue": has_security,
    }

# 节点 2：安全审查 Agent
def security_review_agent(state: CodeReviewState) -> dict:
    """专门检查安全漏洞。"""
    security = llm.invoke(
        f"对以下代码进行安全审计，检查：SQL 注入、XSS、CSRF、权限绕过：\n"
        f"{state['pr_content']}\n"
        f"审查结果：{state['review_result']}"
    )
    return {"review_result": f"{state['review_result']}\n\n## 安全审计\n{security.content}"}

# 节点 3：自动修复 Agent
def auto_fix_agent(state: CodeReviewState) -> dict:
    """自动修复可修复的问题。"""
    fix = llm.invoke(
        f"自动修复以下代码审查中发现的可修复问题：\n"
        f"{state['review_result']}\n"
        f"代码：\n{state['pr_content']}\n"
        f"只输出修复后的完整代码，不要解释。"
    )
    return {"pr_content": fix.content, "auto_fixed": True}

# 节点 4：人工审批节点
def human_approval(state: CodeReviewState) -> dict:
    """等待人工审批。实际运行时阻塞等待用户输入。"""
    print(f"\n=== 等待审批 ===")
    print(f"审查结果：{state['review_result'][:200]}...")
    print(f"自动修复：{'是' if state.get('auto_fixed') else '否'}")
    # 实际集成中，这里会发送通知并等待外部 Webhook
    approved = input("是否批准？(y/n): ").lower() == "y"
    return {"approved": approved}
```

### 定义路由逻辑

路由函数决定下一个节点是谁：

```python
def security_route(state: CodeReviewState) -> str:
    """判断是否需要安全审查。"""
    if state["has_security_issue"]:
        return "security_review"
    return "auto_fix_or_approval"

def fix_or_approve(state: CodeReviewState) -> str:
    """判断是否需要自动修复。"""
    if state["iterations"] < 3 and "可自动修复" in state["review_result"]:
        return "auto_fix"
    return "human_approval"

def approval_route(state: CodeReviewState) -> str:
    """判断审批结果。"""
    if state["approved"]:
        return END
    # 驳回时增加轮次计数，回到代码审查重新修改
    return "code_review"
```

### 构建状态图

```python
# 构建图
workflow = StateGraph(CodeReviewState)

# 添加节点
workflow.add_node("code_review", code_review_agent)
workflow.add_node("security_review", security_review_agent)
workflow.add_node("auto_fix", auto_fix_agent)
workflow.add_node("human_approval", human_approval)

# 设置入口
workflow.set_entry_point("code_review")

# 添加边
workflow.add_conditional_edges(
    "code_review",
    security_route,
    {"security_review": "security_review",
     "auto_fix_or_approval": "auto_fix"}
)
workflow.add_edge("security_review", "auto_fix")
workflow.add_conditional_edges(
    "auto_fix",
    fix_or_approve,
    {"auto_fix": "auto_fix", "human_approval": "human_approval"}
)
workflow.add_conditional_edges(
    "human_approval",
    approval_route,
    {END: END, "code_review": "code_review"}
)

# 编译
app = workflow.compile()
```

## 流程全景

<p align="center">
  <img src="../../assets/12-multi-agent/langgraph-code-review-flow.svg" alt="LangGraph 代码审查工作流：条件分支 + 循环 + 人工审批" width="95%"/>
</p>

这个图展示了完整的执行路径：

```
code_review
  ├── 有安全问题 → security_review → auto_fix
  └── 安全问题   → auto_fix
        ├── 可修复 → auto_fix（修复后到 human_approval）
        └── 不可修 → human_approval
              ├── 批准 → END
              └── 驳回 → code_review（轮次 < 3）
```

## 运行与验证

```python
# 初始状态
initial_state = {
    "pr_content": """
def get_user(id):
    query = "SELECT * FROM users WHERE id = " + id
    return db.execute(query)
""",
    "iterations": 0,
}

# 执行工作流
for event in app.stream(initial_state):
    for node_name, state in event.items():
        print(f"\n--- {node_name} ---")
        if node_name == "human_approval":
            print(f"审批结果：{'通过' if state.get('approved') else '待定'}")
```

## CrewAI vs LangGraph 选型

| 维度 | CrewAI | LangGraph |
|------|--------|-----------|
| **流程控制** | 线性/层级 | 状态图（任意拓扑） |
| **条件分支** | 不支持 | 原生支持 |
| **循环** | 不支持 | 原生支持 |
| **中断恢复** | 不支持 | 原生支持（Checkpoint） |
| **人机协作** | 有限 | 原生支持 |
| **学习曲线** | 低 | 中-高 |
| **适合场景** | 角色扮演、内容生产 | 复杂工作流、自动化流水线 |

<p align="center">
  <img src="../../assets/12-multi-agent/crewai-vs-langgraph-comparison.svg" alt="CrewAI vs LangGraph 框架选型对比" width="90%"/>
  <br/><em>图：CrewAI 角色扮演 vs LangGraph 状态图选型</em>
</p>

**建议**：做角色扮演式的多 Agent 协作用 CrewAI，做有状态、有分支、需要人工介入的工作流用 LangGraph。两者不冲突——CrewAI Agent 内部也可以使用 LangGraph 做流程控制。

## 总结

- **LangGraph 用状态图解决复杂流程**：条件分支、循环、中断恢复——CrewAI 做不到的，LangGraph 是答案
- **四个节点实现完整工作流**：代码审查 → 安全审查 → 自动修复 → 人工审批
- **条件路由 + 循环实现迭代改进**：审批驳回自动回到审查节点，轮次上限防止死循环
- **Checkpoint 机制支持中断恢复**：工作流可以在任意节点保存状态，重启后从断点继续
- **CrewAI 做角色，LangGraph 做流程**：两者互补，不是替代

> 下一篇 [多 Agent 系统设计权衡](./05-design-tradeoffs.md)——技术选型之后，回到架构层面：什么时候该拆、成本多高、怎么演进？

## 参考链接

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph — Multi-Agent Patterns](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [LangGraph — Human-in-the-loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
