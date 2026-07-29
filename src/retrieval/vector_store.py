"""
ChromaDB 向量存储模块
"""

from typing import List, Dict, Optional
from ..config import config

try:
    import chromadb
except ImportError:  # Chroma is intentionally excluded from the default install.
    chromadb = None


class ChromaVectorStore:
    """ChromaDB 向量存储"""

    def __init__(self):
        """初始化 ChromaDB 客户端"""
        if chromadb is None:
            raise RuntimeError(
                "Chroma is disabled in the default build pending a security fix "
                "for CVE-2026-45829"
            )
        # 初始化 ChromaDB 客户端（持久化存储）
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIR
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        documents: List[Dict],
        embeddings: Optional[List[List[float]]] = None,
    ):
        """
        添加文档到向量数据库

        Args:
            documents: 文档列表，每个文档包含 id, content, metadata
            embeddings: 预计算的向量（可选）
        """
        ids = [doc["id"] for doc in documents]
        contents = [doc["content"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]

        if embeddings:
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        else:
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
            )

    def search(
        self,
        query: str,
        top_k: int = 10,
        where: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        搜索相似文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            where: 过滤条件

        Returns:
            搜索结果列表
        """
        kwargs = {
            "query_texts": [query],
            "n_results": top_k,
        }

        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        # 格式化结果
        formatted = []
        if results and results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                score = 0
                if results.get("distances") and results["distances"][0]:
                    score = 1 - results["distances"][0][i]

                formatted.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {},
                    "score": score,
                })

        return formatted

    def delete(self, ids: List[str]):
        """删除文档"""
        self.collection.delete(ids=ids)

    def count(self) -> int:
        """返回文档数量"""
        return self.collection.count()
