"""Asynchronous PubMed retrieval via NCBI E-utilities."""

from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from ..config import config


logger = logging.getLogger(__name__)


class PubMedRetriever:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or config.PUBMED_API_KEY
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.max_requests_per_second = 10 if self.api_key else 3
        self._request_times: list[float] = []
        self._throttle_lock = asyncio.Lock()
        self.client = httpx.AsyncClient(timeout=config.PUBMED_TIMEOUT_SECONDS)

    async def close(self) -> None:
        await self.client.aclose()

    async def _throttle(self) -> None:
        async with self._throttle_lock:
            now = monotonic()
            self._request_times = [item for item in self._request_times if now - item < 1]
            if len(self._request_times) >= self.max_requests_per_second:
                delay = 1 - (now - self._request_times[0])
                if delay > 0:
                    await asyncio.sleep(delay)
                now = monotonic()
                self._request_times = [item for item in self._request_times if now - item < 1]
            self._request_times.append(monotonic())

    async def search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        max_results = max_results or config.PUBMED_MAX_RESULTS
        try:
            pmids = await self._search_pubmed(query, max_results)
            if not pmids:
                return []
            articles = await self._fetch_articles(pmids)
            return self._format_results(articles, query)
        except (httpx.HTTPError, ET.ParseError, asyncio.TimeoutError) as exc:
            logger.warning("PubMed retrieval failed: %s", type(exc).__name__)
            return []

    async def _search_pubmed(self, query: str, max_results: int) -> list[str]:
        await self._throttle()
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmode": "xml",
            "retmax": max_results,
        }
        if self.api_key and len(self.api_key) >= 30:
            params["api_key"] = self.api_key
        response = await self.client.get(f"{self.base_url}/esearch.fcgi", params=params)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        return [element.text for element in root.findall(".//Id") if element.text]

    async def _fetch_articles(self, pmids: list[str]) -> list[dict[str, Any]]:
        if not pmids:
            return []
        await self._throttle()
        params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        if self.api_key and len(self.api_key) >= 30:
            params["api_key"] = self.api_key
        response = await self.client.get(f"{self.base_url}/efetch.fcgi", params=params)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        return [
            parsed
            for element in root.findall(".//PubmedArticle")
            if (parsed := self._parse_article(element)) is not None
        ]

    @staticmethod
    def _parse_article(article_element: ET.Element) -> dict[str, Any] | None:
        try:
            pmid = article_element.findtext(".//PMID", default="")
            title = "".join(article_element.find(".//ArticleTitle").itertext()) if article_element.find(".//ArticleTitle") is not None else ""
            abstract_parts = [
                "".join(element.itertext())
                for element in article_element.findall(".//Abstract/AbstractText")
            ]
            authors = []
            for author in article_element.findall(".//Author"):
                last_name = author.findtext("LastName", default="")
                first_name = author.findtext("ForeName", default="")
                name = " ".join(value for value in (first_name, last_name) if value)
                if name:
                    authors.append(name)
            journal = article_element.findtext(".//Journal/Title", default="")
            pub_date = article_element.findtext(".//PubDate/Year", default="")
            abstract = "\n".join(abstract_parts)
            return {
                "id": f"pubmed_{pmid}",
                "pmid": pmid,
                "title": title,
                "content": f"{title}\n\n{abstract}".strip(),
                "authors": authors,
                "journal": journal,
                "pub_date": pub_date,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _format_results(
        articles: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": article["id"],
                "content": article["content"],
                "title": article["title"],
                "score": 1.0,
                "source": "PubMed",
                "metadata": {
                    "pmid": article["pmid"],
                    "authors": article["authors"],
                    "journal": article["journal"],
                    "pub_date": article["pub_date"],
                    "url": article["url"],
                    "query": query,
                },
            }
            for article in articles
        ]

    async def get_article_by_pmid(self, pmid: str) -> dict[str, Any] | None:
        articles = await self._fetch_articles([pmid])
        return articles[0] if articles else None


async def search_pubmed(
    query: str,
    max_results: int = 5,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    retriever = PubMedRetriever(api_key=api_key)
    try:
        return await retriever.search(query, max_results)
    finally:
        await retriever.close()
