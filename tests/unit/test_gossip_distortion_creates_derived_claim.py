from glasshouse.cognition.claims import Claim, ClaimPredicate, derive_claim


def test_gossip_distortion_creates_new_claim():
    source = Claim(
        subject="max",
        predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID,
        holder_id="lea",
        evidence_ids=["k1"],
    )
    distorted = derive_claim(
        source,
        ClaimPredicate.UNRELIABLE_WITH_MONEY,
        speaker_id="lea",
        tick=10,
        distortion_type="imprecision",
        holder_id="lea",
        evidence_ids=["k2"],
    )
    assert distorted.id != source.id
    assert distorted.provenance is not None
    assert distorted.provenance.source_claim_id == source.id
    assert distorted.predicate == ClaimPredicate.UNRELIABLE_WITH_MONEY
