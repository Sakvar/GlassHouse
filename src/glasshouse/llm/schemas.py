from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from glasshouse.cognition.beliefs import Belief
from glasshouse.cognition.claims import Claim, ClaimPredicate
from glasshouse.relationships.models import SemanticAppraisal


class IntentType(str, Enum):
    MOVE = "move"
    SPEAK = "speak"
    START_CONVERSATION = "start_conversation"
    IDLE = "idle"
    FORM_CLAIM = "form_claim"
    UPDATE_BELIEF = "update_belief"
    APPRAISE = "appraise"


class Intent(BaseModel):
    intent_type: IntentType
    target: str | None = None
    rationale: str = ""


class UtteranceIntent(Intent):
    intent_type: Literal[IntentType.SPEAK] = IntentType.SPEAK
    claim: Claim
    exact_text: str = ""
    volume: float = Field(default=0.7, ge=0.0, le=1.0)


class StartConversationIntent(Intent):
    intent_type: Literal[IntentType.START_CONVERSATION] = IntentType.START_CONVERSATION
    participants: list[str] = Field(default_factory=list)


class FormClaimIntent(Intent):
    intent_type: Literal[IntentType.FORM_CLAIM] = IntentType.FORM_CLAIM
    claim: Claim


class BeliefUpdateIntent(Intent):
    intent_type: Literal[IntentType.UPDATE_BELIEF] = IntentType.UPDATE_BELIEF
    belief: Belief


class AppraisalIntent(Intent):
    intent_type: Literal[IntentType.APPRAISE] = IntentType.APPRAISE
    appraisal: SemanticAppraisal


class SceneSummary(BaseModel):
    scene_id: int
    summary: str
    key_claim_ids: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
