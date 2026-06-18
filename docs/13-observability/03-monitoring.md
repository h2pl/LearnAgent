# 监控体系

> Trace 解决"哪一步出了问题"，监控解决"系统现在健康吗"。四个黄金指标 + 一套告警体系，让系统状态一目了然。

## 目录

- [生产监控体系](#生产监控体系)
- [四大黄金指标](#四大黄金指标)
- [Agent 专属指标](#agent-专属指标)
- [告警策略](#告警策略)
- [工具栈](#工具栈)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。前两篇文章覆盖了全链路追踪和成本监控。Trace 是"手术刀"，帮你精确诊断问题。但你还需要一个"仪表盘"——**实时告诉你系统整体是否健康**。

本文介绍如何建立生产级的 Agent 监控体系。

## 生产监控体系

<p align="center">
  <img src="../../assets/13-observability/monitoring-dashboard.svg" alt="监控仪表盘" width="95%"/>
</p>

## 四大黄金指标

Google SRE 推荐的四个核心监控维度，对于 Agent 系统同样适用。

### 延迟 (Latency)

请求处理时间，区分成功和失败的延迟：

```
Agent 响应时间:
  P50: 1.2s    ← 典型用户体验
  P95: 3.8s    ← 慢请求边界
  P99: 8.5s    ← 异常值（可能有问题）
```

重点关注 P95 和 P99——大多数用户感觉"流畅"还是"慢"，取决于尾部延迟。

### 流量 (Traffic)

系统的请求量：

```
请求量: 3.2 请求/秒（日均 27 万）
并发连接: 45
用户数: 1.2 万 DAU
```

流量趋势比绝对值更重要——突然下降可能表示系统不可用，突然上升可能表示被攻击。

### 错误 (Errors)

请求失败的比例：

```
错误类型:
  - HTTP 5xx: 0.3%（服务端错误）
  - 超时: 0.8%（外部依赖慢）
  - 工具错误: 1.2%（外部 API 失败）
  - LLM 错误: 0.1%（模型异常）
  - 任务失败: 3.5%（Agent 逻辑错误）
```

**任务失败率是最重要的 Agent 专属指标**——它反映的是"用户任务没完成"，而不仅仅是"系统没报错"。

### 饱和度 (Saturation)

系统资源使用程度：

```
CPU: 62%
内存: 78%
并发请求: 45 / 上限 200
队列深度: 12
```

饱和度接近 80% 时就应该考虑扩容。

## Agent 专属指标

除了通用指标，Agent 系统还需要关注：

```
Token 消耗:
  - 日均: 1500 万 token
  - 每请求: 平均 4500 token
  - 输入输出比: 3.2:1

LLM 调用:
  - 每请求次数: 平均 3.5 次
  - 工具调用率: 67%（多少请求调用了工具）
  - 缓存命中率: 22%

用户反馈:
  - 满意度评分: 4.2/5
  - 人工介入率: 2.3%
  - 用户重试率: 1.8%
```

## 告警策略

### 告警分级

| 级别 | 定义 | 响应 | 通知方式 |
|------|------|------|---------|
| P0 | 服务不可用 | 立即 | 电话 + 即时消息 |
| P1 | 核心功能受损 | 15 分钟 | 即时消息 |
| P2 | 非核心功能异常 | 2 小时 | 邮件 |
| P3 | 预警信息 | 24 小时 | 邮件 / 仪表盘 |

### 告警规则示例

```yaml
# P0 规则
- alert: ServiceDown
  expr: up{job="agent-engine"} == 0
  for: 1m
  severity: critical

- alert: HighErrorRate
  expr: rate(http_requests_errors_total[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 3m
  severity: critical

# P1 规则
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
  for: 5m
  severity: warning

- alert: TaskFailureRate
  expr: rate(agent_task_failures_total[30m]) / rate(agent_task_total[30m]) > 0.1
  for: 5m
  severity: warning

# P2 规则
- alert: TokenSpike
  expr: rate(agent_tokens_total[1h]) / rate(agent_tokens_total[24h]) > 2
  for: 10m
  severity: info

- alert: BudgetWarning
  expr: daily_cost > daily_budget * 0.8
  for: 1h
  severity: info
```

### 告警响应

每个告警都应该有对应的 Runbook（运维手册）：

```markdown
# Runbook: HighErrorRate

## 检查步骤
1. 登录 Grafana，查看错误分布 → 是哪个 API 错误最多？
2. 查看最近的部署记录 → 是否有最近变更？
3. 查看 LLM/Tool 面板 → 是内部错误还是外部依赖？

## 常见原因及处理
| 错误模式 | 可能原因 | 处理方式 |
|---------|---------|---------|
| 全是 5xx | 服务内部错误 | 检查日志、回滚最近部署 |
| 全是超时 | 外部依赖慢 | 检查 Redis/数据库/LLM 状态 |
| 全是工具错误 | 外部 API 不可用 | 联系外部 API 负责人 |
| Agent 任务失败 | prompt 或逻辑问题 | 检查最近 prompt 变更 |

## 升级流程
- 15 分钟内未恢复 → 通知 Tech Lead
- 30 分钟内未恢复 → 全组响应
```

## 工具栈

推荐的开源监控栈：

```
指标采集: Prometheus + 自定义 exporter
日志: Loki 或 Elasticsearch
链路追踪: Tempo 或 Jaeger
可视化: Grafana
告警: AlertManager
```

一个 Grafana 仪表盘至少包含以下面板：

- **请求量**（折线图，按 API 维度分组）
- **响应时间**（P50/P95/P99 折线图）
- **错误率**（堆叠面积图，按错误类型分组）
- **Token 消耗**（每日趋势 + 累计）
- **任务完成率**（时间序列）
- **资源利用率**（CPU/内存/并发数）
- **用户满意度**（每日评分趋势）

## 总结

监控是 Agent 系统的"仪表盘"。没有监控，你无法回答"系统现在是否健康"。

核心原则：追踪四大黄金指标（延迟/流量/错误/饱和度）→ 附加 Agent 专属指标（Token/任务完成率）→ 设置分级告警 → 每个告警配 Runbook。

**下一篇**：[安全与治理](../14-safety/01-prompt-injection.md)——从可观测性转向安全防护。

## 参考链接

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
