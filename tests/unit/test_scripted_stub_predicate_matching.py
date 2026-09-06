from glasshouse.cognition.claims import ClaimPredicate
from glasshouse.llm.provider import LLMCallContext
from glasshouse.llm.schemas import FormClaimIntent
from glasshouse.cognition.claims import Claim
from glasshouse.llm.stub import ScriptedStubLLM, UnexpectedLLMCallError


def match_lea_form_claim(ctx, schema):
    return (
        ctx.agent_id == "lea"
        and schema == FormClaimIntent
        and ClaimPredicate.BORROWED_MONEY_UNREPAID.value in ctx.predicates
    )


def test_predicate_based_stub_matching():
    claim = Claim(subject="max", predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID)
    stub = ScriptedStubLLM([
        (match_lea_form_claim, FormClaimIntent(claim=claim)),
    ])
    ctx = LLMCallContext(
        agent_id="lea",
        trigger_type="overheard",
        schema_name="FormClaimIntent",
        predicates=[ClaimPredicate.BORROWED_MONEY_UNREPAID.value],
    )
    result = stub.generate_structured(ctx, FormClaimIntent, None)
    assert result.claim.predicate == ClaimPredicate.BORROWED_MONEY_UNREPAID


def test_unexpected_call_raises():
    stub = ScriptedStubLLM([])
    ctx = LLMCallContext(agent_id="max", trigger_type="x", schema_name="Intent")
    try:
        stub.generate_structured(ctx, FormClaimIntent, None)
        assert False
    except UnexpectedLLMCallError as e:
        assert "max" in str(e)
