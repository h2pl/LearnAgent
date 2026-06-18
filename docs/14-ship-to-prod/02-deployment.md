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

生产级部署不只是"装个 Docker 跑起来"那么简单——环境管理、配置注入、启动顺序、健康检查、滚动更新，每一个细节都影响系统的可靠性。

## 容器化

Docker 是 Agent 容器化的首选方案。一个 Agent 服务至少包含以下几个容器：

```yaml
# docker-compose.yml
version: "3.8"

services:
  agent-engine:          # Agent 核心引擎（无状态，可多副本）
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
      interval: 10s
      timeout: 5s
      retries: 3

  redis:                # 会话缓存 + 消息队列
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  postgres:             # 持久化存储（用户数据、记忆等）
    image: postgres:16-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
    env_file: .env

  qdrant:               # 向量数据库（可选）
    image: qdrant/qdrant
    volumes:
      - qdrant-data:/qdrant/storage

volumes:
  redis-data:
  postgres-data:
  qdrant-data:
```

### 镜像分层

一个典型的 Agent 引擎 Dockerfile：

```dockerfile
# ===== 构建阶段 =====
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== 运行阶段 =====
FROM python:3.12-slim

RUN adduser --system --group agent
WORKDIR /app

# 只复制依赖，不做 curl 安装——用 Python 实现健康检查
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=agent:agent . .

USER agent
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**关键实践**：
- 多阶段构建，分离构建和运行环境
- 使用非 root 用户运行（`USER agent`）
- 只复制需要的文件到生产镜像
- 显式声明 HEALTHCHECK

## Docker 最佳实践

### 启动顺序控制

Agent 系统依赖多个服务。启动顺序错误会导致 Agent 引擎尝试连接尚未就绪的 Redis 或数据库。

**正确的做法是使用健康检查 + 依赖等待**：

```yaml
services:
  agent-engine:
    depends_on:
      redis:
        condition: service_healthy  # 等待 Redis 健康后再启动
      postgres:
        condition: service_healthy
```

注意：`depends_on` 只控制启动顺序，不保证服务在容器启动后能立即接受连接。**健康检查 (healthcheck) 才是正确的方式。**

### 资源限制

Agent 引擎是资源消耗大户。必须显式限制资源：

```yaml
services:
  agent-engine:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: "4G"
        reservations:
          cpus: "0.5"
          memory: "1G"
```

没有资源限制的 Agent 容器可能吃掉宿主机所有内存。

### 日志

容器日志应该输出到 stdout/stderr，不要写到文件：

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,  # 输出到 stdout，Docker 自动收集
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

然后通过 Docker 的日志驱动（`json-file`、`journald`、`fluentd`）统一收集。

## 多环境管理

### 环境分层

```
dev（开发环境）
  ├── 本地 Docker Compose
  ├── 可以调试、断点
  └── 使用 mock 外部依赖

staging（预发布环境）
  ├── 与生产环境配置一致
  ├── 连接真实外部 API（测试账号）
  └── 运行完整评测集

prod（生产环境）
  ├── 多副本 + 负载均衡
  ├── 连接真实外部 API
  ├── 全量监控和告警
  └── 限制：审批流程、安全策略全开
```

### 配置管理

不同环境通过环境变量注入配置，**而不是修改配置文件**：

```
# .env.dev
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-test-key
DATABASE_URL=postgresql://dev:dev@postgres:5432/agent
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=DEBUG
MOCK_TOOLS=true

# .env.prod
LLM_MODEL=gpt-4o
LLM_API_KEY=${PROD_API_KEY}     # 从密钥管理服务读取
DATABASE_URL=${PROD_DB_URL}
REDIS_URL=${PROD_REDIS_URL}
LOG_LEVEL=INFO
MOCK_TOOLS=false
```

**永远不要把生产环境的密钥写入代码仓库。**

## CI/CD 流水线

一个完整的 CI/CD 流水线应该包含以下阶段：

```yaml
# .github/workflows/deploy.yml
name: Deploy Agent

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 运行单元测试
        run: make test
      - name: 运行组件级评测
        run: make eval-component
      - name: 运行安全扫描
        run: make security-scan

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: 构建 Docker 镜像
        run: docker build -t agent-engine:${{ github.sha }} .
      - name: 推送镜像到仓库
        run: docker push registry.example.com/agent-engine:${{ github.sha }}

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: 部署到 Staging
        run: kubectl set image deployment/agent-engine agent-engine=registry.example.com/agent-engine:${{ github.sha }} --namespace staging
      - name: 等待部署完成
        run: kubectl rollout status deployment/agent-engine --namespace staging
      - name: 运行端到端评测
        run: make eval-e2e-staging

  deploy-prod:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main' && success()
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: 灰度发布（10% -> 50% -> 100%）
        run: kubectl set image deployment/agent-engine agent-engine=registry.example.com/agent-engine:${{ github.sha }} --namespace prod
      - name: 监控 10 分钟
        run: make wait-for-stability
      - name: 扩容到 100%
        run: kubectl rollout status deployment/agent-engine --namespace prod
```

## 持续评测

CI/CD 不只是"构建和部署"，对于 Agent 系统，**评测是 CI/CD 的核心环节**。

每次代码变更都应该自动运行评测集：

```
CI Pipeline:
  1. 代码检查 (lint, type check)
  2. 单元测试 (组件级)
  3. 集成测试 (工具 + 检索 + 记忆)
  4. 安全扫描 (注入检测 + 权限检查)
  5. 组件级评测 (500 个用例)
  6. 核心任务评测 (200 个用例)
  7. 性能基准 (响应时间 + token 消耗)
  8. 对比指标 vs main 分支

  如果核心 TSR 下降 > 2% → 阻断合并
  如果响应时间增加 > 20% → 告警
  如果 token 消耗增加 > 30% → 标记审查
```

## 部署策略

### 滚动更新

对于无状态的 Agent 引擎，滚动更新是最安全的策略：

```
初始: 5 个副本，版本 V1
Step 1: 启动 1 个 V2 实例
Step 2: 确认 V2 健康后，停止 1 个 V1 实例
Step 3: 重复直到全部替换为 V2
```

滚动更新确保任何时候都有足量实例在处理请求。

### 蓝绿部署

如果有足够的资源，蓝绿部署更安全：

```
蓝色: 当前生产环境 (V1)
绿色: 新版本环境 (V2)

切换时: 
  1. 将流量从蓝色切到绿色
  2. 观察 10-30 分钟
  3. 确认无问题后保留绿色
  4. 蓝色保留为回滚目标
```

### 回滚策略

每次部署都应该有回滚方案：

```
自动回滚条件:
  - 错误率上升 > 5%
  - P95 延迟上升 > 50%
  - 任务完成率下降 > 5%
  - 健康检查连续失败

回滚操作:
  - 恢复到上一个版本的镜像
  - 通知团队
  - 保存当前版本日志用于事后分析
```

## 环境变量与密钥管理

### 密钥分类

| 类别 | 示例 | 管理方式 |
|------|------|---------|
| LLM API Key | OpenAI/Anthropic Key | 密钥管理服务 (Vault/AWS Secrets Manager) |
| 数据库密码 | PostgreSQL 密码 | 密钥管理服务 |
| 工具 API Key | 外部服务凭证 | 密钥管理服务 |
| JWT Secret | 用户认证密钥 | 密钥管理服务 + 定期轮换 |
| 非敏感配置 | 模型名、日志级别 | 环境变量 |

### 密钥注入方式

**不要在 Docker 镜像中内置密钥**。密钥应该在运行时注入：

```
# ❌ 错误：密钥写在 Dockerfile 或代码中
ENV OPENAI_API_KEY=sk-xxx

# ✅ 正确：运行时通过环境变量注入
docker run -e OPENAI_API_KEY=${OPENAI_API_KEY} agent-engine
```

在 Kubernetes 中，使用 Secrets：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-xxx"
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - envFrom:
            - secretRef:
                name: agent-secrets
```

## 总结

部署是 Agent 落地的最后一步。核心要点：

- **容器化**：多阶段构建、健康检查、资源限制
- **多环境管理**：dev/staging/prod 三层隔离，配置通过环境变量注入
- **CI/CD**：评测是核心环节，核心指标下降应阻断部署
- **部署策略**：滚动更新默认，蓝绿部署后补，自动回滚兜底

**下一篇**：监控与运维——系统上线只是开始，持续监控和文档维护才是长期工作。

## 参考链接

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Production Best Practices](https://kubernetes.io/docs/setup/best-practices/)
- [12-Factor App — Config](https://12factor.net/config)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [HashiCorp Vault](https://www.vaultproject.io/)
