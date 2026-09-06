from __future__ import annotations

from glasshouse.simulation.engine import SimulationEngine

_engine: SimulationEngine | None = None


def get_engine() -> SimulationEngine:
    global _engine
    if _engine is None:
        _engine = SimulationEngine(seed=42)
    return _engine


def set_engine(engine: SimulationEngine) -> None:
    global _engine
    _engine = engine
