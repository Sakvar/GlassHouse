from __future__ import annotations

from glasshouse.agents.state import AgentState
from glasshouse.llm.stub import ReplayLLM
from glasshouse.simulation.engine import SimulationEngine
from glasshouse.simulation.snapshot import SimulationSnapshot


def replay_from(
    snapshot: SimulationSnapshot,
    llm_log: list[dict],
    ticks: int = 1,
) -> SimulationEngine:
    engine = SimulationEngine(
        world=snapshot.world.model_copy(deep=True),
        agents={k: v.model_copy(deep=True) for k, v in snapshot.agents.items()},
        seed=snapshot.seed,
        llm=ReplayLLM(llm_log),
    )
    for _ in range(ticks):
        engine.tick()
    return engine
