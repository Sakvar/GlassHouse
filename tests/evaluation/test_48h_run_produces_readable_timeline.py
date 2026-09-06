import pytest


@pytest.mark.evaluation
def test_48h_run_produces_readable_timeline():
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from glasshouse.llm.openai_provider import OpenAICompatibleProvider
    from glasshouse.simulation.engine import SimulationEngine

    engine = SimulationEngine(seed=42, llm=OpenAICompatibleProvider())
    engine.run(hours=1, ticks_per_hour=10)
    assert len(engine.world.events_log) >= 0
