from glasshouse.agents.seeds import create_seed_agents
from glasshouse.cognition.claims import Claim, ClaimPredicate, derive_claim
from glasshouse.simulation.drama import score_drama
from glasshouse.world.house import create_initial_world


def test_drama_detects_gossip_chain():
    agents = create_seed_agents()
    world = create_initial_world()
    root = Claim(subject="max", predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID, holder_id="lea")
    agents["lea"].claims.add(root)
    derived = derive_claim(
        root,
        ClaimPredicate.UNRELIABLE_WITH_MONEY,
        speaker_id="lea",
        tick=5,
        distortion_type="imprecision",
        holder_id="eva",
        evidence_ids=["k1"],
    )
    agents["eva"].claims.add(derived)
    scores = score_drama(agents, world)
    gossip_scores = [s for s in scores if "gossip_chain" in s.factors]
    assert len(gossip_scores) >= 1
