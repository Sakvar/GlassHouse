from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class LLMCallLogEntry(BaseModel):
    tick: int
    agent_id: str
    schema_name: str
    trigger_type: str
    predicates: list[str] = Field(default_factory=list)
    prompt_hash: str
    response_json: str


class LLMCallLogger:
    def __init__(self) -> None:
        self.entries: list[LLMCallLogEntry] = []

    def log(
        self,
        tick: int,
        agent_id: str,
        schema_name: str,
        trigger_type: str,
        predicates: list[str],
        prompt: str,
        response: BaseModel,
    ) -> None:
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        self.entries.append(
            LLMCallLogEntry(
                tick=tick,
                agent_id=agent_id,
                schema_name=schema_name,
                trigger_type=trigger_type,
                predicates=predicates,
                prompt_hash=prompt_hash,
                response_json=response.model_dump_json(),
            )
        )

    def to_dicts(self) -> list[dict[str, Any]]:
        return [e.model_dump() for e in self.entries]
