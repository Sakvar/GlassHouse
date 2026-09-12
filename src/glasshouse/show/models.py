from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StoryCategory(str, Enum):
    CONVERSATION = "conversation"
    ROMANCE_OPPORTUNITY = "romance_opportunity"
    REVEAL_SECRET = "reveal_secret"
    CONFLICT = "conflict"
    RECONCILIATION = "reconciliation"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    SELECTED = "selected"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class RelationshipChange(FrozenModel):
    actor_id: str
    target_id: str
    dimension: Literal[
        "trust", "affinity", "resentment", "attraction", "respect", "fear", "dependency"
    ]
    before: float
    after: float


class StoryResult(FrozenModel):
    outcome: Literal[
        "conversation", "date", "refusal", "revelation", "disagreement", "reconciliation", "rest"
    ]
    reason: str
    text: str
    event_ids: tuple[str, ...] = ()
    relationship_changes: tuple[RelationshipChange, ...] = ()
    revealed_secret_ids: tuple[str, ...] = ()


class StoryGoal(FrozenModel):
    id: str
    title: str
    description: str
    category: StoryCategory
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: str
    closed_at: str | None = None
    tick: int = Field(ge=1, description="The upcoming tick this choice applies to")
    eligible_characters: tuple[str, str]
    votes: int = Field(default=0, ge=0)
    result: StoryResult | None = None
    locale: Literal["ru", "en"] = "ru"
    director_score: float = 0


class ViewerVote(FrozenModel):
    viewer_id: str = Field(min_length=1, max_length=100, pattern=r"^\S+$")
    story_goal_id: str = Field(min_length=1, max_length=200)
    tick: int = Field(ge=1, strict=True)
    influence_points: int = Field(default=1, ge=1, strict=True)


class Recap(FrozenModel):
    tick: int
    sim_time: str
    locale: Literal["ru", "en"] = "ru"
    what_happened: tuple[str, ...]
    why_it_matters: str
    relationship_changes: tuple[RelationshipChange, ...] = ()
    revealed_secret_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    story_goal_id: str | None = None


class ShowEvent(FrozenModel):
    """JSON is an immutable value; callers cannot mutate nested historical payloads."""

    id: str
    tick: int
    sim_time: str
    kind: Literal["goal_opened", "vote_cast", "goal_selected", "goal_closed", "recap"]
    source: Literal["director:v1", "viewer", "recap:v1"]
    cause_ids: tuple[str, ...] = ()
    data_json: str


class ShowConfig(FrozenModel):
    tick_minutes: int = Field(default=120, ge=1, le=1440, strict=True)
    influence_per_tick: int = Field(default=3, ge=1, le=100, strict=True)


class PublicCharacter(FrozenModel):
    id: str
    name: str
    location: str
    activity: str
    mood: str


class PublicSeason(FrozenModel):
    season_id: str = "villa-1"
    setting: str = "Вилла"
    tick: int
    voting_tick: int
    sim_time: str
    tick_minutes: int
    influence_per_tick: int
    characters: tuple[PublicCharacter, ...]
    latest_recap: Recap | None = None


class TimelineItem(FrozenModel):
    tick: int
    sim_time: str
    story_goal_id: str
    category: StoryCategory
    participants: tuple[str, str]
    result: StoryResult


class PublicTimeline(FrozenModel):
    items: tuple[TimelineItem, ...]
    recaps: tuple[Recap, ...]
