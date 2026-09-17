from __future__ import annotations

from glasshouse.agents.state import AgentState
from glasshouse.cognition.prompts import build_prompt
from glasshouse.cognition.triggers import CognitionTrigger
from glasshouse.cognition.validator import validate_intent
from glasshouse.llm.provider import LLMCallContext, LLMProvider, ModelTier
from glasshouse.llm.schemas import Intent
from glasshouse.memory.retrieval import retrieve_relevant


def should_run_cognition(agent: AgentState, trigger: CognitionTrigger) -> bool:
    if not agent.ref.capabilities.can_perceive and trigger.trigger_type == "overheard":
        return False
    if agent.ref.activity.value == "sleeping":
        return False
    return True


def run_cognition(
    agent: AgentState,
    trigger: CognitionTrigger,
    llm: LLMProvider,
    schema: type[Intent],
    world_locations: dict,
    model_tier: ModelTier = ModelTier.STANDARD,
) -> Intent | None:
    if not should_run_cognition(agent, trigger):
        return None

    prompt = build_prompt(agent, trigger)
    predicates = list(trigger.context.get("predicates", []))
    for claim in agent.claims.entries.values():
        predicates.append(claim.predicate.value)

    context = LLMCallContext(
        agent_id=agent.id,
        trigger_type=trigger.trigger_type,
        schema_name=schema.__name__,
        predicates=predicates,
        scene_id=trigger.context.get("scene_id"),
        participants=trigger.context.get("participants", []),
        target_id=trigger.context.get("target_id"),
        tick=trigger.tick,
    )

    retrieve_relevant(agent)
    result = llm.generate_structured(context, schema, model_tier, prompt)
    return validate_intent(agent, result, world_locations)
