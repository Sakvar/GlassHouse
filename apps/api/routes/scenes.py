from __future__ import annotations

from fastapi import APIRouter

from apps.api.state import get_engine

router = APIRouter()


@router.get("/active")
def get_active_scenes() -> list:
    engine = get_engine()
    return [s.model_dump() for s in engine.scene_manager.active_scenes()]
