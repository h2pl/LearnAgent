# 关键参数与调优

## 目录

- [概述](#概述)
- [temperature 与 top_p](#temperature-与-top_p)
- [max_tokens 与 stop](#max_tokens-与-stop)
- [Context Window 管理](#context-window-管理)
- [常见踩坑](#常见踩坑)
- [参考链接](#参考链接)

## 概述

<!-- TODO: API 参数直接影响输出质量和成本，需要理解每个参数的实际效果 -->

## temperature 与 top_p

<!-- TODO: 控制生成的随机性/确定性，不同场景的推荐值 -->

## max_tokens 与 stop

<!-- TODO: 控制输出长度、stop sequence 的作用 -->

## Context Window 管理

<!-- TODO: 输入+输出共享 context window、超长对话的截断策略 -->

## 常见踩坑

<!-- TODO: 中文 token 数量比英文多、max_tokens 不够导致输出截断、temperature=0 也不完全确定 -->

## 参考链接

- [OpenAI — Chat Completions API](https://platform.openai.com/docs/guides/chat-completions)
