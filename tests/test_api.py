import time

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config import config
from src.generation.llm_client import LLMServiceError


class FakeRetriever:
    def stats(self):
        return {
            "total_documents": 125847,
            "bm25_chunks": 125847,
            "textbook_sources": 18,
            "vector_documents": 0,
            "knowledge_mode": "local_and_pubmed",
            "retrievers": {
                "bm25": "ready",
                "pubmed": "ready",
                "chroma": "disabled_security_hold",
            },
        }


class FakeAgent:
    def __init__(self, *, error=None, delay=0):
        self.retriever = FakeRetriever()
        self.histories = []
        self.error = error
        self.delay = delay

    async def answer(self, question, history, use_rag):
        import asyncio

        self.histories.append(history)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return {
            "answer": f"answer:{question}",
            "thinking": "evidence",
            "citations": [],
            "route": "single_retrieval",
            "timings": {
                "understanding_ms": 1.0,
                "retrieval_ms": 2.0,
                "generation_ms": 3.0,
                "citation_ms": 1.0,
                "total_ms": 7.0,
            },
        }

    async def close(self):
        return None


def make_client(monkeypatch, agent=None):
    monkeypatch.setattr(config, "ACCESS_PASSWORD", "test-password")
    monkeypatch.setattr(config, "SESSION_SECRET", "test-session-secret-with-enough-entropy")
    monkeypatch.setattr(config, "LLM_PROVIDER", "openai_compatible")
    monkeypatch.setattr(config, "LLM_API_KEY", "unit-test-key")
    monkeypatch.setattr(config, "LLM_BASE_URL", "https://api.example.test/v1")
    application = create_app(lambda: agent or FakeAgent(), validate_config=False)
    return TestClient(application)


def authenticate(client):
    response = client.post("/api/auth/login", json={"password": "test-password"})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_health_and_auth_boundaries(monkeypatch):
    with make_client(monkeypatch) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/auth/status").json() == {"authenticated": False}
        unauthorized = client.get("/api/stats")
        assert unauthorized.status_code == 401
        assert unauthorized.json()["error"]["code"] == "authentication_required"
        assert client.post("/api/auth/login", json={"password": "wrong"}).status_code == 401

        authenticate(client)
        assert client.get("/api/auth/status").json() == {"authenticated": True}
        assert client.get("/api/stats").status_code == 200

        client.post("/api/auth/logout")
        assert client.get("/api/auth/status").json() == {"authenticated": False}


def test_login_failures_are_rate_limited_and_success_resets(monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(config, "LOGIN_WINDOW_SECONDS", 60)
    with make_client(monkeypatch) as client:
        assert client.post("/api/auth/login", json={"password": "wrong-1"}).status_code == 401
        assert client.post("/api/auth/login", json={"password": "test-password"}).status_code == 200
        client.post("/api/auth/logout")

        assert client.post("/api/auth/login", json={"password": "wrong-2"}).status_code == 401
        assert client.post("/api/auth/login", json={"password": "wrong-3"}).status_code == 401

        blocked = client.post("/api/auth/login", json={"password": "test-password"})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "login_rate_limited"


def test_stats_report_real_corpus_dimensions(monkeypatch):
    with make_client(monkeypatch) as client:
        authenticate(client)
        stats = client.get("/api/stats").json()
        assert stats["bm25_chunks"] == 125847
        assert stats["textbook_sources"] == 18
        assert stats["vector_documents"] == 0
        assert stats["provider"] == "openai_compatible"
        assert stats["knowledge_mode"] == "local_and_pubmed"
        assert stats["generation"]["max_active"] == 3


def test_question_limits(monkeypatch):
    with make_client(monkeypatch) as client:
        authenticate(client)
        response = client.post(
            "/api/ask",
            json={"question": "x" * 2001, "history": [], "use_rag": True},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "question_too_long"

        history = [{"role": "user", "content": str(index)} for index in range(11)]
        response = client.post(
            "/api/ask",
            json={"question": "test", "history": history, "use_rag": True},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "history_too_long"


def test_request_histories_are_isolated(monkeypatch):
    agent = FakeAgent()
    with make_client(monkeypatch, agent) as client:
        authenticate(client)
        first_history = [{"role": "user", "content": "Alice private context"}]
        first = client.post(
            "/api/ask",
            json={"question": "first", "history": first_history, "use_rag": True},
        )
        second = client.post(
            "/api/ask",
            json={"question": "second", "history": [], "use_rag": True},
        )
        assert first.status_code == second.status_code == 200
        assert agent.histories == [first_history, []]


def test_upstream_error_is_safe_and_structured(monkeypatch):
    agent = FakeAgent(error=LLMServiceError("模型服务当前限流", rate_limited=True))
    with make_client(monkeypatch, agent) as client:
        authenticate(client)
        response = client.post(
            "/api/ask",
            json={"question": "test", "history": [], "use_rag": False},
        )
        assert response.status_code == 503
        payload = response.json()["error"]
        assert payload["code"] == "llm_unavailable"
        assert payload["request_id"]


def test_request_timeout_maps_to_504(monkeypatch):
    agent = FakeAgent(delay=0.05)
    monkeypatch.setattr(config, "REQUEST_TIMEOUT_SECONDS", 0.01)
    with make_client(monkeypatch, agent) as client:
        authenticate(client)
        started = time.perf_counter()
        response = client.post(
            "/api/ask",
            json={"question": "test", "history": [], "use_rag": False},
        )
        assert time.perf_counter() - started < 1
        assert response.status_code == 504
        assert response.json()["error"]["code"] == "request_timeout"


def test_token_plan_is_blocked_for_medical_backend(monkeypatch):
    with make_client(monkeypatch) as client:
        authenticate(client)
        monkeypatch.setattr(config, "LLM_API_KEY", "tp-token-plan-test")
        monkeypatch.setattr(
            config,
            "LLM_BASE_URL",
            "https://token-plan-sgp.xiaomimimo.com/v1",
        )
        response = client.post(
            "/api/ask",
            json={"question": "test", "history": [], "use_rag": False},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "llm_credential_not_authorized"
