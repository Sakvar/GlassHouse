from __future__ import annotations

from glasshouse.agents.models import CurrentState, Goals, Needs, Personality
from glasshouse.cognition.beliefs import Belief, BeliefStore
from glasshouse.cognition.claims import Claim, ClaimStore
from glasshouse.cognition.perception import KnowledgeEntry, KnowledgeStore
from glasshouse.memory.stores import MemoryStore
from glasshouse.relationships.models import RelationshipVector
from glasshouse.world.models import Activity, AgentRef
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    id: str
    name: str
    personality: Personality = Field(default_factory=Personality)
    needs: Needs = Field(default_factory=Needs)
    goals: Goals = Field(default_factory=Goals)
    current: CurrentState = Field(default_factory=CurrentState)
    ref: AgentRef
    relationships: dict[str, RelationshipVector] = Field(default_factory=dict)
    knowledge: KnowledgeStore = Field(default_factory=KnowledgeStore)
    claims: ClaimStore = Field(default_factory=ClaimStore)
    beliefs: BeliefStore = Field(default_factory=BeliefStore)
    memory: MemoryStore = Field(default_factory=MemoryStore)

    def get_relationship(self, other_id: str) -> RelationshipVector:
        return self.relationships.get(other_id, RelationshipVector())
