# 架构

## 请求路径

```text
Browser
  -> signed HttpOnly session cookie
  -> FastAPI /api/ask
  -> generation queue
  -> request-scoped history
  -> query understanding and route selection
  -> BM25 / PubMed retrieval
  -> configured LLM provider
  -> citation mapping
  -> structured response with request_id and timings
```

## 知识库初始化

Docker Compose 先运行一次性 `corpus-init` 服务。启用第三方教材下载时，它从
`MedRAG/textbooks` 的固定 revision 下载18个 JSONL 到命名卷，验证文件大小、
SHA-256、JSONL 结构、唯一 ID 和 125,847 条总数，再允许 API 容器启动。下载使用
临时目录，只有完整验证成功后才原子发布，因此中断下载不会被检索器当成有效知识库。

设置 `TEXTBOOKS_ENABLED=false` 时初始化器成功跳过，API 进入 `pubmed_only`。
仅关闭 `TEXTBOOKS_AUTO_DOWNLOAD` 会阻止网络下载，但仍允许读取已有或自行挂载的语料。
运行时只读取本地数据卷，不向 MedRAG 服务发送用户问题。

## 会话模型

服务端不保存全局对话内存。浏览器只在当前页面内维护最近 10 条历史，并在每次请求中
发送。刷新或退出后历史消失，因此不同浏览器和用户不会共享上下文。

## LLM Provider

`LLMClient` 只负责通用 Prompt 和 JSON 解析；协议差异由
`src/generation/providers/` 中的适配器处理：

- `openai_compatible`：Chat Completions 协议；
- `anthropic`：Messages API。

模型凭证仅从运行环境读取，不进入前端、源码或镜像层。

## 检索模式

- `local_and_pubmed`：本地 BM25 包含文档，同时使用 PubMed；
- `pubmed_only`：教材下载被关闭或没有本地语料。

检索器并发执行后使用 RRF 融合，并按内容去重和关键词相关性过滤。同步 BM25
操作在线程池运行，PubMed 使用异步 HTTP。Chroma 适配器因 CVE-2026-45829
暂停进入默认依赖和运行链路，待上游发布修复版本后恢复。

## 生成控制

只有完整 LLM 生成链路占用生成名额。默认同时运行 3 个生成，额外允许 6 个请求排队
5 秒；登录、健康检查和统计不占生成名额。

## 安全边界

- 问答和统计接口需要登录；
- Cookie 使用签名、HttpOnly、SameSite=Lax；
- 生产 HTTPS 必须启用 Secure Cookie；
- CORS 只允许显式来源；
- 输入长度和历史总量受限；
- 上游错误转换为不含凭证的结构化错误；
- 第三方或私有数据保存在运行时卷，不进入公共镜像。
