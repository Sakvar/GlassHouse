from __future__ import annotations

from enum import StrEnum
from typing import Protocol, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class ModelTier(StrEnum):
    FAST = "fast"
    STANDARD = "standard"
    DIRECTOR = "director"


class LLMCallContext(BaseModel):
    agent_id: str
    trigger_type: str
    schema_name: str
    predicates: list[str] = Field(default_factory=list)
    scene_id: int | None = None
    participants: list[str] = Field(default_factory=list)
    target_id: str | None = None
    tick: int = 0


class LLMProvider(Protocol):
    def generate_structured(
        self,
        context: LLMCallContext,
        schema: type[T],
        model_tier: ModelTier,
        prompt: str = "",
    ) -> T: ...
