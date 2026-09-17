from __future__ import annotations

from glasshouse.agents.state import AgentState
from glasshouse.llm.schemas import Intent, IntentType, UtteranceIntent
from glasshouse.world.house import ADJACENCY
from glasshouse.world.models import Activity


class ValidationError(Exception):
    pass


def validate_intent(agent: AgentState, intent: Intent, world_locations: dict) -> Intent:
    caps = agent.ref.capabilities

    if intent.intent_type == IntentType.SPEAK:
        if not caps.can_speak and agent.ref.activity != Activity.CONVERSING:
            raise ValidationError(f"Agent {agent.id} cannot speak while {agent.ref.activity.value}")
        if isinstance(intent, UtteranceIntent) and intent.claim is None:
            raise ValidationError("Utterance must include a structured claim")

    if intent.intent_type == IntentType.MOVE:
        dest = intent.target
        if dest and dest not in world_locations:
            raise ValidationError(f"Unknown destination: {dest}")
        current = agent.ref.location_id
        if dest and dest != current:
            connected = ADJACENCY.get(current, [])
            if dest not in connected:
                raise ValidationError(f"Cannot teleport from {current} to {dest}")

    if intent.intent_type == IntentType.START_CONVERSATION:
        if not caps.can_speak and agent.ref.activity != Activity.CONVERSING:
            raise ValidationError(f"Agent {agent.id} cannot start conversation")

    if agent.ref.activity == Activity.SLEEPING:
        raise ValidationError(f"Agent {agent.id} is sleeping")

    return intent
