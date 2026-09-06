from __future__ import annotations

from fastapi import FastAPI

from apps.api.routes import agents, claims, drama, events, scenes, sim

app = FastAPI(title="Glasshouse Debug API", version="0.1.0")

app.include_router(sim.router, prefix="/sim", tags=["sim"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(claims.router, prefix="/claims", tags=["claims"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(drama.router, prefix="/drama", tags=["drama"])
app.include_router(scenes.router, prefix="/scenes", tags=["scenes"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
