"""Provider-neutral asynchronous LLM client."""

from __future__ import annotations

import json
import re
from typing import Any

from ..config import config
from .providers import LLMServiceError, LLMTimeoutError, create_provider


class LLMClient:
    """Provider-neutral generation and JSON parsing."""

    def __init__(self) -> None:
        self.provider = create_provider()
        self.model = config.LLM_MODEL
        self.max_tokens = config.MAX_TOKENS

    async def close(self) -> None:
        await self.provider.close()

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        return await self.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt or (
                "你是一个严谨的医学问答助手。请清晰回答问题，区分事实、"
                "推断和不确定性；不得伪造证据或引用。"
            ),
            max_tokens=max_tokens or self.max_tokens,
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        response = await self.generate(
            prompt + "\n\n请只输出有效 JSON，不要使用 Markdown 代码块。",
            system_prompt,
        )
        cleaned = response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise LLMServiceError("模型返回的 JSON 无法解析", code="llm_invalid_json")
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError as exc:
                raise LLMServiceError("模型返回的 JSON 无法解析", code="llm_invalid_json") from exc

        if not isinstance(parsed, dict):
            raise LLMServiceError("模型返回的数据结构无效", code="llm_invalid_json")
        return parsed
