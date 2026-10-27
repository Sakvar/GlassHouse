from __future__ import annotations

from pydantic import BaseModel, Field

from glasshouse.agents.models import (
    AvariceProfile,
    CurrentState,
    Goals,
    Needs,
    Personality,
    ReputationState,
    SecretFact,
    SocialBoundaries,
    ViewerRelation,
)
from glasshouse.cognition.beliefs import BeliefStore
from glasshouse.cognition.claims import ClaimStore
from glasshouse.cognition.perception import KnowledgeStore
from glasshouse.memory.stores import MemoryStore
from glasshouse.relationships.models import RelationshipVector
from glasshouse.world.models import AgentRef


class AgentState(BaseModel):
    id: str
    name: str
    personality: Personality = Field(default_factory=Personality)
    avarice: AvariceProfile = Field(default_factory=AvariceProfile)
    reputation: ReputationState = Field(default_factory=ReputationState)
    viewer_relations: dict[str, ViewerRelation] = Field(default_factory=dict)
    offer_cooldowns: dict[str, int] = Field(default_factory=dict)
    needs: Needs = Field(default_factory=Needs)
    goals: Goals = Field(default_factory=Goals)
    secrets: tuple[SecretFact, ...] = ()
    boundaries: SocialBoundaries = Field(default_factory=SocialBoundaries)
    current: CurrentState = Field(default_factory=CurrentState)
    ref: AgentRef
    relationships: dict[str, RelationshipVector] = Field(default_factory=dict)
    knowledge: KnowledgeStore = Field(default_factory=KnowledgeStore)
    claims: ClaimStore = Field(default_factory=ClaimStore)
    beliefs: BeliefStore = Field(default_factory=BeliefStore)
    memory: MemoryStore = Field(default_factory=MemoryStore)

    def get_relationship(self, other_id: str) -> RelationshipVector:
        return self.relationships.get(other_id, RelationshipVector())
