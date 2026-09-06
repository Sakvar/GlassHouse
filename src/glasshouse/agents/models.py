from __future__ import annotations

from pydantic import BaseModel, Field


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
