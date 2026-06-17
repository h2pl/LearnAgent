# -*- coding: utf-8 -*-
"""生成第五章（Agent 循环）所有 17 张配图。

每篇文章 2-3 张图，覆盖核心循环、模式全景、ReAct、Plan-and-Execute、
Reflexion、停止条件、最小 Agent 等主题。

设计原则：
- 一图一概念，避免信息过载
- 中文标签、配色统一（与 04 章 variants-landscape 一致）
- 不复用其他章节的图
- 图注 ≤ 30 字
"""
import os
import math

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle, Polygon
from matplotlib import font_manager

# ============== 通用配置 ==============
# 多字体 fallback，优先支持中文 + 特殊符号
plt.rcParams['font.sans-serif'] = [
    'Noto Sans CJK SC', 'Source Han Sans CN', 'WenQuanYi Zen Hei',
    'SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans',
]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 12

OUT_DIR = r"e:\Learning\AgentDevGuide\assets\05-agent-loop"
os.makedirs(OUT_DIR, exist_ok=True)

# 配色（与 02/04 章统一）
C = {
    'primary':   '#2563eb',  # 蓝
    'secondary': '#7c3aed',  # 紫
    'success':   '#10b981',  # 绿
    'warning':   '#f59e0b',  # 橙
    'danger':    '#ef4444',  # 红
    'gray':      '#6b7280',  # 灰
    'light':     '#e5e7eb',  # 浅灰
    'dark':      '#1f2937',  # 深灰
    'text':      '#374151',
    'muted':     '#4b5563',
    'pink':      '#ec4899',
    'cyan':      '#06b6d4',
    'amber':     '#d97706',
}
PALETTE = [C['primary'], C['secondary'], C['success'], C['warning'],
           C['danger'], C['gray'], C['pink'], C['cyan']]


def save(fig, name, dpi=150):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"[OK] {name}")


def box(ax, x, y, w, h, color, title='', lines=None, alpha=0.95, fontsize=11):
    """绘制圆角矩形节点"""
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor='white', linewidth=2, alpha=alpha,
    )
    ax.add_patch(box)
    if title:
        ax.text(x, y + 0.12, title, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='white')
    if lines:
        for i, line in enumerate(lines):
            ax.text(x, y - 0.15 - i * 0.25, line,
                    ha='center', va='center', fontsize=fontsize - 1, color='white')


def arrow(ax, x1, y1, x2, y2, color=None, lw=1.5, style='->'):
    if color is None:
        color = C['dark']
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw))


# ============================================================
# 01-agent-vs-chatbot-workflow
# ============================================================
def make_three_forms_comparison():
    """三种应用形态对比：Chatbot / Workflow / Agent"""
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('三种应用形态：Chatbot / Workflow / Agent',
                 fontsize=16, fontweight='bold', pad=20)

    # 三列
    cols = [
        (2.5, 'Chatbot', C['gray'],
         ['一问一答', '无记忆', '无行动',
          '用户 → 文本', '决策权：用户']),
        (7.0, 'Workflow', C['warning'],
         ['预设流程', '固定步骤', '无分支决策',
          '输入 → 步骤1→2→3', '决策权：预设流程']),
        (11.5, 'Agent', C['primary'],
         ['自主决策', '动态调整', '感知-决策-行动',
          'Observe → Think → Act', '决策权：模型自主']),
    ]
    for x, name, color, lines in cols:
        # 头部
        box(ax, x, 6, 3, 0.8, color, name, fontsize=15)
        # 主体内容
        for i, line in enumerate(lines):
            ax.text(x, 4.7 - i * 0.5, '- ' + line,
                    ha='center', va='center', fontsize=11, color=C['text'])

    # 底部能力雷达示意（简化）
    ax.text(7, 1.5, '关键差异：决策权归属',
            ha='center', va='center', fontsize=13, fontweight='bold', color=C['dark'])
    ax.text(7, 0.8, 'Chatbot = 用户决策 │ Workflow = 流程决策 │ Agent = 模型决策',
            ha='center', va='center', fontsize=12, color=C['text'])

    save(fig, 'three-forms-comparison.png')


def make_decision_power_diagram():
    """决策权归属示意图"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title('决策权归属：决定系统形态的本质',
                 fontsize=16, fontweight='bold', pad=20)

    # 三个圆表示不同决策主体
    circles = [
        (3, 3, 1.5, C['gray'], 'Chatbot', '决策权在\n【用户】'),
        (6, 3, 1.5, C['warning'], 'Workflow', '决策权在\n【预设流程】'),
        (9, 3, 1.5, C['primary'], 'Agent', '决策权在\n【模型自主】'),
    ]
    for x, y, r, color, name, label in circles:
        circle = Circle((x, y), r, facecolor=color, alpha=0.3,
                        edgecolor=color, linewidth=3)
        ax.add_patch(circle)
        ax.text(x, y + 0.4, name, ha='center', va='center',
                fontsize=15, fontweight='bold', color=color)
        ax.text(x, y - 0.3, label, ha='center', va='center',
                fontsize=11, color=C['text'])

    # 演进箭头
    ax.annotate('', xy=(7.5, 3), xytext=(4.5, 3),
                arrowprops=dict(arrowstyle='->', color=C['dark'], lw=2.5))
    ax.text(6, 3.6, '决策权转移', ha='center', fontsize=11,
            color=C['dark'], style='italic')
    ax.text(6, 2.4, '从人 → 流程 → 模型', ha='center', fontsize=10,
            color=C['muted'], style='italic')

    # 底部说明
    ax.text(6, 0.5, '越往右，自动化程度越高、对模型能力依赖越重',
            ha='center', fontsize=12, color=C['text'])

    save(fig, 'decision-power-diagram.png')


# ============================================================
# 02-agent-core-loop
# ============================================================
def make_core_loop_four_stages():
    """Agent 核心循环四阶段"""
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('Agent 核心循环：四阶段闭环',
                 fontsize=16, fontweight='bold', pad=20)

    # 四个阶段
    stages = [
        (2, 4, '① Observe\n观察', C['primary'],
         ['读取环境状态', '解析用户输入', '获取工具结果']),
        (6.5, 5, '② Think\n思考', C['secondary'],
         ['分析当前情况', '决定下一步行动', '推理目标差距']),
        (11, 4, '③ Act\n行动', C['success'],
         ['调用工具', '生成回复', '修改环境']),
        (6.5, 2, '④ Observe\n再观察', C['warning'],
         ['评估行动结果', '更新内部状态', '回到步骤 ②']),
    ]

    for x, y, title, color, lines in stages:
        # 圆角矩形
        rect = FancyBboxPatch(
            (x - 1.5, y - 0.7), 3, 1.4,
            boxstyle="round,pad=0.1",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.3, title, ha='center', va='center',
                fontsize=13, fontweight='bold', color='white')
        for i, line in enumerate(lines):
            ax.text(x, y - 0.15 - i * 0.22, line,
                    ha='center', va='center', fontsize=9, color='white')

    # 箭头：Observe → Think → Act
    arrow(ax, 3.3, 4.5, 5.2, 4.8, C['dark'], lw=2)
    arrow(ax, 7.7, 4.8, 9.6, 4.3, C['dark'], lw=2)
    # Act → 再观察
    arrow(ax, 10.5, 3.5, 8, 2.4, C['dark'], lw=2)
    # 再观察 → Think (虚线)
    arrow(ax, 6.5, 2.6, 6.5, 4.4, C['muted'], lw=1.5)

    # 底部说明
    ax.text(6.5, 0.5, '循环的核心：模型在每一步都重新观察、重新思考、重新行动',
            ha='center', fontsize=12, color=C['text'], style='italic')

    save(fig, 'core-loop-four-stages.png')


def make_agent_architecture():
    """Agent 系统架构图"""
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('Agent 系统架构：五大组件协同',
                 fontsize=16, fontweight='bold', pad=20)

    # 中心：Agent 主体
    center = Circle((6.5, 4), 1.5, facecolor=C['primary'],
                    edgecolor='white', linewidth=3, alpha=0.9)
    ax.add_patch(center)
    ax.text(6.5, 4.2, 'Agent', ha='center', va='center',
            fontsize=18, fontweight='bold', color='white')
    ax.text(6.5, 3.7, '核心循环', ha='center', va='center',
            fontsize=11, color='white')

    # 周边 5 个组件
    components = [
        (2, 6.5, 'LLM 大脑', C['secondary'],
         '推理 + 决策'),
        (11, 6.5, '工具集', C['success'],
         'API / 函数 / DB'),
        (2, 1.5, '记忆系统', C['warning'],
         '短期 + 长期'),
        (11, 1.5, '规划器', C['pink'],
         '任务分解'),
        (6.5, 0.5, '停止条件', C['danger'],
         '目标 / 步数 / 超时'),
    ]
    for x, y, name, color, desc in components:
        rect = FancyBboxPatch(
            (x - 1.3, y - 0.5), 2.6, 1,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor='white', linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.15, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        ax.text(x, y - 0.2, desc, ha='center', va='center',
                fontsize=9, color='white')

    # 连线（中心到周围）
    for x, y, _, _, _ in components:
        ax.plot([6.5, x], [4, y], color=C['muted'],
                linewidth=1, alpha=0.4, zorder=0)

    # 顶部小标题
    ax.text(6.5, 7.3, '一个 Agent = 中心循环 + 五大外围组件',
            ha='center', fontsize=12, color=C['text'], style='italic')

    save(fig, 'agent-architecture.png')


# ============================================================
# 03-agent-patterns-overview
# ============================================================
def make_patterns_landscape():
    """Agent 五大模式鸟瞰图"""
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_xlim(-7, 7)
    ax.set_ylim(-6, 6)
    ax.axis('off')
    ax.set_title('Agent 五大模式鸟瞰', fontsize=18, fontweight='bold', pad=20)

    # 中心
    center = Circle((0, 0), 1.0, facecolor=C['dark'],
                    edgecolor='white', linewidth=3, zorder=10)
    ax.add_patch(center)
    ax.text(0, 0.1, 'Agent', ha='center', va='center',
            fontsize=18, fontweight='bold', color='white', zorder=11)
    ax.text(0, -0.3, '模式', ha='center', va='center',
            fontsize=12, color='white', zorder=11)

    # 5 个模式（环形布局）
    import math
    patterns = [
        {'name': 'ReAct', 'angle': 90, 'color': C['primary'],
         'subtitle': '推理+行动\n交替',
         'desc': '基座范式\n边想边做'},
        {'name': 'Plan-and-Execute', 'angle': 90 - 72, 'color': C['success'],
         'subtitle': '先规划\n后执行',
         'desc': '长链任务\n结构清晰'},
        {'name': 'Reflexion', 'angle': 90 - 144, 'color': C['secondary'],
         'subtitle': '失败后\n自我反思',
         'desc': '可重试\n会学习'},
        {'name': 'ReWOO', 'angle': 90 - 216, 'color': C['warning'],
         'subtitle': '批量规划\n并行执行',
         'desc': '省 Token\n省时间'},
        {'name': 'LATS', 'angle': 90 - 288, 'color': C['pink'],
         'subtitle': '树搜索\n多分支',
         'desc': '高价值\n高成本'},
    ]

    for p in patterns:
        rad = math.radians(p['angle'])
        cx = 4.5 * math.cos(rad)
        cy = 4.5 * math.sin(rad)

        # 连线
        ax.plot([0, cx * 0.8], [0, cy * 0.8],
                color=p['color'], linewidth=2.5, alpha=0.7, zorder=1)

        # 圆形节点
        outer = Circle((cx, cy), 1.1, facecolor=p['color'],
                       edgecolor='white', linewidth=3, alpha=0.9, zorder=5)
        ax.add_patch(outer)
        ax.text(cx, cy + 0.35, p['name'], ha='center', va='center',
                fontsize=12, fontweight='bold', color='white', zorder=6)
        ax.text(cx, cy - 0.1, p['subtitle'], ha='center', va='center',
                fontsize=9, color='white', zorder=6)
        ax.text(cx, cy - 0.45, p['desc'], ha='center', va='center',
                fontsize=8, color='white', style='italic', zorder=6)

    # 底部说明
    ax.text(0, -5.5, '五种模式回答同一个问题：怎么让循环更聪明、更稳、更快',
            ha='center', fontsize=12, color=C['text'], style='italic')

    save(fig, 'agent-patterns-landscape.png')


def make_pattern_relationships():
    """模式关系图：三种设计哲学对应五种具体实现"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('Agent 模式关系图：三种设计哲学对应五种实现',
                 fontsize=15, fontweight='bold', pad=20)

    # 三个哲学层（顶部）
    philosophies = [
        (2.5, 7.5, C['primary'], '反应式\n(reactive)',
         ['走一步看一步', '短链、动态']),
        (7, 7.5, C['success'], '深思熟虑\n(deliberative)',
         ['先想后做', '长链、结构化']),
        (11.5, 7.5, C['secondary'], '反复试错\n(iterative)',
         ['错了再反思', '高价值、可重试']),
    ]
    for x, y, color, name, lines in philosophies:
        rect = FancyBboxPatch(
            (x - 1.8, y - 0.7), 3.6, 1.4,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.2, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        for i, line in enumerate(lines):
            ax.text(x, y - 0.15 - i * 0.22, line,
                    ha='center', va='center', fontsize=9, color='white')

    # 五种模式（底部）
    patterns = [
        (2.5, 4, C['primary'], 'ReAct',
         ['推理+行动\n交替']),
        (5.5, 2.5, C['success'], 'Plan-and-Execute',
         ['先规划\n后执行']),
        (7, 4, C['warning'], 'ReWOO',
         ['批量规划\n并行执行']),
        (10, 2.5, C['secondary'], 'Reflexion',
         ['失败\n自我反思']),
        (11.5, 4, C['pink'], 'LATS',
         ['树搜索\n多分支']),
    ]
    for x, y, color, name, lines in patterns:
        rect = FancyBboxPatch(
            (x - 1.2, y - 0.6), 2.4, 1.2,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.15, name, ha='center', va='center',
                fontsize=11, fontweight='bold', color='white')
        for i, line in enumerate(lines):
            ax.text(x, y - 0.15 - i * 0.18, line,
                    ha='center', va='center', fontsize=8, color='white')

    # 映射线：哲学 → 模式
    mappings = [
        (2.5, 6.8, 2.5, 4.6, C['primary']),
        (7, 6.8, 5.5, 3.1, C['success']),
        (7, 6.8, 7, 4.6, C['warning']),
        (11.5, 6.8, 10, 3.1, C['secondary']),
        (11.5, 6.8, 11.5, 4.6, C['pink']),
    ]
    for x1, y1, x2, y2, color in mappings:
        ax.plot([x1, x2], [y1, y2], color=color,
                linewidth=1.5, alpha=0.5, zorder=0)

    # 组合标注
    ax.text(7, 1.0, '实战中常混用：外层规划 + 内层反应 + 失败反思',
            ha='center', fontsize=12, color=C['success'], fontweight='bold')
    ax.text(7, 0.3, 'ReWOO = Plan 的工程优化版  │  LATS = Reflexion 的搜索扩展版',
            ha='center', fontsize=10, color=C['muted'], style='italic')

    save(fig, 'pattern-relationships.png')


def make_selection_decision_tree():
    """Agent 模式选型决策树"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Agent 模式选型决策树', fontsize=16, fontweight='bold', pad=20)

    # 起始节点
    box(ax, 7, 9, 4, 0.8, C['dark'],
        '起点：用户任务', fontsize=13)

    # 决策 1：任务步骤数
    box(ax, 7, 7.5, 5, 0.9, C['primary'],
        'Q1: 任务只有 1-3 步吗？', fontsize=12)
    arrow(ax, 7, 8.6, 7, 7.95)

    # 是 → ReAct
    box(ax, 2.5, 5.8, 3, 0.9, C['success'],
        '→ ReAct（80%场景）', fontsize=12)
    ax.text(4.7, 6.7, '是', fontsize=11, color=C['success'], fontweight='bold')
    arrow(ax, 5.5, 7.3, 3.2, 6.25)

    # 否 → 决策 2
    box(ax, 10, 6, 5.5, 0.9, C['secondary'],
        'Q2: 子任务相互独立？', fontsize=12)
    ax.text(8.8, 6.7, '否', fontsize=11, color=C['danger'], fontweight='bold')
    arrow(ax, 8.5, 7.3, 9, 6.45)

    # 是 → ReWOO
    box(ax, 11.5, 4.2, 2.8, 0.9, C['warning'],
        '→ ReWOO（并行）', fontsize=12)
    ax.text(10.6, 5.0, '是', fontsize=11, color=C['success'], fontweight='bold')
    arrow(ax, 11.5, 5.55, 11.5, 4.65)

    # 否 → 决策 3
    box(ax, 10, 4.2, 5.5, 0.9, C['pink'],
        'Q3: 任务可一次性规划？', fontsize=12)
    ax.text(12.6, 5.0, '否', fontsize=11, color=C['danger'], fontweight='bold')
    arrow(ax, 12.0, 5.55, 11.5, 4.65)

    # 否 → 决策 4
    box(ax, 7, 2.5, 5.5, 0.9, C['amber'],
        'Q4: 任务高价值、允许多次试错？', fontsize=12)
    ax.text(7, 3.3, '是 →', fontsize=11, color=C['success'], fontweight='bold',
            ha='center')
    ax.text(7, 2.0, '否 → 退回到 ReAct',
            fontsize=10, color=C['danger'], fontweight='bold', ha='center')

    # 高价值 + 决策
    box(ax, 3, 0.8, 3, 0.7, C['secondary'],
        '→ Reflexion（反思）', fontsize=11)
    box(ax, 7, 0.8, 3, 0.7, C['primary'],
        '→ LATS（树搜索）', fontsize=11)
    ax.text(4.5, 1.8, '分支少', fontsize=9, color=C['text'])
    ax.text(7, 1.8, '分支多', fontsize=9, color=C['text'])
    arrow(ax, 6.0, 2.05, 3.8, 1.15)
    arrow(ax, 7.0, 2.05, 7.0, 1.15)

    save(fig, 'pattern-selection-decision-tree.png')


# ============================================================
# 04-react-pattern
# ============================================================
def make_react_name_etymology():
    """ReAct 命名由来：Re(asoning) + (A)ct(ing)"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title('ReAct 命名由来：Re(asoning) + (A)ct(ing)',
                 fontsize=16, fontweight='bold', pad=20)

    # Reasoning 框
    box(ax, 3, 3.5, 4, 2.2, C['secondary'],
        'Reasoning',
        ['【推理】', '在每一步用自然语言', '说明「为什么」这么做'], fontsize=12)

    # Acting 框
    box(ax, 11, 3.5, 4, 2.2, C['success'],
        'Acting',
        ['【行动】', '调用工具、执行操作', '或返回最终答案'], fontsize=12)

    # 中间 ReAct 拼写
    circle = Circle((7, 3.5), 1.2, facecolor=C['primary'],
                    edgecolor='white', linewidth=3)
    ax.add_patch(circle)
    ax.text(7, 3.7, 'ReAct', ha='center', va='center',
            fontsize=20, fontweight='bold', color='white')
    ax.text(7, 3.15, '/ri-akt/', ha='center', va='center',
            fontsize=10, color='white', style='italic')

    # 拆解标注
    ax.annotate('', xy=(5.9, 3.5), xytext=(5.0, 3.5),
                arrowprops=dict(arrowstyle='->', color=C['dark'], lw=2))
    ax.text(5.5, 4.0, 'Re', ha='center', fontsize=14,
            color=C['secondary'], fontweight='bold')
    ax.annotate('', xy=(8.1, 3.5), xytext=(9.0, 3.5),
                arrowprops=dict(arrowstyle='->', color=C['dark'], lw=2))
    ax.text(8.5, 4.0, 'Act', ha='center', fontsize=14,
            color=C['success'], fontweight='bold')

    # 底部说明
    ax.text(7, 1.3, '截取主干拼写：Re(asoning) + (A)ct(ing)',
            ha='center', fontsize=13, color=C['text'], fontweight='bold')
    ax.text(7, 0.6, '读作 /riˈækt/，像一个真实单词',
            ha='center', fontsize=11, color=C['muted'], style='italic')

    save(fig, 'react-name-etymology.png')


def make_react_loop_detail():
    """ReAct 详细循环示意图"""
    fig, ax = plt.subplots(figsize=(13, 10))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('ReAct 循环：Thought → Action → Observation 反复迭代',
                 fontsize=15, fontweight='bold', pad=20)

    # 用户问题
    box(ax, 6.5, 9, 6, 0.8, C['gray'],
        '用户：北京今天天气怎么样？适合户外活动吗？', fontsize=12)

    # Step 1
    box(ax, 2, 7, 3.5, 1.5, C['secondary'],
        'Step 1: Thought',
        ['用户想了解北京天气', '我需要先查天气数据'], fontsize=11)
    box(ax, 6.5, 7, 3.5, 1.5, C['success'],
        'Action',
        ['get_weather("北京")'], fontsize=11)
    box(ax, 11, 7, 3.5, 1.5, C['warning'],
        'Observation',
        ['晴，25°C', '微风，湿度 45%'], fontsize=11)

    # 箭头 Step 1
    arrow(ax, 3.7, 7, 4.7, 7)
    arrow(ax, 8.2, 7, 9.2, 7)

    # Step 2
    box(ax, 2, 4.5, 3.5, 1.5, C['secondary'],
        'Step 2: Thought',
        ['天气数据已获取', '晴天+25°C+微风 = 适合'], fontsize=11)
    box(ax, 6.5, 4.5, 3.5, 1.5, C['danger'],
        'Action',
        ['final_answer(...)'], fontsize=11)
    box(ax, 11, 4.5, 3.5, 1.5, C['primary'],
        'Final Answer',
        ['晴 25°C', '非常适合户外活动'], fontsize=11)

    # 箭头 Step 2
    arrow(ax, 3.7, 4.5, 4.7, 4.5)
    arrow(ax, 8.2, 4.5, 9.2, 4.5)

    # 步骤间循环箭头
    arrow(ax, 11, 6.2, 11, 5.25, C['primary'], lw=2, style='->')

    # 底部说明
    ax.text(6.5, 2.5, '核心：每步都让模型「说出」推理过程',
            ha='center', fontsize=13, color=C['text'], fontweight='bold')
    ax.text(6.5, 1.8, '• 便于调试  • 便于审查  • 避免走偏',
            ha='center', fontsize=11, color=C['muted'])
    ax.text(6.5, 0.8, 'Observation 又是下一步 Thought 的输入',
            ha='center', fontsize=11, color=C['secondary'], style='italic')

    save(fig, 'react-loop-detail.png')


def make_react_vs_cot():
    """ReAct vs CoT 对比"""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('ReAct vs CoT：推理+行动 vs 纯推理',
                 fontsize=15, fontweight='bold', pad=20)

    # 左侧 CoT
    box(ax, 3.5, 7, 5, 0.8, C['secondary'],
        'Chain-of-Thought（纯推理）', fontsize=12)
    box(ax, 3.5, 5.5, 5, 0.8, C['light'],
        'Step 1: 数学问题...', fontsize=11)
    ax.text(3.5, 5.4, '（白底黑字示意思考）', ha='center', fontsize=9,
            color=C['muted'], style='italic')
    box(ax, 3.5, 4.3, 5, 0.8, C['light'],
        'Step 2: 继续推理...', fontsize=11)
    box(ax, 3.5, 3.1, 5, 0.8, C['light'],
        'Step 3: 得到答案', fontsize=11)
    ax.text(3.5, 1.7, '优点：逻辑严密\n缺点：无法获取外部信息',
            ha='center', fontsize=10, color=C['text'])
    ax.text(3.5, 0.5, '纯思考，不动手',
            ha='center', fontsize=11, color=C['secondary'], fontweight='bold')

    # 右侧 ReAct
    box(ax, 10.5, 7, 5, 0.8, C['primary'],
        'ReAct（推理 + 行动）', fontsize=12)
    box(ax, 10.5, 5.5, 5, 0.8, C['secondary'],
        'Thought: 需要查天气', fontsize=11)
    box(ax, 10.5, 4.3, 5, 0.8, C['success'],
        'Action: get_weather()', fontsize=11)
    box(ax, 10.5, 3.1, 5, 0.8, C['warning'],
        'Obs: 晴 25°C', fontsize=11)
    ax.text(10.5, 1.7, '优点：兼顾推理+获取信息\n缺点：每步都需 LLM 调用',
            ha='center', fontsize=10, color=C['text'])
    ax.text(10.5, 0.5, '边想边做，循环往复',
            ha='center', fontsize=11, color=C['primary'], fontweight='bold')

    # 中间分割
    ax.plot([7, 7], [0.5, 7.5], color=C['muted'],
            linewidth=2, linestyle='--', alpha=0.5)

    save(fig, 'react-vs-cot.png')


# ============================================================
# 05-plan-and-execute
# ============================================================
def make_plan_execute_flow():
    """Plan-and-Execute 流程：Planner → Executor"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('Plan-and-Execute：规划与执行解耦',
                 fontsize=15, fontweight='bold', pad=20)

    # 用户输入
    box(ax, 7, 8, 6, 0.8, C['gray'],
        '用户任务：调研 RAG 技术并写一份 500 字简介', fontsize=12)

    # Planner
    box(ax, 4, 6, 4, 1.5, C['primary'],
        'Planner（规划器）',
        ['LLM 一次性产出', '完整步骤列表'], fontsize=12)

    # 计划输出
    box(ax, 10.5, 6, 4.5, 1.5, C['light'],
        '计划 JSON',
        ['① search_web()', '② fetch_url()', '③ search_paper()', '④ summarize()'],
        fontsize=10)
    # 改字体颜色（light box 上用深色字）
    ax.text(10.5, 6.3, '计划 JSON', ha='center', va='center',
            fontsize=12, fontweight='bold', color=C['dark'])
    for i, line in enumerate(['① search_web()', '② fetch_url()',
                               '③ search_paper()', '④ summarize()']):
        ax.text(10.5, 5.85 - i * 0.22, line,
                ha='center', va='center', fontsize=10, color=C['text'])

    arrow(ax, 7, 7.6, 5, 6.75)
    arrow(ax, 5, 6, 8.5, 6)

    # Executor
    box(ax, 4, 3.5, 4, 1.5, C['success'],
        'Executor（执行器）',
        ['按步骤执行', '每步调工具', '不重新规划'], fontsize=12)

    # 输出
    box(ax, 10.5, 3.5, 4.5, 1.5, C['warning'],
        '执行过程',
        ['Step 1 → 拿链接', 'Step 2 → 拿内容', 'Step 3 → 拿摘要', 'Step 4 → 出报告'],
        fontsize=10)
    ax.text(10.5, 3.8, '执行过程', ha='center', va='center',
            fontsize=12, fontweight='bold', color='white')
    for i, line in enumerate(['Step 1 → 拿链接', 'Step 2 → 拿内容',
                               'Step 3 → 拿摘要', 'Step 4 → 出报告']):
        ax.text(10.5, 3.35 - i * 0.22, line,
                ha='center', va='center', fontsize=10, color='white')

    arrow(ax, 4, 2.75, 8.5, 2.75)
    # 改：Executor 接收 plan，输出到 step
    arrow(ax, 4, 2.75, 4, 2.75)  # placeholder
    arrow(ax, 4, 4.2, 8.5, 4.2, color=C['muted'])
    ax.text(6.25, 4.4, '按计划执行', ha='center', fontsize=10,
            color=C['muted'], style='italic')

    # 最终输出
    box(ax, 7, 1, 6, 0.8, C['dark'],
        '最终输出：500 字 RAG 简介', fontsize=12)
    arrow(ax, 10.5, 2.75, 8.5, 1.4)
    arrow(ax, 4, 2.75, 5.5, 1.4)

    # 底部
    ax.text(7, 0.2, '关键设计：规划一次、串行执行、计划可复用于出错定位',
            ha='center', fontsize=11, color=C['text'], style='italic')

    save(fig, 'plan-execute-flow.png')


def make_plan_execute_example():
    """Plan-and-Execute 实例：步骤示例"""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('Plan-and-Execute 实例：4 步研究 RAG',
                 fontsize=15, fontweight='bold', pad=20)

    # 4 步
    steps = [
        (2, 5.5, '① search_web', C['primary'],
         '搜索 RAG 综述', '找到 3 个链接'),
        (5.5, 5.5, '② fetch_url', C['secondary'],
         '访问最佳链接', '拿到架构说明'),
        (9, 5.5, '③ search_paper', C['success'],
         '搜索原文', 'Lewis 2020 摘要'),
        (12.5, 5.5, '④ summarize', C['warning'],
         '综合三个源', '500 字简介'),
    ]
    for x, y, name, color, inp, out in steps:
        # 节点
        rect = FancyBboxPatch(
            (x - 1.3, y - 0.7), 2.6, 1.4,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.35, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        ax.text(x, y - 0.1, inp, ha='center', va='center',
                fontsize=10, color='white')
        ax.text(x, y - 0.4, '→ ' + out, ha='center', va='center',
                fontsize=9, color='white', style='italic')

    # 箭头
    for i in range(3):
        x1 = steps[i][0] + 1.3
        x2 = steps[i+1][0] - 1.3
        arrow(ax, x1, 5.5, x2, 5.5, C['dark'], lw=2)

    # 底部说明
    ax.text(7, 2.5, '每步独立：失败可单独重试，不必从头来',
            ha='center', fontsize=12, color=C['text'], fontweight='bold')
    ax.text(7, 1.5, '外层规划、内层仍可用 ReAct 处理每步细节',
            ha='center', fontsize=11, color=C['muted'], style='italic')
    ax.text(7, 0.5, '总耗时 ≈ 4 步串行执行，Token ≈ 规划 1 + 执行 4',
            ha='center', fontsize=10, color=C['muted'])

    save(fig, 'plan-execute-example.png')


# ============================================================
# 06-reflexion-and-other-patterns
# ============================================================
def make_reflexion_loop():
    """Reflexion 自我反思循环"""
    fig, ax = plt.subplots(figsize=(13, 10))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Reflexion：失败 → 反思 → 记忆 → 再试',
                 fontsize=15, fontweight='bold', pad=20)

    # 4 个阶段
    stages = [
        (6.5, 8.5, 4, 0.9, C['primary'], '1. Actor 执行任务', 'ReAct 风格'),
        (6.5, 6.5, 4, 0.9, C['warning'], '2. Evaluator 评估', '成功/失败？'),
        (6.5, 4.5, 4, 0.9, C['danger'], '3. Self-Reflection', '用自然语言写反思'),
        (6.5, 2.5, 4, 0.9, C['success'], '4. 存入 Memory', '下次带进 Prompt'),
    ]
    for x, y, w, h, color, name, sub in stages:
        rect = FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.15, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        ax.text(x, y - 0.2, sub, ha='center', va='center',
                fontsize=10, color='white', style='italic')

    # 箭头
    for i in range(3):
        y1 = stages[i][1] - 0.5
        y2 = stages[i+1][1] + 0.5
        arrow(ax, 6.5, y1, 6.5, y2, C['dark'], lw=2)

    # 成功 → 终止
    ax.annotate('', xy=(11, 8.5), xytext=(8.5, 8.5),
                arrowprops=dict(arrowstyle='->', color=C['success'], lw=2))
    ax.text(11.5, 8.5, '成功 → 结束', ha='left', va='center',
            fontsize=11, color=C['success'], fontweight='bold')

    # 反思 → 下次 Actor
    arrow(ax, 4.5, 2.5, 2.5, 8.5, C['secondary'], lw=2, style='->')
    ax.text(3, 5.5, '反思带进\n下次 Prompt', ha='center', va='center',
            fontsize=10, color=C['secondary'], fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor='white', edgecolor=C['secondary']))

    # 底部
    ax.text(6.5, 1.0, '本质：用自然语言「自评分」代替符号化 reward',
            ha='center', fontsize=11, color=C['text'], style='italic')

    save(fig, 'reflexion-loop.png')


def make_rewoo_flow():
    """ReWOO 流程：批量规划 + 并行执行"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('ReWOO：批量规划 + 并行执行',
                 fontsize=15, fontweight='bold', pad=20)

    # Planner
    box(ax, 7, 8, 8, 1, C['primary'],
        'Planner 一次性产出所有工具调用', fontsize=12)
    ax.text(7, 7.3, 'E1 = Tool[args1]   E2 = Tool[args2]   E3 = Tool[args3]',
            ha='center', fontsize=11, color=C['text'], family='monospace')

    # Worker 并行
    box(ax, 2.5, 5, 3, 1.2, C['success'],
        'Worker 1', ['执行 E1'], fontsize=11)
    box(ax, 7, 5, 3, 1.2, C['success'],
        'Worker 2', ['执行 E2'], fontsize=11)
    box(ax, 11.5, 5, 3, 1.2, C['success'],
        'Worker 3', ['执行 E3'], fontsize=11)

    # 并行箭头
    arrow(ax, 5, 7.5, 2.5, 5.6)
    arrow(ax, 7, 7.5, 7, 5.6)
    arrow(ax, 9, 7.5, 11.5, 5.6)

    # 标注「并行」
    ax.text(7, 6.6, '||  并行执行  ||',
            ha='center', fontsize=14, color=C['success'],
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3',
                      facecolor='white', edgecolor=C['success']))

    # Solver
    box(ax, 7, 2.5, 8, 1.2, C['secondary'],
        'Solver 综合 E1+E2+E3 结果',
        ['一次性生成最终回答'], fontsize=12)

    # 箭头
    arrow(ax, 2.5, 4.4, 5, 3.1)
    arrow(ax, 7, 4.4, 7, 3.1)
    arrow(ax, 11.5, 4.4, 9, 3.1)

    # 对比 ReAct
    ax.text(7, 1.0, 'vs ReAct：省 50%+ Token，省 N× 时间',
            ha='center', fontsize=12, color=C['success'], fontweight='bold')
    ax.text(7, 0.3, '前提：E1/E2/E3 之间相互独立',
            ha='center', fontsize=10, color=C['muted'], style='italic')

    save(fig, 'rewoo-flow.png')


def make_lats_tree_search():
    """LATS 树搜索示意图"""
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('LATS：树搜索 + 反思的结合',
                 fontsize=15, fontweight='bold', pad=20)

    # 根节点
    circle = Circle((7, 8.5), 0.6, facecolor=C['primary'],
                    edgecolor='white', linewidth=2, zorder=5)
    ax.add_patch(circle)
    ax.text(7, 8.5, 'Root', ha='center', va='center',
            fontsize=10, fontweight='bold', color='white', zorder=6)

    # 二级
    level2 = [(3, 6.5, 'A1: 搜索', C['secondary']),
              (7, 6.5, 'A2: 查API', C['success']),
              (11, 6.5, 'A3: 读文档', C['warning'])]
    for x, y, name, color in level2:
        circle = Circle((x, y), 0.55, facecolor=color,
                        edgecolor='white', linewidth=2, zorder=5)
        ax.add_patch(circle)
        ax.text(x, y, name, ha='center', va='center',
                fontsize=9, fontweight='bold', color='white', zorder=6)
        # 连线
        ax.plot([7, x], [8, y], color=C['muted'],
                linewidth=1, alpha=0.5, zorder=1)

    # 三级（部分展开）
    level3 = [(1.5, 4.5, 'B1', C['secondary'], 0.85),
              (3, 4.5, 'B2', C['secondary'], 0.7),
              (4.5, 4.5, 'B3', C['gray'], 0.4),
              (6, 4.5, 'B4', C['success'], 0.9),
              (8, 4.5, 'B5', C['success'], 0.6),
              (10, 4.5, 'B6', C['warning'], 0.8),
              (11.5, 4.5, 'B7', C['warning'], 0.5),
              (12.5, 4.5, 'B8', C['warning'], 0.7)]
    for x, y, name, color, score in level3:
        alpha = 0.4 + score * 0.5
        circle = Circle((x, y), 0.4, facecolor=color,
                        edgecolor='white', linewidth=2, alpha=alpha, zorder=5)
        ax.add_patch(circle)
        ax.text(x, y, name, ha='center', va='center',
                fontsize=8, fontweight='bold', color='white', zorder=6)
        # 找最近的二级父节点连线
        parent_x = min(level2, key=lambda l: abs(l[0] - x))[0]
        ax.plot([parent_x, x], [6, 5], color=C['muted'],
                linewidth=0.8, alpha=0.3, zorder=1)

    # 标注：4 个操作
    ops = [
        ('① Expand\n扩展', 1, 2.5, C['primary']),
        ('② Simulate\n模拟', 4.5, 2.5, C['success']),
        ('③ Evaluate\n评估', 8, 2.5, C['warning']),
        ('④ Backprop\n回传', 11.5, 2.5, C['danger']),
    ]
    for name, x, y, color in ops:
        rect = FancyBboxPatch(
            (x - 1, y - 0.5), 2, 1,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor='white', linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y, name, ha='center', va='center',
                fontsize=10, fontweight='bold', color='white')

    # 底部说明
    ax.text(7, 0.5, 'MCTS/UCT 选下一步：探索 vs 利用的平衡',
            ha='center', fontsize=11, color=C['text'], style='italic')

    save(fig, 'lats-tree-search.png')


# ============================================================
# 07-stop-conditions
# ============================================================
def make_stop_conditions_flowchart():
    """停止条件决策图"""
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('Agent 停止条件：3 种判断 + 组合策略',
                 fontsize=15, fontweight='bold', pad=20)

    # 起点
    box(ax, 6.5, 8, 4, 0.8, C['dark'],
        '每步执行后检查', fontsize=12)

    # 3 种判断
    box(ax, 2.5, 6, 3, 1.2, C['success'],
        '目标达成？', ['final_answer 输出', '任务完成标志'], fontsize=11)
    box(ax, 6.5, 6, 3, 1.2, C['warning'],
        '步数超限？', ['已达 max_steps', '强制停止'], fontsize=11)
    box(ax, 10.5, 6, 3, 1.2, C['danger'],
        '超时/异常？', ['超时熔断', '错误累积过多'], fontsize=11)

    # 起点 → 3 个判断
    arrow(ax, 5.5, 7.6, 2.5, 6.6)
    arrow(ax, 6.5, 7.6, 6.5, 6.6)
    arrow(ax, 7.5, 7.6, 10.5, 6.6)

    # 3 个终止状态
    box(ax, 2.5, 3.5, 3, 1, C['success'],
        '[OK] 正常停止', fontsize=12)
    box(ax, 6.5, 3.5, 3, 1, C['warning'],
        '[!] 强制停止', fontsize=12)
    box(ax, 10.5, 3.5, 3, 1, C['danger'],
        '[X] 异常停止', fontsize=12)

    # 箭头
    arrow(ax, 2.5, 5.4, 2.5, 4)
    arrow(ax, 6.5, 5.4, 6.5, 4)
    arrow(ax, 10.5, 5.4, 10.5, 4)

    # 回到下一步
    box(ax, 6.5, 1.5, 4, 0.8, C['primary'],
        '未触发 → 继续下一轮', fontsize=12)
    arrow(ax, 6.5, 3, 6.5, 1.9)

    # 底部
    ax.text(6.5, 0.3, '实战：3 种条件 OR 组合，任一触发即停',
            ha='center', fontsize=11, color=C['text'], style='italic')

    save(fig, 'stop-conditions-flowchart.png')


def make_stop_state_machine():
    """Agent 状态机图"""
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('Agent 状态机：5 个状态 + 转移条件',
                 fontsize=15, fontweight='bold', pad=20)

    # 5 个状态
    states = [
        (2, 5, 'Idle\n待命', C['gray']),
        (4.5, 6.5, 'Thinking\n推理', C['primary']),
        (8.5, 6.5, 'Acting\n执行', C['success']),
        (8.5, 3, 'Observing\n观察', C['warning']),
        (11.5, 5, 'Done\n结束', C['dark']),
    ]
    for x, y, name, color in states:
        circle = Circle((x, y), 0.7, facecolor=color,
                        edgecolor='white', linewidth=2, zorder=5)
        ax.add_patch(circle)
        ax.text(x, y, name, ha='center', va='center',
                fontsize=10, fontweight='bold', color='white', zorder=6)

    # 转移
    arrow(ax, 2.7, 5.2, 3.8, 6.1, C['primary'], lw=2)
    ax.text(2.9, 6.0, '新任务', fontsize=9, color=C['primary'])

    arrow(ax, 5.2, 6.5, 7.8, 6.5, C['success'], lw=2)
    ax.text(6.5, 6.8, '行动', fontsize=9, color=C['success'])

    arrow(ax, 8.5, 5.8, 8.5, 3.7, C['warning'], lw=2)
    ax.text(8.8, 4.7, '结果', fontsize=9, color=C['warning'])

    arrow(ax, 7.8, 3, 5.2, 4.7, C['primary'], lw=2)
    ax.text(6.3, 3.6, '再思考', fontsize=9, color=C['primary'])

    arrow(ax, 11, 5, 9.2, 5.7, C['success'], lw=2)
    ax.text(9.5, 5.7, '完成', fontsize=9, color=C['success'])

    arrow(ax, 11, 5, 9.2, 3.7, C['danger'], lw=2)
    ax.text(9.5, 4.0, '异常', fontsize=9, color=C['danger'])

    # 底部
    ax.text(6.5, 1.5, '每步都在 4 个状态间转移，Done 终止循环',
            ha='center', fontsize=11, color=C['text'], style='italic')
    ax.text(6.5, 0.7, 'Done 又分 Success / Failure / MaxSteps / Timeout',
            ha='center', fontsize=10, color=C['muted'])

    save(fig, 'stop-state-machine.png')


# ============================================================
# 08-minimal-agent
# ============================================================
def make_minimal_agent_architecture():
    """最小 Agent 架构图"""
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('最小 Agent 架构：5 大组件 + 1 个循环',
                 fontsize=15, fontweight='bold', pad=20)

    # 中心循环
    circle = Circle((6.5, 4.5), 1.0, facecolor=C['primary'],
                    edgecolor='white', linewidth=3, zorder=10)
    ax.add_patch(circle)
    ax.text(6.5, 4.6, 'ReAct', ha='center', va='center',
            fontsize=14, fontweight='bold', color='white', zorder=11)
    ax.text(6.5, 4.2, '循环', ha='center', va='center',
            fontsize=11, color='white', zorder=11)

    # 5 个组件
    components = [
        (2, 7.5, 'LLM 调用', C['secondary'], 'call_llm()'),
        (11, 7.5, '工具定义', C['success'], 'TOOLS dict'),
        (2, 1.5, '工具执行', C['warning'], 'execute_tool()'),
        (11, 1.5, '停止条件', C['danger'], 'should_stop()'),
        (6.5, 0.5, 'Prompt 构造', C['pink'], 'react_loop()'),
    ]
    for x, y, name, color, impl in components:
        rect = FancyBboxPatch(
            (x - 1.4, y - 0.5), 2.8, 1,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor='white', linewidth=2, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.18, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        ax.text(x, y - 0.2, impl, ha='center', va='center',
                fontsize=10, color='white', family='monospace')

    # 连线
    for x, y, _, _, _ in components:
        ax.plot([6.5, x], [4.5, y], color=C['muted'],
                linewidth=1, alpha=0.4, zorder=0)

    # 顶部说明
    ax.text(6.5, 8.3, '~150 行代码 = 一个能跑的 Agent',
            ha='center', fontsize=12, color=C['text'],
            fontweight='bold')

    save(fig, 'minimal-agent-architecture.png')


def make_minimal_vs_production():
    """最小 Agent 到生产系统的差距"""
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('最小 Agent vs 生产 Agent：10 大工程差距',
                 fontsize=15, fontweight='bold', pad=20)

    # 左侧：最小 Agent
    box(ax, 3, 5, 5, 2.5, C['gray'],
        '最小 Agent',
        ['~150 行代码', '1 人维护', '能跑就行'], fontsize=13)

    # 右侧：生产 Agent
    box(ax, 11, 5, 5, 2.5, C['primary'],
        '生产 Agent',
        ['5,000-50,000 行', '3-10 人团队', '稳定 + 可观测 + 安全'], fontsize=13)

    # 中间箭头
    arrow(ax, 5.5, 5, 8.5, 5, C['dark'], lw=3)
    ax.text(7, 5.5, '×30', ha='center', fontsize=18,
            fontweight='bold', color=C['danger'])
    ax.text(7, 4.5, '工程量', ha='center', fontsize=11,
            color=C['muted'], style='italic')

    # 下方：10 大差距
    gaps = [
        '① 可观测性', '② 状态持久化', '③ 错误处理', '④ 流式输出',
        '⑤ 权限安全', '⑥ 成本控制', '⑦ 限流降级', '⑧ 测试评估',
        '⑨ 多租户隔离', '⑩ 工具沙箱',
    ]
    for i, gap in enumerate(gaps):
        col = i % 5
        row = i // 5
        x = 1.5 + col * 2.5
        y = 2.5 - row * 0.8
        rect = FancyBboxPatch(
            (x - 1.1, y - 0.3), 2.2, 0.6,
            boxstyle="round,pad=0.05",
            facecolor=C['warning'], edgecolor='white',
            linewidth=1.5, alpha=0.9,
        )
        ax.add_patch(rect)
        ax.text(x, y, gap, ha='center', va='center',
                fontsize=10, fontweight='bold', color='white')

    # 底部
    ax.text(7, 0.5, '最难的不是 Agent 循环本身，而是围绕它的 10 大工程基础设施',
            ha='center', fontsize=12, color=C['text'],
            fontweight='bold', style='italic')

    save(fig, 'minimal-vs-production.png')


# ============================================================
# 主入口
# ============================================================
if __name__ == '__main__':
    print('=== 01 Chatbot/Workflow/Agent ===')
    make_three_forms_comparison()
    make_decision_power_diagram()

    print('=== 02 核心循环 ===')
    make_core_loop_four_stages()
    make_agent_architecture()

    print('=== 03 模式全景 ===')
    make_patterns_landscape()
    make_pattern_relationships()
    make_selection_decision_tree()

    print('=== 04 ReAct ===')
    make_react_name_etymology()
    make_react_loop_detail()
    make_react_vs_cot()

    print('=== 05 Plan-and-Execute ===')
    make_plan_execute_flow()
    make_plan_execute_example()

    print('=== 06 Reflexion / ReWOO / LATS ===')
    make_reflexion_loop()
    make_rewoo_flow()
    make_lats_tree_search()

    print('=== 07 停止条件 ===')
    make_stop_conditions_flowchart()
    make_stop_state_machine()

    print('=== 08 最小 Agent ===')
    make_minimal_agent_architecture()
    make_minimal_vs_production()

    print(f'\n完成。共生成 20 张图，目录：{OUT_DIR}')
