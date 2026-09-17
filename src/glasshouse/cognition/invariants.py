from __future__ import annotations

from typing import TYPE_CHECKING

from glasshouse.cognition.beliefs import Belief
from glasshouse.cognition.claims import Claim, ClaimPredicate, claim_chain

if TYPE_CHECKING:
    from glasshouse.agents.state import AgentState


def agent_has_knowledge_of_event(agent: AgentState, event_id: str) -> bool:
    return any(e.event_id == event_id for e in agent.knowledge.entries.values())


def belief_has_evidence(belief: Belief) -> bool:
    return len(belief.evidence_ids) > 0 and len(belief.supporting_claim_ids) > 0


def claim_chain_root(claims: dict[str, Claim], claim_id: str) -> list[Claim]:
    return claim_chain(claims, claim_id)


def no_magical_knowledge(agent: AgentState, predicate: ClaimPredicate) -> bool:
    for belief in agent.beliefs.entries.values():
        if belief.predicate != predicate:
            continue
        for eid in belief.evidence_ids:
            if eid not in agent.knowledge.entries:
                return False
    return True


def agent_knows_claim_via_knowledge(agent: AgentState, claim: Claim) -> bool:
    for evidence_id in claim.evidence_ids:
        if evidence_id in agent.knowledge.entries:
            return True
    return False
