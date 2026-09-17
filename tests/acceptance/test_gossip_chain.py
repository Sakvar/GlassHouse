"""Acceptance test: secret → distortion → relationship change, no magical knowledge."""

from glasshouse.cognition.claims import ClaimPredicate
from glasshouse.cognition.invariants import (
    agent_has_knowledge_of_event,
    belief_has_evidence,
    claim_chain_root,
    no_magical_knowledge,
)
from tests.acceptance.gossip_scenario import run_gossip_scenario


def test_gossip_chain_full_pipeline():
    engine, stub, starting_trust, truth_event = run_gossip_scenario()
    agents = engine.agents

    lea = agents["lea"]
    eva = agents["eva"]
    dan = agents["dan"]
    max_agent = agents["max"]

    assert agent_has_knowledge_of_event(lea, truth_event.id)
    lea_claims = lea.claims.by_predicate(ClaimPredicate.BORROWED_MONEY_UNREPAID)
    assert len(lea_claims) >= 1
    assert lea_claims[0].evidence_ids

    eva_unreliable = eva.claims.by_predicate(ClaimPredicate.UNRELIABLE_WITH_MONEY)
    eva_money = eva.claims.by_predicate(ClaimPredicate.HAS_MONEY_PROBLEMS)
    assert len(eva_unreliable) >= 1 or len(eva_money) >= 1

    all_claims = {}
    for a in agents.values():
        all_claims.update(a.claims.entries)
    if eva_money:
        chain = claim_chain_root(all_claims, eva_money[0].id)
        assert len(chain) >= 1

    for kid in max_agent.knowledge.entries.values():
        assert "dan knows" not in kid.sensory_content.snippet.lower()

    dan_trust = dan.get_relationship("max").trust
    assert dan_trust < starting_trust

    dan_knowledge_texts = [
        k.sensory_content.snippet for k in dan.knowledge.entries.values()
    ]
    for text in dan_knowledge_texts:
        assert "unreliable with money" not in text.lower()

    for agent in agents.values():
        for belief in agent.beliefs.entries.values():
            if belief.predicate in (
                ClaimPredicate.HAS_MONEY_PROBLEMS,
                ClaimPredicate.UNRELIABLE_WITH_MONEY,
            ):
                assert belief_has_evidence(belief) or belief.supporting_claim_ids

    assert no_magical_knowledge(max_agent, ClaimPredicate.HAS_MONEY_PROBLEMS)

    event_types = [e.type.value for e in engine.world.events_log]
    assert "truth_admission" in event_types
    assert "utterance" in event_types
