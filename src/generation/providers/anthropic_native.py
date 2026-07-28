"""Native Anthropic Messages API provider."""

from __future__ import annotations

import anthropic

from ...config import config
from .base import LLMServiceError, LLMTimeoutError


class AnthropicProvider:
    def __init__(self) -> None:
        client_options = {
            "api_key": config.LLM_API_KEY,
            "timeout": config.LLM_TIMEOUT_SECONDS,
            "max_retries": config.LLM_MAX_RETRIES,
        }
        if config.LLM_BASE_URL:
            client_options["base_url"] = config.LLM_BASE_URL
        self.client = anthropic.AsyncAnthropic(**client_options)

    async def close(self) -> None:
        await self.client.close()

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
    ) -> str:
        try:
            response = await self.client.messages.create(
                model=config.LLM_MODEL,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError() from exc
        except anthropic.AuthenticationError as exc:
            raise LLMServiceError(
                "模型鉴权失败，请检查部署配置",
                code="llm_authentication",
            ) from exc
        except anthropic.PermissionDeniedError as exc:
            raise LLMServiceError(
                "模型凭证无权访问当前模型",
                code="llm_permission",
            ) from exc
        except anthropic.NotFoundError as exc:
            raise LLMServiceError(
                "模型或接口地址无效",
                code="llm_not_found",
            ) from exc
        except anthropic.RateLimitError as exc:
            raise LLMServiceError(
                "模型服务当前限流，请稍后重试",
                code="llm_rate_limited",
                rate_limited=True,
            ) from exc
        except anthropic.BadRequestError as exc:
            raise LLMServiceError(
                "模型请求参数不兼容",
                code="llm_bad_request",
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMServiceError(
                "无法连接模型服务",
                code="llm_connection",
            ) from exc
        except anthropic.APIStatusError as exc:
            raise LLMServiceError(
                "模型服务暂时不可用",
                code="llm_upstream",
            ) from exc

        content = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        if not content:
            raise LLMServiceError("模型未返回可用文本", code="llm_empty_response")
        return content
