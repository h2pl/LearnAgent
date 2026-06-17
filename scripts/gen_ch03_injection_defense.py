# -*- coding: utf-8 -*-
"""生成 03-05 Prompt 注入防御体系配图。

原图 prompt-injection-defense.png 尺寸仅 179x170 像素、白色 0.2%，
主色 RGB(16-32, 16-32, 48-64) 几乎全深蓝紫，肉眼几乎看不清。

本脚本重画一张清晰 4 层防御体系图：
  输入校验 → 上下文隔离 → 意图验证 → 输出过滤
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
from matplotlib import font_manager

# 中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 12

OUT_PATH = r"e:\Learning\AgentDevGuide\assets\03-prompt-engineering\prompt-injection-defense.png"

# 配色（按防御强度递增：浅黄→红）
COLORS = {
    'layer1': '#FCD34D',   # 浅黄 - 输入校验（前置，最弱）
    'layer2': '#F59E0B',   # 橙 - 上下文隔离
    'layer3': '#EA580C',   # 深橙 - 意图验证
    'layer4': '#DC2626',   # 红 - 输出过滤（最后兜底，最关键）
    'attack': '#7C3AED',   # 紫 - 攻击
    'bg': '#F8FAFC',
    'text': '#1E293B',
    'muted': '#64748B',
    'safe': '#10B981',
}


def make_injection_defense():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    # 标题
    ax.text(7, 7.5, 'Prompt 注入防御体系：4 层纵深防御',
            ha='center', va='center',
            fontsize=17, fontweight='bold', color=COLORS['text'])

    # 左侧：攻击源
    attack_box = FancyBboxPatch(
        (0.3, 3), 2.0, 2,
        boxstyle="round,pad=0.1",
        facecolor=COLORS['attack'], edgecolor='white',
        linewidth=2, alpha=0.9
    )
    ax.add_patch(attack_box)
    ax.text(1.3, 4.3, '攻击源',
            ha='center', va='center',
            fontsize=14, fontweight='bold', color='white')
    ax.text(1.3, 3.8, '恶意 / 注入 / 越狱',
            ha='center', va='center', fontsize=10, color='white')
    ax.text(1.3, 3.4, '用户输入 / 工具返回',
            ha='center', va='center', fontsize=10, color='#FCE7F3')

    # 右侧：安全 LLM
    llm_box = FancyBboxPatch(
        (11.5, 3), 2.2, 2,
        boxstyle="round,pad=0.1",
        facecolor=COLORS['safe'], edgecolor='white',
        linewidth=2, alpha=0.9
    )
    ax.add_patch(llm_box)
    ax.text(12.6, 4.3, '安全 LLM',
            ha='center', va='center',
            fontsize=14, fontweight='bold', color='white')
    ax.text(12.6, 3.8, '最终回复',
            ha='center', va='center', fontsize=10, color='white')
    ax.text(12.6, 3.4, '（已通过 4 层防御）',
            ha='center', va='center', fontsize=9, color='#D1FAE5')

    # 中间：4 层防御
    layers = [
        # (y, color, num, title, desc1, desc2)
        (5.7, COLORS['layer1'], '①', '输入校验',
         '轻量规则拦截', '空 / 过长 / 已知 jailbreak 模式'),
        (4.5, COLORS['layer2'], '②', '上下文隔离',
         '分隔 System / User / Tool', '防止数据源污染 System'),
        (3.3, COLORS['layer3'], '③', '意图验证',
         'LLM 二次判断输入意图', '"这个输入是不是注入？"'),
        (2.1, COLORS['layer4'], '④', '输出过滤',
         '最终兜底，过滤响应', '检查是否泄露 / 越权'),
    ]

    for y, color, num, title, d1, d2 in layers:
        # 防御层（圆角矩形）
        box = FancyBboxPatch(
            (3.3, y - 0.55), 7.5, 1.1,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor='white',
            linewidth=2, alpha=0.9
        )
        ax.add_patch(box)
        # 数字 + 标题
        ax.text(3.7, y, f'{num} {title}',
                ha='left', va='center',
                fontsize=14, fontweight='bold', color='white')
        # 描述
        ax.text(6.0, y + 0.2, d1,
                ha='left', va='center', fontsize=11, color='white',
                fontweight='bold')
        ax.text(6.0, y - 0.2, d2,
                ha='left', va='center', fontsize=10, color='white')

    # 攻击源 → 第一层
    ax.annotate('', xy=(3.3, 5.7), xytext=(2.3, 4.5),
                arrowprops=dict(arrowstyle='->', color=COLORS['attack'], lw=2.5))

    # 各层之间：纵深穿透（紫色虚线）
    for y in [4.5, 3.3, 2.1]:
        ax.annotate('', xy=(3.3, y - 0.3), xytext=(3.3, y - 0.85),
                    arrowprops=dict(arrowstyle='->', color=COLORS['attack'],
                                    lw=1.5, linestyle='dashed', alpha=0.5))

    # 第四层 → 安全 LLM
    ax.annotate('', xy=(11.5, 3.5), xytext=(10.8, 2.1),
                arrowprops=dict(arrowstyle='->', color=COLORS['safe'], lw=2.5))
    ax.text(11.0, 2.7, '通过', ha='center', fontsize=10,
            color=COLORS['safe'], fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white',
                      edgecolor=COLORS['safe'], linewidth=1.2))

    # 拒绝分支：从第一层斜向下
    ax.annotate('', xy=(7.0, 1.0), xytext=(5.0, 5.2),
                arrowprops=dict(arrowstyle='->', color='#94A3B8', lw=2,
                                connectionstyle="arc3,rad=-0.3"))
    reject_box = FancyBboxPatch(
        (5.5, 0.5), 3, 0.9,
        boxstyle="round,pad=0.05",
        facecolor='#1E293B', edgecolor='white', linewidth=2
    )
    ax.add_patch(reject_box)
    ax.text(7.0, 1.05, '任意一层失败 → 拒绝',
            ha='center', va='center', fontsize=11,
            fontweight='bold', color='white')
    ax.text(7.0, 0.75, '"I can\'t help with that."',
            ha='center', va='center', fontsize=9, color='#CBD5E1',
            style='italic')

    # 底部说明
    note = ('纵深防御（Defense in Depth）原则：单层防御不可靠，'
            '多层叠加才能应对 0-day 攻击。\n'
            '前置拦截（轻量、便宜） + 后置过滤（重量、准确）= 成本与安全的平衡。')
    ax.text(7, 7.0, note, ha='center', va='center',
            fontsize=10, color=COLORS['muted'], style='italic',
            bbox=dict(boxstyle="round,pad=0.4", facecolor=COLORS['bg'],
                      edgecolor='none'))

    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"[OK] {OUT_PATH}")


if __name__ == '__main__':
    make_injection_defense()
