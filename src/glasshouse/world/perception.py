from __future__ import annotations

from enum import Enum

from glasshouse.world.house import distance_level
from glasshouse.world.models import AgentRef, WorldEvent, WorldEventType


class PerceptionLevel(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


def _event_volume(event: WorldEvent) -> float:
    return float(event.payload.get("volume", 0.5))


def compute_perception(
    event: WorldEvent,
    observer: AgentRef,
    event_location: str,
) -> PerceptionLevel:
    if not observer.capabilities.can_perceive:
        return PerceptionLevel.NONE

    dist = distance_level(observer.location_id, event_location)
    volume = _event_volume(event)

    if event.type in (WorldEventType.MOVE, WorldEventType.SLEEP, WorldEventType.EAT):
        if dist == "same_room":
            return PerceptionLevel.FULL if observer.attention >= 0.3 else PerceptionLevel.PARTIAL
        if dist == "adjacent" and observer.attention >= 0.7:
            return PerceptionLevel.PARTIAL
        return PerceptionLevel.NONE

    if event.type in (WorldEventType.UTTERANCE, WorldEventType.TRUTH_ADMISSION):
        effective_audibility = volume * observer.attention

        if dist == "same_room":
            if effective_audibility >= 0.5:
                return PerceptionLevel.FULL
            if effective_audibility >= 0.25:
                return PerceptionLevel.PARTIAL
            return PerceptionLevel.NONE

        if dist == "adjacent":
            adjacent_audibility = effective_audibility * 0.6
            if adjacent_audibility >= 0.45:
                return PerceptionLevel.PARTIAL
            if adjacent_audibility >= 0.2 and observer.attention >= 0.8:
                return PerceptionLevel.PARTIAL
            return PerceptionLevel.NONE

        return PerceptionLevel.NONE

    if dist == "same_room":
        return PerceptionLevel.FULL
    if dist == "adjacent" and observer.attention >= 0.6:
        return PerceptionLevel.PARTIAL
    return PerceptionLevel.NONE
