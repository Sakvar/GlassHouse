from glasshouse.agents.models import Personality
from glasshouse.cognition.beliefs import Belief
from glasshouse.cognition.claims import ClaimPredicate
from glasshouse.cognition.invariants import belief_has_evidence
from glasshouse.relationships.appraisal_rules import apply_appraisal
from glasshouse.relationships.models import RelationshipVector, SemanticAppraisal


def test_belief_requires_evidence():
    good = Belief(
        subject="max",
        predicate=ClaimPredicate.UNRELIABLE_WITH_MONEY,
        evidence_ids=["k1"],
        supporting_claim_ids=["c1"],
    )
    bad = Belief(subject="max", predicate=ClaimPredicate.UNRELIABLE_WITH_MONEY)
    assert belief_has_evidence(good)
    assert not belief_has_evidence(bad)


def test_appraisal_reduces_trust():
    vector = RelationshipVector(trust=73)
    appraisal = SemanticAppraisal(target_id="max", trust_shift="negative")
    personality = Personality(jealousy=0.8)
    updated = apply_appraisal(vector, appraisal, personality)
    assert updated.trust < 73
