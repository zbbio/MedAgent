"""Central application configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _as_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _as_csv(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


class Config:
    """Environment-backed project configuration."""

    BASE_DIR = Path(__file__).resolve().parent.parent

    # LLM provider. Each deployment supplies its own credentials.
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible").strip().lower()
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
    LLM_REQUIRE_API_KEY = _as_bool("LLM_REQUIRE_API_KEY", True)
    LLM_TOKEN_PARAMETER = os.getenv("LLM_TOKEN_PARAMETER", "max_tokens").strip()
    LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))

    # Knowledge stores
    CHROMA_PERSIST_DIR = str(BASE_DIR / "data" / "index" / "chroma")
    CHROMA_COLLECTION = "medical_knowledge"
    MEDRAG_DB_DIR = str(BASE_DIR / "data" / "index" / "medrag")
    CORPUS_NAME = "textbooks"
    TEXTBOOKS_CORPUS_DIR = os.getenv(
        "TEXTBOOKS_CORPUS_DIR",
        str(Path(MEDRAG_DB_DIR) / CORPUS_NAME),
    )
    LEGACY_TEXTBOOKS_CORPUS_DIR = str(Path(MEDRAG_DB_DIR) / "MedCorp")
    TEXTBOOKS_ENABLED = _as_bool("TEXTBOOKS_ENABLED", True)
    TEXTBOOKS_AUTO_DOWNLOAD = _as_bool("TEXTBOOKS_AUTO_DOWNLOAD", False)
    MEDRAG_TEXTBOOKS_ACCEPT_TERMS = _as_bool(
        "MEDRAG_TEXTBOOKS_ACCEPT_TERMS",
        False,
    )
    RETRIEVER_NAME = "MedCPT"

    # Retrieval
    RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))
    RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))
    RRF_K = int(os.getenv("RRF_K", "60"))
    PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
    PUBMED_MAX_RESULTS = int(os.getenv("PUBMED_MAX_RESULTS", "5"))
    PUBMED_TIMEOUT_SECONDS = float(os.getenv("PUBMED_TIMEOUT_SECONDS", "15"))
    COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

    # Request protection
    MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "2000"))
    MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "10"))
    MAX_HISTORY_CHARS = int(os.getenv("MAX_HISTORY_CHARS", "20000"))
    MAX_CONCURRENT_GENERATIONS = int(os.getenv("MAX_CONCURRENT_GENERATIONS", "3"))
    MAX_PENDING_GENERATIONS = int(os.getenv("MAX_PENDING_GENERATIONS", "6"))
    QUEUE_WAIT_SECONDS = float(os.getenv("QUEUE_WAIT_SECONDS", "5"))
    REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))

    # Access control
    ACCESS_PASSWORD = os.getenv("MEDAGENT_ACCESS_PASSWORD", "")
    SESSION_SECRET = os.getenv("MEDAGENT_SESSION_SECRET", "")
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(12 * 60 * 60)))
    LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_WINDOW_SECONDS = float(os.getenv("LOGIN_WINDOW_SECONDS", "60"))
    COOKIE_SECURE = _as_bool("COOKIE_SECURE", False)
    CORS_ORIGINS = _as_csv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    )

    # HTTP server
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))

    def validate_startup(self, require_llm: bool = True) -> None:
        """Fail closed when production-critical secrets are missing."""
        missing: list[str] = []
        placeholders = {
            "replace_with_a_strong_password",
            "replace_with_at_least_32_random_bytes",
            "replace_with_your_own_api_key",
            "replace_with_your_anthropic_key",
            "replace_with_your_model_name",
            "replace_with_your_claude_model",
            "replace_with_your_local_model",
            "your-shared-demo-password",
            "at-least-32-random-bytes",
            "your-key",
            "your-model",
            "https://api.example.com/v1",
            "https://your-provider.example/v1",
        }
        supported_providers = {"openai_compatible", "anthropic"}
        if not self.ACCESS_PASSWORD:
            missing.append("MEDAGENT_ACCESS_PASSWORD")
        if not self.SESSION_SECRET:
            missing.append("MEDAGENT_SESSION_SECRET")
        if require_llm and self.LLM_PROVIDER not in supported_providers:
            raise RuntimeError(
                "不支持的 LLM_PROVIDER；可选值: openai_compatible, anthropic"
            )
        if require_llm and self.LLM_REQUIRE_API_KEY and not self.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if require_llm and self.LLM_PROVIDER == "openai_compatible" and not self.LLM_BASE_URL:
            missing.append("LLM_BASE_URL")
        if require_llm and not self.LLM_MODEL:
            missing.append("LLM_MODEL")
        configured_values = {
            "MEDAGENT_ACCESS_PASSWORD": self.ACCESS_PASSWORD,
            "MEDAGENT_SESSION_SECRET": self.SESSION_SECRET,
            "LLM_MODEL": self.LLM_MODEL if require_llm else "",
            "LLM_BASE_URL": self.LLM_BASE_URL if require_llm else "",
            "LLM_API_KEY": (
                self.LLM_API_KEY
                if require_llm and self.LLM_REQUIRE_API_KEY
                else ""
            ),
        }
        placeholder_fields = [
            name
            for name, value in configured_values.items()
            if value.strip().lower() in placeholders
        ]
        if placeholder_fields:
            raise RuntimeError(
                "以下配置仍是示例占位值: " + ", ".join(placeholder_fields)
            )
        if self.ACCESS_PASSWORD and len(self.ACCESS_PASSWORD) < 12:
            raise RuntimeError("MEDAGENT_ACCESS_PASSWORD 至少需要 12 个字符")
        if self.SESSION_SECRET and len(self.SESSION_SECRET.encode("utf-8")) < 32:
            raise RuntimeError("MEDAGENT_SESSION_SECRET 至少需要 32 字节")
        if self.LOGIN_MAX_ATTEMPTS < 1 or self.LOGIN_WINDOW_SECONDS <= 0:
            raise RuntimeError("登录限速配置必须为正数")
        if require_llm and self.LLM_TOKEN_PARAMETER not in {
            "max_tokens",
            "max_completion_tokens",
        }:
            raise RuntimeError(
                "LLM_TOKEN_PARAMETER 可选值: max_tokens, max_completion_tokens"
            )
        if missing:
            raise RuntimeError(f"缺少必需配置: {', '.join(missing)}")

    def llm_usage_is_authorized(self) -> bool:
        """Token Plan credentials are not licensed for a non-coding app backend."""
        return not (
            self.LLM_API_KEY.startswith("tp-")
            and "token-plan" in self.LLM_BASE_URL.lower()
        )


config = Config()
