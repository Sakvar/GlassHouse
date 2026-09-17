from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class ClaimPredicate(StrEnum):
    BORROWED_MONEY_UNREPAID = "borrowed_money_unrepaid"
    UNRELIABLE_WITH_MONEY = "unreliable_with_money"
    HAS_MONEY_PROBLEMS = "has_money_problems"
    DISLIKES = "dislikes"
    START_CONVERSATION = "start_conversation"


class ClaimProvenance(BaseModel):
    source_claim_id: str
    distortion_type: str
    speaker_id: str
    tick: int


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    predicate: ClaimPredicate
    object: str | None = None
    polarity: float = Field(default=0.0, ge=-1.0, le=1.0)
    specificity: float = Field(default=1.0, ge=0.0, le=1.0)
    speaker_id: str | None = None
    holder_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: ClaimProvenance | None = None


class ClaimStore(BaseModel):
    entries: dict[str, Claim] = Field(default_factory=dict)

    def add(self, claim: Claim) -> Claim:
        self.entries[claim.id] = claim
        return claim

    def get(self, claim_id: str) -> Claim | None:
        return self.entries.get(claim_id)

    def by_predicate(self, predicate: ClaimPredicate) -> list[Claim]:
        return [c for c in self.entries.values() if c.predicate == predicate]

    def by_holder(self, holder_id: str) -> list[Claim]:
        return [c for c in self.entries.values() if c.holder_id == holder_id]


def derive_claim(
    source: Claim,
    predicate: ClaimPredicate,
    speaker_id: str,
    tick: int,
    distortion_type: str,
    holder_id: str,
    evidence_ids: list[str],
    specificity: float | None = None,
    object: str | None = None,
) -> Claim:
    return Claim(
        subject=source.subject,
        predicate=predicate,
        object=object or source.object,
        polarity=source.polarity,
        specificity=specificity if specificity is not None else max(0.2, source.specificity - 0.2),
        speaker_id=speaker_id,
        holder_id=holder_id,
        evidence_ids=evidence_ids,
        provenance=ClaimProvenance(
            source_claim_id=source.id,
            distortion_type=distortion_type,
            speaker_id=speaker_id,
            tick=tick,
        ),
    )


def claim_chain(claims: dict[str, Claim], claim_id: str) -> list[Claim]:
    chain: list[Claim] = []
    current_id: str | None = claim_id
    while current_id:
        claim = claims.get(current_id)
        if not claim:
            break
        chain.append(claim)
        current_id = claim.provenance.source_claim_id if claim.provenance else None
    return chain
