from __future__ import annotations

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
        llm=ReplayLLM(llm_log) if snapshot.llm_enabled else None,
        tick_minutes=snapshot.show_config.tick_minutes,
        influence_per_tick=snapshot.show_config.influence_per_tick,
        show_journal=snapshot.show_journal,
    )
    from glasshouse.scenes.models import SceneStatus

    engine.drama_scores = [s.model_copy(deep=True) for s in snapshot.drama_scores]
    for scene in snapshot.scenes:
        engine.scene_manager.scenes[scene.id] = scene.model_copy(deep=True)
        if scene.status == SceneStatus.ACTIVE:
            engine.scene_manager._active_scene_by_location[scene.location] = scene.id
    engine.scene_manager._next_id = max(engine.scene_manager.scenes, default=0) + 1
    for tick, priority, event in snapshot.pending_world:
        engine.event_queue.enqueue_world(event.model_copy(deep=True), tick=tick, priority=priority)
    for _ in range(ticks):
        engine.tick()
    return engine
