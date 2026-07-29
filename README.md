# MedAgent

MedAgent 是一个带证据引用、请求隔离和生成排队的医学 RAG 演示系统。项目以
BYOK（Bring Your Own Key）方式发布：每个部署者使用自己的模型账号和 API Key，
源码仓库与容器镜像不包含模型凭证或教材正文。部署者可以明确接受第三方数据风险后，
从 MedRAG 官方 Hugging Face 数据集下载固定版本的 18 个教材来源和 125,847 个
chunk。

> MedAgent 用于研究和演示，不构成诊断或治疗建议，也不是医疗器械。

## 能力

- FastAPI + React 单体部署；
- 请求级对话历史，不在服务端保存用户会话；
- BM25、Chroma 和 PubMed 混合检索及引用展示；
- 最多 3 个生成任务并行、6 个请求排队；
- 共享访问密码和 12 小时签名 HttpOnly Cookie；
- 输入限制、受控 CORS、结构化错误、请求号和耗时指标；
- 固定版本下载、SHA-256 和 125,847 条语料完整性校验；
- 禁用教材下载或本地知识库缺失时明确进入 `pubmed_only` 模式。

## 模型供应商

| `LLM_PROVIDER` | 用途 |
|---|---|
| `openai_compatible` | OpenAI Chat Completions 兼容服务，例如 OpenAI、MiMo、DeepSeek、OpenRouter、vLLM 和提供兼容端点的 Ollama |
| `anthropic` | 原生 Anthropic Messages API 或兼容代理 |

不同服务对模型名和请求参数的支持可能不同。部署者必须根据自己的服务商文档填写
`LLM_BASE_URL`、`LLM_MODEL` 和 `LLM_API_KEY`。

## Docker 快速开始

要求 Docker Engine 或 Docker Desktop，以及 Docker Compose。

```bash
cp .env.example .env
# 编辑 .env，填写自己的模型凭证、访问密码和随机会话密钥。
# 阅读 docs/corpus-licensing.md 后，选择：
# MEDRAG_TEXTBOOKS_ACCEPT_TERMS=true  下载固定教材语料
# TEXTBOOKS_ENABLED=false             仅使用 PubMed
docker compose up --build -d
```

打开 `http://127.0.0.1:8000`。

Windows PowerShell：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

停止服务：

```bash
docker compose down
```

`corpus-init` 首次运行时将固定版本的第三方教材数据下载到 `medagent-data` 命名卷，
校验完成后才启动应用；后续重启复用该卷。完整部署说明见
[docs/deployment.md](docs/deployment.md)。

## 本地开发

要求 Python 3.10+ 和 Node.js 22+。

```powershell
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements-dev.lock
Copy-Item .env.example .env

npm --prefix frontend ci
npm --prefix frontend run build

# 启用教材时先编辑 .env 确认第三方数据风险，再初始化语料
.\.venv-win\Scripts\python.exe -m src.knowledge.bootstrap

.\.venv-win\Scripts\python.exe -m uvicorn src.api.main:app `
  --host 127.0.0.1 --port 8000
```

## 必需配置

```dotenv
LLM_PROVIDER=openai_compatible
LLM_API_KEY=replace_with_your_own_api_key
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=replace_with_your_model_name
LLM_REQUIRE_API_KEY=true
LLM_TOKEN_PARAMETER=max_tokens

MEDAGENT_ACCESS_PASSWORD=replace_with_a_strong_password
MEDAGENT_SESSION_SECRET=replace_with_at_least_32_random_bytes
```

本地 Ollama/vLLM 等无需鉴权的兼容服务可设置：

```dotenv
LLM_REQUIRE_API_KEY=false
LLM_API_KEY=
```

少数推理模型只接受 `max_completion_tokens`，此时把
`LLM_TOKEN_PARAMETER` 改为该值。

缺少必需配置时服务拒绝启动。生产环境还必须设置：

```dotenv
COOKIE_SECURE=true
CORS_ORIGINS=https://your-medagent.example.com
```

## 数据边界

公开仓库和镜像不包含教材、切片、嵌入或索引。启用下载时，初始化容器从
[`MedRAG/textbooks`](https://huggingface.co/datasets/MedRAG/textbooks) 获取固定
revision `9c72838920a1323ffa867467d3f7aa7b36b0f994`，并验证18个文件、逐文件
SHA-256、JSONL 字段、唯一 ID 和 125,847 条总数。查询检索随后完全在部署者的数据
卷中执行，不调用 MedRAG 在线服务。

该数据集公开可下载，但上游数据卡没有声明明确许可证；公开可访问不等于已获得商业
使用、重新分发或公开展示教材片段的完整授权。启用
`MEDRAG_TEXTBOOKS_ACCEPT_TERMS=true` 仅表示部署者已阅读并接受第三方数据风险，
不构成许可证授予。没有本地数据时系统仍可使用模型和 PubMed，统计接口显示
`knowledge_mode=pubmed_only`。参见：

- [data/README.md](data/README.md)
- [docs/corpus-licensing.md](docs/corpus-licensing.md)

## 测试

```powershell
.\.venv-win\Scripts\python.exe -m pytest -q
npm --prefix frontend run build
.\.venv-win\Scripts\python.exe tests\e2e_smoke.py
```

GitHub Actions 会在 push 和 pull request 时验证后端、前端及容器构建。

## 开源与致谢

代码采用 [Apache License 2.0](LICENSE)。MedRAG 兼容性和论文引用见
[NOTICE](NOTICE)。第三方依赖保留各自许可证。

安全问题请参考 [SECURITY.md](SECURITY.md)，贡献说明见
[CONTRIBUTING.md](CONTRIBUTING.md)。
