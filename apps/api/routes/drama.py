from __future__ import annotations

from fastapi import APIRouter

from apps.api.state import get_engine

router = APIRouter()


@router.get("")
def get_drama() -> list:
    engine = get_engine()
    return [s.model_dump() for s in engine.drama_scores]
