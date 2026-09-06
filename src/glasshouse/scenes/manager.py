from __future__ import annotations

from glasshouse.llm.provider import LLMCallContext, ModelTier
from glasshouse.llm.schemas import SceneSummary
from glasshouse.memory.stores import EpisodicMemory
from glasshouse.scenes.models import Scene, SceneStatus, SemanticChange
from glasshouse.world.models import WorldState


class SceneManager:
    IDLE_COLLAPSE_THRESHOLD = 3

    def __init__(self) -> None:
        self.scenes: dict[int, Scene] = {}
        self._next_id = 1
        self._active_scene_by_location: dict[str, int] = {}

    def start_scene(
        self,
        location: str,
        participants: list[str],
        observers: list[str],
        sim_time: str,
        topic: str | None = None,
    ) -> Scene:
        scene_id = self._next_id
        self._next_id += 1
        scene = Scene(
            id=scene_id,
            location=location,
            participants=participants,
            observers=observers,
            topic=topic,
            started_at=sim_time,
        )
        self.scenes[scene_id] = scene
        self._active_scene_by_location[location] = scene_id
        return scene

    def get_active_at(self, location: str) -> Scene | None:
        scene_id = self._active_scene_by_location.get(location)
        if scene_id is None:
            return None
        scene = self.scenes.get(scene_id)
        if scene and scene.status == SceneStatus.ACTIVE:
            return scene
        return None

    def record_utterance(self, scene_id: int, event_id: str) -> None:
        scene = self.scenes[scene_id]
        scene.utterance_event_ids.append(event_id)

    def advance_turn(
        self,
        scene_id: int,
        semantic_change: SemanticChange,
        knowledge_only: bool = False,
    ) -> bool:
        scene = self.scenes[scene_id]
        if knowledge_only or not semantic_change.is_meaningful():
            scene.idle_turns += 1
        else:
            scene.idle_turns = 0
            if semantic_change.topic_changed:
                pass
            if semantic_change.tension_changed:
                pass
        scene.current_turn_index += 1
        return scene.idle_turns >= self.IDLE_COLLAPSE_THRESHOLD

    def collapse_scene(
        self,
        scene_id: int,
        summary: SceneSummary,
        tick: int,
    ) -> EpisodicMemory:
        scene = self.scenes[scene_id]
        scene.status = SceneStatus.COLLAPSED
        if scene.location in self._active_scene_by_location:
            del self._active_scene_by_location[scene.location]
        return EpisodicMemory(
            id=f"ep_{scene_id}_{tick}",
            tick=tick,
            summary=summary.summary,
            event_ids=list(scene.utterance_event_ids),
            claim_ids=summary.key_claim_ids,
            subject=summary.participants[0] if summary.participants else None,
            salience=0.7,
        )

    def active_scenes(self) -> list[Scene]:
        return [s for s in self.scenes.values() if s.status == SceneStatus.ACTIVE]
