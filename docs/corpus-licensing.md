# MedAgent 语料与服务授权风险清单

## 当前事实

- MedAgent 支持从 `MedRAG/textbooks` Hugging Face 数据集下载固定版本。
- 上游数据集包含 `125,847` 个教材切片，不是 125,847 本教材或原始文档。
- 上游以18个 JSONL 文件发布，可识别出 18 个教材来源：
  Anatomy Gray、Biochemistry Lippincott、Cell Biology Alberts、First Aid Step 1、
  First Aid Step 2、Gynecology Novak、Histology Ross、Immunology Janeway、
  Harrison Internal Medicine、Adams Neurology、Williams Obstetrics、
  Robbins Pathology、Pathoma、Nelson Pediatrics、Katzung Pharmacology、
  Levy Physiology、DSM-5、Schwartz Surgery。
- 上游 Hugging Face 数据卡公开可访问，但没有填写明确的 `license`。
- MedRAG 代码的 Public Domain 声明不能自动改变第三方教材正文的版权状态。
- Chroma 集合当前为空；运行时主要使用本地 BM25 教材切片与实时 PubMed 检索。

## 风险结论

上述教材多数为受版权保护的商业出版物。仅拥有本地副本不等于拥有复制、制作衍生索引、
在线检索、向第三方展示片段或重新分发的权利。在取得逐项书面授权或替换为明确开放许可
语料前，授权状态统一标记为 **未确认**。

MedAgent 不把正文提交到 GitHub 或构建进镜像，而是由部署者明确确认风险后从上游固定
版本下载。`MEDRAG_TEXTBOOKS_ACCEPT_TERMS=true` 只记录这种确认，不构成许可证。

在未获得适用许可前，不应：

- 将下载后的 `data/`、索引文件或包含数据的 Docker 镜像再次分发；
- 在公开演示中展示可还原教材原文的长片段；
- 宣称这些语料已获得授权。

## LLM 服务限制

小米 MiMo Token Plan 当前官方条款说明：套餐仅用于 AI 编程工具，禁止以 API 调用形式
用于自动化脚本、自定义应用后端等明显非 Coding 场景。MedAgent 医学问答后端不属于
编程工具，因此 `tp-` Token Plan 密钥不能作为本项目的合规生产凭证。

上线前应使用允许自定义应用后端的按量付费 `sk-` 密钥，或取得小米的书面例外授权。

## 上线前必须完成

1. 向 MedRAG/MedQA 数据维护者确认数据许可范围，并为每个教材记录权利链。
2. 对无法证明授权的公开服务，改用 PubMed Central Open Access、政府公开指南等
   具有明确许可的来源。
3. 保留固定 revision、逐文件哈希、数据集引用和下载审计记录。
4. 由权利或法务负责人书面确认展示、检索和分发边界。
5. 使用允许医学问答应用后端的 LLM 商业凭证。
