from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from glasshouse.world.house import ADJACENCY
from glasshouse.world.models import (
    Activity,
    AgentRef,
    WorldEvent,
    WorldEventType,
    WorldState,
)

if TYPE_CHECKING:
    pass


def _new_event_id() -> str:
    return str(uuid.uuid4())


def move_agent(
    world: WorldState,
    agent_id: str,
    destination: str,
) -> tuple[WorldEvent, AgentRef]:
    agent = world.agents[agent_id]
    if destination not in world.locations:
        raise ValueError(f"Unknown location: {destination}")
    if destination not in ADJACENCY.get(agent.location_id, []) and destination != agent.location_id:
        if agent.location_id not in ADJACENCY.get(destination, []):
            raise ValueError(f"Cannot move from {agent.location_id} to {destination}")

    old_location = agent.location_id
    updated = agent.model_copy(update={"location_id": destination, "activity": Activity.WALKING})
    event = WorldEvent(
        id=_new_event_id(),
        tick=world.tick,
        type=WorldEventType.MOVE,
        actor=agent_id,
        target=destination,
        location=destination,
        payload={"from": old_location, "to": destination},
        witnesses=_witnesses_in_room(world, destination, exclude=agent_id),
    )
    return event, updated


def set_activity(
    world: WorldState,
    agent_id: str,
    activity: Activity,
) -> tuple[WorldEvent, AgentRef]:
    agent = world.agents[agent_id]
    event_type_map = {
        Activity.SLEEPING: WorldEventType.SLEEP,
        Activity.EATING: WorldEventType.EAT,
        Activity.COOKING: WorldEventType.COOK,
        Activity.SITTING: WorldEventType.SIT,
        Activity.WALKING: WorldEventType.WALK,
    }
    event_type = event_type_map.get(activity, WorldEventType.SIT)
    updated = agent.model_copy(update={"activity": activity})
    event = WorldEvent(
        id=_new_event_id(),
        tick=world.tick,
        type=event_type,
        actor=agent_id,
        location=agent.location_id,
        payload={"activity": activity.value},
    )
    return event, updated


def create_utterance_event(
    world: WorldState,
    speaker_id: str,
    claim_id: str,
    exact_text: str,
    volume: float = 0.7,
    target_id: str | None = None,
) -> WorldEvent:
    agent = world.agents[speaker_id]
    return WorldEvent(
        id=_new_event_id(),
        tick=world.tick,
        type=WorldEventType.UTTERANCE,
        actor=speaker_id,
        target=target_id,
        location=agent.location_id,
        payload={
            "claim_id": claim_id,
            "exact_text": exact_text,
            "volume": volume,
        },
        witnesses=_witnesses_in_room(world, agent.location_id, exclude=speaker_id),
    )


def create_truth_admission_event(
    world: WorldState,
    actor_id: str,
    claim_id: str,
    volume: float = 0.4,
    private: bool = True,
) -> WorldEvent:
    agent = world.agents[actor_id]
    witnesses = _witnesses_in_room(world, agent.location_id, exclude=actor_id)
    return WorldEvent(
        id=_new_event_id(),
        tick=world.tick,
        type=WorldEventType.TRUTH_ADMISSION,
        actor=actor_id,
        location=agent.location_id,
        payload={
            "claim_id": claim_id,
            "volume": volume,
            "private": private,
        },
        witnesses=witnesses,
    )


def _witnesses_in_room(
    world: WorldState, location_id: str, exclude: str | None = None
) -> list[str]:
    return [
        aid
        for aid, ref in world.agents.items()
        if ref.location_id == location_id and aid != exclude
    ]
