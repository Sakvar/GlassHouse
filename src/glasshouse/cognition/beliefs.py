from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from glasshouse.cognition.claims import ClaimPredicate


class Belief(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    predicate: ClaimPredicate
    object: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = "direct"
    evidence_ids: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)


class BeliefStore(BaseModel):
    entries: dict[str, Belief] = Field(default_factory=dict)

    def add(self, belief: Belief) -> Belief:
        self.entries[belief.id] = belief
        return belief

    def get(self, belief_id: str) -> Belief | None:
        return self.entries.get(belief_id)

    def by_predicate(self, predicate: ClaimPredicate) -> list[Belief]:
        return [b for b in self.entries.values() if b.predicate == predicate]

    def about_subject(self, subject: str) -> list[Belief]:
        return [b for b in self.entries.values() if b.subject == subject]
