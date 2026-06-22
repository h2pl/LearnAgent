# 12 — 会话持久化

CC 的会话持久化机制——sessionStorage 与 transcript 模块，断点续传、checkpoint 与状态恢复的完整实现。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [会话持久化源码分析](./01-session-persistence-source.md) | sessionStorage 存储、transcript 记录、checkpoint、断点续传 |

## 涉及源码

- `sessionStorage` 模块
- `transcript` 模块
- checkpoint 相关逻辑

## 对应理论章节

> [08 — 记忆与状态](../../08-memory-state/README.md) — 持久化是记忆的工程基础，会话恢复是用户体验的关键。
