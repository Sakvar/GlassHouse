from __future__ import annotations

from pydantic import BaseModel, Field

from glasshouse.cognition.perception import KnowledgeEntry


class CognitionTrigger(BaseModel):
    agent_id: str
    trigger_type: str
    tick: int
    priority: int = 50
    context: dict = Field(default_factory=dict)
    knowledge_entry: KnowledgeEntry | None = None


TRIGGER_PRIORITIES = {
    "truth_admission": 10,
    "overheard": 20,
    "agent_entered": 30,
    "scene_turn": 40,
    "need_critical": 50,
    "goal_active": 60,
}
