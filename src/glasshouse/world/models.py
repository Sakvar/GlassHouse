from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Activity(str, Enum):
    SLEEPING = "sleeping"
    WALKING = "walking"
    EATING = "eating"
    COOKING = "cooking"
    SITTING = "sitting"
    IDLE = "idle"
    CONVERSING = "conversing"


class ActivityCapabilities(BaseModel):
    can_perceive: bool = True
    can_speak: bool = True
    interruptibility: float = Field(default=0.5, ge=0.0, le=1.0)


CAPABILITIES_BY_ACTIVITY: dict[Activity, ActivityCapabilities] = {
    Activity.SLEEPING: ActivityCapabilities(can_perceive=False, can_speak=False, interruptibility=0.0),
    Activity.WALKING: ActivityCapabilities(can_perceive=True, can_speak=False, interruptibility=0.2),
    Activity.EATING: ActivityCapabilities(can_perceive=True, can_speak=False, interruptibility=0.3),
    Activity.COOKING: ActivityCapabilities(can_perceive=True, can_speak=False, interruptibility=0.3),
    Activity.SITTING: ActivityCapabilities(can_perceive=True, can_speak=True, interruptibility=0.8),
    Activity.IDLE: ActivityCapabilities(can_perceive=True, can_speak=True, interruptibility=0.8),
    Activity.CONVERSING: ActivityCapabilities(can_perceive=True, can_speak=True, interruptibility=0.9),
}


def capabilities_for(activity: Activity) -> ActivityCapabilities:
    return CAPABILITIES_BY_ACTIVITY[activity]


class Location(BaseModel):
    id: str
    name: str
    connected_to: list[str] = Field(default_factory=list)


class AgentRef(BaseModel):
    agent_id: str
    location_id: str
    activity: Activity = Activity.IDLE
    attention: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def capabilities(self) -> ActivityCapabilities:
        return capabilities_for(self.activity)


class WorldEventType(str, Enum):
    MOVE = "move"
    SLEEP = "sleep"
    EAT = "eat"
    COOK = "cook"
    SIT = "sit"
    WALK = "walk"
    UTTERANCE = "utterance"
    TRUTH_ADMISSION = "truth_admission"
    AGENT_ENTERED = "agent_entered"
    SCENE_STARTED = "scene_started"
    SCENE_COLLAPSED = "scene_collapsed"


class WorldEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tick: int
    type: WorldEventType
    actor: str | None = None
    target: str | None = None
    location: str
    payload: dict[str, Any] = Field(default_factory=dict)
    witnesses: list[str] = Field(default_factory=list)


class WorldState(BaseModel):
    tick: int = 0
    sim_time: str = "2026-01-01T08:00:00"
    locations: dict[str, Location] = Field(default_factory=dict)
    agents: dict[str, AgentRef] = Field(default_factory=dict)
    events_log: list[WorldEvent] = Field(default_factory=list)

    def append_event(self, event: WorldEvent) -> None:
        self.events_log.append(event)

    def get_event(self, event_id: str) -> WorldEvent | None:
        for event in self.events_log:
            if event.id == event_id:
                return event
        return None
