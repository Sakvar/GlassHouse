from __future__ import annotations

from glasshouse.agents.models import Personality
from glasshouse.relationships.models import RelationshipVector, SemanticAppraisal

_SHIFT_MAP: dict[str, float] = {
    "strongly_negative": -20.0,
    "negative": -10.0,
    "neutral": 0.0,
    "positive": 10.0,
    "strongly_positive": 20.0,
}


def _apply_shift(current: float, shift: str, multiplier: float = 1.0) -> float:
    delta = _SHIFT_MAP.get(shift, 0.0) * multiplier
    return max(-100.0, min(100.0, current + delta))


def apply_appraisal(
    vector: RelationshipVector,
    appraisal: SemanticAppraisal,
    personality: Personality,
) -> RelationshipVector:
    jealousy_mult = 1.0 + personality.jealousy * 0.5
    impulsivity_mult = 1.0 + personality.impulsivity * 0.3

    trust_mult = jealousy_mult if appraisal.trust_shift in ("negative", "strongly_negative") else 1.0
    resentment_mult = impulsivity_mult if appraisal.resentment_shift in (
        "positive",
        "strongly_positive",
    ) else 1.0

    return RelationshipVector(
        affinity=_apply_shift(vector.affinity, appraisal.affinity_shift),
        trust=_apply_shift(vector.trust, appraisal.trust_shift, trust_mult),
        attraction=vector.attraction,
        respect=_apply_shift(vector.respect, appraisal.respect_shift),
        resentment=_apply_shift(vector.resentment, appraisal.resentment_shift, resentment_mult),
        fear=vector.fear,
        dependency=vector.dependency,
    ).clamp()
