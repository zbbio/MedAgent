"""Concurrent hybrid retrieval with BM25 and PubMed."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from ..config import config
from .bm25_retriever import BM25Retriever
from .pubmed_retriever import PubMedRetrievalError, PubMedRetriever


logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(self) -> None:
        self.bm25_retriever = BM25Retriever()
        self.pubmed_retriever = PubMedRetriever()
        self._pubmed_status = "ready"
        self.rrf_k = config.RRF_K

    async def close(self) -> None:
        await self.pubmed_retriever.close()

    async def retrieve(self, query: str, k: int | None = None) -> list[dict[str, Any]]:
        result_count = k or config.RETRIEVAL_TOP_K
        bm25_task = asyncio.to_thread(
            self.bm25_retriever.search,
            query,
            result_count * 2,
        )
        pubmed_task = self._retrieve_pubmed(query)
        bm25_results, pubmed_results = await asyncio.gather(
            bm25_task,
            pubmed_task,
        )
        fused = self._rrf_fusion([bm25_results, pubmed_results])
        return self._postprocess_results(fused, query, result_count)

    async def _retrieve_pubmed(self, query: str) -> list[dict[str, Any]]:
        try:
            results = await self.pubmed_retriever.search(
                query,
                max_results=config.PUBMED_MAX_RESULTS,
            )
        except PubMedRetrievalError as exc:
            self._pubmed_status = "degraded"
            logger.warning("PubMed degraded: %s", exc)
            return []
        self._pubmed_status = "ready"
        return results

    def stats(self) -> dict[str, Any]:
        bm25 = self.bm25_retriever.stats()
        vector_documents = 0
        local_documents = bm25["chunks"]
        return {
            "total_documents": local_documents,
            "bm25_chunks": bm25["chunks"],
            "textbook_sources": bm25["sources"],
            "vector_documents": vector_documents,
            "knowledge_mode": (
                "local_and_pubmed" if local_documents else "pubmed_only"
            ),
            "retrievers": {
                "bm25": "ready" if bm25["available"] else "unavailable",
                "pubmed": getattr(self, "_pubmed_status", "ready"),
                "chroma": "disabled_security_hold",
            },
        }

    def _postprocess_results(
        self,
        results: list[dict[str, Any]],
        query: str,
        k: int,
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique_results: list[dict[str, Any]] = []
        for document in results:
            content_key = document.get("content", "")[:100].strip()
            if content_key and content_key not in seen:
                seen.add(content_key)
                unique_results.append(document)

        query_keywords = set(re.findall(r"[一-鿿]+", query))
        query_keywords.update(re.findall(r"[a-zA-Z]+", query.lower()))
        scored_results = []
        for document in unique_results:
            content = document.get("content", "").lower()
            title = document.get("title", "").lower()
            matched = [keyword for keyword in query_keywords if keyword in content or keyword in title]
            if query_keywords and not matched:
                continue
            document["final_score"] = document.get("score", 0) * (1 + len(matched) * 0.2)
            document["matched_keywords"] = matched
            scored_results.append(document)

        scored_results.sort(key=lambda item: item.get("final_score", 0), reverse=True)
        return scored_results[:k]

    def _rrf_fusion(
        self,
        results_lists: list[list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        scores: dict[str, float] = {}
        documents: dict[str, dict[str, Any]] = {}
        for results in results_lists:
            for rank, document in enumerate(results):
                document_id = str(document.get("id") or document.get("content", "")[:50])
                scores[document_id] = scores.get(document_id, 0) + 1 / (
                    self.rrf_k + rank + 1
                )
                documents[document_id] = document
        sorted_ids = sorted(scores, key=scores.get, reverse=True)
        return [documents[document_id] for document_id in sorted_ids]
