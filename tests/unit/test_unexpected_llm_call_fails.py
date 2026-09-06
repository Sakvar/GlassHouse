from glasshouse.llm.provider import LLMCallContext
from glasshouse.llm.schemas import FormClaimIntent
from glasshouse.llm.stub import ScriptedStubLLM, UnexpectedLLMCallError


def test_unexpected_llm_call_fails_with_diagnostic():
    stub = ScriptedStubLLM([])
    ctx = LLMCallContext(
        agent_id="eva",
        trigger_type="scene_turn",
        schema_name="FormClaimIntent",
        predicates=["unreliable_with_money"],
        target_id="dan",
    )
    try:
        stub.generate_structured(ctx, FormClaimIntent, None)
        assert False, "Expected UnexpectedLLMCallError"
    except UnexpectedLLMCallError as exc:
        assert exc.context.agent_id == "eva"
        assert "unreliable_with_money" in str(exc)
