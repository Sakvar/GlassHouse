from __future__ import annotations

from threading import RLock

from glasshouse.simulation.engine import SimulationEngine

_state_lock = RLock()

_engine: SimulationEngine | None = None


def get_engine() -> SimulationEngine:
    global _engine
    with _state_lock:
        if _engine is None:
            _engine = SimulationEngine(seed=42)
        return _engine


def set_engine(engine: SimulationEngine) -> None:
    global _engine
    with _state_lock:
        _engine = engine
