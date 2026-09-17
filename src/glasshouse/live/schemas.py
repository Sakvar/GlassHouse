from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Locale = Literal["ru", "en"]


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NarratedRecap(PublicModel):
    headline: str = Field(min_length=3, max_length=120)
    what_happened: str = Field(min_length=3, max_length=700)
    why_it_matters: str = Field(min_length=3, max_length=400)
    teaser: str = Field(min_length=3, max_length=200)

    @field_validator("headline", "what_happened", "why_it_matters", "teaser", mode="before")
    @classmethod
    def normalize(cls, value):
        if not isinstance(value, str):
            raise ValueError("Expected text")
        return " ".join(value.split())


class Episode(NarratedRecap):
    tick: int
    locale: Locale
    outcome: str
    participants: tuple[str, ...]
    relationship_changes: list[dict[str, str | float]]
    sim_time: str
    story_goal_id: str | None
    narrated: bool = False


class Character(PublicModel):
    id: str
    name: str
    location: str
    activity: str
    mood: str


class SeasonView(PublicModel):
    season_id: str
    setting: str
    locale: Locale
    tick: int
    voting_tick: int
    tick_minutes: int
    influence_per_tick: int = 3
    sim_time: str
    revision: int
    next_tick_at: str
    characters: list[Character]
    latest_recap: Episode | None


class Goal(PublicModel):
    id: str
    title: str
    description: str
    category: str
    status: str
    tick: int
    votes: int
    eligible_characters: tuple[str, ...]
    locale: Locale


class GoalsView(PublicModel):
    goals: list[Goal]
    tick: int
    remaining: int | None


class Page(PublicModel):
    items: list[Episode]
    recaps: list[Episode]
    page: int
    limit: int
    total: int
    has_next: bool


class VoteInput(PublicModel):
    story_goal_id: str = Field(min_length=1, max_length=200)
    tick: int = Field(ge=1, strict=True)
    influence_points: int = Field(default=1, ge=1, le=3, strict=True)
    request_id: str = Field(min_length=16, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


class VoteReceipt(PublicModel):
    accepted: bool = True
    duplicate: bool = False
    tick: int
    remaining: int


class TickInput(PublicModel):
    ticks: int = Field(default=1, ge=1, le=100, strict=True)
    expected_revision: int = Field(ge=0, strict=True)


class Health(PublicModel):
    status: str


class Error(PublicModel):
    code: str
    message: str


class SessionView(PublicModel):
    csrf_token: str
    authenticated: bool
