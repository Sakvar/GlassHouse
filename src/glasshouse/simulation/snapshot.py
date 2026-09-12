from __future__ import annotations

from pydantic import BaseModel, Field

from glasshouse.agents.state import AgentState
from glasshouse.scenes.models import Scene
from glasshouse.show.models import ShowConfig, ShowEvent
from glasshouse.simulation.drama import DramaScore
from glasshouse.world.models import WorldEvent, WorldState


class SimulationSnapshot(BaseModel):
    tick: int
    sim_time: str
    seed: int
    world: WorldState
    agents: dict[str, AgentState] = Field(default_factory=dict)
    drama_scores: list[DramaScore] = Field(default_factory=list)
    show_config: ShowConfig = Field(default_factory=ShowConfig)
    show_journal: tuple[ShowEvent, ...] = ()
    llm_enabled: bool = False
    scenes: list[Scene] = Field(default_factory=list)
    pending_world: list[tuple[int, int, WorldEvent]] = Field(default_factory=list)
