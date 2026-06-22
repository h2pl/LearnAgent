# 10 — 权限系统

CC 权限系统的完整分析——permissions.ts（1486 行）与 20 个辅助文件，七种权限模式、ML 分类器与危险操作拦截策略。

## 目录

| # | 文章 | 内容 |
|---|------|------|
| 01 | [权限系统源码分析](./01-permissions-source.md) | 七种权限模式、ML 分类器、危险模式拦截、权限升级流程 |

## 涉及源码

- `utils/permissions/permissions.ts`（1486 行）
- `utils/permissions/` 下 20 个辅助文件

## 对应理论章节

> [10 — 安全与权限](../../10-security-permissions/README.md) — Agent 的自主性越强，权限控制越关键。
