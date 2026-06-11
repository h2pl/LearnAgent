# Transformer 架构直觉

## 目录

- [概述](#概述)
- [为什么是 Transformer](#为什么是-transformer)
- [自注意力机制](#自注意力机制)
- [自回归生成](#自回归生成)
- [位置编码](#位置编码)
- [Encoder vs Decoder](#encoder-vs-decoder)
- [参考链接](#参考链接)

## 概述

<!-- TODO: 不需要能推导公式，但需要理解 Transformer 的主要步骤：tokenization → attention → generation -->

## 为什么是 Transformer

<!-- TODO: RNN/LSTM 的瓶颈（序列依赖、长距离遗忘）→ Transformer 的并行化优势 -->

## 自注意力机制

<!-- TODO: 直觉：每个 token "看一眼" 所有其他 token，判断跟谁关系更大；Q/K/V 的类比 -->

## 自回归生成

<!-- TODO: 逐 token 预测下一个，每次生成一个 token 并把它加入输入，循环生成 -->

## 位置编码

<!-- TODO: Transformer 本身不知道顺序，需要额外编码位置信息；RoPE 等 -->

## Encoder vs Decoder

<!-- TODO: BERT(encoder) vs GPT(decoder-only)，现代 LLM 基本都是 decoder-only -->

## 参考链接

- [3Blue1Brown — Visual intro to Transformers](https://www.youtube.com/watch?v=wjZofJX0v4M)
- [Brendan Bycroft — LLM Visualization](https://bbycroft.net/llm)
- [Lilian Weng — Attention? Attention!](https://lilianweng.github.io/posts/2018-06-24-attention/)
