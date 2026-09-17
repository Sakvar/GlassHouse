from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from apps.api.state import get_engine
from glasshouse.show.models import (
    PublicSeason,
    PublicTimeline,
    ShowEvent,
    StoryGoal,
    ViewerVote,
)

router = APIRouter()


@router.get("/season", response_model=PublicSeason)
def season() -> PublicSeason:
    engine = get_engine()
    with engine.lock:
        return engine.show.public_state()


@router.get("/timeline", response_model=PublicTimeline)
def timeline(
    from_tick: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
) -> PublicTimeline:
    engine = get_engine()
    with engine.lock:
        return engine.show.timeline(from_tick, limit)


@router.get("/goals", response_model=list[StoryGoal])
def goals() -> list[StoryGoal]:
    engine = get_engine()
    with engine.lock:
        return list(engine.show.active_goals())


@router.post("/votes", response_model=ShowEvent, status_code=201)
def vote(vote: ViewerVote) -> ShowEvent:
    try:
        return get_engine().show.vote(vote)
    except KeyError:
        raise HTTPException(404, "Сюжетная цель не найдена") from None
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


class TickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticks: int = Field(default=1, ge=1, le=100, strict=True)


@router.post("/dev/ticks", response_model=PublicSeason)
def ticks(request: TickRequest) -> PublicSeason:
    engine = get_engine()
    with engine.lock:
        for _ in range(request.ticks):
            engine.tick()
        return engine.show.public_state()
