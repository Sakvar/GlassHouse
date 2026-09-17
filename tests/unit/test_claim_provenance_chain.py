from glasshouse.cognition.claims import Claim, ClaimPredicate, claim_chain, derive_claim


def test_provenance_chain():
    root = Claim(subject="max", predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID, holder_id="lea")
    derived = derive_claim(
        root,
        ClaimPredicate.UNRELIABLE_WITH_MONEY,
        speaker_id="lea",
        tick=5,
        distortion_type="imprecision",
        holder_id="eva",
        evidence_ids=["k1"],
        specificity=0.5,
    )
    claims = {root.id: root, derived.id: derived}
    chain = claim_chain(claims, derived.id)
    assert len(chain) == 2
    assert chain[0].predicate == ClaimPredicate.UNRELIABLE_WITH_MONEY
    assert chain[1].predicate == ClaimPredicate.BORROWED_MONEY_UNREPAID
