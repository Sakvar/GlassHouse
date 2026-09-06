from glasshouse.simulation.engine import SimulationEngine


def test_tick_advances_time():
    engine = SimulationEngine(seed=42)
    assert engine.world.tick == 0
    engine.tick()
    assert engine.world.tick == 1
    assert "T" in engine.world.sim_time
