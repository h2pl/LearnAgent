# -*- coding: utf-8 -*-
"""生成第二章所有配图"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib import font_manager

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11

OUT_DIR = r"e:\Learning\AgentDevGuide\assets\02-model-access"
os.makedirs(OUT_DIR, exist_ok=True)

# 通用配色
COLORS = {
    'primary': '#2563eb',   # 蓝
    'secondary': '#7c3aed', # 紫
    'success': '#10b981',   # 绿
    'warning': '#f59e0b',   # 橙
    'danger': '#ef4444',    # 红
    'gray': '#6b7280',
    'light': '#e5e7eb',
    'dark': '#1f2937',
}


def save(fig, name, dpi=150):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"[OK] {name}")


# ========== 1. api-call-flow.png (重做) ==========
def make_api_call_flow():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title('LLM API 调用时序：从用户提问到收到回复',
                 fontsize=15, fontweight='bold', pad=15)

    # 四个角色
    actors = [
        (1.5, '用户', '#dbeafe'),
        (4.5, '客户端代码', '#fef3c7'),
        (7.5, 'API 网关', '#dcfce7'),
        (10.5, '推理引擎', '#fce7f3'),
    ]
    for x, name, color in actors:
        rect = FancyBboxPatch((x - 1, 5.2), 2, 0.6,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='#374151', linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x, 5.5, name, ha='center', va='center', fontsize=12, fontweight='bold')

    # Lifeline
    for x, _, _ in actors:
        ax.plot([x, x], [5.1, 0.4], 'k--', linewidth=0.8, alpha=0.5)

    # 步骤
    steps = [
        (1.5, 4.6, '1. 输入 Prompt', 'right'),
        (4.5, 4.2, '2. 构造请求体\n{model, messages}', 'right'),
        (7.5, 3.8, '3. 鉴权 + 路由', 'right'),
        (10.5, 3.4, '4. Tokenize\n+ 推理', 'right'),
        (10.5, 2.6, '5. 生成 Token', 'right'),
        (7.5, 2.2, '6. 拼装 SSE\n返回', 'right'),
        (4.5, 1.8, '7. 解析 JSON\n渲染回答', 'right'),
        (1.5, 1.4, '8. 看到回答', 'right'),
    ]
    # 箭头（更简化版）
    # 用户 → 客户端
    ax.annotate('', xy=(3.5, 4.6), xytext=(2.5, 4.6),
                arrowprops=dict(arrowstyle='->', color='#374151', lw=1.2))
    ax.text(3.0, 4.75, '输入 Prompt', ha='center', fontsize=9, color='#374151')

    # 客户端 → API网关
    ax.annotate('', xy=(6.5, 4.2), xytext=(5.5, 4.2),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=1.5))
    ax.text(6.0, 4.35, 'POST /v1/chat/completions', ha='center', fontsize=9, color=COLORS['primary'])

    # API网关 → 推理引擎
    ax.annotate('', xy=(9.5, 3.4), xytext=(8.5, 3.4),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=1.5))
    ax.text(9.0, 3.55, '内部调用', ha='center', fontsize=9)

    # 推理引擎 → API网关
    ax.annotate('', xy=(8.5, 2.6), xytext=(9.5, 2.6),
                arrowprops=dict(arrowstyle='->', color=COLORS['success'], lw=1.5))
    ax.text(9.0, 2.75, 'Token 流', ha='center', fontsize=9, color=COLORS['success'])

    # API网关 → 客户端
    ax.annotate('', xy=(5.5, 1.8), xytext=(6.5, 1.8),
                arrowprops=dict(arrowstyle='->', color=COLORS['success'], lw=1.5))
    ax.text(6.0, 1.95, '200 OK + JSON', ha='center', fontsize=9, color=COLORS['success'])

    # 客户端 → 用户
    ax.annotate('', xy=(2.5, 1.4), xytext=(3.5, 1.4),
                arrowprops=dict(arrowstyle='->', color='#374151', lw=1.2))
    ax.text(3.0, 1.55, '渲染输出', ha='center', fontsize=9)

    # 底部说明
    note = "关键点：客户端代码不需要关心后端实现；鉴权、限流、负载均衡都在 API 网关层；\n推理引擎内部还要做 KV 缓存管理、批处理、采样策略等。"
    ax.text(6, 0.5, note, ha='center', va='center', fontsize=10,
            style='italic', color='#4b5563',
            bbox=dict(boxstyle="round,pad=0.4", facecolor='#f3f4f6', edgecolor='none'))

    save(fig, 'api-call-flow.png')


# ========== 2. model-selection-decision.png (重做) ==========
def make_model_selection_decision():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('模型选型决策流程：原型 → 开发 → 生产',
                 fontsize=15, fontweight='bold', pad=15)

    # 三个阶段
    stages = [
        (1.5, 6, '① 原型验证期', '#dbeafe', '#1e40af'),
        (1.5, 4, '② 开发优化期', '#fef3c7', '#92400e'),
        (1.5, 2, '③ 生产部署期', '#dcfce7', '#166534'),
    ]
    for x, y, name, fc, ec in stages:
        rect = FancyBboxPatch((0.3, y - 0.3), 2.4, 0.7,
                              boxstyle="round,pad=0.05",
                              facecolor=fc, edgecolor=ec, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, y, name, ha='center', va='center', fontsize=12, fontweight='bold', color=ec)

    # 决策节点和选项
    # 原型期
    items = [
        # 原型期
        (4, 6, '选最强模型', 'Claude Opus 4.8 / GPT-5.5', '#1e40af'),
        (8, 6, '目标', '验证业务逻辑\n能否跑通', '#1e40af'),
        (4, 4, '降级测试', 'Qwen 3.7 / DeepSeek V4', '#92400e'),
        (8, 4, '对比', '效果下降多少？\n可优化空间？', '#92400e'),
        (4, 2, '多模型混用', '规划用强模型\n执行用便宜模型', '#166534'),
        (8, 2, '成本/隐私/速度', '分类路由\n按场景选型', '#166534'),
    ]
    for x, y, head, sub, color in items:
        rect = FancyBboxPatch((x - 1.4, y - 0.6), 2.8, 1.3,
                              boxstyle="round,pad=0.05",
                              facecolor='white', edgecolor=color, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x, y + 0.35, head, ha='center', va='center', fontsize=10, fontweight='bold', color=color)
        ax.text(x, y - 0.2, sub, ha='center', va='center', fontsize=9, color='#374151')

    # 连接箭头
    for y_from, y_to in [(5.7, 4.7), (3.7, 2.7)]:
        ax.annotate('', xy=(2.7, y_to), xytext=(2.7, y_from),
                    arrowprops=dict(arrowstyle='->', color='#6b7280', lw=1.5))

    # 底部核心原则
    principle = "核心原则：选型是工程决策，不是技术信仰。\n同一个 Agent 系统里同时用多个模型是常态，不是例外。"
    ax.text(6, 0.6, principle, ha='center', va='center', fontsize=11,
            fontweight='bold', color='#1f2937',
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#f3f4f6', edgecolor='#9ca3af', linewidth=1))

    save(fig, 'model-selection-decision.png')


# ========== 3. temperature-distribution.png (重做) ==========
def make_temperature_distribution():
    fig, axes = plt.subplots(1, 4, figsize=(14, 4), sharey=True)
    fig.suptitle('Temperature 参数对概率分布的影响',
                 fontsize=15, fontweight='bold', y=1.02)

    # 模拟一些 token 概率
    tokens = [f't{i}' for i in range(20)]
    # 初始分布（不平滑，越靠前概率越大）
    base_probs = np.array([0.30, 0.18, 0.12, 0.08, 0.06, 0.05, 0.04, 0.03,
                           0.025, 0.02, 0.018, 0.015, 0.012, 0.010, 0.008,
                           0.007, 0.006, 0.005, 0.004, 0.003])
    base_probs = base_probs / base_probs.sum()

    temperatures = [0.2, 0.7, 1.0, 1.5]
    subtitles = ['低温 T=0.2 (保守)',
                 '中温 T=0.7 (平衡)',
                 'T=1.0 (原始分布)',
                 '高温 T=1.5 (发散)']
    colors_list = [COLORS['primary'], COLORS['success'],
                   COLORS['warning'], COLORS['danger']]

    for ax, T, sub, color in zip(axes, temperatures, subtitles, colors_list):
        # 温度调整
        logits = np.log(base_probs + 1e-10)
        scaled = logits / T
        scaled = scaled - scaled.max()
        probs = np.exp(scaled)
        probs = probs / probs.sum()

        bars = ax.bar(range(len(tokens)), probs, color=color, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.set_title(sub, fontsize=11, fontweight='bold', color=color)
        ax.set_xticks([])
        ax.set_xlabel('Token 候选')
        ax.set_ylim(0, 0.55)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

    axes[0].set_ylabel('概率')
    fig.text(0.5, -0.02,
             'T 越小 → 越倾向选概率最高的 token (稳定但可能重复);   T 越大 → 分布越平 (多样但可能跑偏)',
             ha='center', fontsize=10, style='italic', color='#4b5563')

    save(fig, 'temperature-distribution.png')


# ========== 4. top-p-sampling.png (重做) ==========
def make_top_p_sampling():
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Top-p (Nucleus) 核采样原理',
                 fontsize=15, fontweight='bold', y=1.02)

    # 左图：按概率排序的柱状图
    ax1 = axes[0]
    tokens = [f't{i+1}' for i in range(15)]
    probs = [0.40, 0.25, 0.15, 0.08, 0.05, 0.03, 0.015, 0.008, 0.005, 0.003, 0.002, 0.001, 0.001, 0.0005, 0.0005]
    cumprobs = np.cumsum(probs)

    colors = [COLORS['success'] if cp <= 0.9 else COLORS['light'] for cp in cumprobs]
    ax1.bar(tokens, probs, color=colors, edgecolor='white', linewidth=0.5)
    ax1.set_title('1) 按概率降序排列，选累积概率 ≤ p 的 token', fontsize=11)
    ax1.set_ylabel('单个概率')
    ax1.set_xlabel('Token (按概率排序)')
    ax1.tick_params(axis='x', rotation=0)
    for i, (p, cp) in enumerate(zip(probs, cumprobs)):
        ax1.text(i, p + 0.01, f'{cp:.2f}', ha='center', fontsize=7, color='#374151')
    ax1.axhline(0, color='black', linewidth=0.5)
    ax1.set_ylim(0, 0.5)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # 标记 cutoff
    ax1.axvline(x=7.5, color=COLORS['danger'], linestyle='--', linewidth=1.2)
    ax1.text(7.5, 0.45, 'p=0.9 截断点', color=COLORS['danger'],
             ha='center', fontsize=9, fontweight='bold')

    # 右图：累积概率曲线
    ax2 = axes[1]
    ax2.plot(range(1, 16), cumprobs, marker='o', color=COLORS['primary'], linewidth=2)
    ax2.fill_between(range(1, 16), cumprobs, alpha=0.2, color=COLORS['primary'])
    ax2.axhline(y=0.9, color=COLORS['danger'], linestyle='--', linewidth=1.2, label='p = 0.9')
    ax2.axvline(x=8, color=COLORS['danger'], linestyle=':', linewidth=1, alpha=0.6)
    ax2.set_title('2) 累积概率曲线：找到刚好跨过 p 的位置', fontsize=11)
    ax2.set_ylabel('累积概率')
    ax2.set_xlabel('Token 数量')
    ax2.set_xticks(range(1, 16))
    ax2.set_ylim(0, 1.05)
    ax2.grid(alpha=0.3, linestyle='--')
    ax2.legend(loc='lower right')

    # 中间标注
    ax2.annotate('从这 8 个 token\n里重新采样', xy=(8, 0.9), xytext=(11, 0.5),
                 arrowprops=dict(arrowstyle='->', color=COLORS['success'], lw=1.5),
                 fontsize=10, color=COLORS['success'], fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.3", facecolor='white',
                           edgecolor=COLORS['success']))

    fig.text(0.5, -0.04,
             'Top-p 的精髓：候选集大小随概率分布自动调整 — 分布陡时少选，分布平时多选',
             ha='center', fontsize=10, style='italic', color='#4b5563')

    save(fig, 'top-p-sampling.png')


# ========== 5. model-size-comparison.png (缺失) ==========
def make_model_size_comparison():
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.suptitle('模型尺寸 vs 能力 vs 成本：Scaling Laws 直观展示',
                 fontsize=15, fontweight='bold', y=0.98)

    # 三条曲线：能力 (上升趋向饱和)，成本 (指数)，速度 (下降)
    sizes = np.array([1, 3, 7, 13, 30, 70, 120, 200, 400, 700, 1000])  # B
    # 能力 - log 形式接近饱和
    ability = 100 * (1 - np.exp(-sizes / 300))
    # 成本 - 线性递增
    cost = sizes * 1.0
    # 速度 - 下降
    speed = 200 / (1 + sizes / 30)

    ax.plot(sizes, ability, 'o-', color=COLORS['success'], linewidth=2.5,
            markersize=8, label='能力 (基准测试分)')
    ax.plot(sizes, cost, 's-', color=COLORS['danger'], linewidth=2.5,
            markersize=8, label='相对成本 (基准=7B)')
    ax.plot(sizes, speed, '^-', color=COLORS['primary'], linewidth=2.5,
            markersize=8, label='推理速度 (tok/s)')

    ax.set_xscale('log')
    ax.set_xlabel('模型参数量 (B, 对数刻度)', fontsize=11)
    ax.set_ylabel('相对值 (归一化)', fontsize=11)
    ax.set_xticks(sizes)
    ax.set_xticklabels([f'{s}B' for s in sizes], rotation=0, fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='center right', fontsize=11, framealpha=0.95)

    # 标注关键区间
    ax.axvspan(1, 13, alpha=0.1, color='green', zorder=0)
    ax.axvspan(30, 200, alpha=0.1, color='orange', zorder=0)
    ax.axvspan(400, 1000, alpha=0.1, color='red', zorder=0)

    ax.text(3, 118, '本地部署\n性价比甜区', ha='center', fontsize=10,
            color='#166534', fontweight='bold')
    ax.text(70, 118, '主力商用区间', ha='center', fontsize=10,
            color='#92400e', fontweight='bold')
    ax.text(700, 280, '旗舰\n边际收益递减', ha='center', fontsize=10,
            color='#991b1b', fontweight='bold')

    save(fig, 'model-size-comparison.png')


# ========== 6. context-window-comparison.png (缺失) ==========
def make_context_window_comparison():
    fig, ax = plt.subplots(figsize=(11, 6))
    models = ['Qwen 2.5\n(7B)', 'DeepSeek\nR1/V3', 'Llama 3.1\n(8B)', 'Claude\n全系列',
              'GLM-4.6\nGrok-4', 'Qwen3\nMax', 'GPT-5.2', 'Gemini 2.5\nPro/Flash']
    windows = [32, 128, 128, 200, 200, 256, 400, 1000]  # 单位 K
    chars = [f'~{w * 750:,} 字' for w in windows]

    # 渐变色
    colors = plt.cm.viridis(np.array(windows) / 1000)

    bars = ax.barh(models, windows, color=colors, edgecolor='black', linewidth=0.5)

    for bar, w, c in zip(bars, windows, chars):
        ax.text(w + 15, bar.get_y() + bar.get_height() / 2,
                f'{w}K ({c})', va='center', fontsize=10, fontweight='bold')

    ax.set_xlim(0, 1200)
    ax.set_xlabel('上下文窗口 (K tokens)', fontsize=11)
    ax.set_title('主流模型上下文窗口对比 (2026 年)',
                 fontsize=15, fontweight='bold', pad=15)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    # 标注参考线
    ax.axvline(x=32, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=128, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=200, color='gray', linestyle=':', alpha=0.5)

    ax.invert_yaxis()  # 让最大的在上面

    save(fig, 'context-window-comparison.png')


# ========== 7. reasoning-vs-standard.png (缺失) ==========
def make_reasoning_vs_standard():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('推理模型 vs 普通模型：工作流对比',
                 fontsize=15, fontweight='bold', y=1.02)

    # 普通模型
    ax1 = axes[0]
    ax1.set_xlim(0, 6)
    ax1.set_ylim(0, 8)
    ax1.axis('off')
    ax1.set_title('普通 LLM (GPT-4, Claude Sonnet)',
                  fontsize=12, fontweight='bold', color=COLORS['primary'])

    boxes1 = [
        (3, 7, '输入 Prompt', '#dbeafe'),
        (3, 5.5, '一次前向推理', '#dbeafe'),
        (3, 4, '直接输出答案', '#dcfce7'),
    ]
    for x, y, text, color in boxes1:
        rect = FancyBboxPatch((x - 1.5, y - 0.4), 3, 0.8,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='#374151', linewidth=1.2)
        ax1.add_patch(rect)
        ax1.text(x, y, text, ha='center', va='center', fontsize=11, fontweight='bold')

    for y_from, y_to in [(6.6, 5.9), (5.1, 4.4)]:
        ax1.annotate('', xy=(3, y_to), xytext=(3, y_from),
                     arrowprops=dict(arrowstyle='->', color='#374151', lw=1.5))

    ax1.text(3, 2.5, '[快] 1-3 秒', ha='center', fontsize=12,
             color=COLORS['primary'], fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#dbeafe', edgecolor='none'))
    ax1.text(3, 1.8, '适合：文本生成、总结、提取、对话', ha='center', fontsize=10)
    ax1.text(3, 1.2, '不擅长：多步推理、数学证明、复杂规划', ha='center', fontsize=10, color=COLORS['danger'])

    # 推理模型
    ax2 = axes[1]
    ax2.set_xlim(0, 6)
    ax2.set_ylim(0, 8)
    ax2.axis('off')
    ax2.set_title('推理模型 (o1, R1, QwQ)',
                  fontsize=12, fontweight='bold', color=COLORS['secondary'])

    boxes2 = [
        (3, 7, '输入 Prompt', '#ede9fe'),
        (3, 6, '内部思考链 (CoT)\n评估多条路径', '#fef3c7'),
        (3, 4.5, '价值重排序\n挑最优解', '#fef3c7'),
        (3, 3, '输出最终答案', '#dcfce7'),
    ]
    for x, y, text, color in boxes2:
        rect = FancyBboxPatch((x - 1.5, y - 0.5), 3, 1.0,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='#374151', linewidth=1.2)
        ax2.add_patch(rect)
        ax2.text(x, y, text, ha='center', va='center', fontsize=10, fontweight='bold')

    for y_from, y_to in [(6.5, 5.5), (5.5, 4), (4, 2.5)]:
        ax2.annotate('', xy=(3, y_to), xytext=(3, y_from),
                     arrowprops=dict(arrowstyle='->', color='#374151', lw=1.5))

    ax2.text(3, 1.5, '[慢] 10-60 秒', ha='center', fontsize=12,
             color=COLORS['secondary'], fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='#ede9fe', edgecolor='none'))
    ax2.text(3, 0.8, '适合：数学、代码、规划、研究', ha='center', fontsize=10)
    ax2.text(3, 0.2, '代价：贵 3-10 倍，吃更多 token',
             ha='center', fontsize=10, color=COLORS['warning'])

    save(fig, 'reasoning-vs-standard.png')


# ========== 8. reasoning-models-landscape.png (缺失) ==========
def make_reasoning_models_landscape():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('推理模型全景图 (2026 年)',
                 fontsize=15, fontweight='bold', pad=15)

    # 四个象限
    quadrants = [
        (0.2, 4, 6.3, 3.6, '闭源旗舰 - 最强推理', '#1e40af', '#dbeafe'),
        (6.7, 4, 6.1, 3.6, '闭源高性价比', '#7c3aed', '#ede9fe'),
        (0.2, 0.2, 6.3, 3.6, '开源推理 - 可本地部署', '#10b981', '#dcfce7'),
        (6.7, 0.2, 6.1, 3.6, '多模态 / 长上下文推理', '#f59e0b', '#fef3c7'),
    ]
    for x, y, w, h, title, ec, fc in quadrants:
        rect = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                         linewidth=1.5, alpha=0.4)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 0.3, title, ha='center', va='top',
                fontsize=12, fontweight='bold', color=ec)

    # 象限1: 闭源旗舰
    items1 = [
        (3.3, 6.3, 'OpenAI o3 / GPT-5.5', '思考模式 + 多路径评估', '#1e40af'),
        (3.3, 5.3, 'Claude Opus 4.8', 'Extended Thinking + 工具调用', '#1e40af'),
        (3.3, 4.4, 'Gemini 2.5 Pro Deep Think', '1M 上下文 + 思考链', '#1e40af'),
    ]
    for x, y, name, desc, c in items1:
        ax.text(x, y, '● ' + name, fontsize=11, fontweight='bold', color=c)
        ax.text(x, y - 0.3, '  ' + desc, fontsize=9, color='#374151')

    # 象限2: 闭源高性价比
    items2 = [
        (9.7, 6.3, 'OpenAI o4-mini', '价格仅为 o3 的 1/10', '#7c3aed'),
        (9.7, 5.3, 'Gemini 2.5 Flash Thinking', '速度极快 + 1M 上下文', '#7c3aed'),
        (9.7, 4.4, 'Grok-4 Reasoning', 'X 平台原生 + 实时信息', '#7c3aed'),
    ]
    for x, y, name, desc, c in items2:
        ax.text(x, y, '● ' + name, fontsize=11, fontweight='bold', color=c)
        ax.text(x, y - 0.3, '  ' + desc, fontsize=9, color='#374151')

    # 象限3: 开源
    items3 = [
        (3.3, 2.8, 'DeepSeek R1 / V3', 'MIT 协议 / 中文友好', '#10b981'),
        (3.3, 1.8, 'QwQ (阿里)', '数学代码强 / 完全开源', '#10b981'),
        (3.3, 0.8, 'Kimi K2.6 / GLM-5.1', '国产开源 / 高性价比', '#10b981'),
    ]
    for x, y, name, desc, c in items3:
        ax.text(x, y, '● ' + name, fontsize=11, fontweight='bold', color=c)
        ax.text(x, y - 0.3, '  ' + desc, fontsize=9, color='#374151')

    # 象限4: 多模态
    items4 = [
        (9.7, 2.8, 'GPT-5.5 multimodal', '图像 / 音频 / 视频推理', '#f59e0b'),
        (9.7, 1.8, '豆包 1.5 Pro 思考', '国产多模态 + 长视频', '#f59e0b'),
        (9.7, 0.8, 'MiniMax M3 推理版', '开源多模态推理', '#f59e0b'),
    ]
    for x, y, name, desc, c in items4:
        ax.text(x, y, '● ' + name, fontsize=11, fontweight='bold', color=c)
        ax.text(x, y - 0.3, '  ' + desc, fontsize=9, color='#374151')

    save(fig, 'reasoning-models-landscape.png')


# ========== 9. gpu-model-fit.png (缺失) ==========
def make_gpu_model_fit():
    fig, ax = plt.subplots(figsize=(12, 6.5))
    fig.suptitle('GPU 显存 vs 可运行模型尺寸 (FP16 推理)',
                 fontsize=15, fontweight='bold', y=0.98)

    # 主流 GPU
    gpus = ['RTX 3060\n12G', 'RTX 4060 Ti\n16G', 'RTX 4090\n24G',
            'RTX 5090\n32G', 'A100\n80G', 'H100\n80G', '2×H100\n160G', '8×H100\n640G']
    vram = [12, 16, 24, 32, 80, 80, 160, 640]
    # 量化等级对应的最大模型尺寸 (B 参数) - 经验估算
    fp16_max = [v / 2 for v in vram]
    q8_max = [v / 1.2 for v in vram]
    q4_max = [v / 0.6 for v in vram]

    x = np.arange(len(gpus))
    w = 0.25

    ax.bar(x - w, fp16_max, w, label='FP16 (全精度)', color=COLORS['primary'], edgecolor='white')
    ax.bar(x, q8_max, w, label='Q8 (8-bit 量化)', color=COLORS['success'], edgecolor='white')
    ax.bar(x + w, q4_max, w, label='Q4_K_M (4-bit 量化)', color=COLORS['warning'], edgecolor='white')

    # 标注常用尺寸的参考线
    ref_lines = [
        (7, 'Qwen 2.5 / Llama 3.1 7B', '#1e40af'),
        (14, 'Qwen 2.5 14B / Llama 13B', '#1e40af'),
        (32, 'Qwen 32B / Llama 30B', '#92400e'),
        (70, 'Llama 3.1 70B / Qwen 72B', '#92400e'),
        (235, 'DeepSeek V3 235B (MoE 激活 37B)', '#991b1b'),
        (671, 'DeepSeek V3 671B (MoE 激活 37B)', '#991b1b'),
    ]
    for size, name, color in ref_lines:
        ax.axhline(y=size, color=color, linestyle='--', alpha=0.5, linewidth=0.8)
        ax.text(7.4, size, f'{name} ≈ {size}B', va='center', fontsize=8, color=color)

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(gpus, fontsize=9)
    ax.set_ylabel('可加载模型尺寸 (B 参数, 对数刻度)', fontsize=11)
    ax.set_ylim(1, 2000)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    ax.set_title('柱状图越高表示能跑越大的模型。MoE 模型激活参数小，实际显存占用更少',
                 fontsize=10, color='#6b7280', pad=10)

    save(fig, 'gpu-model-fit.png')


# 运行所有
if __name__ == '__main__':
    print(f"输出目录: {OUT_DIR}\n")
    make_api_call_flow()
    make_model_selection_decision()
    make_temperature_distribution()
    make_top_p_sampling()
    make_model_size_comparison()
    make_context_window_comparison()
    make_reasoning_vs_standard()
    make_reasoning_models_landscape()
    make_gpu_model_fit()
    print("\n全部完成 ✓")
