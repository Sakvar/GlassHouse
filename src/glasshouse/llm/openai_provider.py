from __future__ import annotations

import os
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from glasshouse.llm.logging import LLMCallLogger
from glasshouse.llm.provider import LLMCallContext, ModelTier

T = TypeVar("T", bound=BaseModel)

_TIER_ENV = {
    ModelTier.FAST: "LLM_MODEL_FAST",
    ModelTier.STANDARD: "LLM_MODEL_STANDARD",
    ModelTier.DIRECTOR: "LLM_MODEL_DIRECTOR",
}


class OpenAICompatibleProvider:
    def __init__(self, logger: LLMCallLogger | None = None) -> None:
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        self.logger = logger or LLMCallLogger()

    def _model_for_tier(self, tier: ModelTier) -> str:
        env_key = _TIER_ENV[tier]
        defaults = {
            ModelTier.FAST: "gpt-4o-mini",
            ModelTier.STANDARD: "gpt-4o",
            ModelTier.DIRECTOR: "gpt-4o",
        }
        return os.getenv(env_key, defaults[tier])

    def generate_structured(
        self,
        context: LLMCallContext,
        schema: type[T],
        model_tier: ModelTier,
        prompt: str = "",
    ) -> T:
        model = self._model_for_tier(model_tier)
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("LLM returned no parsed response")
        self.logger.log(
            context.tick,
            context.agent_id,
            schema.__name__,
            context.trigger_type,
            context.predicates,
            prompt,
            parsed,
        )
        return parsed
