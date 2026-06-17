# -*- coding: utf-8 -*-
"""生成 04-model-variants-landscape 的配图：变体全景图（6 大维度）"""
import os
import sys
import math
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

# 让脚本能找到 skill
sys.path.insert(0, r'e:\Projects\multi-agent-manager\skills\matplotlib-figures')
from matplotlib_figures.theme import COLORS, set_theme, save_fig

set_theme(font_size=12)

OUT_DIR = r"e:\Learning\AgentDevGuide\assets\02-model-access"
os.makedirs(OUT_DIR, exist_ok=True)


# ============= 1. 变体全景图（6 个维度） =============
def make_variants_landscape():
    fig, ax = plt.subplots(figsize=(13, 12))
    ax.set_xlim(-7.5, 7.5)
    ax.set_ylim(-7.5, 7.5)
    ax.axis('off')
    ax.set_title('模型变体全景：6 大维度',
                 fontsize=18, fontweight='bold', pad=20)

    # 中心
    center = Circle((0, 0), 1.2, facecolor=COLORS['primary'],
                    edgecolor='white', linewidth=3, zorder=10)
    ax.add_patch(center)
    ax.text(0, 0.2, 'LLM', ha='center', va='center',
            fontsize=22, fontweight='bold', color='white', zorder=11)
    ax.text(0, -0.4, '模型变体', ha='center', va='center',
            fontsize=14, color='white', zorder=11)

    # 6 个变体维度（环形布局，每个 60 度）
    dimensions = [
        {
            'name': '训练阶段',
            'angle': 90,           # 顶部
            'color': COLORS['primary'],
            'subtitle': '从续写到听话',
            'examples': 'Base / Instruct / Chat',
            'tag': '',
        },
        {
            'name': '能力专精',
            'angle': 90 - 60,      # 右上
            'color': COLORS['secondary'],
            'subtitle': '把某项能力做到极致',
            'examples': 'Code / Math / Vision\nFunction Calling',
            'tag': '',
        },
        {
            'name': '部署形态',
            'angle': 90 - 120,     # 右下
            'color': COLORS['warning'],
            'subtitle': '适配不同硬件资源',
            'examples': '量化 / 合并 / 剪枝',
            'tag': '',
        },
        {
            'name': '蒸馏',
            'angle': 90 - 180,     # 底部
            'color': '#ec4899',    # 粉
            'subtitle': '小模型继承大模型',
            'examples': 'DeepSeek-Distill\nPhi / SmolLM',
            'tag': '',
        },
        {
            'name': '专用家族',
            'angle': 90 - 240,     # 左下
            'color': COLORS['success'],
            'subtitle': '不同任务不同范式',
            'examples': 'Embedding / Rerank\nSTT / TTS',
            'tag': '',
        },
        {
            'name': '行业场景',
            'angle': 90 - 300,     # 左上
            'color': COLORS['danger'],
            'subtitle': '领域知识 + 合规',
            'examples': '金融 / 医疗 / 法律\n区域语言',
            'tag': '',
        },
    ]

    for d in dimensions:
        rad = math.radians(d['angle'])
        cx = 4.5 * math.cos(rad)
        cy = 4.5 * math.sin(rad)

        # 连线
        ax.plot([0, cx * 0.82], [0, cy * 0.82],
                color=d['color'], linewidth=2.5,
                alpha=0.7, zorder=1)
        # 端点小圆
        ax.plot(cx * 0.82, cy * 0.82, 'o', color=d['color'],
                markersize=10, markeredgecolor='white',
                markeredgewidth=2, zorder=2)

        # 节点圆角矩形
        box_w, box_h = 2.6, 1.6
        box = FancyBboxPatch(
            (cx - box_w/2, cy - box_h/2), box_w, box_h,
            boxstyle="round,pad=0.05",
            facecolor='white', edgecolor=d['color'],
            linewidth=2.5, zorder=3,
        )
        ax.add_patch(box)

        # 文字
        ax.text(cx, cy + 0.4, d['name'],
                ha='center', va='center',
                fontsize=14, fontweight='bold',
                color=d['color'], zorder=4)
        ax.text(cx, cy - 0.05, d['subtitle'],
                ha='center', va='center',
                fontsize=9, color=COLORS['text'],
                style='italic', zorder=4)
        ax.text(cx, cy - 0.45, d['examples'],
                ha='center', va='center',
                fontsize=9, color=COLORS['muted'], zorder=4)

        # 标记
        if d['tag']:
            ax.text(cx, cy - box_h/2 - 0.25, f"（{d['tag']}）",
                    ha='center', va='center',
                    fontsize=9, color=COLORS['gray'],
                    style='italic', zorder=4)

    # 底部说明
    note = ("变体不是营销概念，是 LLM 生态分工协作的必然产物：\n"
            "通用模型负责'什么都能做'，变体负责'把某件事做到极致'")
    ax.text(0, -6.8, note, ha='center', va='center',
            fontsize=11, color=COLORS['muted'],
            bbox=dict(boxstyle="round,pad=0.5",
                      facecolor='#f3f4f6', edgecolor='none'))

    save_fig(fig, os.path.join(OUT_DIR, 'variants-landscape.png'))


if __name__ == '__main__':
    make_variants_landscape()
    print("\n完成")
