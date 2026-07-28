import asyncio

from src.config import config
from src.generation.llm_client import LLMClient
from src.generation.providers.anthropic_native import AnthropicProvider
from src.generation.providers.factory import create_provider
from src.generation.providers.openai_compatible import OpenAICompatibleProvider
from src.retrieval.hybrid import HybridRetriever


def test_provider_factory_supports_openai_and_anthropic(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(config, "LLM_BASE_URL", "https://api.example.test/v1")

    monkeypatch.setattr(config, "LLM_PROVIDER", "openai_compatible")
    openai_provider = create_provider()
    assert isinstance(openai_provider, OpenAICompatibleProvider)
    asyncio.run(openai_provider.close())

    monkeypatch.setattr(config, "LLM_PROVIDER", "anthropic")
    anthropic_provider = create_provider()
    assert isinstance(anthropic_provider, AnthropicProvider)
    asyncio.run(anthropic_provider.close())


def test_default_system_prompt_is_provider_neutral(monkeypatch):
    class FakeProvider:
        def __init__(self):
            self.system_prompt = ""

        async def generate(self, prompt, system_prompt, max_tokens):
            self.system_prompt = system_prompt
            return "ok"

        async def close(self):
            return None

    provider = FakeProvider()
    monkeypatch.setattr(
        "src.generation.llm_client.create_provider",
        lambda: provider,
    )
    client = LLMClient()
    assert asyncio.run(client.generate("test")) == "ok"
    assert "MiMo" not in provider.system_prompt
    assert "不得伪造证据" in provider.system_prompt


def test_empty_local_stores_report_pubmed_only():
    class EmptyBM25:
        def stats(self):
            return {"chunks": 0, "sources": 0, "available": False}

    class EmptyVectorStore:
        def count(self):
            return 0

    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.bm25_retriever = EmptyBM25()
    retriever.vector_store = EmptyVectorStore()
    stats = retriever.stats()

    assert stats["knowledge_mode"] == "pubmed_only"
    assert stats["total_documents"] == 0
