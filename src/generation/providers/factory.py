"""LLM provider factory."""

from __future__ import annotations

from ...config import config
from .anthropic_native import AnthropicProvider
from .base import LLMProvider
from .openai_compatible import OpenAICompatibleProvider


def create_provider() -> LLMProvider:
    if config.LLM_PROVIDER == "openai_compatible":
        return OpenAICompatibleProvider()
    if config.LLM_PROVIDER == "anthropic":
        return AnthropicProvider()
    raise RuntimeError(f"不支持的 LLM_PROVIDER: {config.LLM_PROVIDER}")
