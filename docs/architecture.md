# 架构

## 请求路径

```text
Browser
  -> signed HttpOnly session cookie
  -> FastAPI /api/ask
  -> generation queue
  -> request-scoped history
  -> query understanding and route selection
  -> BM25 / Chroma / PubMed retrieval
  -> configured LLM provider
  -> citation mapping
  -> structured response with request_id and timings
```

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

- `local_and_pubmed`：本地 BM25/Chroma 至少有一个包含文档，同时使用 PubMed；
- `pubmed_only`：公开安装的默认模式，没有本地受限语料。

检索器并发执行后使用 RRF 融合，并按内容去重和关键词相关性过滤。同步 BM25 与
Chroma 操作在线程池运行，PubMed 使用异步 HTTP。

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
- 私有数据通过运行时卷挂载，不进入公共镜像。
