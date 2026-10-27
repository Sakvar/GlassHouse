from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Personality(BaseModel):
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    jealousy: float = Field(default=0.5, ge=0.0, le=1.0)
    impulsivity: float = Field(default=0.5, ge=0.0, le=1.0)
    trustfulness: float = Field(default=0.5, ge=0.0, le=1.0)
    competitiveness: float = Field(default=0.5, ge=0.0, le=1.0)


class AvariceProfile(BaseModel):
    """Stable preferences plus the mutable history used to price audience offers."""

    material_drive: float = Field(default=0.5, ge=0.0, le=1.0)
    reward_salience: float = Field(default=0.5, ge=0.0, le=1.0)
    status_drive: float = Field(default=0.5, ge=0.0, le=1.0)
    autonomy: float = Field(default=0.5, ge=0.0, le=1.0)
    moral_cost_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    reputation_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    bargain_tendency: float = Field(default=0.5, ge=0.0, le=1.0)
    retaliation_tendency: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_reward_multiplier: float = Field(default=1.0, ge=0.0, le=2.0)
    base_refusal_chance: float = Field(default=0.35, ge=0.0, le=1.0)
    max_daily_benefit: int = Field(default=5, ge=0, le=100)
    accumulated_benefit: int = Field(default=0, ge=0)
    benefit_day: str = ""
    accepted_offer_count: int = Field(default=0, ge=0)
    broken_promise_count: int = Field(default=0, ge=0)
    price_memory: dict[str, int] = Field(default_factory=dict)


class ViewerRelation(BaseModel):
    trust: float = Field(default=0.0, ge=-100.0, le=100.0)
    affinity: float = Field(default=0.0, ge=-100.0, le=100.0)
    resentment: float = Field(default=0.0, ge=0.0, le=100.0)
    reliability: float = Field(default=0.0, ge=-100.0, le=100.0)
    last_interaction_tick: int = Field(default=0, ge=0)
    accepted_count: int = Field(default=0, ge=0)
    rejected_count: int = Field(default=0, ge=0)


class ReputationState(BaseModel):
    public_reliability: float = Field(default=50.0, ge=0.0, le=100.0)
    audience_respect: float = Field(default=50.0, ge=0.0, le=100.0)
    promises_kept: int = Field(default=0, ge=0)
    promises_broken: int = Field(default=0, ge=0)


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
