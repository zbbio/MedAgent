import asyncio

import pytest

from src.agent.core import MedAgent
from src.config import Config
from src.generation.citation import CitationGenerator


def _valid_config() -> Config:
    value = Config()
    value.ACCESS_PASSWORD = "a-strong-demo-password"
    value.SESSION_SECRET = "s" * 48
    value.LLM_PROVIDER = "openai_compatible"
    value.LLM_REQUIRE_API_KEY = True
    value.LLM_API_KEY = "unit-test-key"
    value.LLM_BASE_URL = "https://api.example.test/v1"
    value.LLM_MODEL = "unit-test-model"
    value.LLM_TOKEN_PARAMETER = "max_tokens"
    return value


@pytest.mark.parametrize(
    ("field", "placeholder"),
    [
        ("ACCESS_PASSWORD", "replace_with_a_strong_password"),
        ("SESSION_SECRET", "replace_with_at_least_32_random_bytes"),
        ("LLM_API_KEY", "replace_with_your_own_api_key"),
        ("LLM_MODEL", "replace_with_your_model_name"),
        ("LLM_BASE_URL", "https://api.example.com/v1"),
    ],
)
def test_startup_rejects_example_placeholders(field, placeholder):
    value = _valid_config()
    setattr(value, field, placeholder)

    with pytest.raises(RuntimeError, match="占位"):
        value.validate_startup()


def test_startup_enforces_auth_secret_strength():
    value = _valid_config()
    value.ACCESS_PASSWORD = "short"
    with pytest.raises(RuntimeError, match="12"):
        value.validate_startup()

    value = _valid_config()
    value.SESSION_SECRET = "too-short"
    with pytest.raises(RuntimeError, match="32"):
        value.validate_startup()


class _FakeQueryUnderstander:
    async def understand(self, question, history):
        return {
            "rewritten_query": question,
            "needs_retrieval": True,
            "complexity": "简单",
        }


class _FakeRouter:
    def __init__(self, route="single_retrieval"):
        self.calls = 0
        self.result = route

    def route(self, understanding):
        self.calls += 1
        return self.result


class _FakeRetriever:
    def __init__(self):
        self.calls = 0

    async def retrieve(self, query, k):
        self.calls += 1
        return []


class _FakeLLM:
    async def generate(self, *args, **kwargs):
        return "direct answer"

    async def generate_json(self, *args, **kwargs):
        return {"content": "retrieval answer", "thinking": ""}


class _FakeCitationGenerator:
    async def generate(self, answer, snippets):
        return []


def _agent_with_fakes() -> MedAgent:
    agent = MedAgent.__new__(MedAgent)
    agent.query_understander = _FakeQueryUnderstander()
    agent.router = _FakeRouter()
    agent.retriever = _FakeRetriever()
    agent.llm = _FakeLLM()
    agent.citation_gen = _FakeCitationGenerator()
    return agent


def test_use_rag_false_never_retrieves():
    agent = _agent_with_fakes()

    result = asyncio.run(agent.answer("test", use_rag=False))

    assert result["route"] == "direct_generation"
    assert agent.router.calls == 0
    assert agent.retriever.calls == 0


def test_use_rag_true_uses_adaptive_router():
    agent = _agent_with_fakes()

    result = asyncio.run(agent.answer("test", use_rag=True))

    assert result["route"] == "single_retrieval"
    assert agent.router.calls == 1
    assert agent.retriever.calls == 1


def test_use_rag_true_never_downgrades_to_direct_generation():
    agent = _agent_with_fakes()
    agent.router = _FakeRouter("direct_generation")

    result = asyncio.run(agent.answer("test", use_rag=True))

    assert result["route"] == "single_retrieval"
    assert agent.retriever.calls == 1


def test_numbered_pubmed_citation_preserves_source():
    generator = CitationGenerator(_FakeLLM())
    snippets = [
        {
            "title": "PubMed article",
            "content": "Abstract text",
            "source": "PubMed",
            "metadata": {"pmid": "123"},
        }
    ]

    citations = asyncio.run(
        generator.generate({"content": "Medical statement [1]."}, snippets)
    )

    assert citations[0]["source"] == "PubMed"
