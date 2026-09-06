from __future__ import annotations

from pydantic import BaseModel, Field

from glasshouse.agents.state import AgentState
from glasshouse.simulation.drama import DramaScore
from glasshouse.world.models import WorldState


class SimulationSnapshot(BaseModel):
    tick: int
    sim_time: str
    seed: int
    world: WorldState
    agents: dict[str, AgentState] = Field(default_factory=dict)
    drama_scores: list[DramaScore] = Field(default_factory=list)
