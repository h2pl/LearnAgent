# 02 — 启动流程

CC 启动的三秒钟发生了什么——从 entrypoints 到 bootstrap，再到并行预取优化，理解工业级 CLI 的冷启动设计。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [启动流程源码分析](./01-bootstrap-flow.md) | entrypoints/ + bootstrap/ 启动链路，并行预取策略 |

## 涉及源码

- `entrypoints/` — 入口文件
- `bootstrap/` — 启动初始化逻辑

## 对应理论章节

> [02 — 开发环境](../../02-development-environment/README.md) — 环境搭建之后，看看生产级 Agent 如何完成从零到可用的第一步。
