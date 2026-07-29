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
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=60

# 二选一：下载固定教材语料，或只使用 PubMed
TEXTBOOKS_ENABLED=true
TEXTBOOKS_AUTO_DOWNLOAD=true
MEDRAG_TEXTBOOKS_ACCEPT_TERMS=true
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

Compose 默认监听 `127.0.0.1`。只有明确需要其他网络接口连接时才覆盖：

```dotenv
MEDAGENT_BIND_HOST=127.0.0.1
MEDAGENT_PORT=8000
```

首次启动会下载约 212 MB 的第三方教材 chunk。查看初始化进度：

```bash
docker compose logs -f corpus-init
```

初始化器锁定 Hugging Face revision，验证18个文件的大小、SHA-256、JSONL 字段、
唯一 ID 以及 125,847 条总数。只有初始化成功后才启动 `medagent`。数据保存在
`medagent-data` 命名卷，后续重启不会重复下载。

若不接受第三方教材的数据风险，请设置：

```dotenv
TEXTBOOKS_ENABLED=false
TEXTBOOKS_AUTO_DOWNLOAD=false
MEDRAG_TEXTBOOKS_ACCEPT_TERMS=false
```

初始化器会跳过下载，应用以 `pubmed_only` 模式启动。

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

查看经过过滤的日志：

```bash
docker compose logs --tail=100 medagent
```

公开镜像不包含教材；教材仅在部署机器启动时下载到命名卷。

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
MEDAGENT_BIND_HOST=127.0.0.1
```

应用包含基础的登录失败限速；公网环境仍建议在反向代理或网关增加第二层限速。

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

## 6. 教材语料与自有语料

默认下载源是 MedRAG 项目发布的公开 Hugging Face 数据集：

```text
https://huggingface.co/datasets/MedRAG/textbooks
```

固定 revision：

```text
9c72838920a1323ffa867467d3f7aa7b36b0f994
```

容器内保存路径：

```text
/app/data/index/medrag/textbooks/chunk/
```

公开可下载不等于上游提供了明确商业许可证。启用开关只记录部署者的风险确认，不替代
出版社或权利人的许可。不要把下载后的语料重新构建进公共镜像。

自有授权 JSONL 也可以放入上述 `chunk/` 目录，每行至少包含 `id`、`title` 和
`content`。若使用官方完整性校验器，目录必须与固定的18文件 manifest 完全一致；
自有语料应使用独立目录和自己的 manifest。
