"""
BM25 关键词检索模块
"""

import json
import logging
import os
import numpy as np
from rank_bm25 import BM25Okapi
from typing import List, Dict
from ..config import config


logger = logging.getLogger(__name__)


class BM25Retriever:
    """BM25 关键词检索"""

    def __init__(self):
        """初始化 BM25 检索器"""
        self.corpus = []
        self.documents = []
        self.tokenized_corpus = []
        self.doc_map = {}
        self.bm25 = None
        self._load_corpus()

    def _load_corpus(self):
        """加载语料库"""
        if not config.TEXTBOOKS_ENABLED:
            logger.warning("Local textbook retrieval is disabled")
            return

        corpus_dir = os.path.join(config.TEXTBOOKS_CORPUS_DIR, "chunk")
        legacy_corpus_dir = os.path.join(
            config.LEGACY_TEXTBOOKS_CORPUS_DIR,
            "chunk",
        )
        if not os.path.exists(corpus_dir) and os.path.exists(legacy_corpus_dir):
            logger.warning(
                "Using legacy textbook corpus path: %s; migrate to %s",
                legacy_corpus_dir,
                corpus_dir,
            )
            corpus_dir = legacy_corpus_dir

        if not os.path.exists(corpus_dir):
            logger.warning("BM25 corpus directory is missing: %s", corpus_dir)
            return

        logger.info("Loading BM25 corpus")

        for fname in sorted(os.listdir(corpus_dir)):
            if not fname.endswith(".jsonl"):
                continue

            fpath = os.path.join(corpus_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            doc = json.loads(line)
                            doc_id = doc.get("id", "")
                            content = doc.get("content", "")

                            self.doc_map[doc_id] = doc
                            self.documents.append(doc)
                            self.corpus.append(content)
                            self.tokenized_corpus.append(content.lower().split())
            except Exception as e:
                logger.warning("Failed to load BM25 file %s: %s", fname, type(e).__name__)
                continue

        # 构建 BM25 索引
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info("BM25 corpus ready: chunks=%s", len(self.corpus))
        else:
            logger.warning("BM25 corpus is empty")

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        BM25 搜索

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            搜索结果列表
        """
        if not self.bm25:
            return []

        # 分词（支持中英文混合）
        # 将中文和英文分开处理
        import re
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]+', query.lower())
        # 提取中文字符（作为整体）
        chinese_chars = re.findall(r'[一-鿿]+', query)
        # 组合分词结果
        tokenized_query = english_words + chinese_chars

        # 如果分词结果为空，使用原始查询
        if not tokenized_query:
            tokenized_query = query.lower().split()

        # 计算分数
        scores = self.bm25.get_scores(tokenized_query)

        # 获取排序后的索引（按分数降序）
        sorted_indices = np.argsort(scores)[::-1]

        # 过滤和格式化结果
        results = []
        seen_content = set()  # 用于去重
        min_score_threshold = 0.1  # 降低最低分数阈值（中文匹配分数通常较低）
        min_content_length = 50  # 最小内容长度

        for idx in sorted_indices:
            # 跳过低分结果
            if scores[idx] < min_score_threshold:
                continue

            # 跳过无效索引
            if idx >= len(self.corpus):
                continue

            content = self.corpus[idx]

            # 跳过过短的内容
            if len(content) < min_content_length:
                continue

            # 去重（检查内容前100字符）
            content_key = content[:100].strip()
            if content_key in seen_content:
                continue
            seen_content.add(content_key)

            # 获取文档ID和元数据
            doc_info = self.documents[idx] if idx < len(self.documents) else {}
            doc_id = doc_info.get("id", str(idx))

            # 提取标题（从metadata或content第一行）
            title = doc_info.get("title", "")
            if not title:
                # 从content提取第一行作为标题
                first_line = content.split("\n")[0][:100].strip()
                title = first_line if first_line else "医学文献"

            # 从 doc_id 中提取 source（格式如 "Anatomy_Gray_0"）
            # 移除最后的数字编号
            source = "_".join(doc_id.split("_")[:-1]) if doc_id.split("_")[-1].isdigit() else doc_id
            if not source:
                source = doc_info.get("source", "Textbooks")

            results.append({
                "id": doc_id,
                "content": content,
                "title": title,
                "score": float(scores[idx]),
                "source": source,
            })

            # 达到数量限制
            if len(results) >= top_k:
                break

        return results

    def stats(self) -> Dict:
        """Return cheap, already-loaded corpus statistics."""
        sources = {
            "_".join(doc_id.split("_")[:-1])
            if doc_id.split("_")[-1].isdigit()
            else doc_id
            for doc_id in self.doc_map
            if doc_id
        }
        return {
            "chunks": len(self.corpus),
            "sources": len(sources),
            "available": self.bm25 is not None,
        }
