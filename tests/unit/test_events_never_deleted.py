from glasshouse.cognition.claims import Claim, ClaimPredicate
from glasshouse.simulation.engine import SimulationEngine


def test_events_never_deleted():
    engine = SimulationEngine(seed=42)
    claim = Claim(subject="max", predicate=ClaimPredicate.BORROWED_MONEY_UNREPAID)
    event = engine.emit_truth_admission("max", claim, volume=0.5)
    initial_count = len(engine.world.events_log)
    engine.tick()
    assert len(engine.world.events_log) >= initial_count
    assert any(e.id == event.id for e in engine.world.events_log)
