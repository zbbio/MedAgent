# MedAgent 语料与服务授权风险清单

## 当前事实

- 本地 BM25 索引包含 `125,847` 个教材切片，不是 125,847 本教材或原始文档。
- 切片来自一个 `textbooks.jsonl` 文件，可识别出 18 个教材来源：
  Anatomy Gray、Biochemistry Lippincott、Cell Biology Alberts、First Aid Step 1、
  First Aid Step 2、Gynecology Novak、Histology Ross、Immunology Janeway、
  Harrison Internal Medicine、Adams Neurology、Williams Obstetrics、
  Robbins Pathology、Pathoma、Nelson Pediatrics、Katzung Pharmacology、
  Levy Physiology、DSM-5、Schwartz Surgery。
- 当前数据目录没有许可证、购买凭证、授权书、来源清单或可分发证明。
- Chroma 集合当前为空；运行时主要使用本地 BM25 教材切片与实时 PubMed 检索。

## 风险结论

上述教材多数为受版权保护的商业出版物。仅拥有本地副本不等于拥有复制、制作衍生索引、
在线检索、向第三方展示片段或重新分发的权利。在取得逐项书面授权或替换为明确开放许可
语料前，授权状态统一标记为 **未确认**。

因此当前项目只允许本机研究和代码验证，禁止：

- 公网部署包含这些切片或索引的服务；
- 将 `data/`、索引文件或包含数据的 Docker 镜像发给朋友、面试官或第三方；
- 在公开演示中展示可还原教材原文的长片段；
- 宣称这些语料已获得授权。

## LLM 服务限制

小米 MiMo Token Plan 当前官方条款说明：套餐仅用于 AI 编程工具，禁止以 API 调用形式
用于自动化脚本、自定义应用后端等明显非 Coding 场景。MedAgent 医学问答后端不属于
编程工具，因此 `tp-` Token Plan 密钥不能作为本项目的合规生产凭证。

上线前应使用允许自定义应用后端的按量付费 `sk-` 密钥，或取得小米的书面例外授权。

## 上线前必须完成

1. 为每个来源记录书名、版本、出版社、获取渠道、权利人及许可范围。
2. 删除无法证明授权的教材，或替换为 PubMed Central Open Access、政府公开指南等
   具有明确许可的来源。
3. 重新构建索引并记录数据集版本、文件哈希、清洗与去重规则。
4. 由权利或法务负责人书面确认展示、检索和分发边界。
5. 使用允许医学问答应用后端的 LLM 商业凭证。
