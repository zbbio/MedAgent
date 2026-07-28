"""Provider-neutral LLM interface and safe error types."""

from __future__ import annotations

from typing import Protocol


class LLMServiceError(RuntimeError):
    """Safe, classified upstream LLM error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "llm_unavailable",
        rate_limited: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.rate_limited = rate_limited


class LLMTimeoutError(LLMServiceError):
    def __init__(self) -> None:
        super().__init__("模型响应超时，请稍后重试", code="llm_timeout")


class LLMProvider(Protocol):
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
    ) -> str: ...

    async def close(self) -> None: ...
