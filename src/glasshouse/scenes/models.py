from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SceneStatus(StrEnum):
    ACTIVE = "active"
    COLLAPSED = "collapsed"
    SUMMARIZED = "summarized"


class Scene(BaseModel):
    id: int
    location: str
    participants: list[str] = Field(default_factory=list)
    observers: list[str] = Field(default_factory=list)
    topic: str | None = None
    tension: float = 0.0
    utterance_event_ids: list[str] = Field(default_factory=list)
    started_at: str = ""
    status: SceneStatus = SceneStatus.ACTIVE
    idle_turns: int = 0
    current_turn_index: int = 0


class SemanticChange(BaseModel):
    claims_changed: bool = False
    beliefs_changed: bool = False
    relationships_changed: bool = False
    topic_changed: bool = False
    tension_changed: bool = False

    def is_meaningful(self) -> bool:
        return any([
            self.claims_changed,
            self.beliefs_changed,
            self.relationships_changed,
            self.topic_changed,
            self.tension_changed,
        ])
