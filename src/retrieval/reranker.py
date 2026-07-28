"""
Cohere 重排模块
"""

from typing import List, Dict
from ..config import config


class CohereReranker:
    """Cohere 重排器"""

    def __init__(self):
        """初始化 Cohere 重排器"""
        self.api_key = config.COHERE_API_KEY
        self.client = None

        if self.api_key:
            try:
                import cohere
                self.client = cohere.Client(self.api_key)
            except ImportError:
                print("警告：未安装 cohere 包，重排功能将不可用")
            except Exception as e:
                print(f"初始化 Cohere 客户端失败: {e}")

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5,
    ) -> List[Dict]:
        """
        重排文档

        Args:
            query: 查询文本
            documents: 待重排的文档列表
            top_k: 返回的文档数量

        Returns:
            重排后的文档列表
        """
        if not documents:
            return []

        # 如果没有 Cohere API 或客户端，直接返回原文档
        if not self.client:
            return documents[:top_k]

        try:
            # 提取文档内容
            doc_texts = [doc.get("content", "") for doc in documents]

            # 调用 Cohere 重排 API
            response = self.client.rerank(
                query=query,
                documents=doc_texts,
                top_n=top_k,
                model="rerank-english-v2.0",
            )

            # 根据重排结果重新排序
            reranked = []
            for result in response.results:
                idx = result.index
                if idx < len(documents):
                    doc = documents[idx].copy()
                    doc["rerank_score"] = result.relevance_score
                    reranked.append(doc)

            return reranked

        except Exception as e:
            print(f"Cohere 重排失败: {e}")
            # 降级：返回原文档
            return documents[:top_k]
