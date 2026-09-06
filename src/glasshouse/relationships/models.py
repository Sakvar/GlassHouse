from __future__ import annotations

from pydantic import BaseModel, Field


class RelationshipVector(BaseModel):
    affinity: float = Field(default=0.0, ge=-100.0, le=100.0)
    trust: float = Field(default=0.0, ge=-100.0, le=100.0)
    attraction: float = Field(default=0.0, ge=-100.0, le=100.0)
    respect: float = Field(default=0.0, ge=-100.0, le=100.0)
    resentment: float = Field(default=0.0, ge=-100.0, le=100.0)
    fear: float = Field(default=0.0, ge=-100.0, le=100.0)
    dependency: float = Field(default=0.0, ge=-100.0, le=100.0)

    def clamp(self) -> RelationshipVector:
        return RelationshipVector(
            affinity=max(-100, min(100, self.affinity)),
            trust=max(-100, min(100, self.trust)),
            attraction=max(-100, min(100, self.attraction)),
            respect=max(-100, min(100, self.respect)),
            resentment=max(-100, min(100, self.resentment)),
            fear=max(-100, min(100, self.fear)),
            dependency=max(-100, min(100, self.dependency)),
        )


ShiftLevel = str  # strongly_negative | negative | neutral | positive | strongly_positive


class SemanticAppraisal(BaseModel):
    target_id: str
    trust_shift: ShiftLevel = "neutral"
    respect_shift: ShiftLevel = "neutral"
    resentment_shift: ShiftLevel = "neutral"
    affinity_shift: ShiftLevel = "neutral"
    rationale: str = ""
