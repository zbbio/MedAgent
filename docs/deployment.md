# 部署指南

## 正确发布顺序

1. 在本地整理源码、忽略规则和许可证。
2. 在本地构建并测试 Docker 镜像。
3. 只在 `MedAgent` 目录初始化 Git 并上传 GitHub。
4. 由 GitHub Actions 构建无数据、无密钥镜像并发布到 GHCR。
5. 在 VPS、云容器平台或 Kubernetes 上运行镜像。

GitHub 仓库存放源码；GitHub Pages 不能运行 FastAPI。GHCR 存放容器镜像，真正的
在线服务仍需要服务器或容器托管平台。

## 1. 创建运行配置

```bash
cp .env.example .env
```

至少填写：

```dotenv
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_own_key
LLM_BASE_URL=https://your-provider.example/v1
LLM_MODEL=your-model
LLM_REQUIRE_API_KEY=true
LLM_TOKEN_PARAMETER=max_tokens

MEDAGENT_ACCESS_PASSWORD=your-shared-demo-password
MEDAGENT_SESSION_SECRET=at-least-32-random-bytes
```

可以使用下面的命令生成会话密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`.env` 只能保存在部署机器上，不能提交、上传或复制进镜像。

## 2. Docker Compose

```bash
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

查看经过过滤的日志：

```bash
docker compose logs --tail=100 medagent
```

默认数据保存于 Docker 命名卷 `medagent-data`。公开镜像不包含本地教材。

## 3. 模型配置

### OpenAI 兼容服务

```dotenv
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your-key
LLM_BASE_URL=https://provider.example/v1
LLM_MODEL=provider-model-name
LLM_REQUIRE_API_KEY=true
LLM_TOKEN_PARAMETER=max_tokens
```

### 原生 Anthropic

```dotenv
LLM_PROVIDER=anthropic
LLM_API_KEY=your-anthropic-key
LLM_BASE_URL=https://api.anthropic.com
LLM_MODEL=your-claude-model
LLM_REQUIRE_API_KEY=true
```

### 本地 Ollama/vLLM

```dotenv
LLM_PROVIDER=openai_compatible
LLM_API_KEY=
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL=your-local-model
LLM_REQUIRE_API_KEY=false
```

Linux 容器访问宿主服务时，可能需要在 Compose 中增加
`host-gateway` 映射，或改用宿主机实际地址。

## 4. 生产环境

生产环境必须：

- 在 HTTPS 反向代理后运行；
- 设置 `COOKIE_SECURE=true`；
- 将 `CORS_ORIGINS` 设置为准确的 HTTPS 域名；
- 使用强访问密码并轮换曾暴露的模型 Key；
- 对登录入口增加网关级限速；
- 将容器端口只暴露给反向代理；
- 使用平台 Secret/环境变量注入凭证；
- 监控 429、504、上游限流、队列和资源使用。

示例：

```dotenv
COOKIE_SECURE=true
CORS_ORIGINS=https://medagent.example.com
```

## 5. 发布 GitHub 与 GHCR

仓库中的 CI 会验证 Docker 构建。标签发布工作流会把镜像推送到：

```text
ghcr.io/<github-user-or-org>/<repository>:<tag>
```

创建版本：

```bash
git tag v1.0.0
git push origin v1.0.0
```

发布前检查：

```bash
git status --ignored
git ls-files
git grep -n -E "(sk-|tp-|api[_-]?key|session[_-]?secret)"
```

任何真实密钥一旦进入提交历史，都应立即吊销并轮换，不能只删除当前文件。

## 6. 私有或授权语料

无语料时系统运行于 `pubmed_only` 模式。只有确认拥有索引、展示和分发权限后，才能
将 JSONL 挂载到：

```text
/app/data/index/medrag/MedCorp/chunk/
```

不要把语料构建进公共镜像。私有部署应通过只读卷挂载授权数据，并对卷和备份单独做
访问控制。
