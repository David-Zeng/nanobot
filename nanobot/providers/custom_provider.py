"""Direct OpenAI-compatible provider — bypasses LiteLLM."""

from __future__ import annotations

import uuid
from typing import Any

import json_repair
from loguru import logger
from openai import AsyncOpenAI, RateLimitError

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

_CAPACITY_PHRASES = ("maximum capacity", "try again later", "rate limit", "overloaded")


class CustomProvider(LLMProvider):

    def __init__(self, api_key: str = "no-key", api_base: str = "http://localhost:8000/v1", default_model: str = "default"):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        # Keep affinity stable for this provider instance to improve backend cache locality.
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={"x-session-affinity": uuid.uuid4().hex},
        )

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
                   model: str | None = None, max_tokens: int = 4096, temperature: float = 0.7,
                   reasoning_effort: str | None = None, fallback_models: list[str] | None = None) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "messages": self._sanitize_empty_content(messages),
            "max_tokens": max(1, max_tokens),
            "temperature": temperature,
        }
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")

        candidates = [model or self.default_model] + (fallback_models or [])
        last_err: Exception | None = None
        for candidate in candidates:
            try:
                result = self._parse(await self._client.chat.completions.create(model=candidate, **kwargs))
                if candidate != candidates[0]:
                    logger.info("Fallback model {} succeeded", candidate)
                return result
            except RateLimitError as e:
                logger.warning("Model {} rate-limited (429), trying next fallback", candidate)
                last_err = e
            except Exception as e:
                err_str = str(e).lower()
                if any(p in err_str for p in _CAPACITY_PHRASES):
                    logger.warning("Model {} at capacity, trying next fallback", candidate)
                    last_err = e
                else:
                    return LLMResponse(content=f"Error: {e}", finish_reason="error")

        return LLMResponse(content=f"Error: {last_err}", finish_reason="error")

    def _parse(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message
        tool_calls = [
            ToolCallRequest(id=tc.id, name=tc.function.name,
                            arguments=json_repair.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments)
            for tc in (msg.tool_calls or [])
        ]
        u = response.usage
        return LLMResponse(
            content=msg.content, tool_calls=tool_calls, finish_reason=choice.finish_reason or "stop",
            usage={"prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens, "total_tokens": u.total_tokens} if u else {},
            reasoning_content=getattr(msg, "reasoning_content", None) or None,
        )

    def get_default_model(self) -> str:
        return self.default_model

