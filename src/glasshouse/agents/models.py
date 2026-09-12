from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Personality(BaseModel):
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    jealousy: float = Field(default=0.5, ge=0.0, le=1.0)
    impulsivity: float = Field(default=0.5, ge=0.0, le=1.0)
    trustfulness: float = Field(default=0.5, ge=0.0, le=1.0)
    competitiveness: float = Field(default=0.5, ge=0.0, le=1.0)


class Needs(BaseModel):
    social: float = Field(default=0.5, ge=0.0, le=1.0)
    romantic: float = Field(default=0.5, ge=0.0, le=1.0)
    status: float = Field(default=0.5, ge=0.0, le=1.0)
    rest: float = Field(default=0.5, ge=0.0, le=1.0)


class Goals(BaseModel):
    today: str = ""
    medium_term: str = ""
    secret: str = ""


class CurrentState(BaseModel):
    mood: str = "neutral"
    fatigue: float = Field(default=0.3, ge=0.0, le=1.0)
    plan: str = ""


class SocialBoundaries(BaseModel):
    """Mutual, explicit preferences; an empty partner list means no romance."""

    romantic_partners: tuple[str, ...] = ()
    romance_allowed: bool = True
    private_conversation_allowed: bool = True
    secret_sharing_allowed: bool = True
    blocked_characters: tuple[str, ...] = ()
    minimum_trust: float = Field(default=20, ge=-100, le=100)
    minimum_affinity: float = Field(default=10, ge=-100, le=100)
    minimum_attraction: float = Field(default=30, ge=-100, le=100)


class SecretFact(BaseModel):
    """An explicit world-seed fact, separate from a character's private ambitions."""

    model_config = ConfigDict(frozen=True)
    id: str
    other_character_id: str
    # The first season supports a single factual secret, with a fixed safe template.
    predicate: Literal["borrowed_money_unrepaid"] = "borrowed_money_unrepaid"
