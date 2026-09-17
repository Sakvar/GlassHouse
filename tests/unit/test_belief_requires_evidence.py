from glasshouse.cognition.beliefs import Belief
from glasshouse.cognition.claims import ClaimPredicate
from glasshouse.cognition.invariants import belief_has_evidence


def test_belief_requires_evidence_and_claims():
    b = Belief(
        subject="eva",
        predicate=ClaimPredicate.DISLIKES,
        object="dan",
        evidence_ids=["e1"],
        supporting_claim_ids=["c1"],
    )
    assert belief_has_evidence(b)
