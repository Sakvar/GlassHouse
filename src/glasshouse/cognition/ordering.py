from __future__ import annotations

from glasshouse.cognition.triggers import CognitionTrigger


def trigger_sort_key(trigger: CognitionTrigger) -> tuple[int, int, str]:
    return (trigger.tick, trigger.priority, trigger.agent_id)


def sort_triggers(triggers: list[CognitionTrigger]) -> list[CognitionTrigger]:
    return sorted(triggers, key=trigger_sort_key)
