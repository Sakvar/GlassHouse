from glasshouse.llm.logging import LLMCallLogger
from glasshouse.simulation.engine import SimulationEngine
from glasshouse.simulation.replay import replay_from


def test_replay_determinism():
    logger = LLMCallLogger()
    engine1 = SimulationEngine(seed=99)
    snap1 = engine1.snapshot()
    log = logger.to_dicts()

    engine2 = replay_from(snap1, log, ticks=0)
    assert engine2.world.tick == engine1.world.tick
    assert engine2.seed == engine1.seed
