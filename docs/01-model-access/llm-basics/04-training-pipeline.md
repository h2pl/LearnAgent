# 模型训练流程概览

## 目录

- [概述](#概述)
- [预训练](#预训练)
- [指令微调（SFT）](#指令微调sft)
- [人类对齐（RLHF / DPO）](#人类对齐rlhf--dpo)
- [开发者需要知道什么](#开发者需要知道什么)
- [参考链接](#参考链接)

## 概述

<!-- TODO: 知道模型是怎么来的，有助于理解它的行为和局限。不需要会训，但要知道流程 -->

## 预训练

<!-- TODO: 海量语料 + 自监督学习（预测下一个 token），获得通用语言能力，成本极高 -->

## 指令微调（SFT）

<!-- TODO: 用 instruction-response 对让模型学会"听指令"，从补全文本变成回答问题 -->

## 人类对齐（RLHF / DPO）

<!-- TODO: 让模型输出更符合人类偏好，减少有害内容，提升有用性 -->

## 开发者需要知道什么

<!-- TODO: base model vs chat model 的区别、为什么同一模型有不同版本、微调对应用的意义 -->

## 参考链接

- [Andrej Karpathy — State of GPT](https://www.youtube.com/watch?v=bZQun8Y4L2A)
- [Chip Huyen — RLHF: Reinforcement Learning from Human Feedback](https://huyenchip.com/2023/05/02/rlhf.html)
