from __future__ import annotations

from fastapi import APIRouter

from apps.api.state import get_engine

router = APIRouter()


@router.get("/state")
def get_state() -> dict:
    engine = get_engine()
    return {
        "tick": engine.world.tick,
        "sim_time": engine.world.sim_time,
        "locations": list(engine.world.locations.keys()),
        "agents": {
            aid: {"location": ref.location_id, "activity": ref.activity.value}
            for aid, ref in engine.world.agents.items()
        },
        "event_count": len(engine.world.events_log),
    }


@router.post("/run")
def run_sim(hours: float = 1.0, seed: int = 42) -> dict:
    from glasshouse.simulation.engine import SimulationEngine

    engine = SimulationEngine(seed=seed)
    engine.run(hours=hours)
    from apps.api.state import set_engine

    set_engine(engine)
    return {"ticks": engine.world.tick, "events": len(engine.world.events_log)}
