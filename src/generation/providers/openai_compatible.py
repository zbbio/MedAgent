"""OpenAI Chat Completions compatible provider."""

from __future__ import annotations

import openai

from ...config import config
from .base import LLMServiceError, LLMTimeoutError


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.client = openai.AsyncOpenAI(
            api_key=config.LLM_API_KEY or "local-no-key",
            base_url=config.LLM_BASE_URL,
            timeout=config.LLM_TIMEOUT_SECONDS,
            max_retries=config.LLM_MAX_RETRIES,
        )

    async def close(self) -> None:
        await self.client.close()

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
    ) -> str:
        token_options = {config.LLM_TOKEN_PARAMETER: max_tokens}
        try:
            response = await self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                **token_options,
            )
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError() from exc
        except openai.AuthenticationError as exc:
            raise LLMServiceError(
                "模型鉴权失败，请检查部署配置",
                code="llm_authentication",
            ) from exc
        except openai.PermissionDeniedError as exc:
            raise LLMServiceError(
                "模型凭证无权访问当前模型",
                code="llm_permission",
            ) from exc
        except openai.NotFoundError as exc:
            raise LLMServiceError(
                "模型或接口地址无效",
                code="llm_not_found",
            ) from exc
        except openai.RateLimitError as exc:
            raise LLMServiceError(
                "模型服务当前限流，请稍后重试",
                code="llm_rate_limited",
                rate_limited=True,
            ) from exc
        except openai.BadRequestError as exc:
            raise LLMServiceError(
                "模型请求参数不兼容",
                code="llm_bad_request",
            ) from exc
        except openai.APIConnectionError as exc:
            raise LLMServiceError(
                "无法连接模型服务",
                code="llm_connection",
            ) from exc
        except openai.APIStatusError as exc:
            raise LLMServiceError(
                "模型服务暂时不可用",
                code="llm_upstream",
            ) from exc

        if not response.choices:
            raise LLMServiceError("模型未返回可用结果", code="llm_empty_response")
        content = response.choices[0].message.content
        if not content:
            raise LLMServiceError("模型未返回可用文本", code="llm_empty_response")
        return content.strip()
