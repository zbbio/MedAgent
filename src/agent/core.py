"""Stateless asynchronous MedAgent orchestration."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from ..generation.citation import CitationGenerator
from ..generation.llm_client import LLMClient
from ..retrieval.hybrid import HybridRetriever
from ..understanding.query_rewriter import QueryUnderstander
from ..understanding.router import AdaptiveRouter


class MedAgent:
    """A stateless RAG agent. Conversation history belongs to each request."""

    def __init__(self) -> None:
        self.retriever = HybridRetriever()
        self.llm = LLMClient()
        self.query_understander = QueryUnderstander(self.llm)
        self.router = AdaptiveRouter(self.llm)
        self.citation_gen = CitationGenerator(self.llm)

    async def close(self) -> None:
        await self.llm.close()
        await self.retriever.close()

    async def answer(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        use_rag: bool = True,
    ) -> dict[str, Any]:
        started = perf_counter()
        timings: dict[str, float] = {}
        request_history = list(history or [])

        if use_rag:
            step = perf_counter()
            understanding = await self.query_understander.understand(
                question=question,
                history=request_history,
            )
            timings["understanding_ms"] = _elapsed_ms(step)
            route = self.router.route(understanding)
            if route == "direct_generation":
                route = "single_retrieval"
        else:
            understanding = {"rewritten_query": question}
            timings["understanding_ms"] = 0.0
            route = "direct_generation"
        snippets: list[dict[str, Any]] = []

        step = perf_counter()
        if route == "direct_generation":
            timings["retrieval_ms"] = 0.0
            answer = await self._direct_generate(question, request_history)
        elif route == "single_retrieval":
            snippets = await self.retriever.retrieve(
                query=understanding["rewritten_query"],
                k=10,
            )
            timings["retrieval_ms"] = _elapsed_ms(step)
            step = perf_counter()
            answer = await self._generate_with_context(question, snippets, request_history)
        else:
            snippets = await self._multi_hop_retrieval(
                question,
                understanding,
                request_history,
            )
            timings["retrieval_ms"] = _elapsed_ms(step)
            step = perf_counter()
            answer = await self._generate_with_context(question, snippets, request_history)
        timings["generation_ms"] = _elapsed_ms(step)

        step = perf_counter()
        citations = await self.citation_gen.generate(answer, snippets)
        timings["citation_ms"] = _elapsed_ms(step)
        timings["total_ms"] = _elapsed_ms(started)

        return {
            "answer": answer.get("content", "") if isinstance(answer, dict) else answer,
            "thinking": answer.get("thinking", "") if isinstance(answer, dict) else "",
            "citations": citations,
            "snippets": snippets,
            "route": route,
            "timings": timings,
        }

    async def _direct_generate(
        self,
        question: str,
        history: list[dict[str, str]],
    ) -> dict[str, str]:
        prompt = f"""你是一个专业的医学助手。请回答以下问题。

历史对话：
{self._format_history(history)}

问题：{question}

请提供专业、准确的回答。"""
        return {"content": await self.llm.generate(prompt), "thinking": ""}

    async def _generate_with_context(
        self,
        question: str,
        snippets: list[dict[str, Any]],
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        context = self._format_snippets(snippets)
        prompt = f"""你是一个专业的医学助手。请严格依据参考资料回答问题。

参考资料：
{context}

历史对话：
{self._format_history(history)}

问题：{question}

要求：
1. 参考资料不足时明确说明，不要编造；
2. 回答中的医学事实用 [1]、[2] 等标注来源；
3. 不输出内部推理过程，只给出简短的依据摘要；
4. 仅输出以下 JSON：
{{
    "thinking": "简短依据摘要",
    "content": "最终回答"
}}"""
        result = await self.llm.generate_json(prompt)
        if not isinstance(result.get("content"), str) or not result["content"].strip():
            raise ValueError("模型回答缺少 content 字段")
        return result

    async def _multi_hop_retrieval(
        self,
        question: str,
        understanding: dict[str, Any],
        history: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        snippets = await self.retriever.retrieve(
            query=understanding["rewritten_query"],
            k=10,
        )
        if await self._need_more_info(question, snippets):
            queries = await self._generate_supplementary_queries(
                question,
                snippets,
                history,
            )
            for query in queries[:3]:
                snippets.extend(await self.retriever.retrieve(query, k=5))
            snippets = self._deduplicate(snippets)
        return snippets

    async def _need_more_info(
        self,
        question: str,
        snippets: list[dict[str, Any]],
    ) -> bool:
        prompt = f"""判断参考资料是否足够回答问题。

问题：{question}

参考资料：
{self._format_snippets(snippets[:5])}

只回答“是”或“否”：是否需要更多信息？"""
        return "是" in await self.llm.generate(prompt, max_tokens=16)

    async def _generate_supplementary_queries(
        self,
        question: str,
        snippets: list[dict[str, Any]],
        history: list[dict[str, str]],
    ) -> list[str]:
        prompt = f"""基于已有信息生成 2-3 个英文补充检索词，每行一个。

原始问题：{question}
历史对话：{self._format_history(history)}
已有信息：
{self._format_snippets(snippets[:3])}"""
        response = await self.llm.generate(prompt, max_tokens=256)
        return [line.strip(" -0123456789.") for line in response.splitlines() if line.strip()]

    @staticmethod
    def _format_history(history: list[dict[str, str]]) -> str:
        if not history:
            return "无"
        return "\n".join(
            f"{'用户' if item['role'] == 'user' else '助手'}: {item['content']}"
            for item in history
        )

    @staticmethod
    def _format_snippets(snippets: list[dict[str, Any]]) -> str:
        if not snippets:
            return "未检索到相关资料"
        return "\n\n".join(
            f"[{index}] {snippet.get('title', '无标题')}\n{snippet.get('content', '')}"
            for index, snippet in enumerate(snippets, start=1)
        )

    @staticmethod
    def _deduplicate(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for snippet in snippets:
            key = str(snippet.get("id") or snippet.get("content", "")[:100])
            if key not in seen:
                seen.add(key)
                unique.append(snippet)
        return unique


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)
