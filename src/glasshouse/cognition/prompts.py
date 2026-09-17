from __future__ import annotations

from glasshouse.agents.state import AgentState
from glasshouse.cognition.triggers import CognitionTrigger


def build_prompt(agent: AgentState, trigger: CognitionTrigger) -> str:
    beliefs = [
        f"{b.subject}:{b.predicate.value}({b.confidence:.1f})"
        for b in agent.beliefs.entries.values()
    ]
    claims = [
        f"{c.subject}:{c.predicate.value}"
        for c in agent.claims.entries.values()
    ]
    return (
        f"Agent: {agent.name} ({agent.id})\n"
        f"Trigger: {trigger.trigger_type}\n"
        f"Mood: {agent.current.mood}\n"
        f"Location: {agent.ref.location_id}\n"
        f"Activity: {agent.ref.activity.value}\n"
        f"Beliefs: {', '.join(beliefs) or 'none'}\n"
        f"Claims: {', '.join(claims) or 'none'}\n"
        f"Context: {trigger.context}\n"
    )
