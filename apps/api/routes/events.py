from __future__ import annotations

from fastapi import APIRouter

from apps.api.state import get_engine

router = APIRouter()


@router.get("")
def get_events(from_tick: int = 0, to_tick: int | None = None) -> list:
    engine = get_engine()
    events = engine.world.events_log
    if to_tick is not None:
        events = [e for e in events if from_tick <= e.tick <= to_tick]
    else:
        events = [e for e in events if e.tick >= from_tick]
    return [e.model_dump() for e in events]
