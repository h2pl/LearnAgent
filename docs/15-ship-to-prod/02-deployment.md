# 部署方案

> 代码写好了，怎么让它在生产环境稳定运行？Docker 容器化、CI/CD 流水线、多环境管理——这些是 Agent 系统的"交付最后一公里"。

## 目录

- [容器化](#容器化)
- [Docker 最佳实践](#docker-最佳实践)
- [多环境管理](#多环境管理)
- [CI/CD 流水线](#cicd-流水线)
- [持续评测](#持续评测)
- [部署策略](#部署策略)
- [环境变量与密钥管理](#环境变量与密钥管理)
- [总结](#总结)
- [参考链接](#参考链接)

你好，我是江小湖。上一篇文章定义了 Agent 系统的架构和 API。现在，我们要把这些代码**打包、发布、部署到服务器上，让它稳定运行**。

## 容器化

```yaml
services:
  agent-engine:
    build: ./agent-engine
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  redis:
    image: redis:7-alpine

  postgres:
    image: postgres:16-alpine

  qdrant:
    image: qdrant/qdrant
```

### 镜像构建

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
RUN adduser --system --group agent
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=agent:agent . .
USER agent
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

关键：多阶段构建、非 root 用户、显式 HEALTHCHECK。

## Docker 最佳实践

**启动顺序**：使用 `depends_on` + 健康检查，确保 Redis/PostgreSQL 就绪后再启动 Agent。

**资源限制**：显式限制 CPU 和内存，防止 Agent 吃光宿主机。

```yaml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: "4G"
```

**日志**：输出到 stdout/stderr，由 Docker 日志驱动统一收集。

## 多环境管理

```
dev（开发）
  ├── Docker Compose 本地运行
  ├── mock 外部依赖
  └── 可断点调试

staging（预发布）
  ├── 与生产配置一致
  ├── 真实外部 API（测试账号）
  └── 运行完整评测集

prod（生产）
  ├── 多副本 + 负载均衡
  ├── 全量监控告警
  └── 审批流程全开
```

配置通过环境变量注入，而非修改配置文件：

```
# .env.dev
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-test-key
MOCK_TOOLS=true

# .env.prod
LLM_MODEL=gpt-4o
LLM_API_KEY=${PROD_API_KEY}   # 从密钥管理服务读取
```

## CI/CD 流水线

```yaml
jobs:
  test:
    steps:
      - run: make test
      - run: make eval-component
      - run: make security-scan

  build:
    needs: test
    steps:
      - run: docker build -t agent-engine:${{ github.sha }} .
      - run: docker push registry.example.com/agent-engine:${{ github.sha }}

  deploy-staging:
    needs: build
    steps:
      - run: kubectl set image deployment/agent-engine agent-engine=${{ github.sha }} --namespace staging
      - run: make eval-e2e-staging

  deploy-prod:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    steps:
      - run: kubectl set image deployment/agent-engine agent-engine=${{ github.sha }} --namespace prod
      - run: kubectl rollout status deployment/agent-engine --namespace prod
```

## 持续评测

每次代码变更自动运行评测集：

```
CI Pipeline:
1. 代码检查 (lint, type check)
2. 单元测试
3. 安全扫描
4. 组件级评测 (500 用例)
5. 核心任务评测 (200 用例)
6. 性能基准

阻断条件: 核心 TSR 下降 > 2% → 阻断合并
告警条件: 响应时间增加 > 20% → 告警
```

## 部署策略

### 滚动更新

```
初始: 5 个副本 V1
Step 1: 启动 1 个 V2
Step 2: V2 健康 → 停止 1 个 V1
Step 3: 重复直到全部替换
```

### 蓝绿部署

```
蓝色: V1（当前生产）
绿色: V2（新版本）
切换: 流量从蓝切到绿，观察 10-30 分钟
回滚: 切回蓝色
```

### 自动回滚条件

```
错误率上升 > 5%
P95 延迟上升 > 50%
任务完成率下降 > 5%
健康检查连续失败
```

## 环境变量与密钥管理

| 类别 | 示例 | 管理方式 |
|------|------|---------|
| LLM API Key | OpenAI Key | 密钥管理服务 (Vault) |
| 数据库密码 | PostgreSQL | 密钥管理服务 |
| 非敏感配置 | 模型名、日志级别 | 环境变量 |

不要在 Docker 镜像中内置密钥。运行时注入：

```bash
docker run -e OPENAI_API_KEY=${OPENAI_API_KEY} agent-engine
```

## 总结

核心要点：容器化（多阶段+健康检查）→ 多环境（dev/staging/prod）→ CI/CD（评测阻断）→ 部署策略（滚动/蓝绿）→ 密钥管理。

**下一篇**：[运维实战与项目文档](03-operations-and-docs.md)——系统上线只是开始。

## 参考链接

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)
- [12-Factor App — Config](https://12factor.net/config)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [HashiCorp Vault](https://www.vaultproject.io/)
