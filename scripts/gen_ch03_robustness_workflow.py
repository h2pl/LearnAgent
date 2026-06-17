# -*- coding: utf-8 -*-
"""生成 03-05 鲁棒性测试流程配图。

原图 prompt-engineering-workflow.png 内容稀疏（80% 白底+淡蓝紫内容），
且与 05-prompt-robustness.md 文字描述"异常输入 → 校验拦截 → 拒绝响应"不匹配。
本脚本重画一张清晰的 4 阶段流程图。
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

# 中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 12

OUT_PATH = r"e:\Learning\AgentDevGuide\assets\03-prompt-engineering\prompt-engineering-workflow.png"

# 配色（与 04 章 variants-landscape 一致）
COLOR_USER = '#3B82F6'      # 蓝 - 用户输入
COLOR_VALIDATE = '#F59E0B'  # 橙 - 校验拦截
COLOR_REJECT = '#EF4444'    # 红 - 拒绝响应
COLOR_LLM = '#10B981'       # 绿 - 正常通过 → LLM
COLOR_BG = '#F8FAFC'
COLOR_TEXT = '#1E293B'
COLOR_MUTED = '#64748B'


def make_robustness_workflow():
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # 标题
    ax.text(7, 5.5, '鲁棒性测试流程：异常输入的 4 阶段处理',
            ha='center', va='center',
            fontsize=16, fontweight='bold', color=COLOR_TEXT)

    # 4 个节点（菱形=判断，圆角矩形=动作）
    # 阶段 1: 用户输入（圆角矩形）
    nodes = [
        # (x, y, w, h, color, title, lines, shape)
        (1.2, 2.5, 2.4, 1.2, COLOR_USER, '① 用户输入',
         ['任意 Prompt', '（含正常/异常/恶意）'], 'rect'),
        (4.7, 2.5, 2.4, 1.2, COLOR_VALIDATE, '② 输入校验',
         ['空 / 过长 /', 'jailbreak 模式'], 'rect'),
        # 校验失败 → 拒绝
        (8.2, 4.2, 2.4, 1.2, COLOR_REJECT, '③ 拒绝响应',
         ['标准化模板', '（拒绝 + 引导）'], 'rect'),
        # 校验通过 → LLM
        (8.2, 1.0, 2.4, 1.2, COLOR_LLM, '④ 继续处理',
         ['送入 LLM', '（按 System Prompt）'], 'rect'),
        (11.7, 2.5, 2.0, 1.2, COLOR_TEXT, '⑤ 最终输出',
         ['安全回复 /', '拒绝回复'], 'rect'),
    ]

    for x, y, w, h, color, title, lines, shape in nodes:
        box = FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.95,
        )
        ax.add_patch(box)
        ax.text(x, y + 0.35, title,
                ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        for i, line in enumerate(lines):
            ax.text(x, y - 0.05 - i * 0.28, line,
                    ha='center', va='center',
                    fontsize=10, color='white')

    # 箭头
    # ① → ②
    ax.annotate('', xy=(3.5, 2.85), xytext=(2.4, 2.85),
                arrowprops=dict(arrowstyle='->', color=COLOR_TEXT, lw=2))
    # ② → ③（拒绝分支，向上）
    ax.annotate('', xy=(7.0, 4.5), xytext=(5.9, 3.0),
                arrowprops=dict(arrowstyle='->', color=COLOR_REJECT, lw=2))
    ax.text(5.9, 3.7, '校验失败', ha='center', fontsize=10,
            color=COLOR_REJECT, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white',
                      edgecolor=COLOR_REJECT, linewidth=1.2))
    # ② → ④（通过分支，向下）
    ax.annotate('', xy=(7.0, 1.5), xytext=(5.9, 2.3),
                arrowprops=dict(arrowstyle='->', color=COLOR_LLM, lw=2))
    ax.text(5.9, 1.7, '校验通过', ha='center', fontsize=10,
            color=COLOR_LLM, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white',
                      edgecolor=COLOR_LLM, linewidth=1.2))
    # ③ → ⑤
    ax.annotate('', xy=(10.7, 3.4), xytext=(9.4, 4.0),
                arrowprops=dict(arrowstyle='->', color=COLOR_TEXT, lw=2))
    # ④ → ⑤
    ax.annotate('', xy=(10.7, 2.0), xytext=(9.4, 1.3),
                arrowprops=dict(arrowstyle='->', color=COLOR_TEXT, lw=2))

    # 底部说明
    note = ('核心思想：先"前置拦截"（轻量规则）再"后置验证"（LLM + System Prompt）。\n'
            '前置拦截负责成本/速度，后置验证负责准确性 —— 两者结合才是完整的鲁棒性体系。')
    ax.text(7, 0.25, note, ha='center', va='center',
            fontsize=10, color=COLOR_MUTED, style='italic',
            bbox=dict(boxstyle="round,pad=0.4", facecolor=COLOR_BG,
                      edgecolor='none'))

    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[OK] {OUT_PATH}")


if __name__ == '__main__':
    make_robustness_workflow()
