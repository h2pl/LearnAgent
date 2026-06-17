# -*- coding: utf-8 -*-
"""生成 03-06 Prompt 调试与评估配图。

两张图：
1. prompt-iteration-loop.png — 5 步迭代闭环
2. llm-as-judge-pipeline.png — LLM-as-Judge 评估流水线
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# 中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 12

OUT_DIR = r"e:\Learning\AgentDevGuide\assets\03-prompt-engineering"

# 配色（与 03-05 鲁棒性流程图保持一致）
COLOR_BG = '#F8FAFC'
COLOR_TEXT = '#1E293B'
COLOR_MUTED = '#64748B'
COLOR_HYPOTHESIS = '#8B5CF6'  # 紫 - 假设
COLOR_CHANGE = '#F59E0B'      # 橙 - 改动
COLOR_EVAL = '#3B82F6'        # 蓝 - 评估
COLOR_COMPARE = '#10B981'     # 绿 - 对比
COLOR_DECIDE = '#EF4444'      # 红 - 决策
COLOR_DATASET = '#3B82F6'     # 蓝 - 数据集
COLOR_OUTPUT = '#F59E0B'      # 橙 - 输出
COLOR_PROMPT = '#8B5CF6'      # 紫 - 评分 Prompt
COLOR_JUDGE = '#10B981'       # 绿 - 评估模型
COLOR_METRIC = '#DC2626'      # 红 - 指标


def make_iteration_loop():
    """Prompt 迭代闭环：假设 → 改动 → 评估 → 对比 → 决策"""
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # 标题
    ax.text(7.5, 6.5, 'Prompt 迭代闭环：数据驱动的 5 步工程流程',
            ha='center', va='center',
            fontsize=17, fontweight='bold', color=COLOR_TEXT)

    # 5 个步骤节点（横向排列 + 决策节点分支）
    steps = [
        # (x, y, w, h, color, num, title, sub)
        (1.5, 3.5, 2.4, 1.4, COLOR_HYPOTHESIS, '①', '假设', '基于失败案例\n提出改进方向'),
        (4.6, 3.5, 2.4, 1.4, COLOR_CHANGE, '②', '改动', '在 Prompt 中\n实施具体修改'),
        (7.7, 3.5, 2.4, 1.4, COLOR_EVAL, '③', '评估', '跑黄金用例集\n看整体指标变化'),
        (10.8, 3.5, 2.4, 1.4, COLOR_COMPARE, '④', '对比', '跑回归测试集\n确保不退步'),
    ]
    for x, y, w, h, color, num, title, sub in steps:
        box = FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.95,
        )
        ax.add_patch(box)
        ax.text(x, y + 0.4, num, ha='center', va='center',
                fontsize=14, color='white', fontweight='bold', alpha=0.7)
        ax.text(x, y + 0.05, title, ha='center', va='center',
                fontsize=14, fontweight='bold', color='white')
        ax.text(x, y - 0.4, sub, ha='center', va='center',
                fontsize=10, color='white')

    # 决策节点：菱形（通过 / 失败）
    decision_x, decision_y = 13.7, 3.5
    diamond = plt.Polygon(
        [(decision_x, decision_y + 0.7), (decision_x + 0.7, decision_y),
         (decision_x, decision_y - 0.7), (decision_x - 0.7, decision_y)],
        facecolor=COLOR_DECIDE, edgecolor='white', linewidth=2, alpha=0.95,
    )
    ax.add_patch(diamond)
    ax.text(decision_x, decision_y + 0.15, '⑤', ha='center', va='center',
            fontsize=11, color='white', fontweight='bold', alpha=0.7)
    ax.text(decision_x, decision_y - 0.15, '决策', ha='center', va='center',
            fontsize=11, fontweight='bold', color='white')

    # 主箭头：① → ② → ③ → ④ → ⑤
    for x_start, x_end in [(2.7, 3.4), (5.8, 6.5), (8.9, 9.6), (12.0, 13.0)]:
        ax.annotate('', xy=(x_end, 3.5), xytext=(x_start, 3.5),
                    arrowprops=dict(arrowstyle='->', color=COLOR_TEXT, lw=2.5))

    # 决策分支：失败 → 回退到 ①（虚线）
    # 从 ⑤ 向上
    ax.annotate('', xy=(14.0, 5.5), xytext=(14.4, 4.0),
                arrowprops=dict(arrowstyle='->', color=COLOR_DECIDE, lw=2, linestyle='--'))
    # 横线向左
    ax.annotate('', xy=(1.5, 5.5), xytext=(14.0, 5.5),
                arrowprops=dict(arrowstyle='-', color=COLOR_DECIDE, lw=2, linestyle='--'))
    # 向下回到 ①
    ax.annotate('', xy=(1.5, 4.2), xytext=(1.5, 5.5),
                arrowprops=dict(arrowstyle='->', color=COLOR_DECIDE, lw=2, linestyle='--'))

    # 失败标签
    ax.text(7.5, 5.8, '失败：未通过评估，回滚 Prompt，回到 ① 重新假设',
            ha='center', va='center',
            fontsize=11, color=COLOR_DECIDE, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white',
                      edgecolor=COLOR_DECIDE, linewidth=1.5))

    # 通过 → 上线
    ax.annotate('', xy=(14.0, 1.3), xytext=(14.0, 2.8),
                arrowprops=dict(arrowstyle='->', color=COLOR_COMPARE, lw=2.5))
    ax.text(14.0, 1.7, '通过', ha='center', va='center',
            fontsize=11, color=COLOR_COMPARE, fontweight='bold')
    ax.text(14.0, 0.9, '上线发布', ha='center', va='center',
            fontsize=12, color='white', fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLOR_COMPARE,
                      edgecolor='white', linewidth=1.5))

    # 底部：工程纪律
    ax.text(7.5, 0.4,
            '工程纪律：一次只改一个变量 · 改动必须有数据支撑 · 失败案例归档 · Prompt 版本化管理',
            ha='center', va='center',
            fontsize=11, color=COLOR_MUTED,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLOR_BG,
                      edgecolor=COLOR_MUTED, linewidth=1))

    out = os.path.join(OUT_DIR, 'prompt-iteration-loop.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Generated: {out}')


def make_llm_as_judge_pipeline():
    """LLM-as-Judge 评估流水线：黄金用例集 → 被评估模型 → 实际输出 → 评分 Prompt → 评估模型 → 指标"""
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # 标题
    ax.text(7.5, 6.5, 'LLM-as-Judge 评估流水线：用强模型评估弱模型',
            ha='center', va='center',
            fontsize=17, fontweight='bold', color=COLOR_TEXT)

    # 5 个流水线节点（横向）
    nodes = [
        # (x, y, w, h, color, num, title, sub)
        (1.5, 3.5, 2.2, 1.5, COLOR_DATASET, '①', '黄金用例集',
         ['{"input": "...",', '"expected": "..."}']),
        (4.4, 3.5, 2.2, 1.5, COLOR_PROMPT, '②', '被评估模型',
         ['业务 Prompt', '+ 实际调用']),
        (7.3, 3.5, 2.2, 1.5, COLOR_OUTPUT, '③', '实际输出',
         ['{"intent": "...",', '"confidence": 0.9}']),
        (10.2, 3.5, 2.2, 1.5, COLOR_PROMPT, '④', '评估模型',
         ['JUDGE_PROMPT', '+ 评分维度']),
        (13.1, 3.5, 2.0, 1.5, COLOR_METRIC, '⑤', '指标',
         ['各维度分数', '+ 综合分']),
    ]
    for x, y, w, h, color, num, title, sub in nodes:
        box = FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.95,
        )
        ax.add_patch(box)
        ax.text(x, y + 0.55, num, ha='center', va='center',
                fontsize=13, color='white', fontweight='bold', alpha=0.7)
        ax.text(x, y + 0.2, title, ha='center', va='center',
                fontsize=13, fontweight='bold', color='white')
        for i, line in enumerate(sub):
            ax.text(x, y - 0.15 - i * 0.25, line,
                    ha='center', va='center',
                    fontsize=9, color='white')

    # 横向箭头
    for x_start, x_end in [(2.6, 3.3), (5.5, 6.2), (8.4, 9.1), (11.3, 12.1)]:
        ax.annotate('', xy=(x_end, 3.5), xytext=(x_start, 3.5),
                    arrowprops=dict(arrowstyle='->', color=COLOR_TEXT, lw=2.5))

    # 输入流（黄金用例集同时传给被评估模型和评估模型）
    # 从 ① 向上引出，到顶部，再分叉
    ax.annotate('', xy=(1.5, 5.3), xytext=(1.5, 4.25),
                arrowprops=dict(arrowstyle='-', color=COLOR_DATASET, lw=1.5))
    ax.annotate('', xy=(4.4, 5.3), xytext=(1.5, 5.3),
                arrowprops=dict(arrowstyle='-', color=COLOR_DATASET, lw=1.5))
    ax.annotate('', xy=(4.4, 4.25), xytext=(4.4, 5.3),
                arrowprops=dict(arrowstyle='->', color=COLOR_DATASET, lw=1.5))

    # 实际输出也传给评估模型
    ax.annotate('', xy=(10.2, 4.3), xytext=(7.3, 4.3),
                arrowprops=dict(arrowstyle='-', color=COLOR_OUTPUT, lw=1.5))

    # 顶部标签
    ax.text(2.95, 5.55, '输入（黄金用例）',
            ha='center', va='center',
            fontsize=10, color=COLOR_DATASET, fontweight='bold')
    ax.text(8.75, 4.55, '实际输出',
            ha='center', va='center',
            fontsize=10, color=COLOR_OUTPUT, fontweight='bold')

    # 底部：评估维度
    dimensions = [
        ('准确性', '5=无幻觉'),
        ('格式合规', '5=完全符合 Schema'),
        ('指令遵循', '5=完全遵循约束'),
        ('简洁性', '5=精炼无冗余'),
    ]
    for i, (dim, desc) in enumerate(dimensions):
        x = 1.5 + i * 3.7
        ax.text(x, 1.5, dim,
                ha='center', va='center',
                fontsize=11, color='white', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=COLOR_PROMPT,
                          edgecolor='white', linewidth=1.2))
        ax.text(x, 1.0, desc,
                ha='center', va='center',
                fontsize=9, color=COLOR_MUTED)

    ax.text(7.5, 0.3,
            '核心原则：原子化维度 · 强制 JSON 输出 · 锁定评分 Prompt 版本 · 注意位置/长度/自我偏好偏差',
            ha='center', va='center',
            fontsize=10, color=COLOR_MUTED,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLOR_BG,
                      edgecolor=COLOR_MUTED, linewidth=1))

    out = os.path.join(OUT_DIR, 'llm-as-judge-pipeline.png')
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Generated: {out}')


if __name__ == '__main__':
    make_iteration_loop()
    make_llm_as_judge_pipeline()
    print('Done.')
