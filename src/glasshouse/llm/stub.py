from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from glasshouse.llm.logging import LLMCallLogger
from glasshouse.llm.provider import LLMCallContext, ModelTier

T = TypeVar("T", bound=BaseModel)


class UnexpectedLLMCallError(Exception):
    def __init__(self, message: str, context: LLMCallContext, remaining: int = 0) -> None:
        super().__init__(message)
        self.context = context
        self.remaining = remaining


class StubExpectation(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    description: str = ""
    match_fn_name: str = ""
    response: BaseModel

    def matches(self, context: LLMCallContext, schema: type[BaseModel], matcher: Callable) -> bool:
        return matcher(context, schema)


class ScriptedStubLLM:
    def __init__(
        self,
        expectations: list[tuple[Callable[[LLMCallContext, type], bool], BaseModel]],
        logger: LLMCallLogger | None = None,
    ) -> None:
        self._expectations = list(expectations)
        self._used: list[int] = []
        self.logger = logger or LLMCallLogger()

    def generate_structured(
        self,
        context: LLMCallContext,
        schema: type[T],
        model_tier: ModelTier,
        prompt: str = "",
    ) -> T:
        for i, (matcher, response) in enumerate(self._expectations):
            if i in self._used:
                continue
            if matcher(context, schema) and isinstance(response, schema):
                self._used.append(i)
                self.logger.log(
                    context.tick,
                    context.agent_id,
                    schema.__name__,
                    context.trigger_type,
                    context.predicates,
                    prompt,
                    response,
                )
                return response

        remaining = len(self._expectations) - len(self._used)
        raise UnexpectedLLMCallError(
            f"No stub for agent={context.agent_id} schema={schema.__name__} "
            f"trigger={context.trigger_type} predicates={context.predicates} "
            f"target={context.target_id}",
            context=context,
            remaining=remaining,
        )

    def assert_exhausted(self) -> None:
        if len(self._used) != len(self._expectations):
            unused = [
                i for i in range(len(self._expectations)) if i not in self._used
            ]
            raise AssertionError(f"Unused stub expectations at indices: {unused}")

    @property
    def call_count(self) -> int:
        return len(self._used)


class ReplayLLM:
    def __init__(self, log_entries: list[dict], logger: LLMCallLogger | None = None) -> None:
        self._entries = log_entries
        self._index = 0
        self.logger = logger or LLMCallLogger()

    def generate_structured(
        self,
        context: LLMCallContext,
        schema: type[T],
        model_tier: ModelTier,
        prompt: str = "",
    ) -> T:
        if self._index >= len(self._entries):
            raise UnexpectedLLMCallError("Replay log exhausted", context=context)
        entry = self._entries[self._index]
        self._index += 1
        return schema.model_validate_json(entry["response_json"])
