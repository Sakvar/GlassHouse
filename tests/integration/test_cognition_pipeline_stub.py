from glasshouse.cognition.claims import ClaimPredicate
from glasshouse.llm.provider import LLMCallContext
from glasshouse.llm.schemas import FormClaimIntent
from glasshouse.llm.stub import ScriptedStubLLM
from glasshouse.agents.seeds import create_seed_agents
from glasshouse.cognition.pipeline import run_cognition
from glasshouse.cognition.triggers import CognitionTrigger
from glasshouse.cognition.claims import Claim


def test_cognition_pipeline_with_stub():
    agents = create_seed_agents()
    agent = agents["lea"]
    claim = Claim(subject="max", predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID)

    def matcher(ctx, schema):
        return ctx.agent_id == "lea" and schema == FormClaimIntent

    stub = ScriptedStubLLM([(matcher, FormClaimIntent(claim=claim))])
    trigger = CognitionTrigger(
        agent_id="lea",
        trigger_type="overheard",
        tick=1,
        context={"predicates": [ClaimPredicate.BORROWED_MONEY_UNREPAID.value]},
    )
    result = run_cognition(agent, trigger, stub, FormClaimIntent, {})
    assert result is not None
    assert result.claim.predicate == ClaimPredicate.BORROWED_MONEY_UNREPAID
